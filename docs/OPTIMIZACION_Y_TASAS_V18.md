# Optimización integral y tasas V18

Solicitud: 20 voces Synth, revisión de toda la cadena con Astra, objetivo
ADC8 cercano/superior a 1,8 MS/s e incrementos en las demás resoluciones.
V17 y sus tasas públicas se preservan.

## Primera revisión Astra

La separación de I/O de V18 elimina compartir el GIL con la GUI, pero no
resuelve por sí sola las demoras de SPI/READY/Linux ni califica las tasas
privadas anteriores. A 160 MHz, 89 ticks producen 1.797.752,809 S/s y 88 ticks
1.818.181,818 S/s; no existe 1.800.000 exacto con divisor entero.

Revisar por etapas, con el mismo control antes/después:

| Etapa | Medida y criterio | Trabajo |
|---|---|---|
| ADC/DMA | continuidad, dropped/fatal, cola y slack | candidatos privados; no degradar sobremuestreo16 |
| SPI/relay | ciclo de envío medio y cola pico; margen >=10% | conservar SPI40/WORD ADC8 antes de variar reloj |
| USB/hijo | read/decode y saturación | no compilar ni consultar Docker durante alta carga |
| IPC RF | bytes y CPU serialización, edad de lote | transmitir uint32 crudo y convertir voltajes en host |
| DSP | duración y edad de lotes, FILTER OFF sin trabajo | conservar fuente y barreras de generación |
| GUI/FFT | Paint y exposición real, pendientes acotados | medir vista activa, no inferir FPS de timers |
| PCM/DAC | played/accepted, reserva y underrun | productor acotado, warmup previo, créditos confirmados |
| Synth | 20 voces y CPU por480muestras | seno/DX/Piano Virtual a20/40k; separar JIT de render |

No reemplazar medición por memoria compartida ni aumentar buffers sin saber
qué pausa absorben. Mantener RF/ACK FIFO y créditos hasta consumo GUI.

## Optimización IPC incorporada para validar

`RawRfBatch` transmite arrays uint32 y metadatos. El proxy convierte las
columnas con un `SampleClock` por generación antes del DSP y dibujo. Los
valores, wrap, NaN CH2 y créditos conservan el contrato anterior.

[Benchmark local](../diagnosticos/resultados_v18/rf_batch_cpu.json): por lote
20ms ADC8/1,6MS/s, pickle pasó de896465 a512820bytes (-42,8%). P95 roundtrip
local0,557→0,111ms. No equivale a tiempo de IPC real ni mejora física delSPI.
Pruebas de valores exactos y regresiones proxy/owner pasaron15casos.

## Candidatos preparados, todavía sin calificación física

`experimentos/fs_max_v18/` contiene una copia de MCU/relay y perfiles privados.
No escribe `arduino/v17` ni publica las tasas en el monitor. Prepara:

- ADC8: 1,633 /1,667 /1,702 /1,739 /1,778 /1,798 /1,818 MS/s.
- ADC10: 1,270 /1,290 /1,311 MS/s.
- ADC12: 1,081 /1,096 MS/s.
- ADC14: 869,565 /888,889 /909,091 kS/s.
- ADC16 CH1: 145,455 kS/s, con control CH1/80k; no sustituye el dual.

MCU/relay comparten tabla y selección SPI40 también antes de CONFIG. El
empaquetadorC real, validadorC relay y decoderPythonV18 pasan extremos,
wrap, padding y corrupción para los17perfiles con sanitizadores. Eso sólo
acredita el contrato del software: no conversiónADC ni estabilidad física.

Próximo: backup y snapshot/identidad exactos; compilar candidatos a carga baja;
sondeo escalonado sin reintentos selectivos, preservando errores. Después de
cada campaña restaurar firmware/relay/montajes/políticaCPU/configuración y
verificar10s. Finalistas:60s+3×120s independientes, luegoGUI/RADIO/FILTER/A0
visible. Separar integridad, holgura, calidad analógica y capacidad dual.

## Cierre de compilación aislada

`experimentos/fs_max_v18/compile_report.json`: compiló, no instaló, restauró
el Q y verificó10,00577s/16.005.600muestras sin dropped/fatal. El compilador
informa124020bytesflash y257948bytesRAMglobal (98%,4196byteslibres).
No agregar buffers antes de revisar stack/heap y distribución de memoria.
La compilación no acredita1,8MS/s. Próximo bloque pendiente: sondeo físico con
runneraislado y restauración auditada, seguido de calificación de finalistas.

## Sondeo físico aislado iniciado ·22/10/2026

Astra aprobó la preparación tras auditar rollback y memoria, sin aprobar tasas
para producción. Se creó Scope V18 Rate Probe independiente y se retuvo el
contenedor original detenido, sin modificar fuentes de V17.

Dos intentos de preparación se conservan: `resultados/20261022_191505` falló
antes de modificar el Q por un parser de política CPU; se sustituyó por APIs
os.sched. `20261022_191521` no llegó a medir por timeout60s del primer arranque.
Ese cierre verificó firmware, relay, CPU y recuperación10s restaurados.
Se amplió sólo el plazo administrativo a240s y se incorporó journal atómico
previo a cada cambio y adopción de fuentes idénticas por SHA256.

Campaña `experimentos/fs_max_v18/resultados/20261022_192111` concluida: los
siete sondeos ADC8 de 15 s pasaron integridad hasta 1,818 MS/s. El mayor perfil
registró cola pico 5 y margen medio 12,46%; no está calificado ni incorporado.
El cierre confirmó restauración de identidad, relay, CPU y recuperación.


## Recuperación PCM de RADIO · 23/10/2026

Astra identificó que el productor remoto serializaba un bloque por ronda IPC,
aunque el receptor ya permitía recuperar hasta ocho por ráfaga. Los fallos
intermitentes mostraron audio disponible en el host mientras se vaciaba el DAC.

V18 agrupa únicamente RADIO según créditos y tokens existentes, con máximo
ocho bloques. El host produce secuencialmente y devuelve el prefijo disponible;
el receptor lo consume por offsets exactos y reintenta el siguiente pendiente.
No se amplían la cola DAC de 30 bloques ni los buffers de la fuente. WAV/Synth
mantienen sus solicitudes individuales. La caché agrupada puede añadir hasta
96 ms de audio ya producido, también al cambiar sintonía dentro de la sesión.

Validación local: 167 tests del backend y 21 GUI aprobados; incluye prefijos
parciales, sesión obsoleta, falta de audio, créditos y contabilidad de ráfaga.
`gui_pair_v18_burst_40k_20261023.json`: recorrido de 50 s aprobado con Scan,
RADIO/A0, retune, Stop, WAV, Synth de 20 voces y restauración. La traza confirma
peticiones de 1–4 bloques en esta corrida (máximo permitido: ocho); intervalo
máximo observado entre envíos RADIO: 63,98 ms. Es una observación de esta
corrida, no un límite garantizado ni una comparación controlada de rendimiento.
La prueba sin traza a 8 bits/1,6 MS/s falló cerca de 40,9 s por UNDERRUN
y acumulación RF posterior. Restauró correctamente, pero no completó el
objetivo de 60 s. Se compara cadencia de dibujo de 50 ms sólo en el smoke;
La comparación de 50 ms también falló (~29,9 s), aunque el render consumió
25–29 % de CPU del hilo en ventanas de cinco segundos. No se atribuye
resolución al burst ni se cambia la cadencia del producto.
Las tasas máximas públicas siguen sin cambios.


## Tasas: primeros resultados físicos · 23/10/2026

Las tres corridas RADIO120 del perfil público ADC8/1,6 MS/s pasaron, con
restauración. Se retomó el objetivo privado de 1,818 MS/s y los incrementos
de 10/12/14 bits, sin publicar perfiles nuevos.

- `resultados/20261023_013204`: ADC10/126ticks (1,270 MS/s) perdió muestras
  antes de completar el sondeo. Trama rechazada CRC correcto, dropped=1.
  Recuperación e identidad confirmadas; el informe original conserva una
  discrepancia de configuración del relay. Inspección posterior en
  `post_restore_verification.json` confirmó configuración equivalente.
- `resultados/20261023_013512`: ADC12/148ticks (1,081 MS/s) perdió muestras;
  restauración completa confirmada. Se detuvo antes de ADC14.
- `resultados/20261023_013724`: ADC8/88ticks (1,818 MS/s) pasó 60 s,
  cola pico6/8, margen medio12,44 %, restauración confirmada. Holgura no aprobada.
- `resultados/20261023_014040`: la primera repetición120s de ese ADC8 perdió
  muestras (cola8/8); se detuvo la campaña y restauró completamente. No califica.

Se prepara comparación SPI40/WORD para ADC10/12 en app separada
`scope-v18-rate-probe-spi40`. Usa cuatro slots de adquisición, conserva
resolución/empaquetado y ajusta bloques a696/576muestras. Los frames auxiliares
caben al final del espacio libre de timestamps (assert7488×8+1984≤65536), sin
nuevos buffers. Contratos C/relay/Python de17perfiles aprobados en ambas recetas.
El runner permite --recipe y --repeats, con logs independientes por repetición.


### Comparación SPI40/WORD ADC10/12

`resultados/20261023_014440/report.json`, receta `spi40_10_12`: cinco sondeos
15s pasaron integridad y restauración completa.

| Bits | Tasa MS/s | Cola pico | Margen medio envío |
|---|---:|---:|---:|
|10|1,269841|2/4|23,68 %|
|10|1,290323|3/4|23,97 %|
|10|1,311475|3/4|21,77 %|
|12|1,081081|3/4|24,15 %|
|12|1,095890|4/4|23,16 %|

Frente a los fallos anteriores de ADC10/126 y ADC12/148, el cambio combinado
SPI40/WORD pasó estos sondeos; no separa la contribución de cada modificación.
ADC12/146 no aprueba holgura por cola4. Ningún perfil se incorpora por estos
sondeos breves: faltan60s+3×120s, carga GUI/RADIO y aceptación analógica.

`wide8/` conserva27648muestras de cola (4×6912 frente a8×3456), sin más RAM;
se prepara prueba60s para amortizar gestión por nodo. Una reducción del número
de nodos ocupados no equivale por sí sola a mayor reserva temporal.


### ADC8: alternativa de nodos largos descartada

`resultados/20261023_015222/report.json`, wide8:60s de integridad aprobados,
cola pico4/4, margen medio envío4,38 %, restauración completa confirmada.
No aumenta capacidad total ni RAM, pero empeora margen frente a3456/8slots.
No se elige para avanzar ni se presenta el menor conteo de nodos como holgura.
El objetivo ADC8/1,8 sigue sin calificar. SPI40/WORD10/12 queda como línea
prometedora pendiente de pruebas sostenidas; ADC14 se sondea por separado.


### ADC14 y siguiente comparación ADC8

`resultados/20261023_015831/report.json`:14bits/184ticks (0,869565MS/s)
PASS15s, cola3/4 y margen23,20%;180ticks (0,888889MS/s) PASS15s,
cola4/4 y margen21,85%;176ticks (0,909091MS/s) perdió muestras. Restauración
completa confirmada. Priorizar184 para calificación, no incorporar aún.

Receta `spin100`: mismo MCU, reloj y buffers que baseline; sólo espera READY
hasta100µs antes de poll en el relay frente a50µs. Se compara ADC8/88ticks
por60s. Aumenta espera activa y debe medirse; no se presenta como optimización
confirmada ni modifica el relay de producción.


`resultados/20261023_020147/report.json`: spin100 ADC8/88ticks pasó60s,
cola7/8 y margen12,09%, restaurado. No mejora frente a50µs y no se elige
para promoción. El objetivo ADC8/1,8 continúa abierto. Se inicia calificación
60s de ADC10/122 y ADC12/148 con SPI40/WORD; después ADC14/184.


### Calificación60s de ADC10/12 y variantes ADC8

`resultados/20261023_020515/report.json`:SPI40/WORD ADC10/122 PASS60s,
cola3/4,margen22,17%;ADC12/148 PASS60s,cola2/4,margen24,41%. Restauración
completa. Campaña3×120 por perfil iniciada en `resultados/20261023_021652`.

TXClean (`resultados/20261023_020955`):ADC8/88 PASS60s,cola6/8 y margen11,95%,
restaurado. No aporta mejora medida y no se promueve. La variante conservó
RX y sólo cambió mantenimientoTX a clean, apoyándose en las operaciones por
rango de [DCACHE documentadas por ST](https://dev.st.com/stm32cube-docs/stm32u5-hal2/2.0.0-beta.1.1/docs/drivers/hal_drivers/dcache/hal_dcache_how_to_use.html).
La validez de una operación de caché no implica mejora de rendimiento.

Preparado `word14/`:extiende SPI40/WORD aADC14,frames496muestras y cuatro
slots, sin más RAM;contratoC/relay/PythonPASS5perfiles, aún sin medida física.
Preparado `full8/`:872muestras útiles/frente864 porframe,N3488 y8slots,
cola27904muestras frente27648. Los samples ydescriptores caben en la misma
unión estática;sin crecimiento de RAM. Requiere contrato y prueba física.

FrameMetrics agrega métricas ponderadas por trama sin guardar la lista de
cada status durante120s. Conserva contador,suma,maxcola yslackmínimo;test
numérico deponderación agregado. Esto cambia carga del runner, no del MCU;
comparaciones posteriores deben distinguir esa diferencia del firmware.


### Integridad sostenida SPI40/WORD completada

`resultados/20261023_021652/report.json`:seis corridas120s aprobadas y
restauración completa verificada. ADC10/122:colas3/4/4, márgenes21,66/21,82/
22,01%;integridad sostenidaPASS,holguraNO. ADC12/148:colas3/2/3,
márgenes24,36/24,25/24,29%;integridad yholgura aisladaPASS. Junto con60s
previos completa60+3×120 por perfil. Falta GUI/RADIO y aceptación analógica.

Full8 contrato: el test de corrupción de padding asumía bytes libres en el
último frame. Con872muestras no hay padding;alterar byte987 es modificar un
ADC válido. Se corrigió el test para exceder count cuando el payload está
completo. Baseline/SPI40/WORD14/Full8 pasaron los contratos tras la corrección.
La preparación física023249 se canceló yrestauró antes de medir; su informe
queda conservado. Prueba física Full8 relanzada sólo tras los cuatro pases.


### Full8 no completa la calificación sostenida

`resultados/20261023_024131/report.json`:dos120sPASS,cola7/8,márgenes13,00/
13,07%;tercera perdió muestras a28,293s (51.298.016muestras válidas observadas).
Cola8/8 antes del cierre;trama rechazada dropped1 yCRCcorrecto. Restauración
completa confirmada. Conservar ambos pases y el fallo;no se publica1,818MS/s.
La optimización de payload aporta una ganancia pequeña, insuficiente para
calificación. Otros cambios menores medidos tampoco resolvieron el límite.
Siguiente líneaADC8 requiere reducir costo por transacción/encapsulado de
transporte con diseño y pruebas específicos;no aumentar reloj a ciegas.

## ADC8: CRC del relay y verificación PING por palabras

CRC8 (`resultados/20261023_091613/report.json`) pasó 60 s a 1,818181 MS/s sin pérdidas y restauró producción. Cola pico 6/8, margen 13,063%, sin holgura. El cambio acelera el CRC aislado, pero no demuestra mejora material de transporte.

Se prepara WordPing: misma trama y comprobaciones, patrón PING validado por palabras con máscaras constantes y cargas seguras. No cambia reloj ni buffers; conserva CRC8 del relay y utiliza app experimental propia. Comparación contra versión original y alteración de cada bit del payload con CRC válido: PASS. Contrato de datos C/relay/Python PASS. Resultados de microbenchmark host en `experimentos/fs_max_v18/resultados/offline_crc_wordping_20261023/`; no son tiempos STM32.

WordPing físico 60 s (`resultados/20261023_092057/report.json`): PASS sin pérdidas, restauración confirmada; cola 6/8, margen medio 15,7146%, sin holgura. Frente al sondeo CRC8 de 13,0630%, mejora 2,65 puntos porcentuales; check PING del estado final baja 49→26 us. Es una comparación de sondeos, no una garantía de estabilidad. Se inicia calificación 3×120 s.

## BatchFast ADC8: calificación privada del 23/10

El candidato ADC8/88 alcanza 1.818.181,818 S/s. El transporte aislado pasó
60 s y tres arranques independientes de 120 s, con cola pico 2/8 y margen
medio de envío 20,27–20,38 %. Además, tres corridas GUI independientes
completaron RADIO/A0 durante 120 s, Scan, resintonía, WAV, Synth de 20 voces
y cierre, con restauración de producción verificada en cada caso.

[Evidencia consolidada con hashes](../experimentos/fs_max_v18/resultados/batchfast_acceptance_20261023.json).
Los ensayos GUI usaron actividad macOS `user` y guardia temporal de pantalla.
Con CH1+RADIO, la pintura mínima por intervalo fue 14,23–17,17 FPS; no se
atribuye 60 FPS a la cadencia del temporizador. La aceptación analógica sigue
pendiente. No se habilitó ninguna tasa pública nueva.

BatchFast combina CRC rápido en relay, WordPing, SPI16, dos tramas SCP1 por
intercambio y decodificación única con validación de ambas mitades antes de
aplicar comandos. El host V18 evita retener el lock PCM durante correlación
de realimentación y conserva telemetría de entrega. Los fallos anteriores
permanecen documentados; estos resultados no prueban una causa única.

Antes de incorporarlo: regresión de los máximos públicos CH1/dual, ensayo con
las condiciones de actividad de la aplicación normal y respaldo pareado del
candidato. V17 permanece congelada: 175 hashes verificados sin diferencias.

## Regresión BatchStack de perfiles públicos

`experimentos/fs_max_v18/resultados/regression_20261023_205425/report.json`
completó nueve máximos nativos públicos CH1/dual de8/10/12/14 y16dual,
15 s por perfil, con integridad y restauración PASS. Cola pico1–2 y margen
medio15,56–84,42 %. Es screening, no calificación sostenida de los nueve.

BatchFast falló en dual8/632411 con dropped1 y CRC correcto
(`regression_20261023_204039`), restaurado. Se separó el pipeline dual de la
selección del reloj y del validador rápido CH1: scratch dedicado en el stack
permanente de output_worker, no en timestamps DMA. Esta variante es otra app,
BatchStack; el candidato CH1 calificado BatchFast permanece intacto. La variante
intermedia BatchNative con1984bytes BSS adicionales no obtuvo READY en dos
arranques, ambos restaurados; el límite de memoria es hipótesis, no causa
confirmada por log MCU. BatchStack sí arrancó y completó los nueve perfiles.

Respaldo pareado del BatchFast validado: `respaldos/parejas/v18_batchfast_20261023/manifest.json`,
con firmware/relay binarios verificados contra las identidades medidas y fuentes
monitor/Q. Ninguna tasa pública nueva habilitada. Continúa GUI120 de BatchStack
sin actividad macOS ni guardia de pantalla del arnés.

## Revisión de promoción y BatchArena

Astra revisó propiedad DMA, stack y cambios de época. No observó uso después
de retorno en BatchStack, pero su scratch residente consumía1984 de4096bytes
del worker. Se prefirió BatchArena: dos SampleFrame al final de DualMemory,
135616bytes dentro de la unión de163840, sin crecimiento de RAM global y sin
cambiar offsets de ADC/timestamps/muestras. Asserts de ABI objetivo y tests
ASan/UBSan de canarios/rebinding PASS. ELF exacto en artifacts de transitions
230035: storage0x28060, workerprólogo36registros+52locals; esto confirma que
no conserva el array2k, no constituye cota completa del stack de callees.

BatchArena completó15etapas sin reinicio: tres ciclos WordCH1→dual8→normal14
→dual10→WordCH1; cada etapa exige APPLIED y datos del epoch actual, luego5s
sin pérdidas. Incluye dual8 con9fragmentos por nodo. Informe
`experimentos/fs_max_v18/resultados/transitions_20261023_230035_900025/report.json`,
restauracióntrue. La matriz completa y campañas sostenidas del nuevo binario
se registran aparte; no se heredan identidades de BatchStack.

BatchStack quedó como antecedente respaldado en
`respaldos/parejas/v18_batchstack_20261023`: aislado60+3×120 yGUI3×120 sin ayudas
macOS/guardpantalla PASS, cola2 y margen20,31–20,52%, restauracionestrue.
No está promovido. Scope V18 de producción y V17 siguen conservados.

## 24/10: latencia PCM, desacople de DSP y fallo residual DAC

Se instrumentó el recorrido del pedido PCM sin cambiar firmware ni reservas.
GUI102904 falló con hasta302ms antes de atender el pedido, mientras la espera
del ejecutor fue5,8ms y el render14,7ms. Se añadió canal acotado independiente
para pedidos PCM; muestras y ACK de control siguen en su FIFO. Las pruebas
spawn verifican atención PCM sin consumir previamente RF.

El callback publica ahora audio demodulado antes de la correlación pasiva del
detector de loops; la detección positiva sigue vaciando/cortando salida. Se
separó el crédito IPC de la copia RF ya procesada de su consumo GUI durante
RADIO y WAV BUFFERING/PLAYING. La GUI retiene el lote completo bajo el mismo
DeliveryBudget; no se descartan muestras ni se amplían reservas. Tests de
liberación única y estados WAV verifican ambos caminos.

Con este host, `gui_private_20261024_111112/report.json` completó RADIO/A0
120,147s, Scan, WAV, Synth20 y apagado, sin errores, restaurado. La repetición
`111621` falló por UNDERRUN a~44s: audio disponible en padre, RPCmáx50,6ms,
ACKmáx215ms y15CHUNK en vuelo. También restaurada. Por tanto NO está cerrada
la aceptación combinada, y1,818MS/s sigue privada.39tests localesPASS;
V17 conserva175hashes del respaldo.

Astra revisó el último tramo: read/decode no medían el procesamiento posterior
de eventos ni huecos entre pumps. No se atribuye aún la demora a ADB/MCU;
TCP_NODELAY ya existe en ambos extremos propios. Los480samples restantes
reportados al UNDERRUN son contabilidad de la guardia, no audio DMA utilizable.
Siguiente evidencia: wall/threadCPU del receptor completo con ring acotado,
sin cambiar arbitraje ni colas. Una actividad macOS sólo en padre no evitó
el fallo; eso tampoco descarta descheduling del proceso receptor separado.

## 24/10 · cierre para prueba manual

La combinación final pasó tres corridas privadas independientes con RADIO/A0
120 s, Scan, WAV, Synth20 y cierre. [Evidencia consolidada](../experimentos/fs_max_v18/resultados/batcharena_acceptance_20261024.json).
La exposición de la ventana varió y se registra en el informe; esos pases no
constituyen una afirmación de 60 FPS ni aceptación analógica.

El monitor normal sin flags especiales también pasó a8bits/1,6MS/s, con RADIO
60,323s y todas las etapas, restauración10s sin pérdidas. Informe:
`diagnosticos/resultados_v18/gui_public_stock_final_20261024.json`.
La actividad macOS durante adquisición se crea en padre/receptor y se libera
al cerrar; no cambia preferencias de reposo. El máximo público sigue en1,6MS/s.
1,818MS/s espera incorporación y validación de la pareja instalada.

El usuario pidió probar: Q libre/restaurado, sin campañas activas. Se preservó
la pareja actual con fuentes, app, binarios y manifiesto; V17 conserva175hashes.
