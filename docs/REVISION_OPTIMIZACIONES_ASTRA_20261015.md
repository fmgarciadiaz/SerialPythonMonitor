# Revisión de optimizaciones con Astra — 15/10/2026

Revisión de fuentes V17 con Astra y comprobación del coordinador. Sin cambios
de implementación ni operación del Q. Los costes indicados como tamaños son
cálculos de geometría; no son mediciones de tiempo ni de FPS.

Las dos rondas documentadas en OPTIMIZACIONES_ASTRA_V17.md ya incorporaron
IPC selectivo, caché de perfiles, análisis FFT compartido, ventanas mixtas
acotadas, trigger mixto vectorizado y Power en trabajador. No repetirlas.

## Prioridad 1: evitar trabajo innecesario en heatmap

- `monitor/v17/spectrum.py:1192`: con un panel Ninguno, values=None limpia
  curvas pero sólo salta el resto en modo FFT. En heatmap sigue construyendo
  y enviando una imagen enteramente NaN. Omitir la actualización del panel
  desactivado y limpiar su imagen una vez al cambiar selección.
- `monitor/v17/spectrum.py:1172`: dos paneles del mismo canal ejecutan
  `_amplitudes` dos veces por block_end. Compartir resultado por canal dentro
  de cada bloque; la caché de la ruta FFT no cubre esta ruta.

Verificar selección Ninguno, reactivación, mismo canal en dos paneles,
cambio de canal, discontinuidades y coincidencia de espectros. Medir número
de análisis e imágenes publicadas y tiempo p50/p95 antes/después.

## Prioridad 2: raster del heatmap

`monitor/v17/spectrum.py:1225` reserva y rellena float32 de
`(N/2+1) × count` por panel y actualización. Con N65536 y count512 son
64,002 MiB; con RF1,4035 MHz, 10 s y overlap75%, count300 son 37,501 MiB.
El hop impone límites por resolución, duración y 30 columnas/s; 512 no es
el tamaño usado en todas las configuraciones.

En log se construye primero ese raster completo y después se interpola a
un máximo de 512 filas. Evaluar construir directamente la representación
log usando los mismos índices/pesos y NaN, conservando los espectros completos.
Para lineal, evaluar reutilizar un buffer con propiedad clara frente a Qt.

Verificar igualdad numérica, huecos temporales, picos estrechos, cambios de
escala/duración y contexto; medir asignaciones y pintura por separado.

## Prioridad 3: extender el trigger vectorizado

`monitor/v17/app.py:5415` (RADIO sola) y `:5599` (RF sola) todavía recorren
los cruces en Python y ejecutan min/max sobre hasta diez muestras por cruce.
El renderer mixto ya fue optimizado, pero estas rutas conservan el posible
coste patológico con muchos cruces que no cumplen histéresis.

Aplicar la misma estrategia conservando umbrales propios de cada ruta,
último cruce válido e interpolación donde ya existe. Comparar con referencia
ruido/outlier, AM, ambos flancos, Auto/Normal/SINGLE, NaN y ventanas cortas.
No extrapolar a estas rutas la mejora medida anteriormente en modo mixto.

## Próximo paso

Comenzar por el panel heatmap Ninguno y la FFT duplicada del mismo canal:
son cambios acotados con validación offline directa. Después medir raster y
trigger antes de ampliar la intervención. Mantener RADIO40, controles de
integridad, cola acotada, generaciones y ACK.

La aceptación física de las fuentes host actuales y el margen de envío
siguen separados: la evidencia anterior de 8,69–8,83% no demuestra >=10%
de holgura conjunta ni mejora por optimizar GUI. No se verificó el estado
actual del Q durante esta revisión.

## Implementación acotada — 15/10/2026

Autorizado el primer bloque, se implementaron las dos mejoras de prioridad 1:

- Heatmap omite raster y publicación de imagen para paneles en Ninguno.
  El reset de selección limpia su imagen; una comprobación adicional evita
  conservar una imagen previa al omitir el panel.
- Un diccionario local por block_end comparte el espectro de un mismo canal
  entre paneles. No persiste entre bloques ni cambios de configuración.
  Los espectros se leen para construir las imágenes, sin modificarlos.

Verificación con el Python 3.13 configurado en `.vscode/launch.json`:
77 pruebas de `test_fft_widgets`, `test_radio_ui` y `test_spectral_analysis`
pasaron en 36,436 s. Incluyen tres nuevas regresiones para análisis único
por canal/bloque, igualdad exacta con el espectro de referencia, raster
idéntico entre paneles en lineal/log, selección Ninguno y reactivación,
cambio a CH2 y huecos NaN con recuperación.

Se verificó eliminación de análisis duplicados y publicaciones innecesarias;
no se midió una aceleración temporal ni FPS. Raster incremental/proyección
log directa y trigger RF/audio permanecen pendientes. Sin operación del Q.

## Continuación: trigger RF y audio — 15/10/2026

La búsqueda de RF sola y RADIO sola usa ahora `trigger.last_trigger_crossing`.
Primero comprueba el último cruce: conserva el coste acotado del caso tonal
habitual. Si falla, evalúa los candidatos restantes con diez operaciones
vectorizadas en lugar de un bucle Python por cruce.

Conserva el último índice aceptado, los umbrales propios de cada ruta y las
diez muestras de histéresis. Un NaN dentro del lookback invalida ese candidato,
como en el min/max anterior. La interpolación audio sigue en su ruta original.
No cambia el renderer mixto ni la adquisición/DSP.

Las pruebas comparan con la búsqueda anterior en ruido pequeño, outliers,
AM, ambos flancos, ventanas cortas, NaN e infinitos. Una regresión de interfaz
compara ambas búsquedas en RF y RADIO con Auto/Normal/SINGLE, incluidos ejes,
muestras, estado de captura y mensajes.

Runner de comparación: `diagnosticos/benchmark_trigger_v17.py`. Mide sólo
selección de cruce con entradas fijas y llamadas alternadas, no render completo,
FPS ni transporte. No se opera el Q.

Verificación: 91 pruebas de trigger, RADIO/UI, FFT/UI y procesamiento pasaron
en 51,180 s con el Python 3.13 del proyecto. El benchmark se repitió después
de la suite, sin pruebas en paralelo; 60 pares alternados por caso, descartando
cinco pares de calentamiento. Todos los índices coinciden con la referencia.
Resultado: `diagnosticos/resultados_v17/trigger_search_controlled_20261015.json`
(incluye hashes de las funciones comparadas).

Medianas de búsqueda, ventana de 12000 muestras, ambos flancos:

| Entrada | Anterior | Nueva |
|---|---:|---:|
| AM | 0,0210 ms | 0,0203–0,0206 ms |
| Ruido pequeño | 6,0585–6,2009 ms | 0,1881–0,1901 ms |
| Ruido con outliers | 4,4860–4,6535 ms | 0,1759–0,1880 ms |

La mejora demostrada es de aproximadamente 25–33× en estos casos ruidosos
de búsqueda de 12000 muestras. No equivale a esa mejora en render completo,
FPS o transporte. Raster incremental/proyección log directa siguen pendientes.

## CH1 a tasas altas: coste de dibujo — 15/10/2026

El perfil de la vista temporal CH1 mostró trabajo de ejes/etiquetas durante
la pintura. La ruta RF de trigger reinstalaba la etiqueta del eje X y el
stylesheet del indicador en cada frame. Ahora usa la comprobación existente
de etiqueta y una comprobación del stylesheet actual: sólo los reinstala si
cambian. Conserva texto, color, tipografía, muestras, detalle y controles.
La comparación se hace contra el estado real previo guardado en
`diagnosticos/referencias/ch1_render_before_20261015.py`.

### Comparación controlada

`diagnosticos/benchmark_ch1_drawing_v17.py`, entrada sintética ADC8/CH1
a 1,4035 MHz y detalle 50, ventanas de aproximadamente 1/10/100 ms,
40 pares alternados, calentamiento de cada implementación antes de medir.
Ejes y muestras coinciden exactamente entre versiones. Resultado:
`diagnosticos/resultados_v17/ch1_drawing_controlled_20261015.json`.

| Vista con trigger | Preparación anterior → nueva | Raster anterior → nuevo |
|---|---:|---:|
| 1404 muestras | 1,942 → 1,587 ms | 9,944 → 6,828 ms |
| 14035 muestras | 3,471 → 2,728 ms | 8,766 → 6,936 ms |
| 140351 muestras | 6,109 → 5,753 ms | 9,878 → 7,726 ms |

Son medianas offline. El raster incluye `QWidget.grab`; no equivale a FPS
visibles. Sin trigger no aparece una mejora sistemática, como corresponde
a una intervención en la ruta de trigger.

### Ventana nativa visible con entrada sintética

`diagnosticos/benchmark_ch1_visible_v17.py` mide paintEvent reales en Cocoa,
con entrada sintética temporizada a 1,4035 MHz, detalle 50 y 140351 muestras
visibles. Bypassea transporte y decoder; no opera el Q. Orden antes/después/
después/antes, calentamiento de 1 s y medición de aproximadamente 5 s por tramo.

| Tramo | FPS de paintEvent | Exposición |
|---|---:|---:|
| Antes 1 | 25,99 | 100% |
| Después 1 | 29,60 | 100% |
| Después 2 | 22,79 | 100% |
| Antes 2 | 22,86 | 100% |

Resultado: `diagnosticos/resultados_v17/ch1_visible_synthetic_20261015.json`.
La tasa sintética recibida estuvo entre 1,397 y 1,408 MS/s. El primer par
mejora FPS; el segundo queda en paridad. **No demuestra un aumento sostenido
de FPS**, aunque la reducción del coste de raster aparece en la comparación
controlada. No se atribuye una causa a la variación entre tramos.
Se conserva la corrida anterior con oclusión en
`ch1_visible_synthetic_occluded_20261015.json`; no se usa para aceptar FPS.

93 pruebas de CH1/render, trigger, RADIO/UI, FFT/UI y procesamiento pasaron
en 50,455 s con Python 3.13. Las nuevas pruebas cubren reutilización de
etiqueta/estilo, cambio de unidades y flanco, Auto/Normal/SINGLE y captura
inmutable al cambiar detalle. Sin cambios de firmware, transporte ni tasa.

## CH1: búsqueda reciente de trigger — 15/10/2026

La ruta RF y la ruta RADIO sola prueban primero las últimas 2048 muestras
del intervalo de búsqueda permitido. Un cruce sólo se acepta por esa vía
si dispone de las diez muestras anteriores completas. Si falta un cruce
válido o cae en el borde incompleto, se vuelve a la búsqueda original sobre
todo el intervalo. Se conserva la interpolación de audio. No se cambia la
vista mixta, el detalle ni las muestras adquiridas.

En el caso habitual con señal periódica se evita copiar y recorrer toda la
ventana de búsqueda. La referencia incremental conserva la mejora anterior
de etiquetas/estilo:
`diagnosticos/referencias/ch1_render_before_recent_20261015.py`.
Ambos runners CH1 aceptan `--reference` para elegir esa referencia.

Comparación controlada:
`diagnosticos/resultados_v17/ch1_drawing_recent_controlled_20261015.json`.
Preparación de 140351 muestras con trigger: mediana 4,042 → 3,594 ms.
Los ejes y las muestras coinciden exactamente en todos los pares. El raster
permanece prácticamente igual, como corresponde a este cambio de búsqueda.

Ventana nativa con señal sintética de 5 kHz, ADC8/CH1 a 1,4035 MHz,
140351 muestras visibles, detalle 50, aproximadamente 5 s por tramo:

| Tramo | Preparación p50 | FPS paintEvent | Exposición |
|---|---:|---:|---:|
| Antes 1 | 4,995 ms | 55,94 | 100% |
| Después 1 | 3,711 ms | 59,40 | 100% |
| Después 2 | 4,033 ms | 53,12 | 100% |
| Antes 2 | 5,217 ms | 54,50 | 100% |

Resultado: `diagnosticos/resultados_v17/ch1_visible_recent_synthetic_20261015.json`.
La reducción de preparación se repite; **el aumento de FPS no se repite**.
Los FPS no permiten inferir una mejora sostenida ni del transporte físico.
No se operó el Q.

Las nuevas regresiones comparan con la búsqueda completa en ambos flancos,
bordes del tramo reciente, NaN, historial circular envuelto y deque. Verifican
también la lectura acotada a 2048 muestras y el retorno a la ventana completa
cuando el último cruce válido está lejos.

95 pruebas de CH1/render, trigger, RADIO/UI, FFT/UI y procesamiento pasaron
en 46,397 s con Python 3.13; compilación Python y revisión de whitespace
también pasaron.

## CH1: temporales del reductor, sin cambiar puntos — 15/10/2026

Restricción explícita del usuario: conservar calidad y comportamiento del
slider existente. No se cambian resolución, número de puntos seleccionado,
extremos, orden, cortes ni el modo Completo.

La comprobación de equiespaciado usa el mismo criterio de `allclose`
(rtol=atol=1e-9), reutilizando el array descartable de diferencias para
restar y tomar valor absoluto. Se compara su máximo con la misma tolerancia.
Evita temporales completos de resta, absoluto y máscara. La selección de
puntos posterior permanece idéntica. Los arrays de entrada no se modifican.
La ruta de espaciado no finito conserva la llamada original a `allclose`.

Referencia: `diagnosticos/referencias/trace_reducer_before_20261015.py`.
Los runners aceptan `--before-reducer` para aislar esta mejora de las anteriores.
Comparación controlada:
`diagnosticos/resultados_v17/ch1_reducer_controlled_20261015.json`.
Con 140351 muestras, preparación mediana sin trigger 4,387 → 3,843 ms;
con trigger 3,787 → 3,174 ms. No se espera acelerar el raster con los mismos
vértices; sus medianas no muestran una mejora sistemática.

Ventana nativa Cocoa, CH1 sintético a 1,4035 MHz, 500000 muestras visibles,
detalle 50, señal de 5 kHz, aproximadamente 5 s por tramo:

| Tramo | Preparación p50 | FPS paintEvent | Exposición |
|---|---:|---:|---:|
| Antes 1 | 10,945 ms | 36,77 | 100% |
| Después 1 | 9,106 ms | 41,22 | 100% |
| Después 2 | 9,420 ms | 38,02 | 100% |
| Antes 2 | 11,372 ms | 36,40 | 100% |

Resultado: `diagnosticos/resultados_v17/ch1_reducer_visible_synthetic_20261015.json`.
Ambos pares muestran mejora de FPS en este screening sintético. No acredita
transporte físico ni todas las escalas, señales y tasas. No se operó el Q.

Las regresiones comparan los arrays de salida exactamente contra la referencia
en todas las posiciones del slider (0–100), aplicando su mapeo real de píxeles,
escalón/línea y cortes. Incluyen picos aislados, señales planas, timestamps
irregulares/repetidos, NaN/inf, offsets grandes y valores alrededor del límite
de tolerancia de equiespaciado. También verifican entradas inmutables.

112 pruebas de reductor, CH1/render, trigger, RADIO/UI, FFT/UI, análisis
espectral y procesamiento pasaron en 47,005 s. Después se amplió y repitió
la comprobación del slider a sus 101 posiciones: las tres pruebas de calidad
pasaron en 1,012 s. Son las mismas tres regresiones, no tres pruebas distintas
adicionales al total. Compilación Python y revisión de whitespace pasaron.
