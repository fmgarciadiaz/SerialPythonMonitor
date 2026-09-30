# Versiones Arduino

| Versión | Carpeta Q | Carpeta R4 | Monitor | Estado |
|---|---|---|---|---|
| V4 | `v4/oscilloscope/` | `v4/r4_bridge_v4/` | V6, USB 2 Mbps | Estable, 20 kHz |
| V5 | `v5/oscilloscope/` | `v5/r4_bridge_v5/` | V7, USB 3 Mbps | Experimental, 25 kHz |

Cada versión tiene su propio `unoq.json` con una aplicación remota independiente.
V4 se llama **Osciloscopio DMA_TXRX V4**; V5, **Osciloscopio DMA_TXRX V5 Experimental**.
V3/V2 permanecen en App Lab y en los respaldos; no son el destino de estas tareas.

## Comandos

```sh
python3 tools/unoq.py status --version v4
python3 tools/unoq.py compile --version v4
python3 tools/unoq.py compile --version v5
python3 tools/unoq.py create --version v5     # importar app nueva, sin iniciar
python3 tools/unoq.py backup --version v4
python3 tools/unoq.py deploy --version v5     # copia fuentes e inicia/carga firmware
python3 tools/unoq.py logs --version v5 --follow
python3 tools/unoq.py stop --version v5
python3 tools/unoq.py start --version v4
```

Sin `--version`, siempre se usa **V4**. `create` se usa una vez para una app nueva.
Las tareas de VS Code nombran explícitamente versión y estado. Cmd+Shift+B
compila V4 sin cargar. Compilar requiere el Q por USB y no altera su firmware.

`deploy` compila, exporta respaldo, detiene el destino, copia e inicia la app.
Si la compilación o el respaldo falla, no la detiene. No hay rollback automático
si falla la carga. No usar simultáneamente V4 y V5 en el microcontrolador.
Al cambiar de conjunto hay que cargar también el R4 y elegir el baud del monitor.

El repositorio es la copia de referencia; las ediciones de App Lab o Arduino IDE
no se descargan automáticamente. `respaldos/unoq/` conserva exportaciones anteriores.
Los perfiles Q fijan Core Zephyr 1.0.0 y sus bibliotecas. El R4 usa renesas_uno 1.6.0.

[Validación V4](../diagnosticos/VALIDACION_V4.md) · [Plan V5](v5/README.md).
