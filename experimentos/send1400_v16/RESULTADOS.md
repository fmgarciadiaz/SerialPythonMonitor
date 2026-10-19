> Actualización V16: el ensayo 8 se repitió y cumplió integridad y holgura en toda la campaña a 1,4035 MHz. El antecedente de cola4 se conserva; el ensayo9 se descartó. [Resultado posterior](RESULTADOS_CONTINUIDAD_1400.md).

> Actualización V8: integridad aceptada a 1,4035 MHz con buffers por referencia. V16 restaurada. Ver [resultados SPI38](RESULTADOS_SPI38.md).

# Ensayo aislado de envío ADC8 CH1 a 1,4 MHz — 2026-10-13

**Campaña inicial v1–v5: no se alcanzó una tasa aceptada cerca de 1,4 MHz. Producción restaurada y verificada.**

Se ensayaron cinco variantes independientes. v1 falló la referencia; v2–v5
pasaron una referencia de 10 s a 1,221374 MHz, pero rechazaron los 24 casos
objetivo (1,391304 / 1,403509 MHz × tres tamaños de nodo × cuatro variantes).
Todos los casos objetivo perdieron un nodo durante el segundo de estabilización.
No avanzaron a la aceptación 60 + 3×120 + 600 s.

v1–v4 solicitaron SPI a 32 MHz; v5 solicitó 36 MHz (reloj físico no medido).
Se mantuvieron tramas kind20/SCP1 V4 de 992 bytes, CRC/secuencia/epoch,
índice/timestamp, verificación DMA y resguardo de buffers. Fuentes de
producción y selector de tasas conservados. Precisión analógica no evaluada.

| Variante | Referencia 1,221374 MHz / 10 s | Margen medio | Cola pico | Copia máxima | Casos objetivo | Restauración |
|---|---|---:|---:|---:|---|---|
| v1 | Falló en estabilización | — | 4 | — | No ejecutados | Verificada |
| v2 | Íntegra | 6.38% | 4 | 689.9 µs | 0/6 pasan | Verificada |
| v3 | Íntegra | 11.31% | 2 | 476.1 µs | 0/6 pasan | Verificada |
| v4 | Íntegra | 9.13% | 2 | 745.0 µs | 0/6 pasan | Verificada |
| v5 | Íntegra | 13.68% | 2 | 475.6 µs | 0/6 pasan | Verificada |

Los márgenes son observaciones cortas, no aceptación sostenida ni comparación
controlada de rendimiento. El mejor resultado corto fue v5; el menor coste
de copia fue v3/v5. No se incorporó ninguna variante a producción.

En los rechazos objetivo: `dropped=1`, `fatal=0`, cola pico 4/4 y slack de
sobrescritura positivo. Esto apunta a saturación de salida; no prueba un
límite de conversión ADC. El pipeline v1 tampoco sostuvo la referencia.
Para continuar conviene instrumentar el tiempo entre fragmentos y estudiar
un pipeline que entregue buffers por referencia y superponga preparación
con SPI; el pipeline que copia paquetes completos no dio una mejora.

## Matriz objetivo

| Variante | Ticks | Nodo | Presupuesto de nodo | Último envío al rechazo | Slack mínimo al rechazo | Resultado |
|---|---:|---:|---:|---:|---:|---|
| v2 | 115 | 3456 | 2.484 ms | 3.033 ms | 1.042 ms | Pérdida en estabilización |
| v2 | 114 | 3456 | 2.462 ms | 2.906 ms | 1.008 ms | Pérdida en estabilización |
| v2 | 115 | 6912 | 4.968 ms | 5.835 ms | 3.224 ms | Pérdida en estabilización |
| v2 | 114 | 6912 | 4.925 ms | 6.234 ms | 3.157 ms | Pérdida en estabilización |
| v2 | 115 | 8192 | 5.888 ms | 6.607 ms | 4.000 ms | Pérdida en estabilización |
| v2 | 114 | 8192 | 5.837 ms | 7.624 ms | 4.024 ms | Pérdida en estabilización |
| v3 | 115 | 3456 | 2.484 ms | 2.861 ms | 1.152 ms | Pérdida en estabilización |
| v3 | 114 | 3456 | 2.462 ms | 2.785 ms | 1.167 ms | Pérdida en estabilización |
| v3 | 115 | 6912 | 4.968 ms | 5.399 ms | 3.404 ms | Pérdida en estabilización |
| v3 | 114 | 6912 | 4.925 ms | 5.794 ms | 3.363 ms | Pérdida en estabilización |
| v3 | 115 | 8192 | 5.888 ms | 7.045 ms | 4.268 ms | Pérdida en estabilización |
| v3 | 114 | 8192 | 5.837 ms | 7.078 ms | 4.227 ms | Pérdida en estabilización |
| v4 | 115 | 3456 | 2.484 ms | 3.025 ms | 1.022 ms | Pérdida en estabilización |
| v4 | 114 | 3456 | 2.462 ms | 2.507 ms | 0.980 ms | Pérdida en estabilización |
| v4 | 115 | 6912 | 4.968 ms | 6.319 ms | 3.196 ms | Pérdida en estabilización |
| v4 | 114 | 6912 | 4.925 ms | 5.217 ms | 3.106 ms | Pérdida en estabilización |
| v4 | 115 | 8192 | 5.888 ms | 6.823 ms | 3.992 ms | Pérdida en estabilización |
| v4 | 114 | 8192 | 5.837 ms | 7.470 ms | 3.897 ms | Pérdida en estabilización |
| v5 | 115 | 3456 | 2.484 ms | 2.820 ms | 1.144 ms | Pérdida en estabilización |
| v5 | 114 | 3456 | 2.462 ms | 2.764 ms | 1.126 ms | Pérdida en estabilización |
| v5 | 115 | 6912 | 4.968 ms | 5.800 ms | 3.402 ms | Pérdida en estabilización |
| v5 | 114 | 6912 | 4.925 ms | 5.806 ms | 3.402 ms | Pérdida en estabilización |
| v5 | 115 | 8192 | 5.888 ms | 6.871 ms | 4.272 ms | Pérdida en estabilización |
| v5 | 114 | 8192 | 5.837 ms | 6.751 ms | 4.261 ms | Pérdida en estabilización |

115 y 114 ticks corresponden a 1.391.304,35 y 1.403.508,77 muestras/s
en CH1. Cada caso solicita 1 s de estabilización y 5 s de medición, con
reinicio independiente. Fallar antes de medir no equivale a completar 5 s.
La duración nominal no se usa para certificar integridad.

## Restauración final

- ADC original y final: `{'bits': 14, 'rate': 363636}`; SPI, dos canales.
- Generador apagado, con todos sus campos originales restituidos; WAV estaba IDLE antes del cambio.
- 3,634,688 pares íntegros en la verificación de recuperación de 10 s.
- Identidad de firmware original/final idéntica: `{'board_serial': '1060031107', 'app': 'scope-v16-main-1', 'firmware_sha256': '79b0bd376fe26b11b82cbef98fb1cba57ef752f7528c14434c6fef4de295092c'}`.
- Relay original: `/home/arduino/.cache/serialmonitor/usb-stream-add20708d06894b45d4c/unoq_stream`.
- Aplicación experimental detenida; Scope V16 activa.

## Fuentes y evidencia

- [probe_1400_20261013_154022](probe_1400_20261013_154022/report.json): `send1400_pipeline3_adc8_blockcheck_readyread_v1`.
- [probe_1400_20261013_154245](probe_1400_20261013_154245/report.json): `send1400_pipeline3_adc8_blockcheck_readyread_v1`.
- [probe_1400_20261013_154601](probe_1400_20261013_154601/report.json): `send1400_dma_rearm_adc8_blockcheck_readyread_v2`.
- [probe_1400_20261013_155103](probe_1400_20261013_155103/report.json): `send1400_dma_rearm_validation_o3_unroll4_v3`.
- [probe_1400_20261013_155442](probe_1400_20261013_155442/report.json): `send1400_dma_rearm_output_producer_o3_v4`.
- [probe_1400_20261013_155821](probe_1400_20261013_155821/report.json): `send1400_dma_rearm_validation_o3_spi36_v5`.

- ZIP por variante: `sources_pipeline_v1.zip`, `sources_dma_v2.zip`, `sources_validation_v3.zip`, `sources_output_v4.zip`, `sources_spi36_v5.zip`. Todos coinciden con los hashes de las fuentes en sus reportes.
- `run.py` guarda hashes, parámetros, métricas y logs; captura estado vivo y respaldo antes de preparar la variante.
- El intento inicial 154022 cerró el flujo durante la preparación del relay, antes de cambiar firmware: no es un caso de tasa. La recuperación independiente está en `recovery_probe_1400_20261013_154204/report.json`.
- En v5 se detuvo producción después del snapshot y respaldo, antes de compilar el relay, para evitar carga simultánea.
- Pruebas locales: dos tests de equivalencia relay/validación/empaquetado y tres del contrato experimental pasaron. El test de validación cubre corrupción en cada posición, wrap, colas de bucle y límites de escritura.
