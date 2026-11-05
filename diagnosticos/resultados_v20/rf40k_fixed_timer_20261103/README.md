# V20: timer adaptativo contra 16 ms fijo, RF puro 40 kHz

Comparación local nativa PySide6, sin Q ni cambios de producto. Comando:
`PYTHONPYCACHEPREFIX=/tmp/arduscopio-v20-check-cache /Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python tools/run_rf40k_fixed_timer_v20.py`.
Tres pares alternados en procesos separados; cada uno solicitó 3 s de
calentamiento y 10 s de medición. Misma pantalla Retina/DPR 2, geometría
1280×888, CH1, RADIO/FILTER apagados, ventana 9000, detalle 50, Escalón,
Rápido, grid activo, trigger/cursor apagados. `tools/compare_rf40k_fixed_timer_v20.py`
usa `NumericBatch`/`handle_batch` y entrega bloques deterministas de 400
muestras cada 10 ms; recupera todos los bloques vencidos desde reloj
monotónico en cada callback. La candidata sólo convierte
`_refresh_render_cadence` en no-op en esa instancia y fija su QTimer a 16 ms.
El código V20 en disco no se editó.

| Par | Nuevos adaptativo / fijo | Pinturas fijo | Intervalo p95 adaptativo / fijo (ms) | CPU adaptativo / fijo (s) | Atraso feed p95 adaptativo / fijo (ms) | Atraso feed máximo adaptativo / fijo (ms) |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 177 / 450 | 562 | 73,4 / 34,3 | 5,00 / 15,28 | 16,5 / 19,1 | 26,1 / 83,1 |
| 2 | 178 / 474 | 596 | 76,2 / 36,0 | 4,98 / 16,30 | 16,8 / 18,2 | 32,6 / 72,8 |
| 3 | 165 / 446 | 562 | 82,4 / 35,0 | 4,81 / 15,28 | 18,7 / 18,3 | 68,7 / 47,4 |

Todas las pinturas medidas estuvieron expuestas. El timer fijo generó
aproximadamente 45–47 cuadros nuevos/s frente a 17–18/s del adaptativo;
las pinturas adicionales de la columna fija son repintados de una época
ya pintada, excluidos del FPS útil. El QTimer que terminó cada proceso no
marcó exactamente 10 s: los bloques esperados por reloj en la fase medida
equivalen aproximadamente a 10,06/9,56, 10,51/10,10 y 10,05/9,56 s
(adaptativo/fijo). El aumento de cuadros supera 50 % incluso al normalizar
por esas duraciones. Estas duraciones aproximadas no acreditan una prueba
física sostenida.

| Par | Bloques esperados/entregados, adaptativo | Bloques esperados/entregados, fijo | Máximo backlog adaptativo/fijo |
|---|---:|---:|---:|
| 1 | 1317/1311 | 1253/1253 | 4/9 |
| 2 | 1335/1327 | 1325/1325 | 4/8 |
| 3 | 1321/1320 | 1243/1237 | 7/6 |

El déficit final de algunos bloques indica callbacks todavía pendientes al
cerrar el proceso. El harness registra muestras esperadas y entregadas;
no interpreta esa diferencia como pérdida física ni asegura cero demora.
Los p95 de callback del feed fijo fueron similares o algo mayores, pero
sus máximos llegaron a 83/73 ms en dos pares, y el proceso consumió unas
tres veces más CPU. Esa subida es material para la reserva de GUI/adquisición
que motivó el pacing adaptativo. La candidata cumple el objetivo nominal
de FPS de este escenario, pero no queda aceptada como cambio de producto
por coste y picos de latencia. No se ensayó Q ni se propuso una regla para
otras tasas/ventanas.

Los seis JSON `01`–`03` contienen épocas RF preparadas y nuevas pintadas,
coste de preparación/pintura/medición, exposición, intervalos, muestras
esperadas/entregadas, atraso de callback, backlog, CPU y geometría. Los
archivos `00` fueron sólo smoke y no entran en los tres pares. Este ensayo
no mide integridad de transporte, margen ni comportamiento físico con Q.
