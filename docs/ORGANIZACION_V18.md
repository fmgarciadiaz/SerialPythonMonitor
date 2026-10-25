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
