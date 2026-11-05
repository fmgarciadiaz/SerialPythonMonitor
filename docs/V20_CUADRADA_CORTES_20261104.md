# V20: cortes falsos en V(t) reducido

Con cuadrada2kHz muestreada a40kHz se reprodujo un defecto de dibujo en
ventanas amplias: el camino RF Roll comprueba que el reloj crudo no tenga
gaps y selecciona extremos para dibujar. Después volvía a interpretar las
distancias entre esas muestras seleccionadas como silencios de adquisición.
Insertaba NaNs y cortaba segmentos de una señal continua.

La [comparación local reproducible](../diagnosticos/resultados_v20/square_trace_20261104/report.json)
usa400grupos de dibujo y la misma entrada: con80.000muestras, selección de
1.200puntos y salto seleccionado máximo4.725µs, se añadían400NaNs falsos.
V19 leído sin ejecutar su app tiene el mismo comportamiento. Con9.000muestras
no apareció ese fallo; no explica todos los casos del usuario ni demuestra
una regresión exclusiva de V20.

V20 conserva ahora la continuidad demostrada junto a la referencia exacta
del frame reducido RF. Sólo esas mismas matrices evitan la segunda detección
de gaps. Un frame diferente o con gap real sigue por la ruta habitual; el
reloj original con salto y los NaNs mantienen sus separaciones. No se
introdujo envelope, badge ni una heurística para reconocer ondas cuadradas.
Cursor, mediciones y datos originales conservan sus rutas anteriores.

En30repeticiones locales, preparar el trazo de80.000muestras previamente
seleccionado pasó de mediana0,483ms/400NaNs a0,011ms/0NaNs. Es sólo esa etapa,
no un dato de FPS visibles ni del coste completo de render/acquisición.
El raster denso de detalle100 no se cambió. Los ciclos subpíxel no pueden
representarse individualmente mediante este criterio de detalle.

Cuatro pruebas focalizadas pasaron en1,866s:20fases en ventanas9.000/80.000
y ring envuelto, conservación de niveles positivos/negativos, gap temporal
real y NaN, integración del frame RF real y regresión de detalle mixto.
Backup SHA: `respaldos/host/v20_before_reduced_false_gaps_20261104/manifest.json`.
No se operó el Q ni se modificaron versiones congeladas o Arduino. El FPS
bajo general y los borrados fuera de esta condición siguen pendientes de
medición con ventana/detalle concretos.
