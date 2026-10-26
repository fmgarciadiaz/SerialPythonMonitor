# Revisión global V18 · 25/10/2026

## Cambios acotados

Scan US ahora confirma restauración solo después de recibir el mínimo de
muestras nuevas del perfil original. Igualdad de configuración y existencia
del worker no bastan. Un timeout o desconexión mantiene RADIO pausada y A0
sin reanudar. La cancelación que restaura correctamente puede volver a RADIO.

Pruebas GUI base adaptadas a la conexión instalada y preparación explícita V18;
el simulador integrado implementa el canal PCM separado y espera liberación del
worker al cerrar. No se modificaron firmware, tasas ni arquitectura de procesos.

## Grabación CSV: medición sintética

Se ejecutó `_write_record_batch` real con NumericBatch, un canal, doce bloques
por formato, csv.writer y archivo temporal. Incluye conversión a diccionarios,
filas y escritura; excluye adquisición, DSP y dibujo. No es aceptación física
ni medición de recepción con el Q. Valores medios de esta ejecución:

| Bits | Intervalo por bloque (ms) | Escritura CSV (ms) |
|---|---:|---:|
| 8 | 1,92 | 8,76 |
| 10 | 4,25 | 17,38 |
| 12 | 6,83 | 18,17 |
| 14 | 6,55 | 16,17 |
| 16 | 23,11 | 8,43 |

Evidencia: `diagnosticos/resultados_v18/global_review_20261025/csv_synthetic.json`.
La ruta CSV de 8–14 bits no alcanza las tasas máximas en esta medición, incluso
antes de sumar el resto de la GUI. Un hilo con cola no resuelve por sí solo
la velocidad sostenida; una cola sin límite solo aplaza el problema.

Próximo bloque propuesto: conversión columnar sin diccionarios por muestra,
medición de salida y disco con datos representativos, luego escritor separado
con cola acotada, errores y finalización explícitos. Mantener columnas y datos
originales; ninguna pérdida silenciosa. Si no sostiene la FS, informar el límite.
Esta ruta permanece sin modificar en este bloque para no incorporar una
reestructuración de grabación sin sus propias pruebas de integridad.

## Validación

Revisión inicial: 197 pruebas IPC/transporte/audio y 57 GUI/DSP aprobadas.
Tras las correcciones: 28 pruebas específicas aprobadas, incluidas restauración
exitosa/cancelada, timeout sin muestras, desconexión y cierre pendiente.
No se operó el Q. V17 permanece congelada.

Regresión final completa: 282 pruebas aprobadas en 52,852 s. Después se añadió
una prueba de cierre durante preparación WAV y rechazo de audio tardío; las
tres pruebas de cierre rápido pasaron (dos ya incluidas en la regresión).
Total: 283 casos distintos aprobados. Audio Stop y rechazo de respuestas
antiguas están cubiertos por la suite de control PCM incluida.
