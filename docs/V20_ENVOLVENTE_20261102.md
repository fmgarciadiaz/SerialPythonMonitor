# V20: envolvente automática para V(t)

**Histórico: retirado el 3/11 por pedido del usuario.** Estado actual y corrección
de la regresión de detalle: [Recuperación V20](V20_RECUPERACION_20261103.md).

El dibujo denso puede usar una envolvente de mínimos/máximos por columna física de pantalla. Las capturas completas se conservan para los cursores: la reducción es sólo de geometría visual. En ventanas pequeñas o al ampliar el zoom vuelve al dibujo de puntos original. La etiqueta pequeña `envelope`, con fondo sobrio translúcido, borde redondeado y texto claro en la esquina superior derecha, identifica la imagen reducida; no intercepta clics.

## Corte inicial y conservación de datos

- Entrada: al menos100.000muestras visibles en un canal y8muestras por píxel físico.
- Salida: menos de50.000muestras visibles o menos de4muestras por píxel. La histéresis evita cambios continuos cerca del corte.
- La decisión usa el rango visible, no sólo los segundos configurados. Una ventana larga con pocas muestras sigue usando puntos.
- Mínimos y máximos conservan impulsos aislados; se mantienen extremos y conexiones entre columnas. NaNs y huecos de tiempo con corte automático dividen tramos, incluso dentro de una misma columna. Con corte desactivado se conserva la conexión solicitada entre extremos.
- El modo corresponde aV(t); FFT/heatmap/Bode no cambian. Los datos de adquisición, DSP, mediciones y almacenamiento no se sustituyen por barras. La captura que recibe el cursor es completa, incluidos puntos que no son extremos de la envolvente.

Se centralizó la reducción en el proceso de dibujo. La optimización anterior de cuadros ya reducidos, que se desactivaba con cursores, queda deshabilitada para conservar siempre la misma captura completa. El worker sigue siendo único; no se añadió paralelismo de raster ni se cambiaron prioridades.

## Pruebas locales

140testsV20 PASS, incluyendo las regresiones adaptadas del raster y de cursores. Tras el ajuste de no-intercepción de clics y telemetría,23tests focalizados PASS. La integración real con memoria compartida comprobó:

- Imagen envolvente publicada y etiqueta visible.
- Captura completa de200.000puntos y lectura real de un cursor en un punto interior, no sustituida por un extremo de columna.
- Zoom a un tramo corto devuelve el dibujo original y oculta `env`.
- Picos aislados, NaNs, huecos, escalón y rango visible conservan sus contratos.

Benchmark local deQImage2500×600, escalónRápido, señal determinista con pico yNaN, tres repeticiones por modalidad:

| Muestras | Puntos: mediana | Envolvente: mediana |
|---|---:|---:|
|100.000|24,34ms|4,00ms|
|3.720.930|723,58ms|75,09ms|

Es el coste del pintor local; excluye copias de captura, IPC y FPS visibles. No exige imagen idéntica al dibujo completo: la envolvente es una representación visual distinta y está identificada como tal. Sí conserva los extremos y los datos originales según las pruebas.

[Benchmark](../diagnosticos/resultados_v20/temporal_envelope_benchmark_20261102/report.json).

## Prueba física sobre V20 instalada

ADC8/1,86MS/s, ventana2s (3.720.930muestras), detalle100%, RADIO/A0 a40kHz, exposición100%:

| Indicador | Ensayo anterior de puntos | Envolvente |
|---|---:|---:|
|Duración RADIO confirmada|20,035s|60,075s|
|Worker: mediana de tiempos observados|3.091,91ms|129,03ms|
|Imágenes nuevas entre snapshots periódicos activos|0,264/s|2,518/s|

La comparación es de dos corridas separadas y de distinta duración, con la misma configuración principal. No es una garantía universal de FPS ni una comparación aleatorizada. Los eventos de pintado deQt y la publicación de imágenes nuevas son métricas distintas.

La prueba nueva confirmó `env` visible y capturas completas deCH1 (3.720.930muestras) yRADIO (80.000muestras) mientras se dibujaba la envolvente. Pasaron reproducción, progreso, parada, cierre y recuperación del snapshotV20≥10s sin pérdidas/fatales. Se correlacionaron5.037ACK leídos y observados al procesar. Identidad, recibo de trabajo e informe sellado permanecieron iguales. V20 queda activa, generador apagado y sin sesión de prueba; no se inicióV19.

- [Informe físico](../diagnosticos/resultados_v20/v20_envelope_longwindow_radio_vt_20261102_r1/report.json).
- [Resumen comparativo y umbrales](../diagnosticos/resultados_v20/temporal_envelope_validation_summary_20261102.json).

Los hashes del ensayo identifican el código ejecutado. Después sólo se actualizaron dos docstrings del renderer; el resumen verifica por reconstrucción que no cambió el código ejecutable. No se modificaron firmware, relay, límites de flujo ni tasas públicas. Las pausas GUI intermitentes anteriores mantienen su diagnóstico separado: estos pases no prueban su resolución causal.
