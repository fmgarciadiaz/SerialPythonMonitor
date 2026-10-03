# Barrido SPI: 3,5 / 3,8 / 4 MHz — 30/09/2026

**3,8 MHz solicitados funciona en este ensayo:** 76.810 bloques completos
durante dos minutos, sin errores de integridad y con **294.432 B/s** de patrón
verificado. Es aproximadamente un 17,5 % más que los 250.607 B/s obtenidos
previamente a 3 MHz. No se modificó el driver ni el firmware del benchmark.

## Condiciones y resultados

UNO Q `1060031107`, firmware V6 instrumentado (protocolo 2), receptor C,
bloques de 512 bytes con 460 bytes de patrón, pausa solicitada de 250 µs.
Se mantuvieron CRC32, secuencia, confirmación PING y comprobación de cada byte
del patrón. Las frecuencias de la tabla son las **solicitadas a Linux** y
leídas por ioctl, no mediciones eléctricas de SCK.

| Reloj solicitado | Duración | Bloques válidos/total | Patrón B/s | Integridad |
|---:|---:|---:|---:|---|
| 3,8 MHz | 10 s | 6.413/6.413 | 294.914 | OK |
| 3,5 MHz | 10 s | 6.022/6.022 | 276.949 | OK |
| 4 MHz | 5 s | 0/3.351 | 0 | Falla |
| 3,8 MHz | 120 s | 76.810/76.810 | 294.432 | OK |

Registros completos, incluyendo SHA256 del receptor C:

- [3,8 MHz, prueba breve](resultados_spi/20260930_234820_808676.log).
- [3,5 MHz](resultados_spi/20260930_234937_848175.log).
- [4 MHz](resultados_spi/20260930_235028_206615.log).
- [3,8 MHz, dos minutos](resultados_spi/20260930_235054_277202.log).

En los dos minutos se verificaron **35.332.600 bytes de patrón** dentro de
39.326.720 bytes recibidos por SPI. Hubo cero errores CRC, de cabecera, de
patrón o de confirmación; cero pérdidas, duplicados y bloques fuera de orden.
Los contadores MCU se mantuvieron en `[671, 0, 0]`: los 671 errores SPI y el
último error `-5` corresponden a la prueba anterior a 4 MHz, sin nuevos errores
durante los dos minutos. El retorno de las transacciones válidas fue 512.

No se buscó el máximo exacto entre 3,8 y 4 MHz. El resultado identifica una
configuración útil, no certifica estabilidad indefinida ni con ADC concurrente.
Sigue sin alcanzarse el objetivo de 750.000 B/s, por lo que los verificadores
devuelven código 1 aunque `integrity_pass` sea verdadero.

## Un nivel más abajo: driver MCU

Se inspeccionó el ELF distribuido con Arduino Zephyr 1.0.0 mediante objdump,
sin modificar ni ejecutar código nuevo en la placa. La función
`spi_stm32_get_err`, dirección `0x0800f6f8`, lee el registro de estado SPI,
aplica la máscara **`0x3e0`** y devuelve `-5` cuando encuentra un bit activo.
La ISR llama a esa función. La [desensamblación guardada](resultados_spi/20260930_driver_get_err.txt)
incluye el SHA256 del ELF inspeccionado.

Según el encabezado STM32U585 instalado, esa máscara abarca UDR, OVR, CRCE,
TIFRE y MODF (bits 5 a 9): falta de datos para transmitir, exceso de datos
recibidos y otros errores del periférico. El CRC hardware de ese registro
es distinto del CRC32 que calcula nuestro protocolo por software.

Esto identifica una ruta que devuelve ese error desde la ISR, pero **no
demuestra qué ruta ni qué bit se activó durante el fallo físico**.
No se capturó el registro en el instante del
error, y el driver limpia al menos OVR antes de retornar. Para distinguir
las causas habrá que instrumentar el driver antes de esa limpieza o recuperar
su registro de diagnóstico; leer solamente el retorno `-5` no alcanza.

## Un nivel más abajo: reloj Linux

El dispositivo real es el controlador GENI/QUP en `4a94000.spi`, expuesto como
`/dev/spidev0.0`. Una consulta de sólo lectura a `clk_summary`, tras el ensayo
de 3,5 MHz, mostró `gcc_qupv3_wrap0_s5_clk` con una fuente de **100 MHz** y el
controlador inactivo en ese momento. Ese reloj fuente no es SCK.

El [driver upstream Linux 7.0](https://github.com/torvalds/linux/blob/v7.0/drivers/spi/spi-geni-qcom.c)
calcula el reloj SPI mediante un divisor entero y un factor de sobremuestreo.
Por eso la frecuencia efectiva puede ser inferior a la solicitada. No se
verificó que el código del kernel de esta placa sea idéntico al upstream.
El punto habitual `/sys/kernel/debug/dynamic_debug` no existe en este sistema;
no se pudo consultar por esa vía el diagnóstico del divisor aplicado.

**No quedó confirmado el SCK efectivo.** Para medirlo hacen falta una traza
del divisor realmente programado o una medición con analizador/osciloscopio.
El caudal y la integridad de las tablas sí son mediciones del enlace real.

## Reproducir

Con V6 iniciada y el binario C preparado según el [README V6](../arduino/historico/v6/README.md):

```sh
python3 tools/spi_benchmark.py --implementation c --hz 3800000 --seconds 120 --gap-us 250
```

Este barrido no altera la adquisición validada ni habilita DMA SPI. Al cerrar
el ensayo se detuvo V6 y se compiló, cargó e inició Q V5 correctamente. No se
repitió la medición por R4 ni la prueba gráfica del monitor en este barrido.
El siguiente trabajo para ganar margen sigue
siendo resolver la atención del periférico y el rearmado, evaluando DMA SPI
y buffers alternados. El R4 continúa siendo el camino de adquisición validado.
