# Generador V10: validación física y reinicios ADC

Versión final: monitor V10 y firmware V8 configurable, 2 de octubre de 2026.

| Ensayo final | Resultado | Informe |
| --- | --- | --- |
| 12 etapas SPI: formas, amplitud/offset, finalización, 14/16 bits a 50 kHz | 728.524 pares, sin discontinuidades | [JSON](resultados_usb/20261002_215953_131832_generador_v10.json) |
| 24 perfiles alternados: 14/16 bits, 31,25/50 kHz | 686.008 pares, A2/A3 estables en todas las etapas | [JSON](resultados_usb/20261002_215831_688341_generator_channels.json) |
| Panel Qt, cambios automáticos, STOP, SINGLE y un mismo CSV | 381.246 filas, cero discontinuidades | [JSON](resultados_usb/20261002_220115_078941_generador_qt_v10.json) |
| Contrato C++/Python/C, motor e interfaz | 122 pruebas locales pasaron | `python -m unittest discover -s tests -q` |

Amplitud/offset: extremos nominales de 0,8 y 2,5 V; percentiles medidos en A3
0,796 y 2,514 V usando la referencia nominal de 3,3 V. Pulso solicitado de
200 ms: ancho observado de 200,48 ms al cruzar la mitad de escala. No es una
calibración metrológica; el motor actual tiene una grilla de 0,5 ms.

Compilación final en Q: 99.772 bytes de programa, 154.296 bytes de variables y
107.848 bytes libres. Firmware cargado; relay activo. Restaurados ADC de
14 bits / 31,25 kHz, destino SPI y cuadrada de 2,5 Hz entre 0 y 4095.

El relay agrega un asentamiento inicial de 20 ms y lectura del nivel de READY
antes del primer intercambio: durante el arranque aparecieron flancos seguidos
de un paquete íntegramente 0xff. Los CRC, secuencias y checks de muestras siguen
siendo obligatorios; después del primer frame no se agrega espera.

La captura UART con R4 queda sin validar: el Q confirmó el generador, pero el
R4 no entregó muestras. Se requiere comprobar su enlace físico. La validación
SPI no demuestra estabilidad indefinida ni calibración de amplitud.

[Panel en uso](../assets/monitor_v10_generador.png).

## Evidencia y pruebas intermedias

Los informes intermedios se conservan para distinguir errores del ensayo de
fallas físicas. `20261002_212953_425950_generador_qt_v10.json` invocaba el handler
RUN/STOP sin cambiar el botón, por lo que el ensayo no avanzó y llegó al límite
normal de CSV de 30 s; las 934.505 filas no tuvieron discontinuidades. El ensayo
se corrigió para usar los clics reales. Los informes siguientes de Qt pasaron.

## Validación del cambio de pines

Las 115 pruebas locales de protocolo, configuración, interfaz y capturas pasaron.
El mapeo se verificó con el overlay del core Zephyr 1.0.0 y el pinout oficial.
La compilación local con Arduino CLI 1.5.1 y el perfil Zephyr 1.0.0 pasó:
91.840 bytes de programa, 151.872 bytes de variables y 110.272 bytes libres.

El firmware se compiló y cargó en el UNO Q el 2 de octubre: 95.332 bytes de
programa, 152.692 bytes de variables y 109.452 bytes libres. El primer arranque
del relay agotó la espera de READY; el segundo arrancó correctamente.

La [captura física](resultados_usb/20261002_210722_466805_dac_a2_a3.json)
registró 156.867 pares sin discontinuidades, con 2,499 Hz en A2 y 2,498 Hz en A3.
El [gráfico](../capturas/diagnosticos_dac_a2_a3/20261002_210722_466805.png)
muestra ambos puntos; el [CSV completo] — captura pesada eliminada; ver inventario de limpieza
conserva todas las muestras. Los voltajes usan la referencia nominal de 3,3 V,
sin calibración de amplitud.

Con el DAC activo, las [pruebas SPI](resultados_usb/20261002_210842_023032_spi_rates.json)
pasaron en los cuatro perfiles, comprobando índices, timestamps y rango ADC:

| Bits | Tasa | Pares verificados | Resultado |
| --- | --- | --- | --- |
| 14 | 31.250 Hz | 188.416 | Correcto |
| 14 | 50.000 Hz | 296.960 | Correcto |
| 16 | 31.250 Hz | 185.645 | Correcto |
| 16 | 50.000 Hz | 296.960 | Correcto |

Se restauró SPI a 14 bits y 31.250 Hz, con el relay activo. Estas capturas
breves validan el cambio de pines y la convivencia con el DAC de prueba;
la nueva validación del motor y el panel se registra a continuación.

## Validación del generador

Las 122 pruebas locales pasan, incluyendo contrato C++/Python/C, rangos, CRC,
campos reservados, continuidad de adquisición, frecuencia del motor, niveles,
finalización, peticiones idempotentes, panel plegable y aplicación automática.
La compilación local y la compilación en el Q pasan. La compilación remota inicial usó
99.692 bytes de programa y 154.208 bytes de variables (107.936 bytes libres).

Las capturas físicas y la validación Qt/CSV se incorporan tras ejecutar los
ensayos del generador.

## Ensayos de reinicio de adquisición

Al ampliar la prueba a cambios repetidos de bits/tasa se observó intercambio
entre la señal completa y la filtrada en A2/A3, sin que el protocolo detectara
pérdidas de índices o timestamps. Luego el MCU marcó `fatal=1` al iniciar una
época de 50 kHz; el relay rechazó correctamente ese frame con CRC válido.
Se conservaron el [log](resultados_usb/20261002_generador_reconfigure_failure.log)
y las [observaciones previas](resultados_usb/20261002_generator_channel_roles_before.json).

Limpiar flags de ADC y evitar solicitudes DMA durante el UG de TIM2 no bastó:
el [ensayo siguiente](resultados_usb/20261002_214054_397475_generator_channels.json)
volvió a observar intercambio al pasar a 16 bits / 50 kHz. Un ensayo posterior
reinicializó por RCC el bloque ADC12: no arrancó en dos intentos (primer frame
SPI íntegramente 0xff), y ese cambio se retiró. Los validadores estrictos y los
buffers originales se conservan.

Para reproducir:

```bash
python3 tools/usb_stream.py start --build-native  # nuevo protocolo del generador
python diagnosticos/verificar_generador_v10.py
python diagnosticos/verificar_canales_generador.py --cycles 6
python diagnosticos/verificar_generador_qt_v10.py
```

UART se prueba por separado con `--r4-port /dev/cu.usbmodem...`; requiere el
puente físico TX/D1 del Q → RX/D0 del R4 y masa común. En el primer ensayo el
control del Q confirmó el generador en UART, pero el R4 no entregó muestras;
no se considera validación de captura UART.

La revisión del [driver oficial ST](https://github.com/STMicroelectronics/stm32u5xx-hal-driver/blob/main/Src/stm32u5xx_hal_dma_ex.c)
(`DMA_List_Init`) mostró que al reiniciar una lista se deben limpiar también
CTR1, CTR2, CBR1, CSAR y CDAR. El firmware anterior sólo reiniciaba el estado
interno/FIFO y cambiaba el enlace, conservando un bloque parcial de la captura
anterior. Si ese bloque termina tras un número impar de conversiones, el nuevo
nodo comienza por el segundo canal. La corrección pone esos registros a cero
antes de cargar la cabeza del anillo, conservando la sincronización de nodos
que ya estaba validada. El ensayo repetido comprueba ambas formas de señal,
además de los índices y timestamps.
