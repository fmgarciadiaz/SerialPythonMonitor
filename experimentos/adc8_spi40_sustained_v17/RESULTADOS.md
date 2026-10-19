# SPI 40 MHz sostenido: integridad y holgura aceptadas en el experimento

**ADC8/CH1 a 1.428.571,429 muestras/s pasó 60 s + tres corridas independientes
 de 120 s a 40 MHz configurados**, con formato original kind20, N3456 y 864
muestras por trama. Son un 1,786% más muestras/s que el perfil de 1.403.508,772.
No se modificaron firmware, selector ni perfiles de producción.

[Reporte físico completo](probe_1400_20261016_083129/report.json) y
[perfil experimental resumido](qualification.json).

## Evidencia sostenida

599,656,608 muestras íntegras en las cuatro ventanas de aceptación (420 s).
CRC32, secuencia, epoch, índices/timestamps, rango ADC y propiedad DMA
verificados; dropped/fatal=0. Cada caso reinició MCU y relay. Los picos de
cola incluyen startup, no sólo el período posterior al segundo de asentamiento.

| Corrida | Segundos | Muestras | Margen medio de envío | Cola pico | Slack mínimo µs |
|---|---:|---:|---:|---:|---:|
| finalist | 60 | 85,663,872 | 16.900% | 2 | 1083.875 |
| acceptance_1 | 120 | 171,330,336 | 17.076% | 2 | 1084.569 |
| acceptance_2 | 120 | 171,331,200 | 17.410% | 2 | 1083.969 |
| acceptance_3 | 120 | 171,331,200 | 17.424% | 3 | 1083.600 |

Las cuatro cumplen margen medio >=10%, cola pico <4 y slack positivo.
`qualification_integrity_accepted=true` y `qualification_headroom_accepted=true`.
No hubo reintentos selectivos, fallos de integridad ni corridas de 600 s.
Además, dos preflights de 10 s a 250 kS/s verificaron referencia33,333 y40 MHz;
contando esos controles, la campaña recibió 604,653,984 muestras.

## Configuración y límites de la conclusión

Fuentes MCU y relay idénticas a adc8_spi40_pilot_v17. WORD DMA, CRCSIZE7,
READY fresco por trama con spin50µs, un send TCP por trama y validación íntegra.
Sin formato compacto ni optimizaciones de accept/PING/TCP en esta campaña.

Cada caso confirmó el origen del reloj en clk_src sin caché y contrastó
registro GCC DFS activo con selector GENI: referencia100M/DFS5/div3;
ensayos120M/DFS6/div3=40M. DMA GENI habilitado y GSI deshabilitado.
Lecturas fijas O_RDONLY/PROT_READ, contenedor RO y sin red, fuera de las
ventanas de rendimiento. Frecuencia derivada de configuración, no medida
eléctricamente con instrumento. La rama clk_rate cacheada no se usa para
calcular el resultado.

Esta aceptación es física y sostenida bajo las condiciones ensayadas, con
carga aislada CH1 y generador apagado. No certifica el presupuesto eléctrico
publicado ni margen universal frente a tensión, temperatura o variación de
placa. La limitación MISO del piloto sigue vigente; no se realizó aceptación
analógica ni de GUI/RADIO/FILTER/WAV, dual o UART. Tampoco se califica una
tasa superior a ticks112. El piloto ticks110/10s previo llegó a cola4.

## Restauración verificada

`ok/restored/restore_integrity_ok=true`. ADC8/1403508SPI y generador apagado,
con todos sus campos exactos, relay y entorno originales restaurados.
14,030,496 muestras íntegras en 10 s al cierre. Identidad de firmware
antes/después idéntica:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
Relectura del reloj original:100M/DFS5/div3=33,333333M. App experimental
inactiva al cierre. No hay incorporación productiva.

Fuentes coinciden con el piloto y el runner conserva su hash de inicio.
La auditoría local registra fuentes y reporte final; el perfil queda listo
para revisar una incorporación separada, sin convertir esta prueba en una
garantía eléctrica.
