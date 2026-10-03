# Validación de adquisición configurable y monitor V10

2 de octubre de 2026, UNO Q y puente R4 V5 conectados físicamente. Aplicación
**Scope Acquisition Config V8**, core Zephyr 1.0.0, SPI 20 MHz y UART 3 Mbps.

## Perfiles de hardware

[Informe de adquisición](resultados_usb/20261002_110316_862943_acquisition.json):
**20 perfiles y 81.920 pares comprobados**, sin errores de timestamp, índice
ni rango ADC. Se probaron:

- Las once tasas de 1 a 31,25 kHz, a 14 bits por SPI.
- 8, 10, 12 y 14 bits a 31,25 kHz, en SPI y UART.
- 8 bits / 1 kHz en UART, incluyendo nodos de 2,048 segundos.

Cada perfil recibió al menos dos nodos. Los timestamps tuvieron exactamente
el período seleccionado. La señal física alcanzó 255 en 8 bits, 4095 en
12 bits y 16383 en 14 bits en los perfiles donde se capturó el máximo.
La adquisición volvió al final a 14 bits / 31,25 kHz / SPI.
No se ensayaron físicamente las 88 combinaciones de resolución/tasa/salida:
las opciones mantienen el formato y un caudal no superior al máximo probado.

## Interfaz Qt y CSV

[Informe de V10](resultados_usb/20261002_110540_172856_monitor_v10.json):
**344.064 pares entregados a Qt**, con siete etapas que incluyeron:
14 bits / 31,25 kHz; 8 bits / 10 kHz con SPI → UART → SPI;
12 bits / 25 kHz; 10 bits / 1 kHz; retorno a los valores iniciales.
La frecuencia calculada por el monitor coincidió con la solicitada en todas.

| Bits / tasa | Filas CSV | Huecos de tiempo | Huecos de índice | Errores de escala a voltios |
|---|---:|---:|---:|---:|
| 14 / 31,25 kHz | 78.706 | 0 | 0 | 0 |
| 8 / 10 kHz, ambos destinos | 110.539 | 0 | 0 | 0 |
| 12 / 25 kHz | 62.871 | 0 | 0 | 0 |
| 10 / 1 kHz | 4.043 | 0 | 0 | 0 |
| 14 / 31,25 kHz, retorno | 78.282 | 0 | 0 | 0 |

Los cinco CSV suman **334.441 filas**. El cambio de salida conservó el archivo
y su continuidad. Bits/tasa abrieron capturas separadas. Se verificaron panel
plegado/desplegado, resúmenes confirmados, rango raw y normalización a 3,3 V.
Las capturas temporales se leyeron antes de eliminarlas; se conserva el informe.

[Vista principal](../assets/monitor_v10.png) y [panel desplegado](../assets/monitor_v10_config.png),
obtenidos durante la prueba con UART, 8 bits y 10 kHz.

## Verificación local y alcance

**99 pruebas locales pasaron** con `python -m unittest discover -s tests`.

Las pruebas cruzadas ejecutan C++ real con solicitudes Python y verifican las
respuestas con Python y el relay C. Cubren 44 perfiles, parámetros inválidos,
CRC/padding, época, resolución/rango, período, y reintentos sin reiniciar el
lector. Las pruebas Qt comprueban que las elecciones estén dentro del panel y
que un cambio de adquisición limpie un trazo congelado.

El firmware compiló con 94.520 bytes de programa y 152.336 bytes de variables
(58 % de RAM), dejando 109.808 bytes para el resto. El relay se compiló con
`-Wall -Wextra -Werror` en Linux del Q.

Son ensayos funcionales breves, no una validación de precisión analógica ni una
prueba prolongada de horas. UART conserva DATA sin CRC. Las llamadas al render
Qt offscreen no equivalen a FPS presentados en una pantalla real.

El Q queda con la app configurable y su relay listos para V10. V9 y su firmware
V7 dual están conservados; se respaldó esa app antes de ensayar:
[ZIP](../respaldos/unoq/osciloscopio_20261002_105917_996617.zip).
