# V20: caché acotada de coeficientes por nota para DX Piano

## Medición antes de cambiar

Se extrajeron los parámetros del panel real en una instancia local sin Q, seleccionando DX Piano. Se midieron bloques480 con20notas activas durante los primeros~2s, después de~0,2s de priming. No son tiempos IPC ni aceptación de tiempo real.

| Perfil | DAC | Media render | Máximo | Audio por bloque |
|---|---:|---:|---:|---:|
|DX Piano|20kHz|6,242ms|8,838ms|24ms|
|FM básico sostenido|20kHz|1,821ms|3,422ms|24ms|
|DX Piano|40kHz|4,636ms|6,193ms|12ms|
|FM básico sostenido|40kHz|1,209ms|1,862ms|12ms|

El coste se concentra en `voice_render`; DAC/ganancia y preparación de voces son menores en esta captura. El profiler separado localiza operaciones NumPy repetidas dentro de `_render`. No demuestra que todo el underrun anterior proceda del render: la cadena también incluye IPC, espera y planificación.

[Perfil, parámetros exactos y fuentes](../diagnosticos/resultados_v20/dx_render_profile_20261102/report.json). Los archivos `.pstats` adjuntos permiten revisar el perfil; sus tiempos instrumentados no se mezclan con el benchmark sin profiler.

## Optimización incorporada al host

`monitor/v20/fm_source.py` conserva en una LRU de256entradas dos coeficientes escalares e inmutables que dependen sólo de la frecuencia de nota: brillo DX y profundidad del registro grave. Reutiliza las mismas fórmulas originales. No almacena fases, audio, voces, envolventes ni estado mutable. La interpolación entre frecuencias mantiene su rama original.

Comparación local de seis repeticiones alternadas baseline/candidato a40k,100bloques por repetición: mediana4,332→4,065ms/bloque, reducción6,17%. No es una mejora medida de FPS, del cable, de la colaMCU o de la capacidad máxima.

[Experimento y diff](../diagnosticos/resultados_v20/dx_note_cache_candidate_20261102/report.json). El código del experimento no opera Q. La referencia original del host se conserva con SHA256 en [respaldo](../respaldos/host/v20_before_dx_note_cache_20261102/manifest.json); firmware y relay no cambian.

La comparación comprobó audiofloat exacto a20/40k y cambios de notas/release. Los tests de producto ampliaron la equivalencia a cambios de frecuencia, gate, códigosDAC y transición de volumen/estado de ganancia, además del límite de caché. Pasaron18tests focalizados y luego21incluyendo el wrapper; el último ajuste del wrapper sólo incorpora hashes de los módulos Synth al informe y pasó9tests. No se modifican versiones congeladas ni recibos de aceptación pública.

El helper guarda ahora preset, forma de onda y niveles de osciladores en sus snapshots para identificar la carga real. La validación física usa DX Piano original del panel aDAC40k,20notas y hold30s; el preset es percusivo y las voces pueden extinguirse naturalmente. No equivale al controlFM básico sostenido ni a20voces durante todo el hold.


## Cierre físico

DX Piano aDAC40k completó 30.045s desdePLAY, con pico20voces renderizadas y posterior extinción natural del preset. Se confirmaronPLAY/progreso/STOP, salidaapagada y recuperación de la configuración inicialV20 durante≥10s con0pérdidas/fatales. Identidad, recibo y sello de activación permanecieron iguales. El hash del módulo optimizado coincide con el capturado al iniciar el ensayo.

La ventana estuvo oculta(exposición0%): es un pase funcional, no aceptación de carga de dibujo ni prueba de resolución causal del fallo anterior. El arranque usaADC40kdual desde el principio, distinto del ensayo que venía deRADIO1,86MS/s. Los fallos GUI/RF intermitentes siguen pendientes.

[Informe físico](../diagnosticos/resultados_v20/v20_dx_note_cache_physical_20261102_dac40k/report.json) · [Resumen](../diagnosticos/resultados_v20/v20_dx_note_cache_physical_20261102_dac40k/summary.json).

La correlación ACK al cierre no quedó completa: 4552/4551; no se interpreta como pérdida física ni se oculta como diagnóstico completo.
