# Validación del benchmark SPI V6 — 30/09/2026

**Actualización:** el [perfil posterior Python/C](PERFIL_SPI_V6.md) identifica
el costo del verificador y mejora el resultado a unos 250 kB/s con C. Este
documento conserva las mediciones del primer ensayo.

**Resultado: enlace bidireccional demostrado, caudal insuficiente para reemplazar
el R4.** A 3 MHz se recibieron 12.614 bloques íntegros durante 60 segundos,
con unos 99.213 B/s de patrón verificado. No se integró el ADC ni se cambió
el transporte USB del monitor.

## Entorno y método

Este primer ensayo corresponde al protocolo 1. La instrumentación posterior
usa protocolo 2, con 32 bytes de estado y 460 de patrón; las mediciones de
esta sección mantienen su formato original.

- UNO Q `1060031107`, STM32U585 y Linux QRB2210, Debian 13.5/kernel 7.0.0.
- Arduino Zephyr 1.0.0; SPI3 peripheral con interrupciones, sin DMA SPI.
- Linux `/dev/spidev0.0`, modo 0, 8 bits, transacciones full-duplex de 512 bytes.
- Verificador Python estándar en la imagen instalada
  `ghcr.io/arduino/app-bricks/python-apps-base:0.12.0`.
- Datos sintéticos deterministas, CRC32, secuencia y confirmación del PING
  anterior. Cada DATA contiene 472 bytes de patrón y 20 de estado.
- Objetivo elegido: 750.000 B/s verificados, tres veces los 250.000 B/s de
  registros de la adquisición actual. El tiempo incluye todas las operaciones
  del verificador y las pausas solicitadas.

El reloj indicado es el solicitado y confirmado por ioctl. No se midió SCK
con un analizador lógico. Los resultados describen el conjunto firmware,
driver y verificador usado, no la capacidad máxima del hardware SPI.

## Mediciones conservadas

| Reloj | Pausa | Tiempo | Bloques válidos/total | CRC erróneos | Patrón B/s | Integridad |
|---:|---:|---:|---:|---:|---:|---|
| 1 MHz | 1.000 µs | 5,02 s | 493/493 | 0 | 46.362 | OK |
| 4 MHz | 100 µs | 5,01 s | 0/1.403 | 1.403 | 0 | Falla |
| 2 MHz | 1.000 µs | 5,01 s | 622/622 | 0 | 58.554 | OK |
| 4 MHz | 1.000 µs | 5,01 s | 0/1.061 | 1.061 | 0 | Falla |
| 2 MHz | 0 | 10,01 s | 1.748/1.748 | 0 | 82.415 | OK |
| 3 MHz | 0 | 10,01 s | 2.144/2.144 | 0 | 101.091 | OK |
| 3 MHz | 0 | 60,01 s | 12.614/12.614 | 0 | 99.213 | OK |

Salidas completas, en el mismo orden:

- [1 MHz](resultados_spi/20260930_180811_335281.log)
- [4 MHz, pausa 100 µs](resultados_spi/20260930_180831_573454.log)
- [2 MHz, pausa 1.000 µs](resultados_spi/20260930_180852_131024.log)
- [4 MHz, pausa 1.000 µs](resultados_spi/20260930_180906_955508.log)
- [2 MHz, sin pausa](resultados_spi/20260930_180919_209919.log)
- [3 MHz, 10 segundos](resultados_spi/20260930_180940_641847.log)
- [3 MHz, 60 segundos](resultados_spi/20260930_180957_131604.log)

En todas las filas con integridad OK hubo cero pérdidas, duplicados, bloques
fuera de orden, cabeceras/payload incorrectos y confirmaciones PING incorrectas.
En el ensayo de un minuto se verificaron **5.953.808 bytes de patrón** dentro
de **6.458.368 bytes recibidos por SPI**, con retorno del driver de 512.
Los contadores MCU permanecieron en `[1057, 0, 0]`: los 1.057 errores SPI
pertenecían a los ensayos previos a 4 MHz, sin nuevos errores durante ese minuto.

Una lectura exploratoria anterior se ejecutó antes de que finalizara la carga
del firmware y no recibió tramas válidas. No se usa para evaluar V6; el ejecutor
ahora exige que la aplicación figure `running`, y debe esperarse siempre a que
termine `start`.

## Interpretación y siguiente paso

El benchmark verifica el camino MCU→MPU y PING/confirmación en sentido inverso.
No aprueba rendimiento: incluso el mejor resultado breve ronda 101 kB/s,
por debajo de los 250 kB/s actuales y del objetivo de 750 kB/s. Todos los
ensayos terminaron con `throughput_pass=false` y código de salida 1.

Los errores a 4 MHz persisten al ampliar la pausa entre transacciones, por lo
que esa pausa por sí sola no resuelve el problema. El driver MCU contabilizó
errores durante esos ensayos. Esto no identifica todavía su causa exacta:
faltan la instrumentación del retorno de error y el análisis de servicio de
interrupciones, FIFO y temporización. Tampoco se aisló cuánto tiempo consume
Python frente al ioctl/kernel o al MCU.

El siguiente paso es medir esos componentes y evaluar un transporte SPI
con DMA o un driver apropiado, sin tocar aún el ADC validado. Antes de integrar
la adquisición se debe repetir el benchmark con margen de caudal y extender
la prueba sin errores (por ejemplo, 10 minutos). Este minuto es una comprobación
inicial, no una certificación de estabilidad prolongada. No se prolongó a
10 minutos una configuración que ya incumple el requisito de caudal.

## Verificación del código y recuperación

El sketch compiló para `arduino:zephyr:unoq`: 75.368 bytes de programa y
31.528 bytes de variables globales. Pasaron las 37 pruebas locales, incluyendo
interoperabilidad C++/Python real, CRC conocido, wrap de secuencia y detección
de pérdidas, duplicados, corrupción y comandos incorrectos.

Antes de cargar V6 se exportó V5 a
`respaldos/unoq/osciloscopio_20260930_180515_758077.zip`.
V6 quedó instalada como aplicación independiente; los fuentes de V4/V5, el
firmware R4 y los monitores no se modificaron. La recuperación consiste en
detener V6 y cargar/iniciar V5, según el [README V6](../arduino/historico/v6/README.md).
Al finalizar se ejecutó esa recuperación: V6 detenida y Q V5 compilada,
cargada e iniciada correctamente. No se repitió en esta sesión la medición
de muestras a través del R4 ni la prueba gráfica del monitor.
