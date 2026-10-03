# V6 polling: SPI3 por registros

Experimento independiente para comparar con [V6 por interrupciones](../v6/README.md).
Mismos bloques SCP1/v2 de 512 bytes, 460 bytes de patrón, CRC32 y PING con
confirmación en la siguiente trama. Sin ADC ni DMA SPI. Aplicación:
**Scope SPI Polling V6**.

[Resultados físicos](../../../diagnosticos/POLLING_SPI_V6.md): 4 MHz pasó y
6 MHz sostuvo dos minutos sin errores, a unos 402 kB/s útiles. A 8 MHz
aparecieron underruns; aún no se alcanza el umbral de 750 kB/s.

`device_init()` aplica los clocks y pinctrl del core. Después se desactiva
solamente IRQ99/SPI3 y se configura el periférico en modo 0, 8 bits, full
duplex y NSS físico activo bajo (PG12). Los bytes se mueven directamente
mediante accesos de 8 bits a `TXDR` y `RXDR`, consultando `TXP`, `RXP`, `EOT`
y los indicadores de error en `SR`. Para drenar el final del bloque también
se consultan `RXWNE` y `RXPLVL`; EOT por sí solo no autoriza a descartar
los bytes todavía pendientes de recepción. No se usa `spi_transceive()` ni la ISR
del driver para transferir datos. La FIFO se precarga hasta 8 bytes y se
limita la diferencia entre bytes enviados y recibidos a esa capacidad.

Las demás interrupciones siguen habilitadas. **Este polling ocupa CPU incluso
mientras espera al maestro**; no es una integración definitiva con el ADC.
El ensayo mide si evitar el driver permite superar el límite observado.
Las transacciones activas tienen un timeout de 50 ms; esperar al maestro
con NSS inactivo no incrementa los contadores ni las secuencias.

## Diagnóstico de errores sin cambiar el formato

`last_driver_result` conserva el retorno: 512 en una transferencia completa,
o un errno negativo. En esta variante, `last_driver_error <= -65536` codifica
el registro `SR[15:0]` capturado **antes** de deshabilitar/limpiar el periférico:

```python
sr = (-last_driver_error) & 0xffff
underrun = bool(sr & 0x20)  # UDR: faltaron datos para transmitir
overrun = bool(sr & 0x40)   # OVR: recepción no atendida a tiempo
```

Los demás valores negativos son errno, como `-ETIMEDOUT`. La captura queda
retenida hasta otro error; consultar siempre la diferencia de contadores
para distinguir errores previos de errores del intervalo actual. Los bits
0x80/0x100/0x200 corresponden a CRCE/TIFRE/MODF. CRCE es el indicador hardware,
distinto del CRC32 calculado por nuestro protocolo.

## Compilar y medir

Desde la raíz del proyecto, con el Q conectado por USB:

```sh
python3 tools/unoq.py compile --version v6_polling
python3 tools/unoq.py backup --version v5
python3 tools/unoq.py create --version v6_polling  # primera instalación
python3 tools/unoq.py stop --version v5
python3 tools/unoq.py start --version v6_polling
# Esperar a que start termine.
python3 tools/spi_benchmark.py --firmware v6_polling --implementation c --hz 1000000 --seconds 5 --gap-us 1000
python3 tools/spi_benchmark.py --firmware v6_polling --implementation c --hz 3800000 --seconds 10 --gap-us 250
python3 tools/spi_benchmark.py --firmware v6_polling --implementation c --hz 4000000 --seconds 10 --gap-us 250
```

El receptor C se prepara con `python3 tools/spi_benchmark.py --build-native`
si todavía no está compilado para esa revisión del fuente. `--firmware`
selecciona y comprueba la aplicación destino; no la inicia ni carga firmware.
Los registros incluyen la variante y el SHA256 del sketch local.

Para actualizar la variante ya instalada, `deploy --version v6_polling`.
No ejecutar otra aplicación del MCU simultáneamente. Para restaurar:

```sh
python3 tools/unoq.py stop --version v6_polling
python3 tools/unoq.py start --version v5
```

El umbral de aceptación permanece en 750.000 B/s íntegros y no se modifica
para favorecer esta variante. La cabecera de protocolo se conserva idéntica
a V6; una prueba local comprueba que no haya divergencias.
