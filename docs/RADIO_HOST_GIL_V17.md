# RADIO: contención del host y perfiles nativos · 21/10/2026

No se considera resuelto el underrun ni se promueven tasas nuevas.

## Control sin muestreador externo

[Informe](../diagnosticos/resultados_v17/generador_radio_20261021_123627/report.json):
ADC8/1,6MHz, RADIO→A0/40kHz, FFT65536 y11 resintonías en120s. Sin cortes ni
pérdidas ADC; ventana100%expuesta,19,57Paint/s. Cola ADC pico7/8: **sin holgura**.
ACK máximo125,254ms; decode máximo144,697ms; reserva host mínima9225muestras
(230,625ms). Los máximos pertenecen al lifecycle instrumentado y no se suman
como si fueran un solo evento.

## Primer perfil: fallo bajo instrumentación, pilas de cierre

[RADIO](../diagnosticos/resultados_v17/generador_radio_20261021_124229/report.json) ·
[Muestreador](../diagnosticos/resultados_v17/radio_host_sample_20261021_124307/report.json).

Se ejecutó `sample` sobre el PID del diagnóstico propio,45s/20ms, con lectura
anticipada de símbolos (`-mayDie`). HuboUNDERRUN: played2208000muestras,
posición55,2s, accepted2208480; ADCdropped=fatal0, cola6. Había audio en el host
(mínimo7900muestras). La ventana permaneció100%visible. Este resultado está
**perturbado por el perfilador**, no reproduce condiciones equivalentes al
control ni identifica por sí mismo la causa natural del corte.

El perfil resultante contiene525observaciones del hilo principal, sin el
QThread receptor activo; predominan recepción durante restauración y cierre.
No usar ese árbol para atribuir las pausas de reproducción. La fuente del
muestreador anterior se conservó junto al informe.

## Segundo perfil: receptor activo

[RADIO](../diagnosticos/resultados_v17/generador_radio_20261021_124625/report.json) ·
[Muestreador](../diagnosticos/resultados_v17/radio_host_sample_20261021_124707/report.json) ·
[Recuento reproducible por hilo](../diagnosticos/resultados_v17/radio_host_sample_20261021_124707/review.json).

Se quitó la lectura anticipada de símbolos. El muestreo incluye reproducción
activa y el QThread receptor. En808de2125observaciones de ese hilo aparece
`take_gil`; el principal lo muestra en404de2125. Esto establece contención
observable del intérprete bajo esta carga. Son **ocurrencias de muestras de
pila**, no porcentajes de CPU ni una medición continua del tiempo de espera.
Las categorías `sock_recv` yGIL se solapan y no se suman.

La corrida completó120s y10resintonías sin cortes ni pérdidas, FFT100%visible
a18,94Paint/s; cola5. Read máximo103,943ms, decode116,933ms, ACK143,442ms.
Sigue siendo diagnóstico perturbado, sin aprobación de holgura. No demuestra
que el GIL sea la causa única del fallo de la otra corrida.

## Límites y siguiente trabajo

`OutputWorker._process_separately` ya envía sólo columnas necesarias y
`process_owned_result` ya devuelve únicamente resultados DSP/FILTER. No
reimplementar esa optimización ni suponer una devolución redundante de RF.

El siguiente bloque debe medir quién retiene el GIL y el coste de las copias
de entrada al proceso DSP, antes de elegir una modificación. Si se prueba
compartir memoria o compactar metadatos, hacerlo en una copia aislada con
slots acotados, generación/continuidad y datos originales preservados. No
liberar créditos por estimación ni repetir1ms/ReadyRead como corrección.

Todos los ensayos restauraron la configuración original ADC8/1,6MHz,
generadorOFF e identidad96685…;10s finales sin dropped/fatal. El perfilador
sólo inspecciona el proceso diagnóstico propio y no se conecta al Q.

## Coste IPC medido offline · 21/10

Nuevo diagnóstico: `diagnosticos/medir_ipc_radio_v17.py`. Usa el mismo
`ProcessingSettings`, `Configuration` y las tres columnas de entrada RADIO
actuales: CH1 float64, tiempo float64 e índice uint32. Mide serialización con
`ForkingPickler`, deserialización y viaje a un proceso `spawn` que devuelve
solamente una comprobación pequeña. No abre Qt ni accede al Q.

[Primera medición, 200 repeticiones por caso](../diagnosticos/resultados_v17/radio_ipc_20261021_130320/report.json):

| RF acumulada a 1,6 MS/s | Payload actual | CPU serialización mediana | Viaje mediano / p95 |
|---|---:|---:|---:|
| 20 ms / 32000 muestras | 641326 bytes | 0,317 ms | 1,184 / 2,288 ms |
| 40 ms / 64000 | 1281326 bytes | 0,787 ms | 3,001 / 5,242 ms |
| 80 ms / 128000 | 2561332 bytes | 2,160 ms | 11,137 / 19,968 ms |
| 160 ms / 256000 | 5121332 bytes | 5,504 ms | 33,612 / 53,590 ms |

La publicación intenta agrupar unos 20 ms, pero `flush` retiene más datos
cuando la presión de entrega alcanza cuatro. Los tamaños mayores son un
barrido sintético de ese mecanismo: **no son una distribución observada de
los bloques durante el fallo**. Debe medirse esa distribución antes de
atribuirle los cortes.

Como límite de coste, enviar sólo CH1 reduce el payload aproximadamente un
60%; el viaje mediano fue 0,574 ms para 20 ms de RF y 12,573 ms para 160 ms.
Ese payload es deliberadamente inválido para el DSP real: omite los datos
que hoy verifican continuidad y tiempos. **No incorporarlo**. La comparación
secuencial no constituye un A/B de aceptación; CPU de hilo tampoco equivale
a tiempo reteniendo el GIL. El viaje incluye planificación y transporte por
pipe, y excluye el cálculo DSP y la devolución de audio real.

El perfil nativo también contiene 38 observaciones en la rama exterior
`_pickle_Pickler_dump` del hilo feeder, sobre 2125 observaciones de ese hilo;
no sumar sus descendientes recursivos ni interpretarlo como porcentaje de
CPU. Hay un coste medible que crece con el lote, sin evidencia suficiente
para declararlo causa única.

Siguiente candidato: compactar únicamente metadatos regulares, en una copia
aislada, conservando validación de muestras originales, límites entre lotes,
wrap uint32 y generación; mantener los datos originales del padre para
historial/CSV. Antes de promoverlo: equivalencia y rechazo de discontinuidades,
distribución de tamaños real y comparación física visible sin perfilador.
No hubo cambios de reproducción ni de firmware en este bloque.

[Repetición de 100 casos por tamaño/variante con fuente y hash archivados](../diagnosticos/resultados_v17/radio_ipc_20261021_130349/report.json):
el viaje actual mediano fue 0,912 / 2,243 / 8,556 / 29,160 ms para
20 / 40 / 80 / 160 ms de RF. Confirma el crecimiento en este ensayo offline;
la variación entre corridas impide presentar un porcentaje fijo de mejora.

## Candidato aislado con reconstrucción exacta

Implementado en [experimentos/radio_ipc_compact_v17](../experimentos/radio_ipc_compact_v17/README.md),
sin imports desde producción. El descriptor sólo se usa si reconstruir
índices/tiempos produce exactamente los mismos bytes; cualquier anomalía
conserva el payload original y las validaciones DSP existentes. Seis pruebas
offline pasan incluyendo wrap, discontinuidades y equivalencia de audio.

El A/B alternado incluyendo compactación/reconstrucción mostró una regresión
pequeña con 32000 muestras y menor mediana con 128000/256000. Por eso el
umbral inicial fue 128000. En el control físico de 60 s y el ensayo de 120 s
ningún bloque alcanzó ese umbral: la segunda corrida **no ejercitó el codec**.

Un screening adicional con umbral experimental de 64000 sí compactó
39 bloques en 60 s, sin cortes/pérdidas y con FFT visible a 20,01 Paint/s.
La cola llegó a 5 y el ACK máximo a 112,16 ms: **no demuestra mejora de
holgura ni corrección del underrun**. Q restaurado exactamente, identidad
original y 10 s sin pérdidas. El candidato no se incorpora a producción.

El siguiente ensayo, objetivo120s con umbral64000, **falló UNDERRUN** en
posición69,192s tras62compactaciones. ADCsinpérdidas, cola5, FFT100%visible;
ACKmáximo305,07ms. El codec no resuelve el fallo; no hay atribución causal
del fallo al codec ni al GIL con esta evidencia. Restauración exacta e
identidad original,15994368muestras en10s finales sin pérdidas. Campaña
detenida sin incorporar el candidato. Ver el README del experimento y su
`failure_review.json` para la auditoría acotada del host. El siguiente foco
es la atención del transporte durante las pausas largas, no reducir más
metadatos sin una hipótesis medida.

## Ablación de actualización FFT · siguiente bloque

`experimentos/radio_ipc_compact_v17/render_probe.py` limita sólo las llamadas
de análisis/dibujo FFT del diagnóstico. No activa codec, cambia resolución,
descarta RF/audio ni modifica créditos. Bode/SINGLE quedan fuera del límite.

Tres ensayos con RADIO→A0/40kHz, ADC8/1,6MHz y FFT65536100%visible:

| Techo de llamadas FFT | Resultado | ACK máximo | Cola pico | Paint real |
|---|---|---:|---:|---:|
| 8Hz | pasa120s,11resintonías |57,58ms|6/8|14,42/s|
| 60Hz | pasa120s,10resintonías |59,14ms|4/8|19,76/s|
| sin límite adicional | UNDERRUN64,992s de audio |291,14ms|4/8|19,61/s|

El techo60Hz omitió2156llamadas cercanas y no es un control abierto; se
corrigió el diseño con techo0(sin límite), que ejecutó todas3065llamadas.
Paint no equivale a cálculo FFT: Qt repinta por otras causas y hay dospaneles.
Los dos ensayos exitosos no pasan el criterio cola<4. Ninguno promueve una
corrección ni una tasa nueva. El fallo del control **sin codec** confirma
persistencia en el camino original, pero no atribuye causalidad exclusiva.

[Fuentes, informes y comparación](../experimentos/radio_ipc_compact_v17/README.md).
Todas las corridas restauraron exactamente ADC8/1,6MHz/genOFF e identidad
96685…, con10s finales sin pérdidas. Sin procesos de ensayo activos.
Próximo: repetir8Hz frente aabierto en orden inverso con igual instrumentación,
antes de proponer refresco adaptativo. No usar estos tres casos para declarar
que bajar FPS resuelve el audio ni ampliar créditos por estimación.

## Repetición inversa completada

Dos nuevos120s en orden original→8Hz, sin codec y con igual instrumentación,
pasaron sin cortes/pérdidas y con FFT100%visible. Original: ACKmáximo86,71ms,
cola6,19,58Paint/s. Reducido: ACK46,32ms,cola5,14,41Paint/s. CPU acumulada en
el método render16,83→11,89s; ese29,3%es sólo del método en esta pareja y
no del monitor completo. Las resintonías fueron11/10, por temporización real.

[Informes y límites](../experimentos/radio_ipc_compact_v17/resultados/render_reverse_comparison_20261021.json).
Es una tendencia favorable con dos120s reducidos exitosos, no prueba causal
ni calificación de estabilidad. El original también puede pasar120s. Ambos
incumplen cola<4; no incorporar el techo fijo por estos resultados.

Restauración exacta ADC8/1,6MHz/genOFF,identidad96685…y10s15991776muestras
sin dropped/fatal en cada corrida. Próximo candidato aislado: reducir trabajo
visual sólo con RADIO→A0 y presión observada, medir cuándo se activa y cómo
recupera el refresco normal, sin alterar resolución/SINGLE/audio/créditos.


## Política adaptativa aislada: screening de 60 + 120 s

Implementada en `experimentos/radio_ipc_compact_v17/adaptive_refresh.py` y
opción `--adaptive-refresh` del runner. Sólo con RADIO→A0 y FFT live: limita
a 8 Hz ante tres lotes pendientes o un ACK de al menos 40 ms reciente; retira
el límite tras tres segundos sin presión. Detener A0, cambiar sesión, SINGLE
y otros modos desactivan el límite. No cambia audio, créditos, resolución ni
firmware. Cinco tests de política y seis del codec pasan; el codec no se
activa en estos ensayos.

60 y 120 s pasan audio/integridad, FFT 100% visible a 18,77/18,88 Paint/s.
La política se activó 3/5 veces y estuvo reducida 9,07/17,47 s durante los
lifecycle; probó señales de entrega y ACK, y recuperó estado normal. ACK
máximos 35,75/55,75 ms; colas 6/5: sigue sin holgura. CPU del método en 120 s:
16,83 s, igual al control anterior. No hay ahorro CPU demostrado.

[Informe estructurado](../experimentos/radio_ipc_compact_v17/resultados/adaptive_screening_20261021.json).
Sin cambios públicos. Q restaurado exactamente a ADC8/1,6 MHz, gen OFF,
identidad96685… y 10 s finales con 15991776 muestras sin pérdidas en cada
corrida. Ningún ensayo activo. No es una corrección de underrun validada.
Próximo: control con igual instrumentación y medir cálculo FFT efectivo antes
de ajustar umbrales; no confundir llamadas omitidas con trabajo costoso evitado.

## Comparación con cálculo efectivo y nuevo fallo

[Control/adaptativo120s+120s con contadores de etapas](../experimentos/radio_ipc_compact_v17/resultados/stage_comparison_20261021.json):
ambos pasan. CálculosFFT1232→1196,CPU del pipeline15,050→14,418s;
ACKmáximo31,07→71,28ms,cola5→6. El adaptativo no demuestra mejora de estabilidad;
no se incorpora. Un detalle posterior60s midió analyze completo4,254s CPU,
de los cuales1,974s correspondían aFFT; anotaciones0,524s. Son tiempos inclusivos.

Se preparó selección exacta top5 sin ordenar todos los picos: equivalencia
offline y17–19%menos mediana CPU de analyze en dos señales sintéticas. La
prueba física aislada **falló a33,036s de audio**, ACK242,36ms,ADCsinpérdidas y
cola3,FFT100%visible. No corrige el underrun y no se incorpora. Su primer
contador internoFFT quedó fuera por una referencia copiada: ese0 es inválido;
se corrigió el helper y se agregó test. La corrección posterior sólo tiene
evidencia offline. No reescribir los informes archivados de la versión anterior.

[Fuentes, pruebas y límites](../experimentos/radio_ipc_compact_v17/README.md).
Qrestauradoexacto8/1,6MHz/genOFF,identidad96685…y10s15991776muestras sin
pérdidas tras el fallo. Dieciséis tests pasan, diffcheck limpio; ningún ensayo
activo. Siguiente: atención al transporte/ACK en experimento separado;
colaADC3 no demuestra estabilidad A0. No liberar créditos estimados.

## ACK completo por RID y callbacks del receptor

Nuevo observador pasivo `wire_probe.py`, sin reordenar tramas ni generar
comandos. Correlaciona RID/sesión entre el recv que entregó el ACK completo y
su callback. Primera corrida120s pasa,12786ACKmatched,postrecv máximo27,45ms.
Una segunda corrida fallaUNDERRUN a9,36saudio conADCsinpérdidas/cola3: para el
mismo RID2874850373 midió212,599ms envío→recvcompleto y29,453ms
recvcompleto→callback,total242,052ms. La primera parte **no es latencia del
cable**: incluye atención al socket por el host, además de Q/relay/transporte.

Tercera corrida120s con spans de callbacks pasa: ACKmáslento66,696ms, de los
cuales65,900ms antes de recvcompleto y0,797ms después. La entrega de muestras
más lenta duró47,518ms con0,992ms CPU del receptor; los spans padres contienen
la misma pausa. Confirma pared dominante fuera de CPU propia, no GIL único.
Hubo227770callbacks de muestras en el lifecycle. FFT100%visible,cola6.

[Evidencia y limitaciones por versión](../experimentos/radio_ipc_compact_v17/resultados/wire_review_20261021.json).
Los observadores añaden coste y pueden perturbar; estas tres versiones no son
un A/B de corrección. Seis tests nuevos pasan. Todas restauraron configuración
original8/1,6MHz/genOFF,identidad96685…y10s finales sin pérdidas. Nada activo.

Siguiente candidato aislado: agrupar callbacks RF ya validados con presupuesto
acotado y flush de fronteras/configuración/cierre. Antes de Q: tests de orden,
wrap,cancelación y retención; no agrupar ACK ni modificar créditos. Todavía
no se implementó ni se atribuye corrección del underrun a esa hipótesis.

## Agrupación de callbacks implementada y probada

`coalesce_probe.py` y `sample_coalescer.py` implementan un candidato aislado
paraADC8/1,6MHz/RADIO→A0. El decoder/receptor siguen validando cada trama;
sólo agrupa entregas NativeRecords. Retención dura16000muestras/32partes,
plazo cooperativo10ms; flush antes de controles, cambios de contexto y cierre.
No cambia ACK/créditos, firmware, FFT ni el código de producción.

Screening60+120s pasa sin cortes/pérdidas:111052→8432 y222099→16980callbacks
en los periodos agrupados (~92%menos). No quedan muestras pendientes y las
salidas conservan el número de muestras. Edad máxima34,42/162,72ms: el plazo
cooperativo no garantiza latencia bajo bloqueo. Colas5en ambas,ACKmáximos
93,86/118,81ms. No hay aceptación de holgura ni corrección probada del underrun.

[Fuentes e informes](../experimentos/radio_ipc_compact_v17/README.md),
[resumen estructurado](../experimentos/radio_ipc_compact_v17/resultados/coalesce_screening_20261021.json).
Treinta y dos tests pasan, incluido rechazo RF con el receptor real y límites
de memoria/orden/cierre. Qrestauradoexacto8/1,6MHz/genOFF,identidad96685…,
últimos10s15991776muestras sin pérdidas. Nada activo, producción intacta.
Próximo: control emparejado independiente y correlacionar retenciones largas;
no promover con el supuesto de que10ms sea un límite absoluto.

## Control emparejado y repetición independiente del agrupador

[Pareja120s+120s](../experimentos/radio_ipc_compact_v17/resultados/coalesce_matched_20261021.json)
con hashes iguales: ambos pasan,FFT100%visible. CPU del callback de entrega
4,323→0,976s, pero pump inclusivo46,431→45,304s (~2,4%en esta pareja, no
ahorro global). ACK80,36→82,88ms,cola5→6: no mejora demostrada de transporte.
Retención máxima76,385ms se solapa con pump78,812ms/2,610msCPUhilo; pared
dominante fuera de CPU propia, sin atribución única al GIL.

[Otra repetición120s](../experimentos/radio_ipc_compact_v17/resultados/coalesce_repeat_20261021.json)
pasa,FFT100%visible19,95Paint/s,ACK68,94ms,cola4. Retención84,36ms,
sin pendientes al cierre. Existen60s+tres120s exitosos con versiones de
auditoría diferentes: no es calificación formal de fuentes idénticas ni
prueba de resolución del underrun. Producción intacta;33tests pasan.
Qrestauradoexacto8/1,6MHz/genOFF,identidad96685…yúltimos10s15993504muestras
sin pérdidas. Ningúnensayoactivo.

Próximo: eventos GC del proceso host correlacionados con las pausas, sin
desactivar ni retocar GC. El perfil histórico sólo contiene una observación
gc_collect_main: pista débil, no causalidad. No asumir que medir GC resolverá
el problema ni extender cambios a otros bits sin evidencia.

## GC observado: no coincide con el ACK del nuevo corte

Nuevo `gc_audit.py` pasivo, con cuatro tests. No fuerza recolección ni cambia
habilitación/umbrales. Control original120s pasa; registra una coleccióngen2
48,24ms que no coincide con su ACKmáximo89,08ms. La segunda corrida con el
agrupador **fallaUNDERRUN a84,12s**,ACK355,453ms,cola7,ADCsinpérdidas.

Para ese RID299,671ms transcurrieron antes de recvcompleto y55,782ms después.
GCgen2(48,643ms) terminó4,87s antes del primerACKPLAYING. DurantePLAYING
observado,18colecciones y máximo10,984ms; ninguna se solapa con el ACKcrítico.
El ring reciente cubre el intervalo y no quedan colecciones inconclusas.
Un timestamp antiguo no se retuvo(64de65), anterior al ring que cubre el fallo.
Esto no excluye toda contribución indirecta, pero **no justifica retocarGC**.

[Auditoría reproducible del fallo](../experimentos/radio_ipc_compact_v17/resultados/gc_failure_review_20261021.json).
GC habilitado y umbrales(2000,10,10) iguales antes/después. El agrupador no
resuelve el underrun. Qrestauradoexacto8/1,6MHz/genOFF,identidad96685…,
últimos10s15992640muestras sin pérdidas.37tests pasan,ningúnensayoactivo.
Sin cambios públicos. Próximo contrato/prototipo sin Q para aislar el dueño
del transporte del proceso GUI, con IPC acotado, orden de comandos/sesiones,
créditos confirmados y cierre/restauración; todavía no implementado.

## Proceso dueño: primer prototipo offline

Implementado en [experimentos/radio_io_process_v17](../experimentos/radio_io_process_v17/README.md),
sin backend Q y sin imports desde producción. Un proceso spawn posee un
dispositivo simulado; control FIFO, audio, RF y progreso usan colas acotadas.
El control tiene prioridad sobre audio bloqueado por créditos, pero no se
reordena dentro de su propia cola. Épocas/sesiones y offsets invalidan audio
viejo; ACK atrasados no acreditan la época nueva. No estima créditos por reloj.

Cinco baterías de14tests pasan con procesos nuevos: bloqueos del GIL del
padre de350/250ms, avance del dueño/consumo DAC simulado, STOP bajo presión,
ACK perdido, offset inválido, prebuffer confirmado, CONFIG sólo en reposo,
sobrecarga RF explícita y drenaje/cierre con restauración del modelo.
[Informe con fuentes/hashes](../experimentos/radio_io_process_v17/resultados/20261021_191723/report.json).

No es evidencia física de audio, ADC o restauración Q. Los mensajes RF son
sintéticos y el simulador no valida SCP1 ni reproduce latenciaUSB/ADB. Antes
del backend real faltan barreras/generación RF para CONFIG entre colas
independientes, journal RID→época, decoder/control asíncrono reales y pruebas
de EOF/muerte del padre/error. No trasladar el receiver entero todavía.
Este bloque no abrió Q ni modificó firmware o aplicación pública.

## Barreras RF entre colas independientes

El prototipo añade generación y ordinal global a cada bloque RF. CONFIG
confirma la cantidad de bloques admitidos antes del cambio. `RfBarrier`
mantiene la configuración anterior hasta consumir esa cantidad; si las
muestras nuevas llegan antes del evento CONFIG, el llamador retiene un
bloque y atiende control antes de reintentar. No hay buffer interno del gate.

Cinco baterías de 18 pruebas pasan, con ambos órdenes de entrega entre
colas, cambio de configuración en el proceso spawn y desborde uint32.
[Informe y fuentes](../experimentos/radio_io_process_v17/resultados/20261021_192150/report.json).
Esto cubre el contrato offline; sigue pendiente integrarlo en un adaptador
GUI real, junto al journal RID→época y pruebas de EOF/muerte/fallo.
No se conectó al Q ni se modificó la aplicación pública.

## Journal local de pedidos sin época en las respuestas

El simulador deja de adjuntar epoch a los ACK. El proceso dueño resuelve
RID/sesión con `RequestJournal`, limitado a 256 pendientes y 256 retirados.
STOP cancela los pedidos pendientes; una respuesta cancelada se reconoce
sin otorgar créditos. Reutilizar sesión no reutiliza RID. Duplicados de
pedidos completados, identidades incorrectas, RID desconocidos o agotamiento
uint32 provocan fallo explícito. El historial retirado no crece sin límite;
una respuesta que ya quedó fuera de él falla, sin inferir identidad.

Cinco baterías de 22 pruebas pasan. Incluyen respuesta vieja con la misma
sesión nueva, contradicciones sin modificar pendientes y límites del journal.
[Informe con fuentes](../experimentos/radio_io_process_v17/resultados/20261021_192346/report.json).
Sigue siendo un contrato offline: falta adaptar el decoder SCP1 real y
probar EOF/muerte del padre/fallos antes de operar Q. Sin cambios públicos.

## EOF del canal de vida y muerte del padre

El dueño verifica el sentinel del padre y un canal local de vida. EOF cierra
controladamente; un payload inesperado provoca fallo explícito. Con padre
vivo conserva drenaje RF. Sin padre restaura el modelo y no espera a los
feeders de colas sin consumidor; declara `abandon_on_parent_loss`, que admite
RF pendiente sin entregar y no constituye una garantía de integridad.

Una prueba termina un padre real con audio simulado activo; el supervisor
observa restauración del modelo y salida del huérfano mediante su sentinel.
Cinco baterías de 25 pruebas pasan. La primera versión dejaba al tracker
limpiar semáforos del creador terminado; el harness ahora los limpia por
nombre exacto después de observar la salida del hijo. La repetición final no
emite ese aviso. Para transferir descriptores el test usa sockets Unix locales.
[Informe y fuentes](../experimentos/radio_io_process_v17/resultados/20261021_192613/report.json).
No se probó desconexión física ni se abrió Q. Pendientes: fallo/desconexión
del backend, fallo de restauración y adaptación al protocolo/GUI reales.

## Fallos del backend simulado y destino V18

La desconexión inyectada tras un chunk pendiente termina sin inventar ACK.
Una restauración fallida fuerza resultado de fallo y `restored=false`.
Si coinciden ambos fallos se conservan `error` y `restoration_error` por
separado. Cinco rondas de 28 pruebas pasan; no es validación física.
[Informe](../experimentos/radio_io_process_v17/resultados/20261021_192758/report.json).

Por instrucción del usuario, la incorporación será en V18, manteniendo V17
como referencia. [Secuencia de integración y aceptación](PLAN_INCORPORACION_V18.md).
Falta adaptar protocolo/decoder reales y GUI; no se abrió Q en este bloque.

## Puente inicial al protocolo real para V18

El experimento reutiliza ConfigurationDecoder y el encoder WAV sin conexión.
El ingreso acotado entrega eventos por trama, de modo que el callback ACK
ocurre antes de decodificar ADC posterior. Conserva validaciones estrictas;
error cierra el ingreso y EOF incompleto falla. El journal permite el rango
WAV real 0x80000000–0xfffffffe. Pruebas con tramas mixtas/fragmentadas y ACK
viejo confirman orden/correlación; cinco rondas de 37 pruebas pasan.
[Informe y dependencias congeladas](../experimentos/radio_io_process_v17/resultados/20261021_193016/report.json).
Falta unir scheduler asíncrono, capacidad/créditos, transporte y proceso dueño.
No se conectó Q ni se modificó V17; destino de incorporación V18.

## Control asíncrono para WAV y RADIO hacia A0

Máquina sin I/O en audio_control.py: QUERY/BEGIN/CHUNK/PLAY/STOP, capacidades
negociadas, créditos confirmados, ventana, prebuffer de prueba y timeout.
STOP cancela pedidos anteriores. Sesión ocupada se informa; rechazo/UNDERRUN/
contradicción/timeout dejan fallo hasta STOP confirmado. Un ACK fuera de
plazo no se acepta aunque el tick periódico no se hubiera ejecutado.
Cinco rondas de48 pruebas pasan, incluidas11nuevas del controlador.
[Informe](../experimentos/radio_io_process_v17/resultados/20261021_193415/report.json).
Faltan envío/recepción, consultas periódicas, PCM y unión al proceso dueño.
No se conectó Q; incorporación futura V18. Prebuffer960 es sólo de prueba.

## Bucle de transporte abstracto para WAV/RADIO

AudioPump une control/decoder con send/recv no bloqueantes. Retiene una trama
parcial de salida, colaPCM≤48 y lectura≤32tramas por turno; programa consultas
incluso con DAC lleno y PCM esperando. STOP respeta framing parcial y cancela
PCM explícitamente; BEGIN no enviado no cambia la identidad remota para STOP.
Errores/EOF/timeout cierran con salida incierta sin reintentar ni restaurar Q.

Cinco rondas de58 pruebas pasan, incluidas10nuevas con LocalTransport.
[Informe y fuentes](../experimentos/radio_io_process_v17/resultados/20261021_193728/report.json).
Falta ejecutar el bucle en el proceso dueño y unir IPC/adquisición/transporte
real. Este bucle no se sometió aún a la prueba de bloqueo GIL del padre.
Sin Q ni cambios a V17. Destino de incorporación V18.

## AudioPump en proceso spawn, decoder real y peer simulado

ProcessAudio crea el bucle y decoder en el hijo; LocalTransport modela consumo
DAC40kHz con reloj monotónico y límites de memoria. Con48bloques ya recibidos
y prebuffer30 sólo de prueba, el padre mantieneGIL250ms: el hijo procesa más
tramas y played avanza más de6000puntos. La muerte real del padre también
confirma STOP del modelo y salida del nuevo hijo mediante sentinel.
Cinco rondas de66 pruebas pasan,8nuevas del proceso.
[Informe con fuentes](../experimentos/radio_io_process_v17/resultados/20261021_194756/report.json).
Resultado model_only=true; no simular restauración exitosa si no se confirma
STOP. Underrun que ya cerró el transporte devuelve restored=false. No se usó
Q; CONFIG/RF sigue sólo en el prototipo inicial y falta unirlo al nuevo bucle.
Destino V18, aún sin crear ni incorporar. No es aceptación física.

## ADC/configuración y audio comparten el proceso simulado

ProcessAudio con rf_enabled une AcquisitionPath al decoder: RF14dual sintético
40/125kS/s, barreras tras APPLIED, solicitudes en journal compartido y reset de
índice sólo al drenar muestras anteriores. STOP/cierre esperan CONFIGparcial;
restauración del modelo exige STOP y perfilADC original confirmados. Al morir
el padre se suprime publicación nueva, contando abandonados, para liberar el
hijo sin bloquear la limpieza por un consumidor inexistente.

Cinco rondas de76pruebas pasan, diez nuevas de adquisición/configuración.
En ADC+audio con padreGIL250ms, played>6000puntos y RF>50bloques; barreras,
CRC/secuencia y continuidad siguen validados por decoder/gate. ModeloRF no
cubre1,6MS/s ni otrosbits. [Informe](../experimentos/radio_io_process_v17/resultados/20261021_195906/report.json).
SinQniV17modificada. Pendientes transporte real, restauración física yGUIV18.

## Socket no bloqueante validado en localhost

SocketTransport adopta socket conectado, no bloqueante/TCP_NODELAY; send una
syscall, recv acotado con EAGAIN distinto deEOF, timeout de2s sin datos y
closeidempotente. No abre túnelADB ni buscaQ. Ocho pruebas nuevas verifican
socketpair, TCP127.0.0.1, backpressure real del kernel y sesión AudioPump con
peerfragmentado. Cinco rondas de84pruebas pasan sin avisos de recursos.
[Informe](../experimentos/radio_io_process_v17/resultados/20261021_201114/report.json).
El socket real aún no está unido al hijo spawn; la pruebaGIL de LocalTransport
no certifica esta integración. Faltan túnel/identidad/snapshot/restore físicos
y GUIV18. Sin conexión alQ ni cambios enV17.

## TCP en spawn frente a emulador independiente

ProcessSocketAudio es dueño del socket; la copia del padre se cierra tras
spawn. SocketModelPeer observa únicamente decoder/ACK. TcpModelServer corre
en otro proceso, de modo que el GIL del padre no congela al dispositivo
simulado. RF14dual40/125kS/s yDAC40kHz modelados; empiezaRF trasprimerpedido.
Seis pruebas nuevas cubren GIL250ms conplayed>6000/RF>50, CONFIG/barrera,
restauración observada por servidor, EOFtemprano, desconexión, ACKsinrespuesta
y muerte real del padre. Cinco rondas de90pruebas pasan sin avisos de recursos.
[Informe](../experimentos/radio_io_process_v17/resultados/20261021_220841/report.json).
El cierre antes deREADY informa camposNone/restored=false; no fuerza estado.
model_only=true: baseline14/125k esfixture, no snapshotQ. No se abrióQ ni se
modificóV17. Pendientes túnel/identidad/restore físico yGUIV18; no aceptación
1,6MS/s. El resetTCP del servidor se registra como terminación de conexión.

## Lease ADB e identidad con pruebas dobles

AdbTunnel prepara el ciclo de forward: identidad/exclusividad/USB obligatorios,
puerto nuevo verificado, rechazo de preexistentes, no eliminación de mapping
reemplazado o de asignación ambigua. Tras transferir socket espera observación
de salida del dueño para retirar forward. Identidad final se consulta sólo
después del cierre y no acredita restauración de ADC/generador.
Diez pruebas FakeAdb/DummySocket pasan; cinco baterías de100pruebas completas.
[Informe](../experimentos/radio_io_process_v17/resultados/20261021_221818/report.json).
No ADB real ni contactoQ. Aún falta conectar lease al hijo y snapshot/restore
físico; hardware_restored=false por contrato. V17 intacta, destinoV18.

## Snapshot exacto y restauración como contrato offline

DeviceSnapshot conserva bits/períodoADC y GeneratorConfig completo, incluido
duty, con identidadMCU/relay y esquemaJSON. Referencia sóloSPI/WAVdetenido/
genOFF; restore_contract exigeSTOP, readbackexacto, identidad y recuperación
continua10s con suficientes muestras/0pérdidas, sin atribuir evidencia física.
Nueve pruebas nuevas FakeBackend pasan; cinco rondas de109pruebas completas.
[Informe](../experimentos/radio_io_process_v17/resultados/20261021_223053/report.json).
hardware_restored=false incluso cuando restore_contract_ok=true. Falta lector/
ACK real en el dueño y uniónleaseADB; no se abrióQ ni cambióV17 o firmware.

## Consulta del generador integrada al proceso dueño

GeneratorPath comparte journal y serialización ADC/audio. GEN_QUERY usa
encoder/decoder real, emite GENERATOR_READBACK al APPLIED y conserva todos
los parámetros; el emulador incluye duty37 y valores intermedios. Seis pruebas
nuevas local/TCP/fases/RID/plazo pasan; cinco rondas de115pruebas completas.
[Informe](../experimentos/radio_io_process_v17/resultados/20261021_223519/report.json).
Última lectura no implica readback final: falta SET_GENERATOR, consulta tras
Stop, unión DeviceSnapshot/leaseADB e identidad/recuperación físicas. NoQ ni
cambios aV17/firmware/programasQ. Incorporación futuraV18.

## GeneradorOFF restaurado y leído después deStop

GEN_SET sólo admite OFF con referencia previamente consultada. El dueño
restaura todos sus parámetros y hace QUERY independiente tras Stop/SET;
generator_verified sólo estrue con igualdadcompleta y runningfalse. El
servidorTCP confirma por separado una mutación de frecuencia/niveles/duración/
duty seguida de restauración. Cuatro pruebas nuevas; cinco rondas de119pasan.
[Informe](../experimentos/radio_io_process_v17/resultados/20261021_224010/report.json).
No referencia implica generator_verified=false; model_only=true siempre.
Faltan identidad/snapshot/lease y recuperación física10s, másGUIV18. SinQni
cambiosV17/firmware/programasQ.
