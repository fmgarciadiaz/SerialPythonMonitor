# SPI3 con DMA TX/RX — 1 de octubre de 2026

La variante `Scope SPI DMA V6` mueve los bytes con GPDMA1 en ambos sentidos.
**A 20 MHz y pausa solicitada de 150 µs completó 212.221 bloques en 120 s,
sin errores, a 813.510 B/s de patrón verificado.** Superó el umbral de
750.000 B/s sin modificarlo: integridad y caudal aprobados, salida 0.
Es aproximadamente el doble del ensayo prolongado por polling (401.929 B/s)
y 3,25 veces el caudal de adquisición actual de 250.000 B/s.

## Barrido físico

Receptor C ejecutado en Linux del UNO Q, SPI modo 0, bloques SCP1/v2 de 512
bytes, 460 bytes de patrón útil. Misma generación y comprobación que en
V6 por interrupciones y por registros: CRC32, secuencia, contadores MCU y
PING con confirmación en el siguiente bloque. No se conectó todavía el ADC.

| SPI solicitado | Pausa solicitada | Duración | Bloques íntegros | Patrón útil B/s | Resultado |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 MHz | 1.000 µs | 5 s | 938 | 86.144 | [Integridad correcta](resultados_spi/20261001_090324_279560.log) |
| 8 MHz | 250 µs | 10 s | 10.241 | 471.026 | [Integridad correcta](resultados_spi/20261001_090338_701185.log) |
| 16 MHz | 250 µs | 10 s | 13.947 | 641.509 | [Integridad correcta](resultados_spi/20261001_090359_789814.log) |
| 20 MHz | 200 µs | 10 s | 16.244 | 747.170 | [Integridad correcta; caudal insuficiente](resultados_spi/20261001_090424_470394.log) |
| 20 MHz | 150 µs | 10 s | 17.663 | 812.440 | [Integridad y caudal aprobados](resultados_spi/20261001_090447_248012.log) |
| 20 MHz | 150 µs | 120 s | 212.221 | 813.510 | [Integridad y caudal aprobados](resultados_spi/20261001_090506_895003.log) |

Todos los bloques enviados en estos ensayos fueron válidos. Cero errores
de cabecera, patrón, CRC, secuencia, ACK, SPI del MCU, comandos y transferencias
cortas. Los contadores comenzaron y terminaron en cero, sin reiniciar la
aplicación entre pruebas.

La frecuencia indicada es la solicitada y devuelta por spidev; no se midió
SCK con instrumental. La pausa Linux real incluye el despertar del hilo:
en el ensayo corto a 20 MHz/150 µs promedió aproximadamente 225 µs. No se
debe asumir que una pausa exacta de hardware de 150 µs sea suficiente: el
MCU empleó aproximadamente 96 µs preparando DATA y 104 µs comprobando PING,
además del rearmado y la caché.

En el ensayo prolongado se verificaron 97.621.660 bytes de patrón; circularon
108.657.152 bytes en cada dirección del intercambio full duplex. El caudal
informado cuenta sólo el patrón DATA verificado, sin sumar PING ni cabeceras.
El receptor empleó unos 66,89 s en intercambios y 47,63 s en pausas. Este
resultado valida el transporte sintético bajo estas condiciones; dos minutos
no sustituyen las pruebas posteriores con adquisición simultánea y carga real.

## Qué cambió

GPDMA1 canal 2 alimenta TXDR y canal 3 vacía RXDR mediante solicitudes SPI3
11 y 10, respectivamente. Se usan accesos de un byte y bloques lineales.
Se preservaron los canales 0/1 para una futura integración con ADC/timestamps.
Buffers alineados a 16 bytes, limpieza/invalidez de caché antes de armar y
invalidación RX tras detener DMA. El firmware consulta EOT, finalización de
ambos canales y errores; guarda las banderas antes de limpiarlas.

La primera comparación importante es a 8 MHz/250 µs: el
[polling por byte](POLLING_SPI_V6.md) tuvo tres underruns en diez segundos;
DMA completó el ensayo corto sin ese fallo, con caudal similar. La mejora
de caudal posterior provino de poder aumentar el reloj y reducir la pausa.

**Todavía hay espera activa del fin de bloque.** DMA elimina el movimiento
de cada byte por software, pero este ensayo no mide ahorro de CPU ni usa
una notificación asíncrona. No se deshabilitan globalmente las interrupciones
durante la transferencia. La caché utiliza una sección crítica breve.

El core instalado 1.0.0 aporta inicialización de SPI, headers CMSIS/LL y
mapa de pines. No se recompiló Zephyr ni se habilitó su driver SPI DMA.
Referencias de hardware: [manual RM0456 de ST](https://www.st.com/resource/en/reference_manual/rm0456-stm32u575585-armbased-32bit-mcus-stmicroelectronics.pdf)
y constantes LL del STM32U585 incluidas en ese core.

## Reproducibilidad y alcance

SHA256 del sketch probado:
`165df4739d2c8660ed26c3f31d3dd241abf44efbb8e206e280f9396b4ac790ff`.
La compilación usa 76.712 bytes de programa y 32.424 bytes globales.
Las 49 pruebas locales pasaron; incluyen identidad del protocolo entre
variantes y selección del destino DMA independiente.

Comandos y formato de errores en el [README DMA](../arduino/historico/v6_dma/README.md).
El ensayo deja activa la aplicación DMA, según lo solicitado; no restaura V5.
Todavía faltan adquisición real ADC simultánea, entrega USB al monitor y
comandos para configurar bits, muestreo y generador. El PING sólo valida el
camino bidireccional del transporte.
