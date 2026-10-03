# Oversampling de 16 bits en V10

**Estado actual: hasta 50 kHz por SPI y 31,25 kHz por UART**, conservando
oversampling ×16. La ampliación y sus ensayos se detallan al final.

## Primer ensayo hasta 12,5 kHz

Ensayo del 2 de octubre de 2026, UNO Q STM32U585, core Zephyr 1.0.0,
app Scope Acquisition Config V8 y puente UNO R4 a 3 Mbps.

En el selector ADC se agregó **16 bits · oversampling ×16**. ADC1 convierte
cada canal 16 veces a 14 bits, suma y desplaza dos bits. El DMA y los paquetes
siguen llevando timestamp uint32 y dos ADC uint16. El ratio LL es el entero
16 para ADC1; la constante LL_ADC_OVS_RATIO_16 corresponde a ADC4.

| Tasa de pares por segundo | Ventana por subconversión | Tiempo de los dos canales |
|---|---:|---:|
| 1 y 2 kHz | 391 ciclos / 9,775 µs | 326,4 µs |
| 4, 5, 8, 10 y 12,5 kHz | 68 ciclos / 1,7 µs | 68 µs |

Los tiempos incluyen 17 ciclos de conversión por subconversión, a 40 MHz.
El límite de 12,5 kHz deja 80 µs entre disparos. Los timestamps siguen siendo
los del disparo TIM2; cada canal tiene una ventana de integración y se
convierte secuencialmente. Promediar filtra ruido y señales rápidas. La fuente
y su impedancia siguen condicionando el asentamiento del capacitor.

## Prueba física del transporte

[Informe de los perfiles](resultados_usb/20261002_134030_893745_acquisition.json):
las siete tasas pasaron en **SPI y UART**, con 4096 pares por combinación:
**57.344 pares de 16 bits**. Se comprobó período exacto, índices consecutivos
y rango. Las capturas alcanzaron 65532 y registraron valores no múltiplos
de cuatro: los bits adicionales contienen información, no son ceros añadidos.
Esto comprueba la ruta de datos; no mide precisión analógica ni ENOB.

El retorno a 14 bits / 31,25 kHz / SPI también pasó con 4096 pares.
El oversampling se deshabilita al volver a cualquier resolución nativa.
Las pruebas son breves, de al menos dos nodos por perfil.

## Verificación local

113 pruebas pasaron. Los perfiles válidos se recorren con solicitudes Python,
respuestas del código C++ real, decodificación Python y validación del relay C.
Se prueba además el rechazo de 16 bits por encima de 12,5 kHz y la interfaz:
seleccionar 16 bits reduce la tasa, bloquea opciones incompatibles y actualiza
la escala a 65535; volver a 14 bits habilita nuevamente las tasas SPI altas.

El firmware compiló y se cargó: 94.768 bytes de programa, 152.504 bytes de
variables, 109.640 bytes libres. El relay inicial recibió un paquete inválido
al arrancar; reiniciarlo permitió completar el ensayo con el validador intacto.

El máximo matemático es 65532; la escala nominal del monitor es 65535.
La reducción de ruido puede aumentar la resolución efectiva si las condiciones
analógicas lo permiten, pero una salida de 16 bits no garantiza 16 bits de
precisión efectiva. Referencias: [ST RM0456](https://www.st.com/resource/en/reference_manual/rm0456-stm32u5-series-armbased-32bit-mcus-stmicroelectronics.pdf)
y [ST AN2834](https://www.st.com/resource/en/application_note/cd00211314-how-to-get-the-best-adc-accuracy-in-stm32-microcontrollers-stmicroelectronics.pdf).

Para repetir: `python diagnosticos/verificar_adquisicion_q.py --oversampling --r4-port PUERTO_R4`.

## Monitor, voltios y CSV

[Repetición completa de Qt](resultados_usb/20261002_134248_254527_monitor_v10.json):
405.557 pares entregados al monitor. Pasaron las etapas 14 bits / 31,25 kHz,
16 bits / 1 kHz, 16 bits / 12,5 kHz SPI, el cambio a UART conservando captura,
y el retorno a 14 bits / 31,25 kHz SPI. Los cuatro CSV contienen 392.543 filas,
sin huecos de timestamp, índice ni errores de escala a voltios. La escala y
la tasa estimada coinciden con el perfil confirmado.

[Primera ejecución de Qt](resultados_usb/20261002_134114_387247_monitor_v10.json):
se cerró el relay por integridad durante la etapa final de 14 bits, tras
311.296 pares. Los CSV recibidos hasta ese momento no tuvieron errores. La
repetición pasó completa después de reiniciar el relay. La causa del cierre
no quedó identificada; no se ha demostrado estabilidad prolongada. El
validador se conservó estricto, sin omitir paquetes ni ocultar discontinuidades.

Para repetir Qt/CSV: `python diagnosticos/verificar_monitor_v10.py --oversampling --stage-seconds 4 --r4-port PUERTO_R4`.

El Q quedó al finalizar en 14 bits / 31,25 kHz / SPI, con el relay activo.

## Ampliación de tasas con ventanas más cortas

El límite inicial de 12,5 kHz conservaba una ventana de 68 ciclos en cada
subconversión. No era un límite absoluto del oversampling: se acorta la ventana
por tasa, conservando las 16 subconversiones por canal y el reloj de 40 MHz.

| Tasas de pares | Ciclos de adquisición por subconversión | Ventana | Tiempo total de ambos canales |
|---|---:|---:|---:|
| 15,625 y 20 kHz | 36 | 0,9 µs | 42,4 µs |
| 25 y 31,25 kHz | 20 | 0,5 µs | 29,6 µs |
| 40 kHz, SPI | 12 | 0,3 µs | 23,2 µs |
| 50 kHz, SPI | 5 | 0,125 µs | 17,6 µs |

A 50 kHz el período es 20 µs: quedan 2,4 µs de margen calculado. A 62,5 kHz,
16 µs no alcanzan para las 32 subconversiones mínimas, por eso no se habilita
esa tasa en 16 bits. Los modos nativos conservan sus ventanas y tasas.
En UART sigue rigiendo el límite de transporte de 31,25 kHz.

[Ensayo SPI de las seis tasas nuevas](resultados_usb/20261002_135221_942563_spi_rates.json):
**1,077,248 pares** comprobados en etapas de seis segundos. Pasaron todos
los perfiles, sin discontinuidades de timestamp o índice ni errores de rango.
A 50 kHz se recibieron 296.960 pares, con valores hasta 65532. Se comprobó
que el firmware rechaza UART a 40 y 50 kHz conservando SPI activo.

Las ventanas cortas exigen que la fuente cargue el capacitor del ADC más
rápido; el resultado debe evaluarse con la impedancia y señal reales. Estas
pruebas verifican integridad y caudal, no precisión efectiva de 16 bits.
El selector FS muestra la ventana correspondiente a la resolución elegida.

114 pruebas locales pasaron: se recorren 69 perfiles válidos en C++, C y
Python; 16 bits / 62,5 kHz se rechaza y seleccionar 16 bits desde una tasa
nativa alta envía una única configuración de 50 kHz automáticamente.

[Ensayo de destinos rápidos](resultados_usb/20261002_135249_882510_acquisition.json):
pasaron las seis tasas por SPI y las cuatro tasas UART nuevas (15,625, 20,
25 y 31,25 kHz), con 4096 pares por combinación, además del retorno a
14 bits / 31,25 kHz SPI. Total: 45.056 pares con período, índice y rango correctos.

Para repetir el barrido SPI: `python diagnosticos/verificar_spi_rates.py --bits 16 --rates 15625 20000 25000 31250 40000 50000 --seconds 6`.
Para repetir destinos: `python diagnosticos/verificar_adquisicion_q.py --oversampling --min-rate 15625 --r4-port PUERTO_R4`.

[Monitor y CSV con las tasas ampliadas](resultados_usb/20261002_135358_362040_monitor_v10.json):
690.229 pares entregados a Qt, con 16 bits / 50 kHz SPI y 16 bits / 31,25 kHz
UART, además de 1 kHz y los perfiles nativos inicial/final. Los cinco CSV
suman 581,949 filas, sin huecos de timestamp o índice ni errores de escala.
No hubo cierres ni errores en esta ejecución. Las llamadas Qt offscreen
no miden FPS presentados en una pantalla física.

Firmware compilado y cargado: 94.800 bytes de programa, 152.536 bytes de
variables y 109.608 bytes libres. La adquisición quedó en 14 bits / 31,25 kHz
SPI, con el relay preparado para elegir los nuevos perfiles desde V10.

## Bloqueo reportado al elegir 16 bits desde 62,5 kHz

Se reprodujo localmente una excepción en la limpieza de Python:
`wrapped C/C++ object of type QThread has been deleted`. El hilo Qt se borraba
automáticamente al terminar; luego `stop_input()` consultaba ese objeto.
Se conserva ahora el hilo hasta completar su detención y se elimina después.
Una prueba con un receptor que termina antes de detener la interfaz verifica
esta ruta y la detención repetida. Pasaron 115 pruebas locales.

[Registro original del relay](resultados_usb/20261002_bloqueo_oversampling_relay.log)
termina en `Dual acquisition/control integrity failure at seq=657428`.
Se recibieron más de 24 millones de pares antes del fallo. No se conservó
ese paquete, por lo que no se puede distinguir corrupción SPI de un estado
fatal de adquisición, ni atribuir el bloqueo del Q a la excepción de Python.
El relay ahora registra CRC, estado previo y el paquete completo rechazado
en su log de error; mantiene la validación estricta.

[Ocho ciclos físicos](resultados_usb/20261002_141136_979714_monitor_v10.json)
entre 14 bits / 62,5 kHz y 16 bits / 50 kHz pasaron con 1.456.181 pares.
[Dos ciclos usando aplicación automática](resultados_usb/20261002_141223_681976_monitor_v10.json)
pasaron con 800.310 pares. Los CSV no tuvieron huecos ni errores de escala.
La selección de 16 bits redujo la tasa a 50 kHz automáticamente. No se
reprodujo el fallo del relay en estas pruebas; su causa sigue pendiente.

El primer reinicio tuvo un timeout de READY; el segundo arrancó correctamente.
El firmware de adquisición conserva su implementación. El Q quedó al final
con 14 bits / 31,25 kHz SPI y el relay con diagnóstico ampliado activo.
