# WORD con burst corregido — 15/10/2026

Campaña cerrada: integridad aceptada en ADC8 CH1 a **1.428.571,429 muestras/s**
(ticks112,N3456), sin mejora frente al candidato BYTE previo. WORD no alcanzó
la holgura requerida en ninguna de las dos tasas calificadas. No incorporado.

## Causa y corrección

La variante anterior usaba width4/burst1. El header DMA del core instalado
Zephyr1.0.0 documenta source_burst_length y dest_burst_length en **bytes**.
El [driver oficial Zephyr](https://github.com/zephyrproject-rtos/zephyr/blob/main/drivers/dma/dma_stm32u5.c)
rechaza bursts no divisibles por el ancho; burst4 representa un beat WORD.
Se cambió únicamente esa asignación en el sketch experimental. WORD inició
READY y transfirió con CRC32, byte frames, FIFO4 y validación intactos.
No se capturó el retorno EINVAL del arranque anterior: la atribución se apoya
en la incompatibilidad documentada y en el éxito físico tras corregirla.

## Sondeo y aceptación

- Ticks114/112/110 pasaron10s; ticks110 sólo mostró5,64% de margen medio.
- Ticks108 (1,481481MS/s) falló dos veces, una desde arranque independiente.
- Ticks110 (1,454545MS/s) falló al intentar60s, durante asentamiento.
- Los tres fallos registraron dropped1,fatal0,cola pico4 y slack positivo:
  evidencia compatible con saturación de salida, no límite demostrado ADC.
- Ticks112 y114 completaron60s+3×120s, dropped/fatal0 en todas las etapas.
  No hubo sondeos en ticks109/111/113 ni se exploraron otros nodos.

| Ticks | Etapa | Muestras | Cola pico | Margen medio | Holgura |
|---:|---|---:|---:|---:|---|
| 112 | finalist | 85,666,464 | 3 | 11.235% | Sí |
| 112 | acceptance_1 | 171,330,336 | 3 | 12.041% | Sí |
| 112 | acceptance_2 | 171,330,336 | 4 | 11.860% | No |
| 112 | acceptance_3 | 171,329,472 | 4 | 11.579% | No |
| 114 | finalist | 84,163,968 | 3 | 10.500% | Sí |
| 114 | acceptance_1 | 168,323,616 | 3 | 10.788% | Sí |
| 114 | acceptance_2 | 168,323,616 | 3 | 9.962% | No |
| 114 | acceptance_3 | 168,323,616 | 3 | 10.552% | Sí |

Ticks112 falla holgura por cola4 en dos repeticiones. Ticks114 falla por
margen9,962% en una repetición; todas las demás condiciones fueron válidas.
Los slack mínimos fueron positivos. No se repiten selectivamente los fallos
para declarar aceptación. Los costes y percentiles completos están en el JSON.
Sin comparación sostenida BYTE/WORD aleatorizada, no se afirma causalidad
sobre pequeñas diferencias de tiempo ni superioridad de una variante.

## Cierre y siguiente decisión

[Informe físico completo](probe_1400_20261015_204602/report.json):
`ok/restored/restore_integrity_ok=true`. `ok` significa que existe candidato
íntegro; **no** que haya holgura aceptada. `qualified_headroom=null`.

Restaurados exactamente V17,relay original,ADC10/1167883SPI,generadorapagado
y todos sus campos;11.676.792 muestras íntegras en10s. Hash firmware original
idéntico: `3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
La app experimental quedó detenida. Fuentes y perfiles productivos sin cambios.

Prueba local C++: configuración BYTE/WORD y geometría pasan. El sketch local
final queda en WORD; sus hashes coinciden con los de la campaña desplegada.
La validación física cubre integridad y métricas de transporte, sin aceptación
analógica,dual,UART,GUI,RADIO/FFT/FILTER.

La siguiente optimización debería atacar costes de salida medidos (sellado,
packing,espera READY y envío), en vez de asumir que ensanchar DMA libera margen.
Antes de otro cambio, medirlos por separado y elegir un único candidato.
