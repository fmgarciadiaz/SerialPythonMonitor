# V20: raster paralelo privado · 1/11/2026

Hay un candidato más rápido para detalle completo, todavía sin incorporar al monitor. No se modificaron fuentes de producto, firmware, relay ni tasas. La selección sólo existe en las herramientas privadas con --raster-workers 2 o 4; el valor habitual 1 conserva el camino actual.

## Experimentos fuera del Q

Se compararon imágenes de Línea/Escalón, tres estilos, DPR 1/2, dos canales, datos subpíxel, NaN/Inf y valores recortados. También se dibujaron 3.720.930 puntos con tres repeticiones por caso denso.

- Coordenadas enteras: descartadas; hasta 50.802 píxeles distintos en un caso.
- Lotes de 4096 segmentos: imágenes iguales en fixtures, mejora mediana global cercana al 6%; no incorporado.
- Composición Source: imágenes iguales en estos fixtures, ganancia pequeña; no incorporada.
- Franjas en 2 procesos: aceleración mediana 1,75× en el benchmark denso.
- Franjas en 4 procesos: aceleración mediana 2,98×. Cero diferencias de píxeles en los casos densos medidos y en los fixtures Rápido/Intenso.

Suave produjo diferencias en Línea/DPR 2 (hasta 56 píxeles); ese estilo mantiene el worker original. X no finito o no monótono también toma el camino original. No se afirma equivalencia universal de todos los trazados por estos fixtures.

El prototipo divide el trabajo por franjas y añade un halo del ancho del pen, conservando vecinos, puntos, mapeo global y orden de canales. Los procesos escriben regiones separadas de una imagen compartida; no poseen adquisición, puertos ni estado del Q. Hay un trabajo en vuelo. La imagen y su frame/token se publican juntos por el coordinador habitual. Al cerrar se terminan sólo los hijos gráficos propios antes de liberar arenas compartidas.

## Pruebas y aislamiento

26 tests locales PASS. Los casos nuevos verifican píxeles con procesos reales, frame/token, fallback Suave, rechazo de un segundo trabajo, cancelación en vuelo, unlink de arenas y cierre idempotente. Una prueba de regresión impide que importar el helper fuerce el backend oculto.

El primer ensayo con adquisición heredó offscreen del módulo benchmark. Su restauración pasó, pero se EXCLUYE como prueba de ventana visible. Se aisló ese ajuste al entrypoint offline y se repitió con Cocoa. Ahora el informe registra el backend y nunca considera offscreen/minimal como visible_gui_ok.

## Ensayos físicos privados

Mismo ADC8/1.860.465S/s, ventana verificada de 2 s/3.720.930 muestras, detalle 100%, estilo Rápido, Cocoa/DPR 2, exposición 100% durante las observaciones:

| Caso | Resultado funcional | Raster al final | Pinturas de ventana |
|---|---|---:|---:|
|Sin audio,20s|Datos/imagen/cierre PASS|650ms|2,1–2,2/s en los últimos intervalos|
|RADIO→A0 40kHz,60,013s|Audio/progreso/imagen/cierre PASS|650–715ms al final de reproducción|Aproximadamente1,8/s con RADIO activa|

Como referencia anterior, el worker único había medido 1329 ms y 1,2 eventos/s en la ventana larga sin audio. Son ensayos no apareados; la comparación causal más controlada es el benchmark offline. Las pinturas de ventana no equivalen necesariamente a imágenes nuevas de señal. Ninguno de los dos casos paralelos cumple el piso diagnóstico de 8 pinturas/s.

RADIO/A0: 111.720.640 muestras, margen 12,64%, pico 4/16 y slack mínimo 68.569 ticks; sin errores de audio/raster reportados. El retraso máximo observado de GUI fue aproximadamente 264 ms. Pasa el screen privado de reserva, mientras legacy headroom_pass permanecefalse por el umbral absoluto<4. No atribuir una mejora de margen MCU al raster.

Las tres restauraciones (incluida la offscreen) confirmaron V19 exacta y lectura final continua sin pérdidas/fatales. Q libre con V19 activa y V20 detenida.

## Pendientes antes de incorporar

Medir coste total CPU/RAM y duración de 120 s; ampliar pruebas con gaps temporales, datos extremos, cursores, STOP/SINGLE/zoom y cambios de modo/estilo. Comparar 2 vs 4 workers bajo carga de audio y definir un límite de recursos. Mantener fallback para Suave y configuraciones no admitidas. No habilitar por defecto hasta completar esa revisión. El cierre nativo original sigue mitigado, sin causa raíz confirmada; ADC10/RADIO y 2 MS/s siguen pendientes de holgura.

[Resumen, hashes e informes](../diagnosticos/resultados_v20/raster_tiles_summary_20261101.json).
