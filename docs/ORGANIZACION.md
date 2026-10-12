# Organización del proyecto

## Entradas actuales

- [Monitor V16](../monitor/v16/README.md): `python monitor/v16/app.py`.
- [Q V16](../arduino/v16/README.md): MCU/app/relay de la pareja actual.
- `tools/`: preparación del Q y relay por defecto V16; calibración V15 conservada para la versión histórica.
- `transport/`: herramientas y documentación del transporte.

## Versiones archivadas

[Monitores históricos](../monitor/historico/README.md) reúne V6–V15 y los
scripts anteriores. V12, V13 y V14 conservan sus receptores, recursos y
calibraciones. Sus imports y tareas de VS Code apuntan a las rutas históricas.

[Firmwares históricos](../arduino/historico/README.md) incluye V12 Audio, V13 Pulse, V11 P992
(adquisición sin WAV) y las versiones anteriores. Las herramientas siguen
aceptando `--version v11_p992` de forma explícita. El valor predeterminado
de consola es V16; V12 Audio y V13 Pulse siguen seleccionables explícitamente.

Las imágenes V10 están en `assets/historico/`; las capturas usadas en la
presentación actual permanecen en `assets/`.

## Datos y validación

`capturas/`, `calibraciones/`, `audios/`, `diagnosticos/` y `respaldos/`
conservan los datos y evidencia existentes. Esta organización no elimina
capturas ni modifica apps instaladas en el Q.

`tests/v13`, `tests/v14` y las pruebas anteriores verifican las versiones
archivadas, incluida `tests/v15`; `tests/v16` verifica la actual. Qt5 y Qt6 se prueban en procesos
separados. La verificación de rutas y pruebas locales no implica una nueva
validación física.

## Verificación de la consolidación · 8 de octubre de 2026

469 pruebas locales aprobadas: 208 anteriores, 123 de V13, 32 de V14 y
106 de V15, en procesos separados. Se comprobaron enlaces Markdown, tareas
de VS Code y configuraciones/catálogo Arduino. Los 250 archivos versionados
migrados permanecen en sus destinos históricos. No se operó el Q.

V16 es la pareja activa. Monitor V15 está en `monitor/historico/v15`; Q V12 Audio y V13 Pulse están en `arduino/historico/v12_audio` y `arduino/historico/v13_pulse`. Catálogos, imports, tests y herramientas siguen esas rutas.
