# Organización del proyecto

## Entradas actuales

- [Monitor V15](../monitor/v15/README.md): `python monitor/v15/app.py`.
- [Q V12 Audio](../arduino/v12_audio/README.md): audio y adquisición.
- [Q V13 Pulse](../arduino/v13_pulse/README.md): variante compatible con pulsos cortos.
- `tools/`: preparación del Q, relay y calibración; las herramientas de calibración usan V15.
- `transport/`: herramientas y documentación del transporte.

## Versiones archivadas

[Monitores históricos](../monitor/historico/README.md) reúne V6–V14 y los
scripts anteriores. V12, V13 y V14 conservan sus receptores, recursos y
calibraciones. Sus imports y tareas de VS Code apuntan a las rutas históricas.

[Firmwares históricos](../arduino/historico/README.md) incluye V11 P992
(adquisición sin WAV) y las versiones anteriores. Las herramientas siguen
aceptando `--version v11_p992`; se conserva su valor predeterminado de consola
para evitar cambiar el firmware elegido al ejecutar comandos existentes.
Para audio especificar `--version v12_audio` o `--version v13_pulse`.

Las imágenes V10 están en `assets/historico/`; las capturas usadas en la
presentación actual permanecen en `assets/`.

## Datos y validación

`capturas/`, `calibraciones/`, `audios/`, `diagnosticos/` y `respaldos/`
conservan los datos y evidencia existentes. Esta organización no elimina
capturas ni modifica apps instaladas en el Q.

`tests/v13`, `tests/v14` y las pruebas anteriores verifican las versiones
archivadas; `tests/v15` verifica la actual. Qt5 y Qt6 se prueban en procesos
separados. La verificación de rutas y pruebas locales no implica una nueva
validación física.

## Verificación de la consolidación · 8 de octubre de 2026

469 pruebas locales aprobadas: 208 anteriores, 123 de V13, 32 de V14 y
106 de V15, en procesos separados. Se comprobaron enlaces Markdown, tareas
de VS Code y configuraciones/catálogo Arduino. Los 250 archivos versionados
migrados permanecen en sus destinos históricos. No se operó el Q.
