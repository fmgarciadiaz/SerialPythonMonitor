# Limpieza autorizada · 4/11/2026

Se eliminaron4.702archivos de caché regenerable Python/JIT/test y6dumps
derivados de compilación/relocalizaciones. Total:88.228.596bytes lógicos y
65.613.824bytes de bloques asignados estimados (62,57MiB). La diferencia
incluye archivos que ya estaban dataless; no se leyó su contenido para
materializarlos. Los bloques asignados no garantizan el mismo cambio de
espacio libre debido a APFS/sincronización.

- [Inventario de cachés anterior](caches_before.json).
- [Seis derivados y ELF conservados](derived_before.json).
- [Resultado](result.json).
- [Mayores diagnósticos, sólo metadatos](diagnostics_top20.json).

No se borraron entornos completos, monitor de ninguna versión, código de
tests, documentos, audios originales, respaldos, `.git`, binarios ELF/bin,
recibos ni informes primarios de pruebas/crashes. Tampoco se operó el Q.
Los pyc de V20 recién materializados se conservaron por el problema de
arranque bajo demanda. No se hicieron pruebas de producto para esta limpieza.

El principal espacio adicional está en `.venv-v19Pyside` (~884MiBresidentes);
se conservó. Los intérpretes configurados actualmente en `.vscode` apuntan a
Conda externo Python3.13, también en entradas V19/V18. No se completó una
búsqueda exhaustiva de helpers históricos por las lecturas cloud bloqueadas.
