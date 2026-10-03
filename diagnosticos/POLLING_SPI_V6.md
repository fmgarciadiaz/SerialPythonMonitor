# SPI3 por registros: prueba del 1 de octubre de 2026

El acceso directo a TXDR/RXDR supera el fallo observado a 4 MHz con el driver
por interrupciones. A 6 MHz se verificaron **104.852 bloques en 120 segundos,
sin errores**, con **401.929 B/s de patrón útil**. Todavía no alcanza el objetivo
de 750.000 B/s y ocupa la CPU con polling, incluso esperando al maestro.
La integración con ADC DMA sigue pendiente.

## Condiciones y resultados

UNO Q, aplicación independiente `Scope SPI Polling V6`, receptor nativo C en
Linux, protocolo SCP1/v2: bloques de 512 bytes con 460 bytes de patrón
verificado, CRC32 y PING confirmado en el bloque siguiente. Pausa solicitada
entre intercambios: 250 µs, salvo la prueba a 1 MHz (1.000 µs).
Las frecuencias son las solicitadas/configuradas por spidev; no se midió SCK
con instrumental externo. Las demás interrupciones permanecieron habilitadas.

| SPI solicitado | Duración | Bloques válidos / intercambios | Patrón útil B/s | Integridad | Registro |
| --- | ---: | ---: | ---: | --- | --- |
| 1 MHz | 10 s | 1.872 / 1.872 | 86.054 | Sin errores | [log](resultados_spi/20261001_000857_785052.log) |
| 3,8 MHz | 10 s | 6.423 / 6.423 | 295.391 | Sin errores | [log](resultados_spi/20261001_084718_429588.log) |
| 4 MHz | 10 s | 6.700 / 6.700 | 308.133 | Sin errores | [log](resultados_spi/20261001_084735_150434.log) |
| 8 MHz | 10 s | 10.243 / 10.246 | 471.125 | Tres errores | [log](resultados_spi/20261001_084753_209485.log) |
| 6 MHz | 10 s | 8.739 / 8.739 | 401.919 | Sin errores nuevos | [log](resultados_spi/20261001_084825_388492.log) |
| 6 MHz | 120 s | 104.852 / 104.852 | 401.929 | Sin errores nuevos | [log](resultados_spi/20261001_084848_407573.log) |

El ensayo prolongado registró cero errores de CRC, patrón, secuencia, ACK,
comandos y transferencias cortas. Los contadores MCU empezaron y terminaron
en `[3,0,0]`: eran los errores históricos del ensayo a 8 MHz. El valor
`last_driver_error` también queda retenido; no representa un error nuevo.
Todos los ensayos terminaron con código 1 porque **ninguno alcanzó el umbral
de caudal**. `integrity_pass` y `throughput_pass` se evalúan por separado.

## Qué mostró el registro de error

A 8 MHz hubo tres CRC incorrectos, tres saltos de secuencia, tres errores de
ACK y tres errores SPI nuevos del MCU. La captura previa a limpiar SPI fue
`last_driver_error=-122919`, que decodifica `SR=0xe027`; la máscara de errores
es `0x20`: **UDR, underrun de transmisión**. En ese momento faltaron bytes
para alimentar la transmisión. No se detectó OVR en esa captura.
Esto identifica el fallo de esta variante a 8 MHz; no prueba por sí solo
qué bandera produjo el fallo del driver anterior a 4 MHz.

## Implementación y corrección

El core inicializa clocks y pines. Después se deshabilita solamente IRQ99/SPI3
y se transfieren bytes por registros, sin `spi_transceive()`. El bucle precarga
la FIFO de ocho bytes, atiende TX/RX y conserva el estado de error antes de
limpiarlo. Hay timeout de 50 ms para transacciones activas.

La primera versión cerraba RX prematuramente cuando EOT estaba activo y RXP
apagado: produjo cinco recepciones cortas en la
[primera prueba a 1 MHz](resultados_spi/20261001_000526_017540.log).
Se corrigió drenando también RXWNE/RXPLVL hasta completar los 512 bytes.
La prueba posterior a 1 MHz y toda la tabla usan esa corrección.
Como referencia para el tratamiento de la FIFO se consultó el
[driver SPI oficial de ST](https://github.com/STMicroelectronics/stm32u5xx-hal-driver/blob/main/Src/stm32u5xx_hal_spi.c).

SHA256 del sketch corregido:
`7ced0196b1deca94ac8eba06b3fcb7578789d917f61cf6f20d9f86ea1b675b25`.
Los logs incluyen identificación del firmware y hashes de fuentes locales.
Entre la prueba inicial nocturna y las pruebas de la mañana se observó un
reinicio de Linux de causa no determinada; se reconstruyó el verificador
temporal y se volvió a iniciar la misma variante corregida.

## Implicaciones y siguiente paso

La API síncrona puede esperar mientras una ISR mueve los bytes. Reemplazarla
por registros eliminó ese camino, pero este bucle también bloquea el hilo
y consume CPU. El resultado permite investigar **DMA SPI para alimentar y
vaciar las FIFO**, manteniendo el ensayo sintético y bidireccional antes de
conectarlo al ADC. No demuestra todavía captura ADC simultánea ni entrega
USB al monitor.

El tiempo medio MCU fue aproximadamente 96 µs preparando cada bloque y
110 µs comprobando el PING. A 6 MHz, en 120 s, el receptor dedicó unos
83,5 s al intercambio y 33,8 s a las pausas: también queda trabajo fuera
del movimiento de bytes. La siguiente implementación deberá medirse con
los mismos criterios de integridad y caudal.

Instrucciones reproducibles y restauración en
[README de la variante](../arduino/historico/v6_polling/README.md).

## Cierre de la prueba

Se detuvo `Scope SPI Polling V6` y se volvió a compilar, cargar e iniciar
`Osciloscopio DMA_TXRX V5 Experimental` correctamente en el UNO Q.
No se repitió la adquisición completa R4/monitor después de restaurar.
La suite local terminó con **47 pruebas aprobadas**.
