# Organización del proyecto · 19/10/2026

## Código y recursos

| Ruta | Función |
|---|---|
| `monitor/v17`, `arduino/v17`, `tests/v17` | Pareja activa y pruebas |
| `monitor/v16`, `arduino/v16`, `tests/v16` | Respaldo local anterior |
| `monitor/historico`, `arduino/historico` | Versiones archivadas; rutas conservadas |
| `tools`, `transport` | Preparación, relay y utilidades de transporte |
| `experimentos` | Candidatos aislados con capturas, informes y restauración |
| `diagnosticos` | Scripts de ensayo y resultados por área |
| `respaldos/unoq` | Exportaciones del Q y archivos de recuperación |
| `audios`, `capturas`, `calibraciones`, `assets` | Datos, evidencia y recursos |

Se mantuvieron las rutas del código, los experimentos y la evidencia para no romper imports ni runners. No se eliminaron capturas ni respaldos.

## Documentación

El [estado vigente](ESTADO_ACTUAL_V17.md), el [plan](../Plan%20de%20trabajo.md) y la [continuidad](../%23%20Continuar%20desde%20donde%20quedaste.md) son las entradas para retomar. Las guías de monitor/firmware enlazan ese estado antes de sus informes fechados.

Se archivaron sin perder su contenido la presentación V16 y los registros acumulados de plan/continuidad. Se ajustaron sus enlaces Markdown relativos desde la raíz original:

- [Presentación anterior](historico/README_v16_20261019.md).
- [Plan acumulado](historico/PLAN_ACUMULADO_20261019.md).
- [Continuidad acumulada](historico/CONTINUIDAD_ACUMULADA_20261019.md).
- [Inventario anterior de apps](historico/APPS_APPLAB_20261019.md).

Los informes históricos conservan sus cifras y resultados. Un ensayo aprobado en una fecha no acredita automáticamente la estabilidad global actual. Los documentos técnicos heredados siguen disponibles como descripción de su implementación original.

## Q

Sólo Scope V17 queda como app de usuario, activa. V16 y Send1400 se exportaron y verificaron antes de retirarlas; los ejemplos Arduino se conservaron. [Inventario, hashes y recuperación](../arduino/APPS_APPLAB.md).

La limpieza no cambió lógica, fuentes de firmware, configuración ADC/DAC ni reinició V17. Las herramientas CLI conservan el valor predeterminado V16; elegir V17 explícitamente.

## Validación de esta organización

Se verifican enlaces de las entradas vigentes, catálogos JSON y rutas locales de la app activa. La limpieza del Q comprueba inventario final e identidad de firmware antes/después. Son comprobaciones de organización e instalación; no agregan validación analógica, de tasas o de estabilidad de audio.
