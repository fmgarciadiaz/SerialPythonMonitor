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

La pareja aceptada incluye ADC16 CH1 a 150.943,396 S/s (1060 ticks).
Se conserva sobremuestreo ×16, desplazamiento de 2 bits y reloj del ADC de 54 MHz. ADC16 dual
permanece en 76.226,775 S/s/canal. No se habilitan los candidatos más rápidos
que fallaron; sólo 1060 ticks se publica como nueva opción CH1 de 16 bits.
[Validación y despliegue](../../docs/TASAS_ALTAS_V18_20261025.md).

La pareja aceptada incorpora además CH1 ADC8 a 1.860.465,116 S/s,
ADC10 a 1.333.333,333 S/s y ADC14 a 941.176,471 S/s. Solo se ampliaron
listas y condiciones de perfiles: los relojes, DMA, packing y métodos de
las tasas existentes permanecen. ADC12 y ADC16 conservan sus máximos.
Ver [incorporación y evidencia](../../docs/SONDEO_TASAS_V18_20261025.md).

Segunda tanda: ADC10 CH1 1.355.932,203 S/s; ADC12 1.103.448,276 S/s;
ADC14 1.000.000 S/s. ADC8 conserva 1.860.465,116 S/s: el escalón siguiente
falló con audio instalado y no está habilitado. Métodos anteriores intactos.
