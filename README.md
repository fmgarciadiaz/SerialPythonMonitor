# Osciloscopio UNO Q + R4 / SerialMonitor

[Características y uso del SerialMonitor](monitor/README.md) ·
[README anterior completo](docs/historico/README_anterior.md).

## Qué usar

| Conjunto | Firmware Q + R4 | Monitor | Muestreo | Q → R4 | R4 → PC | Estado |
|---|---|---|---|---|---|---|
| **Estable** | **V4** | **V6** | 20 kHz por canal | 3 Mbps | **2 Mbps** | Probado en las placas y CSV |
| Experimental | V5 | V7 | 25 kHz por canal | 3 Mbps | **3 Mbps** | Preparado para pruebas; sin validación física |

La versión experimental se elige explícitamente. Las placas conservan la V4.
Los números del firmware y del monitor son independientes: V4 se usa con V6.

## Abrir el monitor

```sh
python iniciar_monitor.py                      # V6 estable
python iniciar_monitor.py --version v7         # V7 experimental
python iniciar_monitor.py --list               # ver versiones sin abrir ventanas
```

Seleccionar el puerto **R4**. La V6 usa 2.000.000 baudios; V7 usa 3.000.000.
Instalar dependencias en el entorno elegido con `python -m pip install -r requirements.txt`.
En VS Code también están las tareas **Monitor V6: Abrir estable** y
**Monitor V7: Abrir experimental**, y las mismas opciones para ejecutar con F5.

## Dónde está cada cosa

```text
iniciar_monitor.py              Entrada única para abrir el monitor
monitor/
  v6/app.py                   Monitor estable
  v7/app.py                   Monitor experimental
  historico/                  V1–V5, Tkinter, consola y notebook originales
arduino/
  v4/oscilloscope/            App Lab Q estable (sketch + Python + perfil)
  v4/r4_bridge_v4/            Sketch R4 estable
  v4/unoq.json                Destino de las tareas V4
  v5/oscilloscope/            App Lab Q experimental
  v5/r4_bridge_v5/            Sketch R4 experimental
  v5/unoq.json                Destino independiente V5
capturas/                     Capturas existentes y nuevas de V6
  experimental_v7/            Capturas nuevas de V7
respaldos/                    Respaldo de firmware y exportaciones de App Lab
  unoq/                       Incluye la V3 original
diagnosticos/                Herramientas y resultados de validación
tests/                       Pruebas automatizadas
tools/                       Operaciones sobre el Q
docs/historico/              Documentación anterior, sólo referencia
```

## Firmware y versiones

[Guía Arduino y comandos](arduino/README.md) ·
[Detalle V4 estable](arduino/v4/oscilloscope/README.md) ·
[Preparación V5](arduino/v5/README.md) ·
[Validación física V4](diagnosticos/VALIDACION_V4.md).

```sh
python3 tools/unoq.py status                  # por defecto, V4 estable
python3 tools/unoq.py compile --version v5    # compilar V5 sin cargar
```

Arduino IDE: los sketches del Sketchbook se llaman `r4_bridge_v4` y
`r4_bridge_v5`. Son copias de las carpetas versionadas del repositorio.
El código de referencia está aquí: después de editar en el IDE, incorporar
esos cambios a la carpeta de la versión correspondiente antes de desplegar.
El antiguo `DebuggerRtRx` se conserva como histórico a 1,1 Mbps.

Cada nueva revisión experimental usa otra carpeta y otro destino de App Lab.
Sólo se marca estable tras compilar, medir continuidad y comprobar captura.
No promover una versión únicamente porque el gráfico se vea bien.

Pruebas: `python -m unittest discover -s tests`.
