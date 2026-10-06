# Firmware de adquisición SPI y generador

App Lab: **Scope Acquisition P992 V11**. Carpeta remota independiente:
`/home/arduino/ArduinoApps/scope-acquisition-p992-v11`.

Contrato fijo SCP1 V3, 992 bytes, 113 pares por trama, 19 fragmentos por
nodo de 2048 pares; SPI 32 MHz, cola de cuatro nodos, TCP 8766. Firmware,
relay y receptor V12 deben utilizarse juntos. [Manifiesto](manifest.json).

A2/A3 entradas ADC y A0/DAC0 salida. ADC, DMA, propiedad de buffers,
coordinación, timestamps y generador conservan la implementación P992
[validada](../../experimentos/tasas_spi/opt125/README.md). El relay propio
se encuentra en `relay/`; no depende de fuentes de `experimentos/`.

Preparación inicial (sin alterar las otras apps):

```sh
python3 tools/unoq.py compile --version v11_p992
python3 tools/usb_stream.py build --firmware v11_p992
python3 tools/unoq.py create --version v11_p992
```

Antes de iniciar, cerrar el monitor, detener el relay actual y su app
explícita; detener también cualquier candidato opt125 activo. Después:

```sh
python3 tools/usb_stream.py start --firmware v11_p992
python monitor/v12/app.py
```

Rollback a V11/100 kHz: detener relay, detener app `v11_p992` e iniciar
`tools/usb_stream.py start --firmware v9_fast`; abrir `monitor/historico/v11/app.py`.
Las herramientas seleccionan V11 P992 por defecto. Se conserva la selección
explícita de versiones históricas mediante `--version` y `--firmware`.

## ADC de 16 bits a 62,5 kHz

PLL2 toma HSE de 16 MHz, divide por 2, multiplica por 25 y divide por 4:
ADC a 50 MHz para todos los perfiles. Se conservan 16 subconversiones de
14 bits por canal y shift derecho de 2 bits. 16 bits/62,5 kHz está permitido
sólo por SPI; UART conserva 31,25 kHz.

[Ensayo inicial](../../capturas/adc16_rate/test62k5_20261005_002648/informe.json):
311.409 pares en 5 s, dropped=fatal=0.
[Regresión ADC14/125 kHz](../../capturas/validacion_v12/20261005_003145_591574/informe.json):
FFT, heatmap, SINGLE y 507.565 filas CSV continuas. Estos ensayos no
certifican precisión absoluta, ENOB ni estabilidad prolongada.

El kernel ADC/DAC es compartido; ver [arquitectura MCU/MPU](../../docs/UNO_Q_TECNICO.md)
y [relay](../../docs/TRANSPORTE_TECNICO.md). Las calibraciones Bode previas
se obtuvieron con reloj ADC de 40 MHz y requieren nueva comprobación.

[Revisión y prueba sostenida ADC16](../../diagnosticos/ADC16_V12.md): 7.495.680 pares en120s,
sin discontinuidades y con restauración exacta del perfil y generador.

## Versiones y enlaces

Esta carpeta conserva [V11 P992](unoq.json), pareja de [Monitor V12](../../monitor/v12/README.md).
El conjunto usado para audio es [V12 Audio](../v12_audio/README.md) con [Monitor V13](../../monitor/v13/README.md).
