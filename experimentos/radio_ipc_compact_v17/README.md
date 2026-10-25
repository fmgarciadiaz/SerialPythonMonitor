# Metadatos RADIO compactos · V17

Experimento aislado para ADC8/1,6 MS/s, RADIO con FILTER OFF o RADIO.
No cambia producción, firmware, créditos de audio ni tasa de salida de 40 kHz.

`codec.py` sustituye índices y tiempos regulares por un descriptor. Antes de
enviarlo reconstruye y compara los bytes originales: cualquier diferencia,
gap, NaN, redondeo, columna adicional o configuración no admitida conserva
el payload original. El hijo reconstruye las columnas y llama al DSP actual,
que conserva sus comprobaciones de continuidad entre bloques y generaciones.
El padre mantiene las columnas originales para historial/CSV.

No usa memoria compartida ni cambia el número de trabajos pendientes. El
worker sigue esperando un único resultado serial del proceso propietario.
Los descriptores viajan junto con los settings de su propio trabajo.

## Validación offline

Con Python 3.13 del entorno del proyecto:

```sh
python -m unittest experimentos.radio_ipc_compact_v17.test_codec
python experimentos/radio_ipc_compact_v17/benchmark.py
```

Seis pruebas pasan: reconstrucción exacta, wrap uint32, arrays readonly,
fallback de arrays discontinuos/tiempos dañados y perfiles no admitidos,
equivalencia de audio con cambios de ganancia/generación y FILTER RADIO,
rechazo de saltos de índices/tiempos entre bloques.

[A/B alternado, 100 repeticiones](resultados/20261021_130735/report.json),
incluyendo el coste de compactar y reconstruir:

| Muestras | Actual, mediana | Compacto, mediana |
|---:|---:|---:|
| 32000 | 0,956 ms | 1,131 ms |
| 64000 | 2,355 ms | 2,142 ms |
| 128000 | 8,434 ms | 5,601 ms |
| 256000 | 27,917 ms | 17,530 ms |

Los bytes bajan aproximadamente 60%, pero compactar no conviene en todos los
tamaños. El runner físico sólo lo intenta desde 128000 muestras. Los máximos
individuales siguen variables; esto no prueba corrección de underrun.

## Ensayo físico

`run.py` usa el validador existente y sus reglas de acceso exclusivo,
snapshot/restauración, identidad y recuperación de 10 segundos. Sin
`--compact-ipc` sólo agrega un histograma acotado de tamaños. Con esa opción
activa el candidato para bloques grandes. Ambos mantienen el mismo camino
normal para los bloques pequeños. Las fuentes y sus hashes quedan guardadas
con el informe del experimento, enlazado al informe físico completo.

No promover sin comparación visible, continuidad y estabilidad sostenida.
Una corrida corta es screening; ausencia de cortes no equivale a holgura.

`--compact-min-samples N` permite ejercitar otros umbrales sólo en el ensayo.
El valor predeterminado sigue siendo 128000. Un umbral menor requiere medir
su coste: con 32000 muestras el A/B offline mostró una regresión.

## Primeras pruebas físicas

RADIO→A0/40 kHz, ADC8/1,6 MS/s, FFT65536 visible todo el ensayo:

- [Control 60 s](resultados/physical_20261021_130848/report.json): sin cortes
  ni pérdidas, 5 resintonías, 20,08 Paint/s, cola pico 4/8. 2839 bloques,
  máximo 122688 muestras; 33 bloques entre 64001 y 128000 muestras.
- [Candidato configurado a 128000, 120 s](resultados/physical_20261021_131030/report.json):
  sin cortes ni pérdidas, 11 resintonías, 19,97 Paint/s, cola pico 4/8.
  5589 bloques, máximo 101088; **cero compactaciones**. No cuenta como
  validación del camino compacto ni permite atribuirle cambios de latencia.

Ambos restauraron ADC8/1,6 MS/s, generador OFF e identidad original 96685…;
10 s de recuperación sin dropped/fatal. No pasan el requisito cola <4.

- [Camino compacto desde 64000 muestras, 60 s](resultados/physical_20261021_131924/report.json):
  **39 compactaciones reales**, cero fallbacks, 2789 bloques totales y máximo
  124416 muestras. Sin cortes/pérdidas, 5 resintonías, FFT 100% expuesta a
  20,01 Paint/s. Cola pico 5/8, ACK máximo 112,16 ms; reserva host mínima
  9050 muestras. Compactación en el padre: 56,77 ms CPU acumulados y 73,90 ms
  de pared acumulados durante el lifecycle. Restauración exacta e identidad
  correctas, 10 s finales sin dropped/fatal. **Valida que el camino se ejecutó,
  no una mejora de holgura**. Frente al control corto no mejoraron cola ni ACK;
  la variabilidad y una sola pareja no establecen causalidad.

- [Camino compacto desde 64000, objetivo 120 s](resultados/physical_20261021_132102/report.json):
  **FALLA UNDERRUN WAV 4/2**, posición de audio 69,192 s; el último checkpoint
  periódico era 60 s y no es el instante del fallo. Hubo 62 compactaciones,
  cero fallbacks y máximo 204768 muestras por bloque. ADC dropped=fatal=0,
  cola pico5; FFT100%visible a19,84Paint/s durante70,10s de pared. ACK máximo
  305,07ms, read82,67ms, decode43,43ms; no sumar máximos como un solo evento.
  Reserva host mínima6429muestras. El fallo persiste: **candidato no aceptado**.
  No prueba que el codec haya causado el fallo: el underrun ya existía en
  producción y estos ensayos no aíslan esa causalidad.
  [Auditoría acotada del fallo](resultados/physical_20261021_132102/failure_review.json).
  Se restauraron configuración original ADC8/1,6MHz/genOFF e identidad96685…,
  con15994368muestras de recuperación en10s sin dropped/fatal. Sin reintentos
  ni incorporación a producción.

Próximo trabajo: estudiar la atención al transporte durante las pausas largas
del host. Esta reducción de bytes no basta; no bajar el umbral ni extender el
codec a otros bits sin un mecanismo que explique la mejora esperada.

## Ablación de carga FFT

`render_probe.py` es una prueba independiente del codec: limita las llamadas
de análisis/dibujo FFT mediante `--probe-fft-hz` (predeterminado8Hz), preserva
resolución, canales, recepción y audio. No aplica el límite a SINGLE ni a
otros modos de análisis. Cuenta llamadas ejecutadas/omitidas y tiempo del
método, mientras el validador existente mide Paint real y exposición.

Hipótesis: reducir el trabajo de FFT/Qt puede disminuir la contención sobre
el receptor. No identifica por sí solo al GIL como causa, no mide sólo la
pintura (también reduce análisis), ni propone ese límite como cambio público.
La frecuencia real queda cuantizada por el temporizador existente. Todos los
settings de audio, token bucket y créditos siguen iguales a producción.

El último fallo mostró un intervalo host de169,98ms entre comienzos de envío
en el ring reciente. En ese intervalo hubo callbacks `service` bloqueados por
créditos con audio disponible: un snapshot tenía18slots libres y18envíos sin
confirmar. Esos18slots ya estaban reservados por los comandos pendientes;
no son permiso para duplicar envíos. El ACK más lento demoró305ms y su último
`recv` observado terminó24ms antes del callback. El ring no identifica cuándo
llegaron todos los bytes del ACK al kernel ni separa transporte de scheduling.

[Ablación 8Hz, 120s](resultados/render_20261021_133718/report.json): pasa sin
cortes ni pérdidas ADC, 11 resintonías, FFT100%expuesta. El wrapper ejecutó925
llamadas y omitió5287 durante el lifecycle; acumuló11,98s CPU de hilo y14,80s
de pared en el método. El Paint real fue14,42/s: **no equivale a14,42 cálculos
FFT/s** (Qt puede pintar por otras razones y hay dos paneles). ACKmáximo57,58ms,
read65,69ms, decode24,26ms; cola pico6/8, sin holgura. Reserva host mínima8152
muestras. Qrestaurado exactamente, identidad96685… y15992640muestras de
recuperación en10s sin dropped/fatal. Una sola corrida pasa también a veces
en producción: no prueba causalidad ni corrección. Se prepara control con
`--probe-fft-hz 60`, mismo wrapper e instrumentación; ese techo deja actuar
al temporizador habitual y no fuerza60cálculos/s.

[Techo60Hz,120s](resultados/render_20261021_133954/report.json): sin cortes ni
pérdidas, 10resintonías, FFT100%visible19,76Paint/s; cola4, ACKmáximo59,14ms.
CPU del método16,26s y pared20,63s. **No es un control completamente abierto**:
omitió2156 de6051llamadas por cercanía temporal. El método original tiene
su propia limitación/deferido; estos recuentos no son cálculos FFT efectivos.
Se agregó `--probe-fft-hz 0` para instrumentar sin omitir ninguna llamada.

La pareja8/60 muestra menor coste de método al reducir actualizaciones, pero
ACKmáximos semejantes y ninguna ventaja demostrada de cola (6 frente a4).
No se incorpora una degradación del refresco por estos resultados.

[Control sin límite adicional, objetivo120s](resultados/render_20261021_134240/report.json):
**FALLA UNDERRUN** a64,992s de audio (65,99s de pared medidos; checkpoint60s).
El wrapper ejecutó3065/3065llamadas, cero omitidas. Sin codec compacto.
ADCsinpérdidas,cola4,FFT100%visible19,61Paint/s; ACKmáximo291,14ms,
decode79,56ms,read37,92ms. Reserva host mínima6442muestras. CPU del método
9,15s sobre el lifecycle más corto: no comparar ese total directamente con
las corridas completas de120s. Qrestauradoexacto8/1,6MHz/genOFF,identidad96685…,
15991776muestras de recuperación en10s sin dropped/fatal.

[Comparación estructurada de las tres corridas](resultados/render_comparison_20261021.json)
y [auditoría del fallo sin límite](resultados/render_20261021_134240/failure_review.json).
El control sin codec confirma que el fallo persiste con el payload original.
La secuencia8Hz/60Hz/abierto no es una comparación repetida aleatoria y no
demuestra causalidad de FFT/GIL. No promover ni dejar el límite en producción.
Siguiente: comparación independiente en orden inverso de8Hz frente aabierto,
con instrumentación idéntica y sin codec, antes de diseñar una medida adaptativa.

## Repetición en orden inverso ·21/10

[Comparación estructurada](resultados/render_reverse_comparison_20261021.json):

| Condición | Duración | Audio / ADC | ACK máximo | Cola pico | Paint real | CPU acumulada en render |
|---|---:|---|---:|---:|---:|---:|
| [Original, sin límite](resultados/render_20261021_142331/report.json) |120s|sin cortes/pérdidas|86,71ms|6/8|19,58/s|16,83s|
| [Techo8Hz](resultados/render_20261021_142606/report.json) |120s|sin cortes/pérdidas|46,32ms|5/8|14,41/s|11,89s|

Ventana100%expuesta en ambas. Resintonías11/10; reserva host mínima6892/7610
muestras. El wrapper original omitió cero llamadas. El reducido ejecutó925
y omitió5355 durante el lifecycle. La CPU acumulada del método fue29,3%menor
en esta pareja; **no es29,3%de mejora del monitor**, ni una medición exacta del
GIL. Incluye startup/cierre y excluye otros callbacks/paint encolados.

El refresco reducido pasó dos corridas independientes de120s; el original
falló una y pasó otra sin límite adicional. La tendencia favorece reducir
carga de análisis/dibujo, pero son pocos ensayos, orden secuencial y no hay
aislamiento causal del transporte/GIL. No se cumple cola<4 en ninguna de
estas dos corridas. No llamar a esto calificación ni corrección del underrun.

Ambas restauraron exactamente ADC8/1,6MHz, genOFF e identidad96685…; cada
recuperación10s entregó15991776muestras sin dropped/fatal. Ningún ensayo
quedó activo. No se modificó producción ni se promovió una tasa.

Siguiente diseño: un candidato aislado que reduzca análisis/dibujo sólo
durante RADIO→A0 bajo presión, conserve SINGLE/controles/resolución y vuelva
al refresco normal al detener la salida. Debe medirse su activación y
estabilidad; no seguir repitiendo una calificación estricta mientras la cola
ya incumple el criterio. Mantener visible la degradación de refresco en los
informes, sin presentarla como un aumento de velocidad del ADC.

## Candidato adaptativo aislado

`render_probe.py --adaptive-refresh` usa `adaptive_refresh.py` únicamente
en el diagnóstico. Con RADIO→A0 activo, limita las llamadas FFT a8Hz cuando
observa ACK≥40ms (observación de hasta0,5s) o al menos3lotes GUI/DSP pendientes.
Tras3s sin esas señales retira el límite. Cambio de sesión, parada de A0,
SINGLE u otro modo de análisis retiran la limitación inmediatamente.

Los contadores pendientes son observaciones para priorizar trabajo visual,
no créditos ni decisiones de propiedad. Los ACK de fuentes anteriores no
pueden activar la sesión nueva. El observador conserva el método original de
telemetría y sólo registra presión; no toca los comandos de audio. No activa
el codec compacto, ni modifica resolución, muestras o firmware. El estado y
las transiciones guardadas están acotados (32eventos recientes), con conteos
totales y segundos acumulados bajo limitación.

Cinco pruebas offline pasan: ámbito de sesión, histéresis, frescura/identidad
del ACK, bypass y almacenamiento acotado. Los umbrales son candidatos de
diagnóstico, no valores públicos aceptados. El runner archiva fuente y hash
de la política junto con su propio archivo.

[Primer screening adaptativo60s](resultados/render_20261021_144338/report.json):
sin cortes ni pérdidas, FFT100%expuesta18,77Paint/s. Política activa3veces,
9,07s acumulados en refresco reducido; recuperó estado normal. Las tres
entradas se debieron a backlog de entrega (ACKmáximo35,75ms, por debajo del
umbral40ms). ColaADCpico6/8: no es aprobación de holgura. Las transiciones y
tiempos del controlador incluyen el lifecycle, no sólo PLAYING. Restauración
exacta8/1,6MHz/genOFF,identidad96685…y15991776muestras de recuperación en10s
sin dropped/fatal. Candidato aún aislado; no incorporado.


[Screening adaptativo de 120 s](resultados/render_20261021_144510/report.json):
pasa sin cortes ni pérdidas, 10 resintonías, FFT 100% visible a 18,88 Paint/s.
La política se activó 5 veces, acumuló 17,47 s de limitación durante el
lifecycle, observó presión de entrega y ACK y recuperó el estado normal.
ACK máximo 55,75 ms, cola ADC pico 5/8 y reserva host mínima 7543 muestras.
CPU acumulada del método: 16,83 s, prácticamente igual al control original
anterior de 120 s. **No hay ahorro CPU demostrado con esta política**: el
método original ya puede retornar temprano; omitir llamadas no equivale a
eliminar cálculo costoso.

[Resumen de ambos screenings](resultados/adaptive_screening_20261021.json).
Restauración exacta ADC8/1,6 MHz, gen OFF e identidad96685…; 15991776 muestras
finales en 10 s sin dropped/fatal en ambas. Los 11 tests de política y codec
pasan. No cumple holgura, no es 60 s + 3×120 ni tiene control emparejado de
esta política. No incorporar. Próximo: control con instrumentación idéntica
y medición de cálculo FFT efectivo antes de ajustar umbrales.

`--stage-audit` instrumenta tres etapas con contadores y CPU/tiempo de pared
acumulados: `analysis_pipeline` (`_render_fft_analysis`), `fft_numeric`
(`spectral_analysis._fft`) y `draw_submission` (`_draw_fft_arrays`). Las
llamadas numéricas verifican trabajo FFT real, a diferencia de intentos de
render que pueden retornar temprano. Son tiempos inclusivos anidados: no
sumarlos. Preparar curvas no incluye los Paint posteriores de Qt. Todas las
métricas abarcan el lifecycle; no equivalen a intervalos PLAYING exactos.
La instrumentación está habilitada en ambos lados de cada nueva comparación.

## Comparación adaptativo/control con etapas medidas

[Pareja120s+120s](resultados/stage_comparison_20261021.json), control primero,
adaptativo después. Ambos pasan audio/integridad, FFT100%visible.

| Medida | Control | Adaptativo |
|---|---:|---:|
| Cálculos `_fft` |1232|1196|
| CPU `_fft` |3,699s|3,539s|
| CPU pipeline de análisis |15,050s|14,418s|
| CPU preparación de dibujo |1,944s|1,833s|
| ACK máximo |31,07ms|71,28ms|
| Cola pico |5/8|6/8|
| Paint real |19,16/s|18,91/s|

El adaptativo se activó3veces y acumuló14,16s limitados durante el lifecycle.
Evitó sólo36de1232llamadas FFT (~2,9%) y redujo4,2%la CPU del pipeline en
esta pareja, sin mejorar ACK ni cola. No incorporar por estos datos ni
ajustar umbrales a ciegas. La diferencia de una pareja no establece causalidad
de una regresión; no demuestra estabilidad ante el underrun intermitente.
Q restauradoexacto a8/1,6MHz/genOFF,identidad96685…y10s sin pérdidas en ambas.

La medición detallada posterior amplía `--stage-audit` con `analyze` completo,
anotaciones y panel de mediciones. Las fuentes de cada corrida se archivan;
no atribuir esas etapas nuevas a los informes anteriores que no las medían.

[Detalle de etapas,60s](resultados/render_20261021_150901/report.json): sin
cortes/pérdidas,cola5,19,35Paint/s,98,64%exposición. CPU del pipeline8,063s;
`analyze` completo4,254s, incluyendo FFT1,974s; preparación de dibujo1,042s,
anotaciones0,524s. Panel de mediciones0,612s incluye llamadas fuera del
pipeline: no restarlo directamente como etapa exclusiva. ACKmáximo77,89ms.
Q restauradoexacto8/1,6MHz/genOFF,identidad96685…y15994368muestras finales
en10s sin pérdidas. Es perfilado, no aceptación de holgura.

## Selección exacta de cinco picos

`peak_selection.py` evita ordenar todos los máximos locales cuando sólo se
necesitan cinco. Usa partición, conserva los empates en el orden original y
ordena únicamente el conjunto elegido. Casos pequeños y NaN conservan la
ordenación original. No cambia amplitud, fase, PSD, interpolación ni entrada.
Cuatro tests pasan: orden estable, empates/infinito/NaN, vistas strided y
equivalencia de analyze completo con ventanas/tasas/tamaños distintos.

[Benchmark offline alternado de analyze completo](resultados/peaks_20261021_151138/report.json):
200pares por señal,65536puntos,ruido2,704→2,201ms CPU mediana; AMconruido
2,644→2,204ms. El p95 de AM no mejoró. Es17–19%de mediana del método en estas
dos señales, no del monitor. Fuentes archivadas; falta evidencia física.

`--peak-select` aplica sólo en el runner una copia del analyze actual con esa
asignación sustituida. La creación falla si no reconoce exactamente una
asignación. Archiva fuente original y helper con hashes. No modifica el
archivo público y puede probarse sin codec ni política adaptativa.

[Prueba física, objetivo120s](resultados/render_20261021_151218/report.json):
**FALLA UNDERRUN a33,036s de audio**, conADCsinpérdidas ycola pico3/8.
FFT100%visible19,61Paint/s; ACKmáximo242,36ms,decode93,41ms. WAV4/2 seguido
de4/0 representa fallo y cierre, no dos cortes independientes. El ahorro
offline no corrige el problema de audio. No incorporar este candidato como
solución de estabilidad ni atribuirle causalidad del corte sin control repetido.

La primera copia aislada de analyze conservó una referencia anterior a `_fft`:
el contador `fft_numeric` reporta0 y **es inválido en esta corrida**. El
pipeline y analyze completos sí se instrumentaron; no usar ese0 para afirmar
ausencia de cálculos. Se corrigió el helper para que respete instrumentación
posterior y se añadió una regresión que verifica una llamada al contador.
La versión corregida tiene sólo validación offline; no es la fuente del
ensayo fallido. Las fuentes originales del ensayo permanecen archivadas.

[Auditoría acotada](resultados/render_20261021_151218/failure_review.json).
Qrestauradoexacto8/1,6MHz/genOFF,identidad96685…y15991776muestras en10s sin
dropped/fatal. Dieciséis tests pasan. Ningún ensayo activo, producción intacta.

Este fallo concola3 confirma que la integridad/colaADC no certifica la
alimentación de A0. La siguiente hipótesis debe actuar sobre atención al
transporte y entrega de ACK, en un experimento separado, conservando créditos
confirmados y reservas acotadas. No seguir modificando FFT a ciegas para
declarar resuelto el underrun.

## Observación pasiva de ACK completo

`wire_probe.py` utiliza el validador físico habitual y su restauración. El
observador `wire_ack_audit.py` recompone tramas SCP1 de992bytes por conexión,
valida cabecera y CRC de ACK tipo12, y registra el `recv` que entregó el último
byte de cada ACK. Al procesar el receptor el mismo RID/sesión, mide el tiempo
hasta el callback y la posición del ACK dentro del `recv`.

No adelanta, descarta ni reordena tramas; devuelve los mismos bytes al
receptor original. No genera comandos ni libera créditos. Cada observador
mantiene hasta256RIDs, ocho casos más lentos y32recientes. Si detecta framing
o CRC incorrectos desactiva su análisis sin sustituir al decoder de producción.
Reporta el coste CPU añadido. Los cinco tests pasan: fragmentación, offsets,
lecturas posteriores, identidad de sesión, corrupción y límites de memoria.

El intervalo medido empieza cuando devuelve `recv`, no cuando llegó el ACK al
kernel ni cuando lo produjo el Q. Incluye trabajo previo en el host y
planificación; no atribuye el tiempo exclusivamente al GIL. Los ACK no
entregados todavía por `recv` quedan fuera de esta medida.

[Primera corrida pasiva120s](resultados/wire_20261021_175951/report.json):
sin cortes/pérdidas, FFT100%visible19,62Paint/s, cola6. Correlacionó12786ACK
RADIO; observadores sin errores, sin evicciones. Mayor intervalo entre recv
completo y callback27,45ms, ACK situado tras1984bytes de esa devolución.
ACKtotalmáximo106,97ms según el validador; **no restar ambos máximos**, pueden
serRIDs distintos. Sobrecoste del observador1,634s CPU acumulados durante el
lifecycle (incluye conexiones de preparación/restauración).

Qrestauradoexacto8/1,6MHz/genOFF,identidad96685…y15994368muestras finales en10s
sin pérdidas. No es evidencia de holgura ni resolución del underrun.

La segunda versión registra para cada RID emparejado el inicio ya existente
en `wav_inflight`: envío→recvcompleto, recvcompleto→callback y envío→callback.
Conserva además los ocho ACKtotales más lentos; permite comparar partes del
mismo evento, sin mezclar máximos. Sexto test verifica la suma porRID.

[Segunda corrida, objetivo120s](resultados/wire_20261021_180242/report.json):
**FALLA UNDERRUN a9,36s de audio**, ADCsinpérdidas,cola3,FFT100%visible.
998ACKcorrelacionados,sin errores ni evicciones del observador. Para el RID
2874850373: envío→recvcompleto212,599ms y recvcompleto→callback29,453ms,
total242,052ms. El ACK empezaba a59328bytes dentro de ese recv; el decoder
conservó el orden de las tramas anteriores. Las pausas antes del recv incluyen
atención del host, no sólo transporte. La traza muestra actividad de decode
en ese intervalo, pero aún no medía todos los callbacks.

[Auditoría del mismo RID](resultados/wire_20261021_180242/failure_review.json).
Sobrecoste observador0,292s CPU durante el lifecycle. Qrestauradoexacto
8/1,6MHz/genOFF,identidad96685…y15991776muestras finales en10s sin pérdidas.
WAV4/2 seguido de4/0 es fallo y cierre, no dos cortes.

La siguiente versión del diagnóstico añade spans inclusivos de
`_process_decoder_events`, `_emit` y callback `on_samples` por conexión, con
CPU de hilo y ocho casos lentos por etapa. No cambia las decisiones del
receptor; su instrumentación también puede perturbar el ensayo. Los spans
anidados no se suman y pared menos CPU de hilo no equivale a espera GIL.

[Tercera corrida120s con callbacks medidos](resultados/wire_20261021_180424/report.json):
sin cortes/pérdidas, FFT100%visible19,65Paint/s,cola6. ACKtotalmáximo66,696ms:
para ese RID65,900ms envío→recvcompleto y0,797ms recv→callback. La entrega
`on_samples` más lenta duró47,518ms con0,992ms CPU del hilo; los spans `_emit`
y `_process_decoder_events` contienen ese mismo evento, no son pausas
independientes. No prueba GIL exclusivo: puede incluir planificación/esperas.
El callback activo se invocó227770veces durante el lifecycle.

Sobrecoste CPU del parser1,593s; no incluye todo el coste de los wrappers de
timing. Qrestauradoexacto8/1,6MHz/genOFF,identidad96685…y15991776muestras
en10s finales sin dropped/fatal. Ningún ensayo activo.

[Resumen de las tres versiones observadas](resultados/wire_review_20261021.json).
No comparar estas versiones como si fueran un A/B de una corrección. La
prueba intermedia captura fallo temprano; las otras pasan, mostrando de nuevo
intermitencia. Seis tests del observador y16tests previos pasan.

Siguiente experimento: coalescer de callbacks de muestras ya validadas, con
límites explícitos de tiempo/muestras y flush antes de cambios de
configuración/generador/estado y cierre. Debe preservar orden, wraps,
generaciones y cancelación; primero tests offline de fronteras. No agrupar
ACK ni alterar créditos, no acumular memoria sin límite. Busca reducir
trabajo por trama; no constituye aún una solución de las pausas observadas.

## Agrupador de callbacks RF, aislado

`coalesce_probe.py` envuelve la entrega de muestras ya validada por el
receptor; **la validación de cada trama sigue ejecutándose**. Sólo agrupa
NativeRecords en ADC8/1,6MHz con RADIO→A0 activo. No utiliza el codec compacto,
refresco adaptativo ni selección de picos. Usa el observador pasivo de ACK.

`sample_coalescer.py` retiene hasta16000muestras/32partes. El plazo10ms se
comprueba al recibir muestras y al entrar/salir de pump; es cooperativo,
no garantiza10ms absolutos bajo bloqueo/desplanificación. Reporta la edad
real máxima. Concatena sin modificar las muestras originales, y vacía antes
de cambios de contexto/callback y fronteras de control. En un dispatch que
contenga controles, las muestras se entregan directamente en su orden.
Configure/generator/wav_request/switch/shutdown/close vacían antes de actuar.
Fuera del perfil admitido se conserva la entrega original. No agrupa ACK ni
modifica créditos. La memoria está acotada; las excepciones de entrega se
propagan y no vuelven a entregar las mismas muestras al reintentar flush.

Nueve tests offline pasan: orden y wrap, integridad e inmutabilidad, plazo
cooperativo, límites de muestras/partes, cambio de callback/contexto, fronteras
mixtas, cierre, perfil no admitido y restauración de callback tras excepción.
El runner conserva el acceso exclusivo y restauración del validador habitual.

[Primer screening60s](resultados/coalesce_20261021_181224/report.json),
[auditoría ACK](resultados/wire_20261021_181225/report.json): pasa sin cortes
ni pérdidas, FFT100%visible19,60Paint/s. En el periodo agrupado111052entradas
se entregaron como8432callbacks (92,4%menos). Conservó95948928muestras,
retuvo como máximo15552muestras/18partes y terminó con cero pendientes.
Edad máxima observada34,42ms, superior al plazo cooperativo10ms. ColaADC5,
ACKmáximo93,86ms: no es calificación de holgura ni prueba de corrección del
underrun. Los callbacks fuera del ámbito agrupado siguen su camino original.

Restauración exacta8/1,6MHz/genOFF,identidad96685…y15994368muestras finales
en10s sin dropped/fatal. Las siguientes versiones del runner enlazan su
informe directamente al informe de ACK y al físico, además de guardar hashes.

[Segundo screening120s](resultados/coalesce_20261021_181409/report.json): pasa
sin cortes/pérdidas,18,93Paint/s,98,36%exposición. Agrupó222099entradas en
16980callbacks, conservando191893536muestras y cerrando con cero pendientes.
Máximo15552muestras/18partes; **retención real máxima162,72ms**, muy superior
al plazo cooperativo10ms. No presentarlo como una garantía de latencia.
Cola5,ACKmáximo118,81ms,decode118,52ms; máximos no necesariamente simultáneos.

El callback `on_samples` de la conexión activa consumió1,315sCPU durante el
lifecycle, pero el dispatch inclusivo9,790sCPU: no convertir la reducción de
callbacks en un porcentaje de ahorro global ni una corrección del underrun.
No hay un nuevo control emparejado y el fallo original es intermitente.

[Resumen60+120s](resultados/coalesce_screening_20261021.json). Ambas restauran
exactamente8/1,6MHz/genOFF e identidad96685…; recuperación última10s15991776
muestras sin dropped/fatal. Treinta y dos tests pasan, incluido receptor real
que sigue rechazando un salto RF antes de entregar muestras inválidas.
Ningún ensayo activo. Producción intacta, candidato no incorporado.

Siguiente: control independiente con la misma instrumentación y correlación
de la retención larga con los spans del receptor. El presupuesto de memoria
sí es duro; el de tiempo no lo es bajo bloqueo del mismo hilo. No promover
sin medir ese riesgo y la continuidad de audio sostenida.

La auditoría posterior conserva ocho retenciones lentas por agrupador, con
inicio, instante de vaciado, cantidad y motivo (`deadline`, frontera, capacidad
o contexto). `wire_probe.py` también mide spans de `pump`, inclusivos de sus
lecturas/decoder/callbacks, para correlacionar intervalos en un mismo reloj.
No sumar spans padres e hijos ni asumir GIL por la diferencia pared/CPU.
`coalesce_probe.py --control` ejecuta el mismo validador y auditoría con el
agrupador deshabilitado; los dos lados archivan las mismas fuentes. Once
tests de agrupador/integración pasan, incluida retención con reloj simulado.

## Control emparejado y correlación de retención

[Comparación120s+120s con hashes idénticos](resultados/coalesce_matched_20261021.json):
control deshabilitado primero, agrupador después. Ambos pasan audio/ADC y
mantienen FFT100%visible.

| Medida | Control | Agrupador |
|---|---:|---:|
| CPU del callback activo de entrega |4,323s|0,976s|
| CPU inclusiva de pump |46,431s|45,304s|
| ACK máximo |80,36ms|82,88ms|
| Cola ADC pico |5/8|6/8|
| Paint real |19,18/s|19,70/s|

El ahorro77,4%del callback **no es ahorro global**: pump sólo bajó2,4%en esta
pareja y contiene etapas anidadas. No hay mejora demostrada de ACK o cola.
El agrupador procesó222104entradas como16901callbacks, conservó191897856
muestras y terminó sin pendientes. Su máxima retención76,385ms coincidió
con un pump78,812ms de pared y2,610msCPUdelhilo. Esa correlación acota espera
fuera de CPU propia; no demuestra GIL exclusivo ni causalidad del agrupador.
Otras retenciones y sus spans solapados quedan en el informe estructurado.

Ambos restauraronexacto8/1,6MHz/genOFF,identidad96685…y10s finales sinpérdidas.
Es una sola pareja secuencial, no una corrección del underrun calificada.

[Repetición independiente120s](resultados/coalesce_20261021_183239/report.json),
con hashes iguales al último candidato, pasa sin cortes/pérdidas y FFT100%
visible19,95Paint/s. Cola4/8,ACKmáximo68,94ms. Agrupó222149entradas como
16974callbacks,conservó191936736muestras y cerró sin pendientes. Máximo
15552muestras/18partes,retención84,36ms. Qrestauradoexacto8/1,6MHz/genOFF,
identidad96685…y15993504muestras finales en10s sin dropped/fatal.

[Resumen y correlaciones de la repetición](resultados/coalesce_repeat_20261021.json).
En total hubo60s+tres120s exitosos con agrupación, **pero con versiones de
auditoría distintas**: no declarar calificación formal con fuentes idénticas.
La evidencia de menor coste del callback no prueba solución del underrun ni
holguraADC. Treinta y tres tests pasan; producción sigue intacta.

Próximo diagnóstico acotado: medir eventos de GC del proceso host y
correlacionarlos por reloj con retenciones/ACK, sin desactivar GC ni cambiar
umbrales. El perfil nativo histórico contiene una observación gc_collect_main;
eso no demuestra que GC sea dominante ni causa de los cortes. Mantener la
hipótesis separada de los resultados y conservar el agrupador aislado.

## Auditoría GC pasiva

`wire_probe.py --gc-audit` registra callbacks naturales de GC sólo en el
proceso host: duración de pared, CPU del hilo, generación y cantidades
recogidas/no recuperables. No llama a `gc.collect`, no desactiva GC ni cambia
umbrales. Guarda totales por generación,16intervalos mayores y64recientes;
no inspecciona objetos del heap. El contexto retira su callback al terminar,
incluido el caso de excepción. Registra estado/umbrales antes y después.

Cuatro tests pasan: intervalos/CPU, almacenamiento acotado, identidad de hilo
y limpieza de registro sin cambiar la política GC. El observador es una
medición adicional que puede perturbar el proceso; una coincidencia temporal
no basta para atribuir causalidad. Las colecciones del DSP en otro proceso no
se miden aquí. La combinación `coalesce_probe.py --control --gc-audit` permite
observar primero el camino original sin agrupación de callbacks.

[Control original120s con GC](resultados/coalesce_20261021_185612/report.json):
sin cortes/pérdidas,FFT100%visible16,89Paint/s,cola5. GCregistró60colecciones
gen0(máximo2,17ms),6gen1(máximo5,42ms) y1gen2(48,24ms). El GCgen2 sucedió
unos101s antes del ACKmáslento89,08ms, no coincide con ese evento.
No atribuir todos los bloqueos a ese GC ni comparar máximos independientes.
Política antes/después idéntica: habilitado,umbrales(2000,10,10).
Qrestauradoexacto8/1,6MHz/genOFF,identidad96685…y15991776muestras finales
en10s sin pérdidas. El primer informe no marcaba el intervalo PLAYING.

La siguiente versión marca primera/última confirmación PLAYING de cada
sesión y su ACK de salida si se observa, para distinguir arranque de audio.
Estas son fronteras observadas en host, no timestamps de inicio DAC del Q.

[Agrupador+GC, objetivo120s](resultados/coalesce_20261021_185936/report.json):
**FALLA UNDERRUN a84,12s de audio**, ADCsinpérdidas,cola7,FFT98,80%expuesta.
El ACKmáslento355,453ms se divide para el mismo RID en299,671ms antes de
recvcompleto y55,782ms después. El agrupador terminó sin muestras pendientes;
no se considera corrección del underrun pese a los screenings anteriores.

GCregistró58coleccionesgen0,6gen1 y1gen2. Gen2duró48,643ms y terminó4,87s
antes del primer ACKPLAYING. Durante el intervalo PLAYINGobservado hubo
18colecciones, máximo10,984ms. **Ninguna colección se solapa con el ACK de
355ms**. El historial conserva64de65timestamps; el evento descartado es
anterior al inicio del ring reciente, mucho antes del ACKanalizado. No hay
colecciones inconclusas ni stops sin pareja. No descarta toda contribución
indirecta de GC en otros momentos, pero no sustenta cambiar su política.

[Auditoría GC/fallo por RID](resultados/gc_failure_review_20261021.json).
GC siguió habilitado con umbrales(2000,10,10) antes/después. Qrestauradoexacto
8/1,6MHz/genOFF,identidad96685…y15992640muestras finales en10s sin pérdidas.
Treinta y siete tests pasan. Nada corriendo, producción intacta. No ajustar
GC ni promover el agrupador como solución de estabilidad por esta evidencia.

Siguiente hipótesis: aislar el dueño del transporte y su alimentación A0 del
proceso GUI, con IPC limitado y semántica explícita de comandos, sesiones,
créditos confirmados y cierre. Primero contrato y pruebas de simulación sin
Q; no trasladar el receiver entero ni tocar firmware sin esas garantías.
La evidencia apunta a pausas del host, pero esta arquitectura aún no se
implementó ni validó y no tiene una promesa de corrección.
