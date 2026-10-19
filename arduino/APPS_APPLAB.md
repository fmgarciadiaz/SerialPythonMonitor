# Aplicaciones del Q · inventario verificado 19/10/2026

| App de usuario | Estado |
|---|---|
| Scope V17 | Única instalada, activa; pareja de `monitor/v17` y `arduino/v17` |
| Scope V16 | Retirada; respaldo local y exportación recuperable |
| Scope V16 Send1400 Experimental | Retirada; experimento y exportación conservados |

Los ejemplos del catálogo Arduino no son apps de usuario instaladas; se conservaron.

## Limpieza y respaldo

Antes de eliminar las dos apps antiguas se exportaron con datos y se verificaron integridad ZIP y SHA256. App CLI `destroy` quitó contenedores y caché; para retirar las entradas del catálogo también se eliminaron sus carpetas de fuentes ya respaldadas. Scope V17 no se reinició ni recompiló y conservó su identidad de firmware.

- [Inventario antes/después y hashes](../diagnosticos/resultados_v17/cleanup_apps_20261019_160438.json).
- [Exportaciones](../respaldos/unoq/apps_retiradas_20261019_160438).
- [Catálogo vigente](apps_catalogo.json).
- [Catálogo de referencias históricas](historico/apps_catalogo.json): rutas anteriores, no inventario instalado.
- [Inventario narrativo anterior](../docs/historico/APPS_APPLAB_20261019.md).

## Recuperar una app archivada

Usar `arduino-app-cli app import` en el Q con el ZIP correspondiente, transferido previamente por ADB. Importar recupera la app; arrancarla puede sustituir el firmware activo. Para volver a operar una versión antigua, cerrar el monitor y seguir su guía con el argumento explícito de versión. No ejecutar dos parejas simultáneas.

Las herramientas mantienen V16 como valor predeterminado por compatibilidad: para la app actual indicar siempre `--version v17` o `--firmware v17`.
