# Firmware V11 P992 · pareja del Monitor V12

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
`tools/usb_stream.py start --firmware v9_fast`; abrir `monitor/v11/app.py`.
Las opciones por defecto de las herramientas siguen en V8 config/V10;
seleccionar explícitamente `v11_p992` para esta nueva pareja.
