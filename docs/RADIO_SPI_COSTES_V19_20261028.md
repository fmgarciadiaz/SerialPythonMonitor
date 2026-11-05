# RADIO/A0: costos por batch SPI · 28/10/2026

Continúa la [medición del intercalado](RADIO_SPI_V19_20261028.md), tras
[descartar admisión alternada de CHUNK](RELAY_CHUNK_PACING_V19_20261028.md).
Se mantiene relay/firmware aceptado. Sólo se aplica ACK-refresh en el proceso
host privado; sin tocar ADC, tasas, buffers ni propiedad DMA.

## Método revisado con Astra

Se recogen los campos existentes `prepare_us` y `check_us`, offsets40/44 de
los frames nativos. Ambos describen el batch físico anterior. Preparación
incluye bloqueo de salida, copias y sellado; check incluye validación y
procesamiento de comandos. No son tiempos exclusivos de CRC ni de TCP.

Se deduplican por época y `sequence//2`, con wrap. Se conservan sólo tres
batches recientes y128 grupos de histogramas acotados. Perfil/época previos
se marcan iguales, distintos o desconocidos. El resumen estricto incluye
únicamente observaciones PLAYING cuyo batch anterior también se observó en
PLAYING y con igual perfil/época. No extrapola silenciosamente lo no cubierto.

Los estados nativos sin muestras participan en salud (pico, ocupación, slack
y errores), sin añadir muestras ni volver a ponderar envío del nodo anterior.
Los frames de stack tipo21 no se interpretan como envío. El observador no
agrega relojes al MCU, solicitudes ni alteraciones de bytes.

El mix previo describe lo transmitido por MCU; check mide lo recibido y
procesado. No inferir que un ACK WAV visible identifique el CHUNK que generó
ese costo. Los límites de fase son observaciones host, no marcas temporales MCU.

## Evidencia

Primera corrida `radio_spi_costs_20261028`:60s de audio sin errores,
STOP/cierre/restauración confirmados, ventana oculta. Mostró preparación
alrededor145µs y check70µs. El observador inicial aún no marcaba fronteras
de época ni recogía extremos de salud presentes sólo en estados vacíos.
Se preserva como diagnóstico inicial, no aceptación visible ni fuente estricta.

Corrida corregida `radio_spi_costs_verified_20261028`:60,043s,
2.400.480 muestras de audio, cero errores,12/12 observaciones PLAYING expuestas,
1.431Paint. STOP confirmado2,730ms, cierre y restauración confirmados.

| Medida | Resultado |
|---|---:|
| Batches con timing en PLAYING |68.079|
| Subconjunto estricto estable |68.077 (99,997%)|
| Batches físicos observados en fase |68.078|
| Preparación media / máxima |145,256 /417µs por batch|
| Check medio / máximo |70,510 /394µs por batch|
| Cable nominal SPI40MHz |396,8µs por batch|
| Costo parcial nominal sumado |612,566µs por batch cubierto|
| Servicio medio MCU |1.684,144µs por nodo|
| Presupuesto |1.874,8µs por nodo|
| Margen / pico de cola |10,169% /4: **FAIL**|

La diferencia de uno entre conteos físicos y timing por fase se conserva:
los límites de fase host se observan en mitades distintas. No truncar ni
forzar igualdad de conjuntos. Hubo1.987 estados vacíos en PLAYING considerados
en los extremos de salud, sin ponderarlos de nuevo como envío de datos.

`prepare + check + cable` es sólo un costo parcial nominal por batch cubierto,
no utilización de CPU ni duración total del ciclo. No restar “dos batches
medios” al servicio por nodo: hay ACK, huecos y fronteras. El tiempo no explicado
incluye READY, partes de exchange, planificación y trabajo entre iteraciones;
no se asigna automáticamente a TCP.

46 tests dirigidos pasan (fronteras, dedup, wrap, histogramas, estados vacíos,
identidad, locks, rollback y resumen ponderado). Los hashes runtime siguen
iguales a la revisión global; V17/V18 intactos. No se promueve ningún candidato.

Herramientas: `relay_wire_metrics_v19.py`, `spi_batch_timing_v19.py` y
`summarize_spi_costs_v19.py`. Resumen reproducible en `cost_summary.json`;
los contadores completos y distribuciones permanecen en `wire_metrics.json`.

## Siguiente paso revisado

Astra propone comparar compilaciones aisladas de `prepare_batch_half` conOs
yO2, antes de cualquier despliegue. El comentarioOs limita la huella LLEXT:
comparar ensamblado hotpath, secciones/símbolos/relocaciones, RAM y pilas mediante
`.su`/callchain. Descartar sin hardware si no cambia el camino caliente o crece
sin explicación. No está implementado ni habilitado para instalar.

Los145µs incluyen espera de `output_lock`, preempciones y flags de transporte:
no son íntegramente optimizables por compilador. CRCcompute, data_frame y
build_samples ya llevanO2; el cambio sólo podría afectar selección, copias e
inlining del wrapper. No quitar comprobaciones ni modificar propiedad DMA.
