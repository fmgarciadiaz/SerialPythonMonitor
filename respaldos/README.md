# Respaldos

Copias para recuperar fuentes y parejas de firmware/relay. La carpeta
`parejas/` conserva los archivos congelados de cada versión, variantes distintas
y respaldos relevantes de V20. Las copias de producción redundantes se
depuraron comparando SHA256 de fuentes, firmware y relay; los respaldos completos
retenidos mantienen sus cachés y manifiestos intactos.

[Inventario de copias equivalentes y limpieza](LIMPIEZA_20261105.md).

| Carpeta | Contenido |
|---|---|
| [parejas](parejas) | Parejas y archivos congelados verificados |
| [host](host) | Copias del monitor previas a cambios concretos |
| [unoq](unoq) | Exportaciones ZIP de las apps del Q previas a cargas de firmware |
| [fuentes](fuentes) | Copias aisladas de fuentes conocidas |
| [experimentos](experimentos) | Respaldos asociados a ensayos |
| [historico](historico) | Sketches `.bak` de etapas iniciales |

Los informes de cada ensayo identifican el respaldo correspondiente.
La reorganización conserva el contenido de los archivos; no carga firmware.

## Apps retiradas del Q · 19/10/2026

[Exportaciones V16 y Send1400](unoq/apps_retiradas_20261019_160438), verificadas antes de eliminar las apps. [Inventario y SHA256](../diagnosticos/resultados_v17/cleanup_apps_20261019_160438.json). Sólo V17 queda instalada como app de usuario. Las fuentes y evidencias locales anteriores se conservan.
