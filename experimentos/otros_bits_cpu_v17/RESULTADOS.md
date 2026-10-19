# Primera comparación CPU — 10/12/14/16 bits

A/B/B/A, cuatro corridas de 10 s por resolución. A=política normal;
B=CPU2 y performance. Mismo firmware, mismas tasas, mismo SPI.

| Bits | Tasa por canal | Canales | Margen A medio | Margen B medio | Cola pico |
|---|---:|---:|---:|---:|---:|
| 10 | 1167883.212 | 1 | 5.114% | 14.153% | 2 |
| 12 | 981595.092 | 1 | 5.020% | 12.683% | 2 |
| 14 | 851063.830 | 1 | 6.759% | 13.481% | 2 |
| 16 | 76226.775 | 2 | 77.491% | 80.016% | 1 |

Las 16 corridas conservaron integridad. En las cuatro resoluciones, los dos
tiempos medios B fueron menores que ambos A. En 10/12/14 bits el margen B
supera10% con cola<4 y slack positivo durante este screening. Esto no es
aceptación prolongada ni habilita tasas nuevas o perfiles nuevos con holgura.

16 bits: formato actual dual, ADC14 con sobremuestreo16 y desplazamiento2.
El envío ya tiene77% de holgura; aplicar la política CPU por sí sola no
demuestra mayor tasa ADC. El pack CH1 actual sólo implementa8/10/12/14;
para buscar16bits CH1 hay que agregar ese formato en un experimento aislado
y validar empaquetado/decoder antes de operar la placa.

Siguiente bloque: aplicar CPU2/performance en el relay experimental para
los perfiles CH1 de10/12/14, aislar la variante SPI40/WORD manteniendo4slots
y comparar a tasas iguales antes de buscar ticks menores. Cola8 no se
copia directamente: la arena actual asume8×3456 y los nodos10/12 pueden
ser mayores. Para16, separar primero el soporte CH1 del cambio de tasa.

Restauración exacta ADC8/1600000 y generador apagado con todos sus campos
previos; recuperación10s:15.990.912muestras, dropped=fatal=0. Firmware y
relay de producción permanecieron idénticos. No se compilaron fuentes enQ.

Informe: `probe_20261016_202450/report.json`.
Snapshot y respaldo guardados en el informe. Intento inicial de preparación
fallido por permisos del usuario remoto conservado en probe_20261016_202410;
no produjo corridas y su restauración posterior está registrada.
