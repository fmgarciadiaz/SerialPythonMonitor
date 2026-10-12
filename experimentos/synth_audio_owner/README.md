# Dueño de audio/Q separado

`diagnosticos/probar_audio_owner_v16.py` es un ensayo, no una integración GUI.
El hijo es el único dueño de la conexión Q y ejecuta Synth/reposición/control.
El padre envía notas/pedal por Pipe y verifica ADC por Queue de 32 lotes
de aproximadamente 2048 pares (memoria acotada, sin descartes silenciosos).
Si se llena el canal, el ensayo falla. Se verifican rango ADC, continuidad
de índices/timestamps, wrap uint32 e igualdad entre muestras enviadas/recibidas.
El hijo guarda/restaura ADC/generador/WAV al terminar o ante errores normales.
Si termina forzosamente, la restauración requiere verificación explícita.

Se introducen pausas del padre de al menos75ms cada segundo, además de
gc.collect; controles simulados cada350ms, hasta11voces y pedal. Es prueba
digital headless a20kHz con ADC14/100k, no medición de tecla→sonido ni GUI.

GC normal: 5bloques estable30s pese a135ms de pausa padre, todas2.996.902
muestras IPC recibidas. 4bloques creció6 sin cortes30s. Ensayo120s con5:
sin cortes y todas11.992.170muestras recibidas, pero target creció7;
padre pausó158ms, gap ACK53,37ms. La separación protege de pausas del padre,
pero aún no aprueba sostener120ms ni reducir a96ms.

`--freeze-worker` prueba una política adicional sólo en el hijo descartable:
collect/freeze después de warmup/preparación; GC normal para objetos nuevos,
unfreeze al finalizar. No cambia el GC del padre ni activa nada en el monitor.
`--targets 5 --seconds 120` limita el ensayo al perfil indicado.

Evidencia en `diagnosticos/resultados_piano/eficiencia_v16/`:
`20261010_133125_audio_owner.json`, `20261010_133345_audio_owner.json`.
Fuente estable del relay y firmware quedan iguales; Q restaurado en ambos.
Comparación120s con freeze sólo en hijo: sin cortes y todas11.991.492 muestras
recibidas, pero target5→9, gap ACK67,12ms, generación50,93ms y sendall19,11ms;
padre pausó188ms. No demostró mejora ni se promueve esa política. Evidencia
`20261010_133706_audio_owner.json` en la misma carpeta. Las comparaciones
son ensayos separados y los máximos incluyen esperas de planificación.
Pruebas de IPC: `tests/v16/test_audio_owner.py`.

Pendiente antes de integrar: lifecycle/errores y cierre GUI, volumen/filtros,
preservación ADC/trigger/capturas/CSV, MIDI real y medición acústica. Ninguno
de esos aspectos queda certificado por este ensayo.

`--timings` guarda una traza acotada de hasta100.000 eventos en el hijo.
Incluye tiempo real y CPU del hilo para render, decode, read, sendall,
controles, IPC ADC y pump; registra GC y crecimiento del target. La escritura
ocurre al terminar, después de intentar restaurar el Q. El informe indica
si se alcanzó el límite: la traza cubre sólo el comienzo en ese caso.
Analizar con `diagnosticos/analizar_tiempos_synth_v16.py <trace.json>`.
Los intervalos pump/IPC/controles se presentan aparte para evitar sumarlos
sobre sus etapas internas. Tiempo real menos CPU no identifica por sí solo
si hubo espera de socket, competencia de CPU o suspensión del proceso.
La instrumentación añade trabajo y asignaciones; no certifica una mejora
de latencia. Compatibilidad con trazas anteriores sin CPU cubierta por tests.

Traza `20261010_134704_audio_owner_target5_trace.json`: cubre27,71s;
primer crecimiento5→7 inmediatamente después de render42,24ms, GC39,70ms.
También read26,11ms/CPU0,31ms e IPC30,41ms/CPU1,67ms: no confundir esas
esperas con cálculo de síntesis. Ensayo completo120s sin cortes,5→9,
11.991.718 muestras íntegras y Q restaurado. Segundo crecimiento fuera de
traza; no atribuido. Primer intento134620 tuvoUNDERRUN al arranque y se
restauró; no ocultar ese fallo al evaluar estabilidad. Instrumentación
puede alterar GC y rendimiento. No reduce ni aprueba la cola.

Con auxiliares ramp/phase compartidos enFMSource, ensayo sin traza pesada
`20261010_135340_audio_owner.json`:120s,11.992.396 muestras IPC íntegras,
sin cortes, pero5→9. Generación máxima15,94ms y gap ACK53,93ms.
Q restaurado. El cambio conserva códigos DAC exactamente y reduce trabajo
por bloque; no resuelve la cola. A/B host guardado en
`20261010_alloc_shared_helpers.json`;72 tests de síntesis pasan.

`--shared-adc` sustituye Queue32 por un anillo ADC preasignado de memoria
compartida,32 ranuras con hasta4096 registrosuint32 de4 columnas cada una.
Un productor y un consumidor; semáforos publican cada ranura después de la
copia y no permiten reutilizarla hasta que el lector haya copiado los datos.
No hay pickle ni hilo feeder. Si se llena, el ensayo falla explícitamente,
igual que con Queue; no pierde muestras para mantener el audio andando.
No está integrado en la interfaz.

`diagnosticos/benchmark_adc_ipc_v16.py` compara ambos transportes localmente
en orden Queue/ring/ring/Queue, pausando al consumidor con GC y20ms de sleep.
Aquí, únicamente para medir throughput, se reintentan los envíos al llenarse;
esto no certifica margen de audio. Informe20261010_shared_adc_local.json:
2.048.000 registros por corrida, todos exactos/en orden; CPU del productor
Queue97,23/104,54ms, ring41,29/44,05ms (~58% menos). Tiempo de put individual
no es comparable como costo completo: Queue difiere serialización al hilo.
Diez tests cubren worker, capacidad, retención de lector, FIFO con spawn y muchas
vueltas, IPC ADC, análisis temporal y detección de monitor abierto.

El intento físico20261010_142430_audio_owner.json no es evidencia de rendimiento:
monitor abierto y conexión cerrada antes de adquirir muestras/capturar perfil.
No se verificó restauración en ese intento; no conectar de nuevo mientras
la interfaz use el Q. El CLI ahora comprueba procesos del monitor y rechaza
el ensayo antes de conectar si hay alguno abierto. Pendiente comparar120s
físicos con Q exclusivo; no bajar cola por el benchmark local.

Ensayo físico shared_ring `20261010_143852_audio_owner.json`:120s,
11.993.780 muestras ADC/IPC exactas, sin cortes, pero5→9 y gap ACK53,01ms.
No mejora el perfil fijo respecto de Queue135340 (también5→9). Q restaurado
al ADC14/100k de esta sesión, generador previo off y WAV IDLE. No activar
la arquitectura ni bajar cola por el ahorro de CPU local.
El CLI acepta también WAV DONE sin error, estado que BEGIN del firmware
puede reemplazar; no manda STOP a otra sesión ni acepta audio activo.
11 tests relevantes pasan. Intentos143657/143742 rechazados antes del
ensayo por antigua condición sóloIDLE; no son evidencia de rendimiento.

`--adc-rate40000` permite comparar la limitación ADC de Synth; valida25us
entre muestras. Default100000 conserva los ensayos anteriores (10us).
Ensayo20261010_144500_audio_owner.json:120s,4.796.416 muestras íntegras,
sin cortes, target5→7 y gap ACK54,35ms. El previo100k creció5→9, pero los
máximos ACK siguen similares: no aprueba cola fija ni menor latencia acústica.
Q restaurado ADC14/100k anterior, generador off y WAV IDLE. La GUI incorpora
el límite ADC40k sin activar esta arquitectura experimental.

La traza actual `--timings` usa NumericTransportTrace:500.000 eventos en
un arrayfloat64 preasignado (~20MB), sin retener tuplas rastreadas por GC.
Es circular: conserva la ventana reciente, exporta events+metadata y cuenta
los eventos sobrescritos. El reporte conserva también todos los aumentos de
cola (pocos episodios), aunque salgan de la ventana. Conversión JSON sólo
tras terminar/restaurar. El análisis acepta este formato y listas antiguas,
y cuenta IPC/controles por separado del pump para no duplicar intervalos.
La instrumentación sigue añadiendo trabajo; no equivale a funcionamiento sin
traza ni mide tecla→sonido. Tests cubren vueltas, IDs uint32 exactos, CPU
opcional, formato anterior y separación de tiempos anidados.

Traza numérica145129: corteUNDERRUN a20,855s,833.536 muestras exactas,
Q restaurado.61.784 eventos completos, sin sobrescribir. Read87,600ms,
CPU0,0537ms, sin GC; peor send→ACK89,831ms mayormente lectura89,084ms.
Generación máxima15,948ms; GC máximo2,597ms en3 episodios. Pico está en
espera/planificación, no CPU de síntesis; no distingue relay/ADB de scheduler.
No promover perfil5 por esta corrida ni interpretar reason0 como ausencia
de corte si state esUNDERRUN.13 tests relevantes pasan.

Con --timings, SocketProbe observa readiness por select cada1ms en otro hilo,
sin consumir datos ni cambiar timeout/read de producción. Guarda muestras
numéricas acotadas (200.000 iniciales) y marca cualquier exceso, error y gap
entre observaciones. El hilo también depende de scheduler/GIL; no es reloj
externo ni timestamp de llegada. Ausencia de readiness observada no prueba
que faltaran paquetes. `analizar_socket_synth_v16.py` correlaciona reads largos
con esas observaciones. Las pausas futuras del padre incluyen start/end para
correlación temporal, además de máximos de GC/sleep.

Ensayo145611: UNDERRUN a103,733s, target5→7,4.145.152 muestras íntegras,
Q restaurado. Gen118,590ms con CPU del hilo21,148ms y sin GC; GC máximo
2,841ms. Probe83.830 observaciones sin pérdida/error, gap máximo43,451ms.
Read50,126ms/CPU0,162ms coincide con4 observaciones y un gap23,023ms;
ninguna observó readiness antes de regresar la lectura. No decide si faltó
transporte o reactivación. El corte por generación fuera de CPU/GC muestra
que bajar ADC/optimizar cálculo no basta. El tiempo fuera de CPU puede
incluir espera interna o trabajo de otros hilos, no sólo scheduler. Esta
instrumentación añade un hilo y no certifica menor latencia.

Traces nuevas admiten6 campos: stage,start,end,rid,CPUhilo,CPUproceso;
array500.000x6float64 (~24MB). Analyzer --report <audio_owner.json> cruza
las pausas absolutas del padre; no interpreta coincidencia como causalidad.
150300:120s sin cortes,4.796.416 muestras exactas,5→7,Q restaurado.
Gen34,141ms con CPUproceso4,631ms/sinGC/pausa padre0; read47,107ms con
CPUproceso0,341ms/sinGC/pausa padre0. No son CPU oculta en otros hilos.
Otro gen21,636ms sí superpone GC padre; decode11,592ms incluye GC11,510ms.
No reducir todas las fuentes a una sola ni certificar menor latencia.
15 tests relevantes pasan y formatos anteriores siguen analizándose.

audio_trace detalla voice_prepare,voice_render,piano_post,source_render y
DAC; sólo parent source tiene callback y analyzer no duplica etapas anidadas.
150901:120s sin cortes,5→9,4.796.416 muestras exactas,Q restaurado.
Faltaba set_wav_levels: el owner anterior usaba ruta cruda (__getitem__),
sin compresor/volumen GUI. No reinterpretar esos ensayos como cadena completa.
Owner ahora usa1Vpp/1,65V y registra dac_levels (GUI inicial2,5Vpp no ensayado).
151149:30s sin cortes,5 estable,1.198.080 muestras exactas,Q restaurado.
Voces16,511ms/post7,095ms/DAC0,574ms/read25,022ms máximos.30s no aprueba
estabilidad120s ni menor latencia.73 tests de síntesis/equivalencia y6 de
traza/análisis pasan; instrumentación sigue optativa fuera de GUI.

### 2026-10-10 — Plan Astra y ensayos de cola/reflexiones

Plan: conservar audio exacto, medir candidatos CPU en host y probar cola5→4
sólo después de estabilidad; distinguir owner experimental de GUI/MIDI real.
Reordenar resonadores conservó muestras/estado pero hizo el kernel1.5–2x
más lento: descartado y restaurado. Resultado20261010_astra_resonadores.json.

Baseline153649 con niveles1Vpp120s: sin cortes pero5→9; no admite bajar cola.
QoS154456: override reversible validado, base ya user_interactive; UNDERRUN
a89.8s, sendACK188.4ms, ADC3.588.096 muestras íntegras yQ restaurado.
Astra localiza142.15ms en decode y44.55ms controles, poca CPU, sinGC propio
ni pausa padre superpuesta; no atribuir a timeout100ms. QoS no se habilitaGUI.

Driver separa --timings y --socket-probe (antes eran inseparables); --qos
es optativo y sólo afecta al child. --amplitude1.0/2.5 registra ruta DAC real.
Sin instrumentación154724: target5 ytarget4 pasaron120s cadauno sincrecer
ni cortes, ADC íntegro yQ restaurado enambos. Target4=96ms vs5=120ms,
reducción experimental24ms; no certifica GUI ni atribuye causa a quitarprobe.

Reflexiones: normalización de pesos constante fuera del bucle de muestras.
ABBA calentado kernel mediana0.10846→0.03299ms; exactos salida,buffer,
posición y288.000 códigosDAC a20/40k. Fullsynth timing variable: no afirmar
70% menoslatencia global. Resultado20261010_astra_reflexiones.json.
48 tests QoS/resonadores/owner/instrumentos y29 finales reflexiones/owner/
instrumentos/audio_trace pasan. Synth/colaGUI no se cambian con este ensayo.

Ensayo final 165214, con normalización optimizada, sin instrumentación y
2,5 Vpp: target 4 permaneció estable durante 300,001 s, sin cortes ni
crecimiento. Se validaron 11.991.266 muestras ADC por índice y timestamps;
Q restaurado a ADC14/100 kHz, generador previo apagado y WAV IDLE.
Máximos: generación 24,414 ms; envío→ACK 11,805 ms; socket 0,301 ms.
Resultado: cola objetivo experimental 96 ms, 24 ms menos que target 5.
La mejora CPU de reflexiones sí queda aplicada al camino normal; el owner
separado y target 4 todavía requieren validación GUI/MIDI antes de promoverlos.
Reporte: diagnosticos/resultados_piano/eficiencia_v16/20261010_165214_audio_owner.json.

### 2026-10-10 — Optimización común y revisión de todos los instrumentos

Se ensayan los 13 presets del panel con sus mezclas reales, 11 notas, pedal,
release y cambios de drive/mix. `diagnosticos/synth_presets_v16.py` extrae
parámetros del FMPanel sin conectar MIDI ni hardware. El owner acepta
`--presets` y restaura/verifica el Q entre casos; aborta si falla restauración.

Mejora común aplicada en FMSource: curvas constantes del compresor y
transición del filtro con caché acotada e inmutable; transición calculada
sólo cuando se usa. Drive y wet estables reutilizan `_ramp`, manteniendo
interpolaciones al cambiar controles. No cambia ADSR, mezcla ni timbre.

Benchmark de 26 casos (13 presets × 20/40 kHz) conserva exactamente
2.246.400 códigos DAC. Suma de medianas: 20 kHz 28,72→28,22 ms;
40 kHz 24,09→23,66 ms. Son corridas secuenciales host, diferencia pequeña
y sensible a carga; no equivale a una reducción garantizada de latencia.
Resultado: 20261010_cache_instrumentos.json. Benchmark inicial general:
20261010_instrumentos.json. Los mayores p95 fueron piano, DX y guitarra;
Brass mostró picos aislados. Pasaron 72 tests FM/feedback/owner/límite ADC.
La cola GUI permanece en su valor previo hasta validar esa arquitectura.

Ensayos físicos 200843, ADC40 kHz, 2,5 Vpp y target inicial4, con presets
del panel y controles simulados: guitarra120s sin cortes pero target4→8;
DX Brillo UNDERRUN a70,738s (generación máxima31,402ms); Brass120s
sin cortes pero4→8. Guitarra/Brass tuvieron send→ACK máximos55,55/58,53ms.
ADC íntegro en los tres casos (4.796.416 / 2.826.240 / 4.796.416 muestras),
y Q restaurado entre todos los casos: ADC14/100k, generador previooff,
WAV IDLE. Resultado20261010_200843_audio_owner.json.
Conclusión: no promover cola4 a la GUI ni generalizar aprobación previa
de piano a otros presets. Sí conservar optimización común exacta; requiere
seguir investigando pausas de transporte/scheduling y margen de generación.

### 2026-10-10 — Guitarra y Brass: coeficientes y PolyBLEP

Guitarra: caché acotada de 512 combinaciones para coeficientes de pérdida
de la cuerda (rate/frequency/brightness/decay/bridge). No contiene buffer,
cursor ni estado de ruido. Controles nuevos invalidan por clave; comparación
de muestras/buffer/cursor exacta en cambios de brillo, decay y bridge.

Brass: nuevo `synth_oscillator.py` calcula PolyBLEP de sierra/cuadrada en
un kernel Numba sin fastmath, respetando orden de operaciones y evitando
arrays temporales y máscaras por voz. Warmup de las variantes de frecuencia
escribible e inmutable antes de BEGIN; fallback NumPy si Numba no existe.
También beneficia Lead, Bass Punch y Warm Pad, que usan esas ondas.

Benchmark calentado ABBA con parámetros reales del panel, 11 notas,
pedal/releases y cambios de drive/mix; 10 casos × 115.200 códigos DAC,
exactos entre cuatro corridas cada caso. Resultado20261010_guitarra_brass.json.
Medianas a20k: guitarra2,884→2,718ms (-5,8%); Brass2,096→0,991ms (-52,7%).
A40k: guitarra2,176→2,030ms (-6,7%); Brass1,650→0,848ms (-48,6%).
Lead/Bass Punch/Warm Pad también mejoran, aproximadamente49–61% según
preset/rate. Son tiempos de generación host, no latencia acústica total.
93 tests de oscilador/cuerda/FM/feedback/instrumentos/owner pasan.

Ensayo físico201809, mismo rig a40k/2,5Vpp, sin instrumentación,120s
por instrumento: guitarra sin cortes, target4→8; Brass sin cortes,4→10.
Cada caso validó4.796.416 muestras ADC y restauró Q aADC14/100k, generador
previo apagado yWAV IDLE. Guitarra sendACK38,916ms/generación31,633ms;
Brass sendACK82,870ms/generación33,763ms. Estos máximos de pared incluyen
pausas y no contradicen la mejora de cálculo host; no prueban menor latencia
física. Target4 rechazado nuevamente, colaGUI conservada. Optimización CPU
exacta aplicada; se necesitan pruebas de pausas/transport para bajar cola.
Reporte20261010_201809_audio_owner.json.

### 2026-10-10 — Segunda optimización guitarra/Brass

Perfil host: guitarra dominada por GuitarStrings.render y dos waveguides;
Brass por preparación de voces, fases/osciladores y wrappers de sosfilt.
No confundir ese perfil CPU con pausas largas del transporte.

Guitarra: calcular índice/fracción de interpolación para cada posición
del buffer una vez por delay, mediante el mismo cálculo escalar original.
Guardar una sola tabla por cuerda y regenerarla cuando cambia delay; estado
y contenido del buffer no se cachean. El kernel sustituye modulo de float
por acceso a tabla y wrap entero por comparación, con muestras/estado exactos.

Filtros internos: kernel SOS stateful directo sin fastmath, con salida y
estado final exactos respecto de SciPy en señales fragmentadas/strided y
órdenes2/4/8. Conserva semántica de no modificar zi de entrada; fallback
SciPy sin Numba. Warmup C/strided y coeficientes mutables/inmutables antes
de BEGIN. Limitado a filtros internos normalizados, no API general SciPy.

ABBA completo20261010_filter_table.json: a20k guitarra2,805→2,300ms
(-18,0%), Brass1,021→0,861ms (-15,6%); a40k guitarra2,126→1,827ms
(-14,1%), Brass0,856→0,711ms (-16,9%). Mejoras adicionales a la etapa
anterior. Lead a40k varió levemente hacia peor; no afirmar mejora uniforme.
Comparación26casos/13presets a20/40k conserva2.246.400 códigosDAC exactos
(20261010_filter_all_presets.json). 93 tests generales pasan; test SOS
corregido para usar copia escribible en referenciaSciPy también pasa.

Diagnóstico --scheduler opcional: getrusage antes/después de pump; sólo
guarda iteraciones>=20ms, hasta256 registros y contador de omitidos.
Incluye CPU proceso, faults minor/major y context switches; no permite
atribuir causalidad ni interpretar minor faults como disco. Sin hilo extra
ni traza de todos los eventos. No activado en GUI.

Fases sin uso: avanzar sólo estado final de portadora virtual y modulador
noFM, sin construir sus arrays; usar recorrido original cuando cambia el
pitch. Estados exactos, incluidos cambios de pitch y continuidad de fase.
Warmup de waveguide/tabla añadido a prepare_audio antes de BEGIN.
ABBA final20261010_filter_table_phase.json, frente a inicio de esta etapa:
guitarra20k2,769→2,092ms (-24,5%),40k2,085→1,646ms (-21,0%);
Brass20k0,997→0,805ms (-19,2%),40k0,848→0,671ms (-20,9%).

Ensayo202923, target4: guitarraUNDERRUN a12,447s, Brass120s sin cortes
pero4→8; ADC íntegro yQ restaurado en ambos. Pausa guitarra52,606ms
con CPU0,296ms, sin major/minor faults: no atribuir el corte a generación.

Con warmup/fases y target5,203451: guitarraUNDERRUN a25,597s tras
lectura138,494ms/CPU0,091ms; generación máxima10,675ms. Brass60s
sin cortes pero5→7; generación16,022ms. ADC íntegro yQ restaurado.
Diagnóstico --scheduler ahora también mide lecturas largas, sin hilo extra.
--read-timeout-ms5/20/100 optativo; restaura timeout antes de restaurarQ.

Comparativo203701 con timeout5ms: guitarra60s, target5 estable, ADC
2.398.208 muestras ysendACK9,845ms/generación12,423ms. BrassUNDERRUN
a5.634s. target5.224.136 muestras; sendACK145,894ms/generación6,383ms.
Dos lecturas61,330/62,488ms con CPU0,060/0,107ms, sin major faults,
aun con timeout5ms. Un timeout no limita toda demora de reactivación del
proceso. No atribuir mejora estable a5ms ni promoverlo aGUI. Q restaurado
en ambos casos. Quedan aplicadas mejoras CPU exactas; cola y política de
lectura de producción conservadas. Investigar transporte/reactivación
separadamente; no ocultar los cortes ni reducir validación ADC.


Ensayos 2026-10-10: observador independiente y ventana de créditos
----------------------------------------------------------------
ProcessSocketProbe usa un proceso separado y select sobre un duplicado del
socket: no consume datos ni cambia el timeout. Guarda muestras en memoria
compartida preasignada y cierra sólo el duplicado. Es diagnóstico optativo
(--probe-process), no se activa en GUI. Prueba verifica datos preservados,
readiness y que el socket original sigue abierto.
20261010_204406_audio_owner.json: Guitarra/Brass 60s cada uno, ADC40k,
synth20k, 2,5Vpp, target5→7; sin cortes, ADC íntegro y Q restaurado.
El proceso observador también demoró 43,335ms (guitarra) y23,771ms (Brass).
La ausencia de readiness observada no demuestra ausencia de datos: el owner
puede haberlos consumido antes de que el observador vuelva a ejecutarse.
No atribuir toda pausa al GIL del owner ni certificar causa de transporte.

--credits1/2/3/4 permite ensayar ventana acotada sin cambiar el target ni
las confirmaciones. Producción conserva2. BEGIN/PLAY/QUERY/STOP y WAV
siguen serializados; se respetan reservas y espacio libre confirmado.
20261010_204744_audio_owner.json, créditos3, target5, ADC40k/synth20k:
Guitarra120,002s sin cortes pero target5→9; 4.796.416 muestras ADC.
Brass UNDERRUN a94,247s, target5→9; 3.766.272 muestras ADC.
Ambos con ADC íntegro, cero dropped/fatal y restauración exacta del Q:
ADC14/100k, generador apagado, WAV IDLE. No promover créditos3 ni bajar
cola normal con estos resultados. 70 tests pasaron (FM, audio owner,
sondas y ventana de créditos); incluyen offsets, ACK, STOP y límites.


Comparativo de carga de voces, 2026-10-10
---------------------------------------
Driver agrega --voices0..11 (default11), conservando el patrón de controles,
intervalos, pedal y GC del padre. No cambia la aplicación ni el firmware.
ADC40k/synth20k,2,5Vpp,target5,créditos2,timeout100ms,--scheduler;
60s por preset, en serie sin benchmarks concurrentes.
20261010_205346_audio_owner.json, cero voces:
Guitarra cola5→7, generación máxima2,636ms, sendACK58,610ms;
Brass cola5→9, generación1,734ms, sendACK96,202ms.
20261010_205637_audio_owner.json, once voces:
Guitarra cola5→7, generación20,981ms, sendACK53,794ms;
Brass cola5→7, generación8,662ms, sendACK36,286ms.
Los cuatro casos sin cortes, 2.398.208 muestras ADC cada uno, continuidad
índice/timestamp válida, cero dropped/fatal y Q restaurado exactamente.
Ninguno acepta reducir cola fija: todos crecieron. Son ensayos secuenciales,
no prueban que once voces mejore transporte. Demoras persisten sin carga de
voces: síntesis no explica por sí sola el límite de cola. Revisar scheduling
host/Q, ADB/TCP y tramo SPI con tiempos independientes; no atribuir causa
única con estos máximos. Relay estable sin cambios: envíos no bloqueantes,
TCP_NODELAY y espera READY; no quitar sincronización para ganar latencia.


Serie alternada comparable, 2026-10-10
------------------------------------
20261010_210056_audio_owner.json. Seis casos secuenciales, parámetros reales
del panel, once voces/controles/pedal idénticos, synth20k/ADC40k,2,5Vpp,
cola inicial5,créditos2,timeout100ms,--scheduler. Driver ahora conserva
presets repetidos en --presets; snapshot por nombre, orden de ejecución
exacto. Restauración entre cada caso y sin benchmark concurrente.
Orden y resultado (tope60s):
1 Piano: UNDERRUN53,89s,cola5→7,gen máx15,434ms,sendACK53,899ms.
2 Guitarra:60s sin cortes,5→7,gen43,231ms,sendACK28,222ms.
3 Piano:60s sin cortes,5→7,gen25,040ms,sendACK50,543ms.
4 Brass:60s sin cortes,5→7,gen10,376ms,sendACK56,036ms.
5 Guitarra:UNDERRUN24,47s,cola5,gen31,411ms,sendACK70,901ms.
6 Piano:60s sin cortes,5→7,gen34,335ms,sendACK32,489ms.
Piano no es garantía de estabilidad a cola baja: mismo preset pasa y falla.
Guitarra también pasa y falla. Muestra pequeña: no estimar tasas de fallo ni
atribuir diferencias a preset o a un único componente. Máximos por etapa
no son una reconstrucción temporal del corte. En piano hay lectura23,660ms
con CPU0,135ms; en guitarra pump33,151ms/CPU4,559ms y23 cambios
involuntarios. Los tiempos sugieren investigar esperas/reactivación además
del cálculo, pero no prueban causalidad del corte.
Total12.722.176 muestras ADC válidas, continuidad índice/timestamp y IPC
sin pérdida, dropped/fatal0 en seis casos. Q restaurado exactamente cada
vez (ADC14/100k, generador apagado, WAV IDLE). Ningún caso acepta cola5
estable; conservar política normal. No modificar firmware/relay estable.


Generación asíncrona y despertar por audio, 2026-10-10
---------------------------------------------------
Driver --async-synth usa SynthProcess existente y lo cierra en finally.
--worker-wakeup implica async y multiplexa socket/pipe cuando un bloque está
pendiente. read_with_audio_wakeup no consume respuesta de worker; devuelve
vacío para que service_wav la retire, prioriza socket si ambos están listos.
Sin audio pendiente conserva Connection.read. Sólo diagnóstico, GUI normal
sin cambios. Test socketpair/pipe comprueba respuesta preservada, prioridad
de ACK y lectura normal. Audio DAC exacto de SynthProcess validado por tests.
20261010_210923_audio_owner.json: async sin despertar, target5;
Guitarra60s sin cortes5→7; BrassUNDERRUN14,970s; PianoUNDERRUN34,978s5→7.
20261010_211254_audio_owner.json: async con despertar, target5;
Guitarra/Brass/Piano60s cada uno sin cortes, targets máximos7/9/9.
Reposición del owner máxima0,952/1,097/1,454ms. No afirmar causalidad o
mejora estable entre series de una repetición; ventanas de ejecución difieren.
20261010_211644_audio_owner.json: target4 (96ms), despertar y margen
experimental3 en alarma; cortes Guitarra34,397s,Brass21,331s,Piano9,726s.
Los tres mantuvieron target4 hasta corte; NO aceptado.
Revisión de wav_queue.h: ready requiere4 bloques (salvo fin de archivo),
accepts en PLAYING requiereused>=2, guarded corta cuandoused<=1 para
proteger DMA. Margen experimental3 con target4 advierteused<=1: coincide
con corte preventivo del firmware y llega demasiado tarde. Retirados override,
CLI --low-margin y test experimental: umbral original min(4,target-2) intacto.
No concluir que crecer5→7 sea falsa alarma sólo por dos créditos pendientes:
las reservas host todavía no son datos publicados en el Q.
Los nueve casos: 14,201,058 muestras ADC íntegras, cero dropped/fatal,
IPC sin pérdida y restauración exacta (ADC14/100k, generador apagado,WAV IDLE).
No modificar firmware/relay ni promover async/despertar aGUI sin aceptación.
Próxima reducción requiere resolver tiempos de entrega y/o estudiar bloques
más cortos en firmware aislado; no reducir resguardo DMA para ocultar cortes.


WAV240 aislado (2026-10-10): experimentos/synth_wav240/README.md registra
compilación, nueve ensayos y restauraciones exactas.240p no aceptado paraGUI:
Guitarra pasó60s a96ms pero repeticiones cortaron96,085/65,956s; Brass yPiano
fallaron. Créditos4 tampoco sostuvieron96ms.19.761.152 muestras ADC íntegras.
Hostdefault480,firmware/relayV16 estables conservados. Appexperimental detenida,
V16 activa,ADC14/100k,generadorapagado,WAVIDLE. Primer arranque rechazado por
selección de relayantiguo no es evidencia de latencia; wrappercorregido y
restauración finalverificada. No confundir wallrender146ms conCPU delworker.


Revisión de ruido reportado, 2026-10-10
-------------------------------------
Sin acceso al Q ni modificación de timbre/calibración/firmware: monitor activo
según logs recientes.20261010_noise_ab.json compara DAC completo ABBA frente
/tmp/fm_before_filter_table.py y/string_before_filter_table.py:10 casos,
20/40k,Guitarra/Brass/Lead/BassPunch/WarmPad,1.152.000 muestras por recorrido,
igualdad exacta.20261010_noise_signal_check.json agrega Piano/Guitarra/Brass
20/40k, controles/notas/pedal,57.600 muestras por caso, diferencia máxima0.
En seis casos sin notas19200 muestras constantes en código2048; sin muestras
0/4095 en las secuencias con notas. Ausencia de rails no certifica ausencia de
distorsión ni ruido analógico. Comparaciones usan fuente previa a filtros/fases
pero módulos compartidos actuales: no prueban equivalencia frente a todos los
cambios históricos de timbre o calibración. No hay captura acústica/ADC externa.
LogsGUI recientes fm_20261010_184906_538660 y184657_722093 no muestran
terminalUNDERRUN/FAULT en filas disponibles; no prueba que todo transitorio
quede registrado. Pregunta pendiente: soplido, chasquidos o zumbido; distinguir
también señal visible vs ruido audible antes de retocar brillo/ganancia.


Aclaración de ruido (2026-10-10): usuario refiere timbre más sucio durante
notas en varios instrumentos, no zumbido de reposo. No inferir ruido analógico
estacionario de la primera respuesta. Pregunta auditiva pendiente: comparar
mismas notas aVol1Vpp para distinguir influencia de nivel de salida.
20261010_noise_headroom.json:1/4/11notas,velocity110,Vol2,5Vpp;
softlimit0 enPiano/Brass y0,0375% enGuitarra11notas.
20261010_noise_maxvol.json:11notas36..76,velocity127,20k,1/2,5/3,3Vpp;
fracciónDAC fuera de0,35..2,95V usada como indicador de softlimit (no prueba
acústica ni clipping del amplificador). Máximo a3,3Vpp:Piano0,0625%,
Guitarra0,1125%,Brass0%,DXPiano1,6167%. A1Vpp:0/0/0/0,0042%.
Hay saturación digital en acordes extremos, más marcadaDXPiano, pero no
explica aún timbre sucio en varios instrumentos. No cambiar calibración,
armónicos, ganancia ni ataque mientras se discrimina nivel/timbre.


Usuario informa que bajarVol1Vpp sólo mejora algo y que antes no ocurría:
no considerar saturación como explicación completa ni problema resuelto.
20261010_noise_older_source.json:Brass/Lead/WarmPad,20k,1Vpp,48000 muestras
cada uno: igualdad exacta frente a /tmp/fm_source_before_shared.py CON
CONTROLES ACTUALES IGUALES. No compara los presets históricos (ADSR cambió);
DXPiano excluido porque vieja clase no soportaosc2 FM. No extrapolar a cadena
física ni a todos los controles MIDI dinámicos.
FMSource diagnóstico agrega,preset,modelo,gate,notas/voces,pedal,niveles OSC,
filtro,drive,feedback,amplitud aplicada,pico AC último bloque ycontador de
muestras procesadas por limitador suave. Audio sin cambios:63 tests pasaron,
incluido DAC exactamente igual con/sinregistro. Se computan nuevos datos sólo
si diagnostic_path estáactivo; usa máscaras y pico ya calculados. No modifica
volumen,armónicos,ADSR ni firmware. InstanciasGUI actuales requieren reiniciar
monitor para disponer del registro nuevo. Pregunta pendiente: salida Qdirecta,
amplificador Q o audioPC para continuar localizando regresión.

### Protección de picos de salida, 2026-10-10

El usuario comparó el motor V15 y oyó el mismo sonido sucio. Se restableció el motor V16. El compresor anterior empezaba a 0,95 V de pico y tenía ataque de 3 ms; los transitorios podían atravesarlo y llegar al limitador tanh. Se reemplazó esa reducción por una ganancia máxima calculada con el pico del bloque ya generado y el margen simétrico respecto al offset, con 20 mV de reserva dentro de 0,35–2,95 V. La ganancia se reduce inmediatamente para proteger todo el bloque y recupera suavemente en 150 ms. El limitador de seguridad final permanece. No agrega bloques ni latencia de espera; puede cambiar el volumen de ataques fuertes. No modifica drive ni feedback de los presets.

Comparación host: 36 casos, 1/4/11 voces, velocidad 127, Vol 1/2,5/3,3, 20 kHz, 60 bloques de 480 muestras por caso. 1.036.800 muestras por versión. Muestras que alcanzan el limitador: Piano Virtual 30→0, Guitarra 45→0, Brass 0→0, DX Piano 741→0. Pico de salida nuevo máximo 1,28011 V respecto al offset (incluye cuantización). Estos resultados prueban protección digital de los transitorios, no aceptación auditiva ni ausencia de saturación en el amplificador.

Ensayo reproducible: `PYTHONPATH=. python diagnosticos/comparar_limitador_synth_v16.py`. Baseline guardada en `respaldos/synth/20261010_output_limiter/fm_source.py`; resultado en `diagnosticos/resultados_piano/eficiencia_v16/20261010_output_limiter_comparison.json`.

Validación: 65 pruebas de synth, proceso y diagnósticos pasaron; después de simplificar la rama de ataque a ganancia constante, volvieron a pasar las 4 pruebas específicas de transitorios, margen, metadatos y recuperación. Falta audición con amplificador/Q tras reiniciar el monitor.

### Aspereza residual y seno limpio, 2026-10-10

El usuario informa que mejoró algo pero persiste, incluso con una nota suave. Capturas `fm_20261010_192848_809628.jsonl` y `fm_20261010_192905_386092.jsonl`: DX Piano, filtro apagado, drive 1, feedback de Osc 3 en 4, cero muestras limitadas; ganancia mínima de protección 0,666 y 0,617 respectivamente. No atribuir esta aspereza al drive del filtro ni dar por resuelta la salida analógica.

Se agregó el preset diagnóstico Seno limpio: un oscilador sinusoidal, sin FM, sin feedback, sin filtro, sin Osc 2/3 ni sala. Conserva MIDI, Vol y el mismo transporte de audio. `PYTHONPATH=. python diagnosticos/verificar_seno_synth_v16.py` genera a 20/40 kHz con Vol 0,5/1/2,5 y nota A4 a velocidad 100. Tras descartar un segundo de establecimiento, se ajusta una senoide de 440 Hz y se mide residuo (incluye cuantización de 12 bits). Residuo relativo entre -54,55 y -68,69 dB; todos los casos con ganancia de protección 1 y cero muestras limitadas. Resultado en `diagnosticos/resultados_piano/eficiencia_v16/20261010_clean_sine.json`. Es verificación digital; falta escuchar una sola nota por la conexión habitual al Q. Si ese tono también presenta aspereza, investigar transmisión/reproducción/salida/amplificación; si resulta limpio, investigar modulación y timbre de los presets.

### Quinta y modulación de ganancia, 2026-10-10

El usuario oye una tecla limpia y aspereza/tremolación al tocar una quinta. La captura `fm_20261010_193316_094182.jsonl` muestra Seno limpio, notas 48/55, Vol final 0,97, cero muestras limitadas. El pico máximo y ganancia mínima son acumulados de la sesión: no asignarlos automáticamente al acorde actual. Ensayo digital con notas 48/55, velocidades 90/94, 20 kHz, 250 bloques: Vol 0,5 y 0,97 mantienen ganancia 1, residuo respecto a dos senoides -56,92 y -62,67 dB. Vol 2,5 sí tenía ganancia variable entre bloques (aprox. 0,785–0,812) y residuo -39,32 dB.

Se mantiene la atenuación máxima alcanzada mientras se sostiene el mismo gesto (notas, note_id, frecuencia, gate, Vol y offset). La recuperación de 150 ms vuelve al cambiar el gesto o soltarlo; un pico posterior mayor todavía reduce la ganancia para proteger el DAC. Evita que la recuperación siga los máximos de interferencia de las notas y module artificialmente la mezcla. No agrega cola. La cola del mismo acorde puede quedar más baja hasta el siguiente gesto; no se certifica solución auditiva. Tras el cambio, Vol 2,5 da residuo -68,78 dB. `PYTHONPATH=. python diagnosticos/verificar_quinta_synth_v16.py` reproduce el ensayo. Pasaron 65 pruebas. Está pendiente la prueba auditiva a Vol 0,25 compensando el amplificador: el defecto reportado a niveles bajos no se reprodujo en esta mezcla digital.

### Umbral auditivo de Vol 0,75, 2026-10-10

El usuario identifica una quinta limpia hasta aproximadamente Vol 0,75 y aspereza por encima, y sospecha recorte intermedio de proceso. No asumir saturación analógica ni declarar resuelto. Se agregó `diagnosticos/verificar_cadena_quinta_v16.py`: preset real Seno limpio, notas 57/64 de `fm_20261010_193846_657728.jsonl`, velocidades 90/94 y 127/127, Vol 0,5/0,75/0,8/0,97/1,25/2,5. Cada ensayo pasa por el método real `_wav_chunk_codes` de OutputReceiver y el codificador de tramas WAV; se extraen y comparan exactamente las 480 muestras empaquetadas de cada bloque. No se conecta al Q: esto valida la preparación del paquete, no el transporte físico, DAC ni amplificador.

A Vol 0,75/0,8/0,97 la ganancia es exactamente 1. Con velocidad máxima, los códigos quedan en 1210–2885 / 1154–2941 / 964–3131 dentro de 0–4095; residuo relativo respecto a dos senoides -63,25 / -63,79 / -65,49 dB (incluye cuantización). No se reproduce el umbral reportado en esa cadena host. Archivos de referencia `quinta_vol_0.75_referencia.wav` y `quinta_vol_0.97_referencia.wav`: muestras extraídas del paquete, convertidas a PCM y normalizadas al mismo pico para comparar por PC; no son grabaciones de la salida física. Resultados y audios en `diagnosticos/resultados_piano/eficiencia_v16/quinta_cadena/`. Pendiente audición comparativa y aclaración de si el recorte fue observado en una traza o identificado por oído.

### Primera captura ADC de la deformación, 2026-10-10

CSV del usuario encontrado en `capturas/v14/log_20261010_194748_14bit_40kHz.csv` (carpeta heredada del grabador). 75.550 pares, 1,888725 s, timestamps continuos de 25 us. CH1 1,00513–2,45581 V; CH2 1,40355–2,02476 V. Ninguna muestra alcanza 0/3,3 V. La forma de CH1 presenta un quiebre en la bajada de la mitad inferior, con segmentos casi rectos: no es un límite de dibujo ni un tope en los extremos del ADC. No describir como meseta plana o recorte duro ideal; es deformación asimétrica. Ajuste de frecuencia de una senoide a CH1: 174,614058 Hz (nota MIDI 53), residuo RMS 69,39 mV, -16,93 dB relativo al tono; CH2 15,65 mV, -22,26 dB. No es una medición THD formal ni prueba que identifique por sí sola la etapa causal.

Gráfico y resumen: `diagnosticos/resultados_piano/eficiencia_v16/recorte_adc/captura.png` y `analisis.json`. El sintetizador Seno limpio se verifica como mezcla lineal antes del Q, pero falta una comparación contemporánea con las mismas condiciones físicas. Firmware local: DMA envía palabras directamente a DHR12R1; inicializa el DAC mediante analogWrite y configura reloj/trigger. No se modificó ni se flasheó firmware durante este análisis. Pendiente confirmar A0→medidor y repetir al mismo Vol sin el cable del amplificador, si estaba conectado.

### Causa localizada por el usuario y vuelta a latencia, 2026-10-10

El usuario identificó que A0 estaba conectado a un circuito de baja resistencia que deformaba la salida. No seguir tratando esa deformación como regresión del motor. Se conserva V16 optimizado; los cambios de protección de picos también resolvieron recortes digitales extremos/bombeo en ensayos host, pero no eran la explicación del defecto físico observado. No se actualizó firmware ni se operó el Q en esta etapa.

Perfil host actual de 100 bloques con 11 voces y cambios de pedal/acordes: DX Piano concentra coste en render/FM; guitarra en GuitarStrings.render. Se fusionó la mezcla de dos cuerdas y la radiación por velocidad en un kernel Numba sin fastmath, manteniendo orden de operaciones, memoria de última muestra y el ruido/filtrado de ataque existentes. Se precalienta el kernel antes del audio. Comparación ABBA a 20/40 kHz, 600 bloques por recorrido: DAC exacto; medianas 2,009→1,730 ms a 20 kHz (13,9%), 1,612→1,373 ms a 40 kHz (14,8%). Ensayo reproducible `PYTHONPATH=. python diagnosticos/benchmark_radiacion_guitarra_v16.py`; resultado `20261010_guitar_radiation.json`. Las medianas son tiempos de generación host, no latencia MIDI-audio física.

También se cachean incrementos de fase para frecuencias constantes, con límite de 256 entradas de sólo lectura; las transiciones de frecuencia conservan el cálculo previo. Una comparación amplia de 28 casos/2.419.200 muestras a 20/40 kHz conserva códigos DAC exactos, pero sus tiempos tuvieron variabilidad; repetir con ABBA antes de atribuir una mejora. 89 pruebas de synth, instrumentos y diagnósticos pasaron.

Confirmación ABBA de fases: `PYTHONPATH=. python diagnosticos/benchmark_fases_synth_v16.py`, 8 casos (DX Piano/Guitarra/Brass/Piano Virtual, 20/40 kHz), 300 bloques por recorrido, DAC exacto. DX Piano: medianas 3,514→3,385 ms (3,7%) a 20 kHz y 2,627→2,477 ms (5,7%) a 40 kHz. Brass: 0,788→0,724 ms (8,1%) y 0,660→0,601 ms (8,9%). Guitarra no cambia adicionalmente por este caché. Una pasada de piano virtual a 20 kHz fue anómala; repetición aislada ABBA de 600 bloques dio 2,204/2,207 ms antes y 2,208/2,208 ms después, sin regresión material ni diferencias DAC. Datos en `20261010_phase_cache_abba.json` y `20261010_phase_piano_repeat.json`. La cola mínima y el transporte no se redujeron ni se validaron físicamente en este turno.

### Recepción SPI sin validar dos veces cada posición derivada, 2026-10-10

ConfigurationDecoder valida CRC, configuración/epoch, índices/timestamps de frontera y rango ADC; deriva los índices/timestamps interiores de cada paquete compacto. OutputReceiver ahora comprueba primera/última posición y continuidad de frontera sólo para lotes SPI producidos por ese decodificador. Conserva el recorrido completo para UART, lotes no verificados y muestras SPI retenidas durante el cambio de transporte. No retira validación del firmware ni del decodificador. La frontera del receptor sigue comprobando índice, período y wrap uint32.

Ensayo ABBA `PYTHONPATH=. python diagnosticos/benchmark_fronteras_spi_v16.py`: alimentación real de ConfigurationDecoder y procesamiento de eventos de OutputReceiver, 8 nodos/16.384 muestras por ensayo, 35 pasadas por variante (5 iniciales fuera de tiempos), todos los datos entregados exactamente iguales. Medianas antes 7,273/7,226 ms y después 4,681/4,714 ms: aproximadamente 35,2% menos tiempo host de decodificación y entrega. No usa conexión al Q, no mide latencia física ni modifica cola, timeout o firmware. Resultado `20261010_spi_emit.json`; referencia guardada en `respaldos/synth/20261010_spi_emit/unoq_config_receiver.py`.

29 pruebas de continuidad SPI, protocolo compacto, créditos/audio, trazas y latencia pasaron. Las nuevas pruebas comparan el recorrido completo con el validado, cubren wrap de índices/timestamps, rechazan fronteras incorrectas, mantienen detección de corrupción interior en lotes no verificados y preservan las 4.096 muestras de dos nodos reales del formato wire.

### Publicación MIDI antes de indicadores, 2026-10-10

FMPanel ahora publica el acorde completo al motor antes de actualizar indicadores de nota, velocidad, pedal y actividad. Conserva la aplicación previa de los controles CC y los valores de frecuencia/relación, para entregar los mismos parámetros. Evita reaplicar el estilo de actividad si su estado no cambió, y el del pedal si ya coincide. No cambia la duración de actividad (150 ms) ni su comportamiento al cerrar MIDI.

Ensayo Qt ABBA `PYTHONPATH=. QT_QPA_PLATFORM=offscreen python diagnosticos/benchmark_publicacion_midi_v16.py`: 350 lotes por variante, cambios de acordes, CC1, CC7 y pedal; 50 lotes iniciales fuera de tiempos. Parámetros FM exactamente iguales. Medianas hasta actualización del motor antes 428,806/430,317 us, después 332,559/332,292 us (unos 97 us menos). Tiempo total de poll antes 431,389/433,098 us y después 380,475/380,832 us. No mide transporte MIDI físico ni espera de la cola DAC. 66 pruebas FM/latencia pasaron.

### Reensayo físico con motor y recepción optimizados, 2026-10-10

Resultado `diagnosticos/resultados_piano/eficiencia_v16/20261010_231430_audio_owner.json`. Dueño dedicado del Q, ADC 14 bits/40 kHz, DAC 20 kHz, bloques de 480 puntos, dos créditos, 11 voces y cambios de acordes/pedal; pausas forzadas del padre por GC. Sin GUI ni entrada MIDI física: este ensayo valida continuidad y tamaño de cola, no latencia total MIDI-audio ni calidad acústica. No se modificó firmware.

| Instrumento | Cola inicial | Duración | Resultado |
| --- | --- | --- | --- |
| Guitarra | 120 ms | 60 s | PLAYING, sin crecimiento |
| Guitarra | 96 ms | 1,414 s | UNDERRUN, reason 2 |
| Brass | 120 ms | 60 s | PLAYING, sin crecimiento |
| Brass | 96 ms | 60 s | PLAYING, sin crecimiento |
| Piano Virtual | 120 ms | 60 s | PLAYING, sin crecimiento |
| Piano Virtual | 96 ms | 60 s | PLAYING, pero crecimiento a 6 bloques/144 ms; no pasa el criterio de 96 ms |

En el fallo de guitarra, envío-a-ACK máximo 64,876 ms frente a generación máxima 6,310 ms: la espera domina ese episodio, aunque el ensayo no identifica por sí solo su etapa causal. Brass a 96 ms sigue experimental; una pasada de un minuto sin GUI no permite promover el mínimo general. Se conserva el mínimo de producción de cinco bloques a 20 kHz.

Los seis casos conservaron continuidad exacta ADC/IPC (12.048.214 muestras en total), dropped=0 y fatal=0. Se verificó restauración del perfil previo después de cada caso: ADC 14 bits/40 kHz, generador deshabilitado con sus parámetros originales y WAV IDLE. El proceso finalizó correctamente.
