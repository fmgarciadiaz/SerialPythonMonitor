# Megaboom ADC8: ensayo aislado, 11/10/2026

Objetivo: 160 MHz / 133 ticks = 1.203.007,519 muestras/s por canal.
ADC1 usa resolución nativa de 8 bits y ventana de cinco ciclos a 54 MHz.
Se conservan CRC, secuencia, índices, rango ADC, timestamps individuales DMA,
comprobación de propiedad de nodos y detección de pérdidas. No integrado en GUI.

## Resultados físicos

- Dos canales, tramas 992/SPI8 a 32 MHz: tras corregir buffers heredados de CH1,
  el verificador rechazó el flujo por una pérdida de nodo (seq 17, nodo 3).
- CH1, tramas 992/SPI8: pérdida de un nodo (seq 50, nodo 16).
- CH1 con espera inactiva de 20 us y k_yield: pérdida de un nodo
  (seq 53, nodo 16). Acortar la pausa no resolvió el fallo.
- CH1, tramas 1120/SPI16 a 32 MHz: compiló tras adaptar TSIZE a palabras de
  16 bits y anchos DMA; el relay no recibió READY inicial. No validado físicamente.

No se usó SPI48: excede el máximo de transmisión esclava aplicable en la tabla 150
[STM32U585](https://www.st.com/resource/en/datasheet/stm32u585ri.pdf).
La integridad de simulaciones no acredita rendimiento real ni precisión analógica.

Cada runner restaura firmware/relay estables y el ADC/generador previo en finally.
Últimos resultados: `results.json`, `relay_trial.log`; ensayos anteriores retenidos
como `first_results.json`/`first_relay_trial.log` o `dual_first_results.json`.
Pruebas locales: `python -m unittest experimentos.megaboom_ch1_v16.test_contract`.

Estado: el perfil 1,203 MHz no supera la validación y no debe habilitarse en el
selector estable. Queda pendiente caracterizar la duración por trama y la cola,
y diagnosticar el arranque de SPI16 antes de nuevas pruebas sostenidas.


### Medición de etapas, 2026-10-11

El relay instrumentado acumuló tiempos sin imprimir por trama. El ensayo CH1 a 1,203 MHz volvió a rechazar un nodo (seq=65). READY promedió 252,392 µs, SPI ioctl 380,468 µs y validación 9,639 µs, frente a un presupuesto de 567,467 µs por trama (tres tramas por nodo). La media de ciclo incluye el crédito inicial de 20 ms y no representa rendimiento sostenido. Falta medir dentro del MCU qué parte de READY corresponde a preparación, planificación y entrega entre hilos. No se puede atribuir toda la espera al productor ADC. El Q se restauró a ADC16/71428, generador deshabilitado; 712704 pares validados en la comprobación de restauración. Tres tests locales pasaron. No integrado en el monitor.
