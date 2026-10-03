# Ampliación de tasas SPI en V10

Ensayo del 2 de octubre de 2026, UNO Q real, core Zephyr 1.0.0, SPI 20 MHz.
Se mantienen DMA, nodos de 2048 pares, timestamps TIM5 de 1 MHz, ADC 40 MHz,
8/10/12/14 bits y formato de 8 bytes por par. El caudal sólo aumenta en SPI.

| Tasa por canal | Período | Ventana ADC por canal | Destinos |
|---|---:|---:|---|
| Hasta 31,25 kHz | ≥32 µs | 391 ciclos = 9,775 µs | SPI y UART |
| 40 kHz | 25 µs | 391 ciclos = 9,775 µs | SPI |
| 50 kHz | 20 µs | 68 ciclos = 1,7 µs | SPI |
| 62,5 kHz | 16 µs | 68 ciclos = 1,7 µs | SPI |

391 y 68 son las opciones reales del ADC1 en el header STM32U5 del core:
`LL_ADC_SAMPLINGTIME_391CYCLES` y `LL_ADC_SAMPLINGTIME_68CYCLES`.
No se usan las opciones 247,5/92,5 ciclos de otras familias STM32.
A 50 kHz la ventana larga de ambos canales ya ocupa prácticamente todo el
período, sin margen suficiente para sus conversiones; se utiliza la corta.

## Primer barrido

[Informe](resultados_usb/20261002_113316_774075_spi_rates.json), 14 bits:

| Tasa | Pares recibidos | Duración | Continuidad y rango |
|---|---:|---:|---|
| 40 kHz | 597.081 | 15 s | Correctos |
| 50 kHz | 747.115 | 15 s | Correctos |
| 62,5 kHz | 934.259 | 15 s | Correctos |

**100 kHz falló**: el relay detectó una violación del contrato de integridad
en secuencia 68724 y cerró el flujo. El informe completo figura como fallido
por esa etapa. No permite atribuir el límite al ADC o a un componente concreto
del transporte. 100 kHz no queda habilitado. 125 kHz era un candidato y no se
llegó a ensayar; tampoco queda habilitado.

## Uso y alcance

El selector marca las opciones altas con **SPI** y muestra su ventana ADC.
Elegir UART propone 31,25 kHz y deshabilita las tasas altas. Pulsar Aplicar
realiza la reconfiguración; el MCU también rechaza UART si sigue activa una
tasa superior al máximo de ese enlace. Se conserva el cierre de CSV y nueva
captura al cambiar tasa o bits.

Una ventana más corta permite mayor tasa, pero exige que la fuente cargue el
capacitor ADC en menos tiempo. Puede aumentar el error con fuentes de alta
impedancia; mantener 14 bits de salida no garantiza 14 bits de precisión.
La prueba de índices, timestamps y rango detecta fallas del flujo, no cuantifica
ese error analógico. Referencia: [ST AN2834](https://www.st.com/resource/en/application_note/cd00211314-how-to-get-the-best-adc-accuracy-in-stm32-microcontrollers-stmicroelectronics.pdf).

El generador A2 y los pasos posteriores del plan permanecen sin cambios.

Se exportó la app anterior antes del ensayo: [respaldo](../respaldos/unoq/osciloscopio_20261002_113003_199067.zip). El firmware final compiló con 94.688 bytes de programa y 152.416 bytes de variables. Pasaron 101 pruebas locales, incluyendo contratos C/C++/Python, perfiles y restricciones UART en el panel.

## Resoluciones y protección UART

El [barrido final](resultados_usb/20261002_113938_239458_spi_rates.json) pasó los doce perfiles de 8/10/12/14 bits a 40/50/62,5 kHz, cinco segundos por perfil. Sin huecos ni errores de rango. En cada perfil se envió una solicitud UART directamente al MCU: las doce fueron rechazadas con UNSUPPORTED, conservando SPI. Al finalizar se restauró 14 bits / 31,25 kHz / SPI.

## Monitor y CSV

La [prueba Qt con las placas](resultados_usb/20261002_114026_782023_monitor_v10.json) recibió **849.920 pares**, recorrió las tres tasas SPI nuevas y volvió a 31,25 kHz en SPI → UART → SPI. Cinco CSV sumaron **806,310 filas**, sin huecos de índices/timestamps ni errores de conversión a voltios. Las estimaciones de tasa fueron exactamente 40.000, 50.000 y 62.500 Hz. Las capturas temporales se verificaron antes de eliminarlas.

[Panel rápido](../assets/monitor_v10_fast_config.png). El ensayo usa Qt offscreen; los render calls no miden FPS de una pantalla real.

Durante la instalación final, un primer arranque del relay recibió un frame inválido (secuencia 0xffffffff) y se detuvo. Se reinició la app/relay antes de los ensayos finales; no se omitió el frame ni se relajaron los controles de integridad.

## Un minuto al máximo habilitado

El [ensayo continuo de 62,5 kHz](resultados_usb/20261002_114157_368563_spi_rates.json) recibió **3.744.857 pares** durante 60 segundos a 14 bits, sin discontinuidades ni errores de rango. Se comprobó nuevamente el rechazo UART y se restauró 14 bits / 31,25 kHz / SPI antes de cerrar el cliente. El relay permanece activo para V10. Es una comprobación de un minuto, no un ensayo de estabilidad de horas.
