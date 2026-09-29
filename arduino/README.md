# UNO Q desde este proyecto

Entorno USB preparado para **Osciloscopio DMA_TXRX V2** el 28/09/2026.

## Código que se edita

- `oscilloscope/python/main.py`: Python de Linux en el Q (actualmente un ejemplo que imprime Hello world y ejecuta `App.run`).
- `oscilloscope/sketch/sketch.ino`: firmware del microcontrolador del Q.
- `oscilloscope/sketch/sketch.yaml`: perfil y dependencias Arduino.
- `oscilloscope/app.yaml`: configuración de App Lab.

El monitor `SerialMonitorAppQt_V6.py` sigue ejecutándose en el Mac.
La copia histórica anterior está en `respaldos/sketch_pre_applab.ino.bak`; **el despliegue usa
`arduino/oscilloscope/sketch/sketch.ino`**. El sketch traído de la placa usa
`SERIAL_BAUD = 1100000U`, frente a 1000000U en la copia anterior.

## Comandos desde la raíz del proyecto

```sh
python3 tools/unoq.py status
python3 tools/unoq.py compile
python3 tools/unoq.py backup
python3 tools/unoq.py deploy
python3 tools/unoq.py logs
python3 tools/unoq.py logs --follow
python3 tools/unoq.py stop
python3 tools/unoq.py start
```

En VS Code: **Terminal → Run Task**, tareas `UNO Q: …`.
`Cmd+Shift+B` ejecuta la compilación sin carga.

`compile` valida la sintaxis Python local y en destino, transfiere los fuentes a
una carpeta temporal única del Q y compila allí con Arduino CLI. No ejecuta
Python ni carga firmware. No valida imports o dependencias Python en el
contenedor; eso se comprueba al iniciar la aplicación. Elimina su carpeta temporal
al finalizar. La primera compilación puede demorar por las dependencias.

`deploy` compila, exporta un respaldo de los fuentes actuales a
`respaldos/unoq/*.zip`, detiene la aplicación, copia los archivos locales y la
inicia mediante App CLI (que gestiona compilación/carga y Python). Este comando
reinicia la aplicación y actualiza el firmware. Si falla compilación o respaldo,
no llega a detenerla. Si falla después de detenerla, se informa el error; no hay
restauración automática. El ZIP puede importarse desde App Lab para recuperar
los fuentes. No incluye los datos persistentes de la aplicación.

El despliegue reemplaza archivos del mismo nombre, pero no elimina archivos
remotos ausentes localmente. Si renombrás/eliminás módulos, revisá también la
copia remota. No se sincronizan `.cache`, `data`, `.git` ni entornos Python.
Trabajá en la copia local al usar este flujo: cambios posteriores hechos en
App Lab no se descargan automáticamente y podrían ser reemplazados al desplegar.
Los respaldos previos al despliegue permiten recuperar esos fuentes.

## Conexión y herramientas

`unoq.json` identifica la aplicación, ruta remota, FQBN y dispositivo USB.
No guarda contraseñas. `UNOQ_SERIAL` permite seleccionar otra placa explícitamente;
`UNOQ_ADB` permite indicar otro ejecutable ADB. Por defecto se busca ADB en PATH
y en las herramientas ya instaladas por Arduino IDE en macOS.

Verificado en esta placa:

- USB ADB: `1060031107`.
- Arduino App CLI: 0.13.0.
- Arduino CLI: 1.5.1.
- Plataforma: `arduino:zephyr` 1.0.0; placa: `arduino:zephyr:unoq`.
- Aplicación remota: `/home/arduino/ArduinoApps/osciloscopio-dma_txrx-v2`.
- Compilación correcta: 79.992 bytes de programa y 76.000 bytes de RAM global.
- Lectura de estado/logs y exportación de respaldo comprobadas por USB.
- Despliegue disponible, todavía no ejecutado durante la preparación del entorno.

La fuente importada se conservó tal como estaba en el Q. La aplicación que ya
estaba en ejecución no se reinició durante la preparación.

Referencias: [Arduino App CLI](https://github.com/arduino/arduino-app-cli),
[estructura de aplicaciones](https://github.com/arduino/arduino-app-cli/blob/main/docs/app-specification.md).
