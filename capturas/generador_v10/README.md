# Capturas del generador V10

Informes y explicación de fallas intermedias: [validación](../../diagnosticos/GENERADOR_V10.md).

| Carpeta | Contenido y estado |
| --- | --- |
| `20261002_212845_836596` | Formas SPI y 14/16 bits a 50 kHz correctos; UART terminó sin muestras del R4. |
| `qt_20261002_212953_425950` | CSV de 30 s continuo; ensayo Qt detenido por uso incorrecto del handler RUN/STOP. |
| `qt_20261002_213056_993872` | Panel, STOP/SINGLE y CSV correctos antes de corregir el reinicio ADC. |
| `20261002_213144_358206` | Amplitud/offset correctos; descubrió intercambio entre canales después de reconfigurar ADC. |
| `channels_20261002_214054_397475` | Casos antes de limpiar los registros DMA; incluye el caso que intercambió las señales. |
| `channels_20261002_215831_688341` | Versión final: 24 perfiles con canales estables. CSV del caso inicial. |
| `20261002_215953_131832` | Versión final: 12 etapas SPI completas, correctas. |
| `qt_20261002_220115_078941` | Versión final: un CSV de 381.246 filas sin discontinuidades al cambiar el generador, usar STOP y SINGLE. |

Los CSV conservan todos los pares recibidos durante cada ventana; los voltajes
se calculan con la referencia nominal del ADC. A2 y A3 son los puntos del circuito
indicados por el usuario; el generador excita el circuito desde A0/DAC0.

Validación de la columna permanente y motor DMA final: [CSV Qt](qt_20261002_232217_882337/continuo.csv), 381.545 filas sin gaps, y [40 perfiles repetidos](../../diagnosticos/resultados_usb/20261002_231937_033811_generator_channels.json), captura de referencia en [case_0](channels_20261002_231937_033811/case_0.csv).
