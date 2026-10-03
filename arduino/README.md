# Firmware actual del UNO Q

La versión actual es [V8 config](v8_config/README.md), utilizada por el monitor
Python V10. El sketch está en [sketch.ino](v8_config/oscilloscope/sketch/sketch.ino).

```sh
python3 tools/unoq.py status
python3 tools/unoq.py compile
python3 tools/unoq.py deploy
python3 tools/usb_stream.py start
```

Estos comandos seleccionan V8 config por defecto. Las aplicaciones anteriores
están en [historico](historico/README.md) y se pueden seleccionar explícitamente
con `--version` o `--firmware`. Ver [catálogo](apps_catalogo.json).
Para UART al R4 se conserva el [puente R4 V5](historico/v5/r4_bridge_v5/README.md).
