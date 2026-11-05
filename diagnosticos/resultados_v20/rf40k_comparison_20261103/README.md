# Comparación nativa V(t) RF 40 kHz: V19/V20

Se ejecutó `tools/run_rf40k_comparison_v20.py` con
`/Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python`
y `PYTHONPYCACHEPREFIX=/tmp/arduscopio-v20-check-cache`. El runner abrió
secuencialmente procesos nativos V19/V20 en tres pares de orden alternado.
No se conectó al Q. Un intento inicial bajo sandbox no pudo crear pantalla
(`Cannot create window: no screens available`); los ensayos válidos usaron
acceso nativo a la pantalla, con aprobación automática.

Configuración idéntica: ventana solicitada 1280×800 (geometría efectiva
1280×888 por mínimo de la UI), posición (100,128), pantalla Built-in Retina
Display, DPR 2, CH1, RADIO/FILTER apagados, RF 40.000 muestras/s mediante
`NumericBatch` y `handle_batch` en lotes de 400 cada 10 ms, ventana temporal
9000 muestras, detalle 50, Escalón, Rápido, grid activo, cursor y trigger
apagados. Cada proceso usó 3 s de calentamiento y 10 s medidos con su QTimer
real. El observador envolvió callbacks originales sin cambiar su efecto.

| Par | V19 cuadros nuevos / 10 s | V20 cuadros nuevos / 10 s | Diferencia V20 | Mediana pintura V19/V20 (ms) | Mediana preparación V19/V20 (ms) |
|---|---:|---:|---:|---:|---:|
| 1 | 166 | 155 | −6,6 % | 10,42 / 10,58 | 1,72 / 1,67 |
| 2 | 180 | 180 | 0 % | 10,50 / 10,45 | 1,63 / 1,64 |
| 3 | 184 | 177 | −3,8 % | 10,51 / 10,53 | 1,65 / 1,65 |

En todas las corridas, cada pintura registrada tuvo exposición de ventana
verdadera; el cuadro se contó como nuevo sólo cuando se pintó una época RF
preparada distinta. La mediana de intervalos entre cuadros nuevos fue
57–58 ms. La mediana de ingestión de lote fue 0,116–0,123 ms y hubo 18–19
actualizaciones de medición por corrida, con medianas 0,365–0,381 ms.
`paint_ms × 4` dominó el intervalo adaptativo en los 1042 renders medidos;
ni la base de 16 ms ni `prepare_ms × 3` dominaron. Las tasas de título
observadas rondaron 17–18 FPS. La diferencia de puntos dibujados al cierre
(4141–4143) refleja la fase de la señal/ventana al terminar cada proceso.

El caso de unos 14 FPS se reprodujo en un smoke nativo de 2 s (V20: 28
cuadros; V19: 36), pero los tres pares de 10 s no muestran una degradación
V20 repetida de al menos 15 %. Ambos quedan cerca de 17–18 FPS bajo esta
configuración y comparten el límite dominado por pintura. No se lanzó la
variante de 2 s/80 kHz ni CH1+CH2 porque el caso base ya reprodujo FPS bajos
y permitió identificar el factor dominante compartido. No se cambió el
temporizador ni código de producto.

Los seis JSON `01`–`03` guardan tiempos de timeout/preparación/pintura,
intervalo y `timerId`, muestras nuevas pintadas, exposición, coste de
medición/ingestión, geometría y DPR. Los `00` son smoke separados y no entran
en la comparación de tres pares. La entrada es sintética y ejercita la ruta
GUI `handle_batch`; no acredita integridad, margen de transporte ni el
firmware físico a 40 kHz.

## Referencia breve V17/V18

Por pedido posterior se ejecutó una corrida nativa adicional de 3 s de
calentamiento y 10 s de medición por versión con
`tools/compare_rf40k_archive_v20.py --version v17|v18`. V17/V18 usan PyQt6,
en procesos separados de V19/V20 (PySide6). El filtro de eventos del viewport
registra el comienzo de cada `Paint`; no se infiere duración de pintura de
ese filtro. También se conservó el callback de render original y el timer
fijo de 16 ms.

| Versión | Cuadros nuevos / 10 s | Mediana intervalo / p95 (ms) | Mediana preparación (ms) | Exposición | Geometría |
|---|---:|---:|---:|---:|---:|
| V17 | 622 | 16,13 / 17,79 | 1,57 | 624/624 eventos | 1280×897 |
| V18 | 592 | 16,07 / 17,80 | 1,67 | 594/594 eventos | 1280×888 |

La pantalla, DPR 2 y ancho de plot 634,3 fueron iguales; V17 impuso 9 px
adicionales de alto mínimo. Los JSON `archive_v17_w9000_ch1.json` y
`archive_v18_w9000_ch1.json` guardan épocas preparadas/pintadas, intervalos,
exposición y costes de preparación/ingestión. Ambas referencias son mucho
más rápidas en este caso (59–62 cuadros/s) que V19/V20 (15–18 cuadros/s).
El timer fijo frente al adaptativo coincide con la diferencia observada;
los bindings Qt y otros cambios de versión también difieren. Esta lectura
no atribuye por sí sola la pérdida a un único cambio ni justifica modificar
la cadencia de V20 sin un ensayo aislado allí.
