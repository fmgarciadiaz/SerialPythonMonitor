# Firmware actual del UNO Q

La pareja actual es [V11 P992](v11_p992/README.md) con el monitor Python V12.
El sketch MCU está en [sketch.ino](v11_p992/oscilloscope/sketch/sketch.ino)
y el relay MPU en [relay](v11_p992/relay/).

```sh
python3 tools/unoq.py status --version v11_p992
python3 tools/unoq.py compile --version v11_p992
python3 tools/unoq.py deploy --version v11_p992
python3 tools/usb_stream.py start --firmware v11_p992
```

Los comandos anteriores seleccionan explícitamente V11 P992. Sin estas
opciones, las herramientas conservan V8 config por defecto. Las aplicaciones anteriores
están en [historico](historico/README.md) y se pueden seleccionar explícitamente
con `--version` o `--firmware`. Ver [catálogo](apps_catalogo.json).
Para UART al R4 se conserva el [puente R4 V5](historico/v5/r4_bridge_v5/README.md).

[MCU y cableado](../docs/UNO_Q_TECNICO.md) · [Relay](../docs/TRANSPORTE_TECNICO.md) · [Historia completa](../docs/HISTORIA.md).
