# Organización del proyecto

- `monitor/v18/`: aplicación actual autocontenida y soporte de Preparar Q.
- `arduino/v18/`: firmware y relay pareados con el monitor actual.
- `tests/v18/`: pruebas de la versión actual.
- `monitor/v17/` y `arduino/v17/`: pareja congelada, conservada sin cambios.
- `monitor/historico/`, `arduino/historico/`, `tests/historico/`: versiones anteriores, incluida V16.
- `respaldos/parejas/`: respaldos inmutables pareados, fuentes y manifiestos.
- `docs/`: guías, planes, informes y validación; los índices apuntan a V18.
- `capturas/`: destino de grabaciones nuevas. Los registros generados anteriores se eliminaron.
- `audios/`: archivos de entrada de ejemplo, conservados; no son grabaciones del monitor.
- `diagnosticos/` y `experimentos/`: scripts e informes de medición, con la evidencia histórica conservada.

## Revisión local del 26/10/2026

Se conservaron las rutas de fuentes y campañas para no romper imports ni
informes históricos. Se corrigió el índice de experimentos a V18 y se añadieron
índices de [herramientas](../tools/README.md),
[resultados recientes](../diagnosticos/resultados_v18/README.md) y procedencia
de [imágenes de Radio](../assets/README.md).
Se limpiaron cachés Python regenerables y carpetas de capturas vacías;
[inventario](orden_archivos_20261026.json). La limpieza de imágenes temporales
está registrada por separado en [capturas](../capturas/limpieza_20261026.json).
No se operó el Q ni se modificaron fuentes de firmware o la pareja V17.

En el Q quedan Scope V18 activa y Scope V17 detenida. Se eliminaron trece apps
Rate Probe y sus cachés de relay, y un container saved obsoleto. El catálogo de
ejemplos de fábrica sin inicializar se conserva. Los manifiestos de limpieza
son [local](limpieza_local_20261024.json) y [Q](limpieza_q_20261024.json).

Los accesos activos del IDE son V18. Los accesos históricos están separados en
`.vscode/launch_historico.json` y `.vscode/tasks_historico.json`; son referencias,
no tareas de despliegue de la versión actual.

El README raíz sigue siendo la landing con badges, imágenes y explicación de
funciones. La auditoría de migración y evidencia heredada está en
`docs/historico/migracion_v18/`, sin ser dependencia del runtime actual.
