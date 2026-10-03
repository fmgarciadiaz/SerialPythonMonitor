# SPI DMA con IRQ y READY — 1 de octubre de 2026

La aplicación independiente **Scope SPI IRQ READY V6** reemplaza el polling
de finalización del MCU por callbacks DMA y un semáforo. Linux reemplaza la
pausa fija por eventos de READY. El transporte sigue siendo sintético y
bidireccional SCP1/v2, con los mismos CRC, secuencias y ACK del ensayo anterior.

**Validación final: 215.002 bloques en dos minutos, sin errores, a
824.169 B/s útiles con 20 MHz solicitados y pausa fija de 0 µs.**
Integridad y caudal aprobados, código de salida 0.

## Resultados físicos

| SPI solicitado | Pausa fija | Duración | Bloques válidos / transferencias | Patrón útil B/s | Resultado |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 MHz | 0 µs | 5 s | 1.112 / 1.112 | 102.177 | [Integridad correcta](resultados_spi/20261001_141059_782392.log) |
| 20 MHz | 0 µs | 10 s | 17.893 / 17.893 | 823.003 | [Integridad y caudal aprobados](resultados_spi/20261001_203943_304082.log) |
| 20 MHz | 0 µs | 120 s | 215.002 / 215.002 | 824.169 | [Integridad y caudal aprobados](resultados_spi/20261001_204019_030031.log) |

Se cuentan 460 bytes útiles de patrón por cada bloque de 512 bytes; no se
suman PING ni cabeceras al caudal útil. La frecuencia es la solicitada y
devuelta por spidev, sin medición externa de SCK. El umbral permanece en
750.000 B/s. El ensayo a 1 MHz devuelve código 1 sólo por caudal insuficiente.

La prueba final verificó 98.900.920 bytes de patrón. Todos los contadores de
errores permanecieron en cero: cabeceras, patrón, CRC, secuencias, ACK, SPI,
comandos y transferencias cortas. Las tres pruebas se ejecutaron sin recargar
el sketch entre ellas. La espera acumulada Linux por READY fue 49,73 s,
aproximadamente 231 µs por bloque, con un máximo de 3,51 ms tolerado sin
pérdidas. El campo `gap` acumula el pequeño coste del bucle, sin `nanosleep`.

Frente a los 813.510 B/s del [ensayo DMA anterior](DMA_SPI_V6.md), el caudal
sube aproximadamente un 1,3 %. El avance principal es retirar la espera
activa del MCU y coordinar cada bloque por disponibilidad real, manteniendo
el margen de caudal; no una gran reducción del tiempo de preparación.

## Cómo se maneja la pausa

El MCU publica READY sólo después de preparar DATA y armar ambos DMA.
Linux reserva GPIO70 como entrada y usa `poll()` para esperar un flanco
ascendente por bloque. No envía el siguiente bloque por ver nuevamente el
nivel alto anterior. Se valida la secuencia de eventos; los flancos iniciales
tardíos anteriores al intercambio previo no cuentan como nuevos permisos.
Si no hay READY durante un segundo, la medición termina con error sin
generar una transferencia especulativa.

En el MCU, la primera finalización DMA baja READY. Cuando terminaron ambos
canales, el callback entrega un semáforo y el hilo comprueba EOT, contadores
de bytes, errores SPI y PING antes de preparar la siguiente trama. SPI3 sigue
por registros; GPDMA1 usa el controlador del core para sus callbacks.
No hay ISR por byte ni polling continuo durante la espera normal.

**Pausa fija cero no significa tiempo entre bloques cero.** En el ensayo
corto a 20 MHz, Linux esperó READY unos 232 µs por bloque. El MCU necesitó
aproximadamente 99 µs preparando DATA y 110 µs verificando PING, además del
rearmado y caché. Deshabilitar globalmente las IRQ no elimina ese trabajo y
evitaría recibir las notificaciones de DMA usadas ahora. Se conservan las
secciones críticas breves para mantenimiento de caché; las otras IRQ siguen
habilitadas y la IRQ SPI3 se mantiene deshabilitada.

La espera MCU por semáforo tiene revisión cada 50 ms para detectar una
transferencia truncada (detección aproximada en 50–100 ms). Esperar al maestro
sin transferencia no consume secuencia ni cuenta como error. No se midió
un porcentaje de CPU; sólo se verificó el funcionamiento del mecanismo de
espera y del transporte.

## Dos particularidades del core resueltas

1. **READY también autoriza el arranque.** El
   [esquema oficial del UNO Q](https://docs.arduino.cc/resources/schematics/ABX00162-schematics.pdf)
   conecta PG13 con GPIO70 a 1,8 V. Arduino Router pone GPIO70 alto al estar
   listo, y el loader del core 1.0.0 espera ese nivel antes de ejecutar el
   sketch. Cambiarlo a entrada antes del arranque dejó el MCU esperando:
   [primer intento, cero bloques y timeout](resultados_spi/20261001_135513_045896.log).
   Ahora `tools/unoq.py start --version v6_irq` prepara ese nivel bajo reset
   del MCU. El sketch espera que el receptor reserve GPIO70 como entrada
   con pull-down antes de tomar PG13 como salida. `stop --version v6_irq`
   devuelve el nivel de arranque para poder iniciar otras variantes.
2. **Las IRQ son compartidas.** El core tiene `CONFIG_SHARED_INTERRUPTS=1`.
   Agregar una ISR dinámica dejó al driver DMA original activo; éste limpiaba
   TC antes de nuestra lectura. El
   [segundo intento](resultados_spi/20261001_140240_881162.log) entregó un bloque
   válido y después timeout. La lectura SWD mostró EOT y contadores DMA en
   cero, pero sus banderas TC ya limpias. La corrección usa `dma_config()` y
   callbacks del controlador existente; no modifica la tabla ISR con
   direcciones absolutas ni sustituye el core.

Entre intentos hubo una desconexión y reinicio de Linux, de causa no
determinada. El ejecutable C ahora se conserva por hash en la caché del
usuario del Q para sobrevivir a reinicios; las dependencias de compilación
siguen instalándose únicamente en un contenedor temporal.

## Código y alcance

Sketch final SHA256:
`466260a7421e552c75b30dede401d879e4765fefe52aa14d106ba1cb2e074538`.
Receptor C SHA256:
`363dbbf38f8a1aa84607e60ac21f6da31eefe2bb4df9a1fe0bcb87b10d9ce8a8`.
Compilación: 78.024 bytes de programa y 33.056 bytes globales.
**57 pruebas locales aprobadas**, incluyendo protocolo idéntico, verificador
C/Python, destino independiente y orden/recuperación de los GPIO de arranque.

La variante IRQ + READY queda cargada; no se restaura V5, según lo pedido.
Los comandos reproducibles y errores están en el
[README de la variante](../arduino/historico/v6_irq/README.md).
El siguiente paso es integrar buffers alternados y ADC/timestamps manteniendo
la comprobación de secuencias, CRC y desbordamientos. La entrega USB al monitor
y los comandos de configuración siguen pendientes.
