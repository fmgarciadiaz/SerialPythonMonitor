# Perfil SPI V6: comparación Python/C — 30/09/2026

**Actualización:** el [barrido posterior a 3,8 MHz](BARRIDO_SPI_38MHZ.md) alcanzó
294 kB/s sin errores durante dos minutos. Esta sección conserva las mediciones
de la comparación inicial a 3 MHz.

La medición identificó dos límites diferentes: el costo del patrón sintético
en Python y el tiempo de rearmado del MCU. El receptor C alcanzó unos
**250 kB/s íntegros a 3 MHz** en la prueba breve, frente a **95 kB/s** del
Python original instrumentado. Se optimizó también Python, que alcanzó
**206 kB/s**. Ninguna configuración alcanza todavía el objetivo de 750 kB/s.

## Cambios y condiciones

- Firmware V6 instrumentado: protocolo 2, bloques de 512 bytes, 32 bytes de
  estado y 460 de patrón; se mantienen CRC32, secuencia y PING/confirmación.
- El MCU informa tiempo de preparación/verificación y conserva el último
  error negativo aunque las siguientes transacciones funcionen.
- Receptor C independiente, compilado con GCC 14.2 en ARM64, `-O2`, sin
  bibliotecas externas aparte de libc/libm. Se ejecuta en la misma imagen
  Arduino que Python, mediante el mismo `SPI_IOC_MESSAGE(1)`.
- Preparación, intercambio, verificación y pausa se miden con reloj monótono
  en Linux. `ioctl` está incluido dentro de `exchange`; no deben sumarse.
- La optimización Python sustituye los bucles por byte por tablas XOR,
  `bytes.translate` y asignaciones por pasos. Produce exactamente el mismo
  patrón y sigue verificándolo completo: no se eliminó ninguna comprobación.
- Las mediciones se realizaron después de terminar compilaciones y descargas.
  No hay ADC activo ni transporte al PC en estos ensayos.

## Comparación breve

| Receptor | Reloj | Pausa solicitada | Duración | Válidos/total | Patrón B/s | Integridad |
|---|---:|---:|---:|---:|---:|---|
| Python original instrumentado | 3 MHz | 0 | 10 s | 2.072/2.072 | 95.256 | OK |
| C | 3 MHz | 0 | 10 s | 3.320/6.635 | 152.687 | Falla |
| C | 3 MHz | 250 µs | 10 s | 5.446/5.446 | 250.446 | OK |
| C | 4 MHz | 250 µs | 5 s | 0/3.357 | 0 | Falla |
| Python optimizado | 3 MHz | 250 µs | 10 s | 4.489/4.489 | 206.412 | OK |

Registros completos:

- [Python original instrumentado](resultados_spi/20260930_182725_699706.log)
- [C sin pausa](resultados_spi/20260930_182745_335136.log)
- [C con pausa de 250 µs](resultados_spi/20260930_182802_084359.log)
- [C a 4 MHz](resultados_spi/20260930_182829_759925.log)
- [Python optimizado](resultados_spi/20260930_182900_101888.log)

Los tiempos medios por intercambio a 3 MHz explican el resultado:

| Fase | Python original | C, pausa 250 µs | Python optimizado, pausa 250 µs |
|---|---:|---:|---:|
| Preparar PING | 1.600 µs | 13 µs | 92 µs |
| Intercambiar, incluyendo ioctl | 1.562 µs | 1.485 µs | 1.619 µs |
| Verificar DATA | 1.658 µs | 13 µs | 172 µs |
| Pausa y administración del bucle | 5 µs | 325 µs | 340 µs |

Python original consume aproximadamente 6,75 de cada 10 segundos preparando
y verificando el patrón. C elimina gran parte de ese costo. La pausa real
supera la solicitada porque interviene la planificación de Linux.

El ioctl de C tarda aproximadamente 1.485 µs por bloque, próximo a los
1.365 µs teóricos para 512 bytes a 3 MHz. Esta comparación no sustituye
una medida eléctrica de SCK ni separa todos los tiempos del kernel.

## Rearmado y error a 4 MHz

La [validación de C durante 60 segundos](resultados_spi/20260930_182929_089745.log)
confirmó **32.689 bloques íntegros**, **15.036.940 bytes de patrón** y
**250.607 B/s**, a 3 MHz y con pausa solicitada de 250 µs. No hubo CRC,
cabeceras, patrones o confirmaciones incorrectos, ni pérdidas, duplicados,
desorden o incrementos de los contadores de error del MCU. El último error
conservado siguió siendo `-5`, de la prueba previa a 4 MHz.

El MCU informa unos **99 µs de preparación y 104 µs de verificación**.
Con C sin pausa, aproximadamente una de cada dos lecturas recibió una trama
inválida y falló la confirmación del comando. Los contadores SPI del MCU no
aumentaron en esa prueba. Al agregar 250 µs se recibieron todas las tramas
correctamente. El resultado es consistente con un maestro que inicia la
siguiente transacción antes de que el periférico se haya rearmado.

A 4 MHz fallan todas las tramas incluso con pausa. Al volver a 3 MHz se
recuperó el estado MCU: **672 errores SPI acumulados y último retorno negativo
`-5`**. Ese código corresponde a `EIO`, un error de entrada/salida; por sí solo
no demuestra que la causa sea un overflow o una latencia de interrupción.
Durante la recuperación no se agregaron errores. La lentitud de Python
no explica esta corrupción, porque se reproduce con C.

## Qué falta para reemplazar el R4

El camino C ya está cerca de los 250 kB/s de registros de la adquisición
actual, pero sin el margen necesario para absorber variaciones ni ejecutar
el ADC concurrentemente. El umbral de aceptación se mantiene en 750 kB/s;
`throughput_pass` sigue siendo falso.

El siguiente trabajo es aislar el fallo a mayor reloj y evaluar SPI por DMA
con buffers alternados y coordinación del rearmado. El core instalado usa
SPI por interrupciones: aún no se habilitó DMA SPI ni se asignaron sus canales.
No corresponde conectar el ADC hasta validar ese transporte y verificar que
sus recursos no interfieran con el DMA de adquisición.

Para reproducir la comparación, consultar el
[README V6](../arduino/historico/v6/README.md). La prueba C `--replay` utiliza el mismo
validador que el acceso físico; las pruebas locales le inyectan secuencias con
wrap, pérdidas, duplicados, CRC/patrón incorrecto, tramas cortas, confirmaciones
incorrectas y reinicios de contadores, y comparan los resultados con Python.

## Estado final

Pasaron **45 pruebas locales**, incluyendo interoperabilidad del firmware
C++ con Python y equivalencia del verificador C ante fallos inyectados.
El firmware instrumentado compiló y se probó físicamente; al terminar se
detuvo V6 y se volvió a compilar, cargar e iniciar **Q V5** correctamente.
Los fuentes del ADC, el R4 y los monitores permanecen sin cambios. No se
repitió la prueba de adquisición por R4 ni la prueba gráfica en esta sesión.

Respaldos previos al ensayo:

- V5: `respaldos/unoq/osciloscopio_20260930_182558_615813.zip`.
- V6 anterior: `respaldos/unoq/osciloscopio_20260930_182559_158769.zip`.
