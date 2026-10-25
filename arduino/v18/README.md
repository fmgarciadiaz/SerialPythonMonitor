# Pareja del Q para Monitor V18

- App: `Scope V18`, ruta `/home/arduino/ArduinoApps/scope-v18`.
- Fuentes: `arduino/v18/oscilloscope` y `arduino/v18/relay`.
- Relay: `serialmonitor-usb-stream-v18`, protocolo SCP1 V4, TCP8766.
- Configuración: `unoq.json`.

La primera versión parte de las funciones y tasas validadas de V17. Las tasas
privadas del experimento `fs_max_v18` no se incluyen automáticamente.
V17 permanece instalada y respaldada con su monitor y binarios; sus fuentes
no se modifican. Sólo una pareja puede estar activa sobre SPI/ADC a la vez.

`python tools/activate_v18_pair.py` muestra el destino sin cambiar el Q.
`--run` crea una app independiente si no existe; rechaza sobrescribirla.
La GUI conecta únicamente con la app y relay V18 ya activos.

[Respaldo y transición](../../docs/PAREJAS_V17_V18.md).
