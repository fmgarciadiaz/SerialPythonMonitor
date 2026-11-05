# V20: coste del raster y prioridad de audio · 1/11/2026

Se midió el árbol completo GUI/recepción/DSP/dibujo, una vez por segundo, con el mismo ADC8/1.860.465 S/s, ventana de 2 s, detalle 100%, Cocoa y RADIO→A0 a 40 kHz. La decisión es conservar el worker único normal; el paralelo sigue privado y no se incorpora. No se cambiaron fuentes de producto, firmware, relay, tasas ni reservas/timeout de audio.

## Comparación

| Gráfico | Prioridad | RADIO/A0 | Raster mediano | Pinturas/s medianas | CPU mediana, núcleos | Pico RSS sumada |
|---|---|---|---:|---:|---:|---:|
|1 worker(s)|nice +0|120 s PASS|1398 ms|1.19|2.80|2.66 GiB|
|2 worker(s)|nice +0|FAIL, interrumpido|874 ms|1.96|3.90|2.69 GiB|
|2 worker(s)|nice +10|120 s PASS|1035 ms|1.39|3.93|2.58 GiB|
|4 worker(s)|nice +10|120 s PASS|696 ms|1.87|5.48|3.59 GiB|

CPU=1 equivale a un núcleo completo, no al 100% de toda la máquina. Los valores incluyen GUI y descendientes propios; excluyen observador y coordinador. Se separa el tramo estable de reproducción del arranque. La RSS sumada cuenta algunas páginas compartidas varias veces: no es memoria física exclusiva y su diferencia no demuestra el mismo cambio de RAM real. No hubo muestras parciales por permisos en estos tramos. El muestreo puede perder CPU de procesos que terminan entre observaciones. El observador tardó hasta unos 55 ms en una muestra, coste adicional que no se incluye en la CPU del árbol.

Los contadores de pintura no son necesariamente imágenes nuevas. La mediana raster usa observaciones periódicas activas después de 10 s de reproducción; no mide cada imagen. Son corridas secuenciales, no una comparación aleatorizada ni repeticiones suficientes para inferir causalidad. Ninguna alcanza el piso diagnóstico de 8 pinturas/s.

## Fallo conservado, no aprobado por margen medio

La primera variante de 2 procesos, sin bajar prioridad, sufrió UNDERRUN a los23,55s aproximados de audio. El Q reportó state 4/reason 2, y luego el relay registró PC disconnected or too slow; close session. La GUI no pudo confirmar su apagado de salida, pero el coordinador reinició y restauró V19 exactamente. El caso de 4 procesos de prioridad normal NO se ejecutó: la campaña se detuvo al primer fallo.

El PCM ya estaba disponible en el host: roundtrip máximo de generación 18,79 ms. Sin embargo, send→ACK alcanzó 666,47 ms, había 9 peticiones DAC en vuelo y la cola de audio se agotó. No hubo error de raster reportado. Margen MCU medio 12,25% y pico RF 6/16 no evitaron el corte: el screen privado de RF es insuficiente para aprobar el audio de extremo a extremo. Estos datos sugieren presión en entrega/planificación; no demuestran su causa raíz.

## Mitigación privada y repetición

Se añadió únicamente al adaptador experimental --raster-nice 10: os.nice reduce prioridad dentro de cada hijo gráfico propio. No modifica prioridad de la GUI, recepción, otros procesos ni el Q. Cada hijo devuelve su nice observado; se confirmaron 10,10 y 10,10,10,10 en las repeticiones correspondientes. Hay copia y hash del adaptador anterior en diagnosticos/resultados_v20/raster_priority_before_20261101/.

Dos y cuatro procesos de baja prioridad pasaron 120 s, progreso, imagen, cierre y restauración. La ausencia de fallo en una repetición no prueba que la prioridad cure el UNDERRUN.29tests locales pasan, incluida la prioridad real de los hijos gráficos y la contabilidad del observador.

## Decisión y continuación

Cuatro procesos casi duplicaron el consumo CPU total frente al original (5,48 vs 2,80 núcleos) para aproximadamente duplicar velocidad de raster. El máximo de demora GUI pasó de 140 ms en la referencia a 300/421 ms con 2/4 procesos de baja prioridad. No activar por defecto este intercambio de recursos; conservar el candidato y su fallo como evidencia. El producto normal sigue con un worker y el control de detalle existente.

Las cuatro corridas, incluida la fallida, restauraron V19 exacta: fuentes/caché/BIN/relay, snapshot/configuración/CPU, lectura final de 10 s sin pérdidas/fatales. Q libre, V19 activa, V20 detenida. No se modificaron V17/V18/V19.

Priorizar ahora la entrega de audio y la holgura ADC10/RADIO y 2 MS/s; cualquier nuevo candidato debe conservar cero errores de audio, no sólo margen medio RF. El cierre nativo anterior sigue mitigado sin causa confirmada. Si se retoma el paralelo, faltan más repeticiones, coste bajo otras cargas y cursor/STOP/SINGLE/zoom/modos/gaps antes de incorporarlo.

[Resumen, hashes y observaciones](../diagnosticos/resultados_v20/raster_resources_summary_20261101.json).
