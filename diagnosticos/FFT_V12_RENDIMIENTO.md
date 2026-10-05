# FFT V12 · carga temporal oculta y atraso de interfaz

4 de octubre de 2026. A 100–125 kHz, el temporizador seguía ejecutando
`render_frame` para V(t) mientras FFT ocupaba la pantalla. Preparaba curvas,
ejes y dibujo temporal a aproximadamente 60 Hz, además del análisis espectral.

Cambio limitado a V12: omitir la preparación/dibujo temporal oculto.
Se mantienen Fs y las mediciones numéricas, actualizadas a 10 Hz; SINGLE
conserva su ruta de trigger y congelación también desde FFT. Recepción,
historial, CSV y saltos del heatmap conservan todas las muestras recibidas.
FFT/heatmap siguen limitados a 20 Hz de pintado en muestreo >=100 kHz.

Los lotes ahora incluyen su instante monotónico de publicación, sin alterar
los diccionarios de muestras. La interfaz mide su espera al recibirlos;
esto mide la cola worker→GUI, no toda la latencia ADC→pantalla.
Los campos de diagnóstico son `batch_queue_delay_ms`,
`batch_queue_delay_max_ms` y `timed_batch_count`.

## Evidencia

- Perfil sintético anterior: cálculo temporal oculto mediano 1,1 ms con
  9000 muestras y 7,69 ms con 250000. FFT8192 más eventos/pintado Qt:
  mediana 7,02 ms, máximo observado 58,67 ms.
- Tras el cambio: la ruta oculta sin renovación de mediciones cuesta
  aproximadamente 0,005 ms. Las renovaciones numéricas siguen teniendo
  un costo separado; el resultado no describe toda la carga de FFT.
- 201 pruebas locales aprobadas: contrato, retorno a V(t), mediciones/Fs,
  SINGLE desde FFT, recepción de lotes demorados sin descartar datos y CSV.
- [Ensayo real inicial](../capturas/validacion_v12/20261004_205746_899121/informe.json):
  ADC14/125 kHz, FFT, heatmap, SINGLE y 509500 filas CSV sin saltos.
- [Ensayo con diagnóstico por modo](../capturas/validacion_v12/20261004_205848_224845/informe.json):
  507339 filas CSV sin saltos, generador restaurado exactamente al estado
  previo. Para FFT, 140 lotes: espera mediana 4,78 ms, percentil95 16,03 ms,
  máximo 22,76 ms tras excluir el primer segundo del modo. Pico global
  148,98 ms, que incluye conexión y transiciones. Este ensayo coexistió
  con la suite local de pruebas; no representa un benchmark de CPU aislado.

Qt offscreen y USB real; FFT de 2048 muestras, dos canales, seno ~2 kHz.
No se afirma validación manual de la fluidez de la pantalla. Reproducir
con `python diagnosticos/verificar_v12.py`, con el relay V12 activo y libre
de otro cliente; el script restaura el generador al terminar.

## Segunda mejora: FFT8192 y layout

Suite final: 203 pruebas locales aprobadas, incluyendo conservación de
picos FFT8192 en ambas escalas y cadencia independiente del temporizador.

- Se calcula el espectro completo de 8192 muestras (4097 bins); sólo el
  dibujo se reduce a extremos por ancho de pantalla, en coordenadas lineales
  o logarítmicas. Los picos, el historial y CSV no se reducen.
- Ventana y eje de frecuencias se reutilizan mientras no cambie el contexto.
- Relleno y línea FFT comparten un PlotDataItem; se evita construir una
  segunda curva poligonal. Conserva sombreado y cortes de datos inválidos.
- Cadencia objetivo FFT de 30 Hz a Fs>=100 kHz. El calendario conserva su
  fase para evitar redondear cada espera a múltiplos de 16 ms. Heatmap
  mantiene su límite de 20 Hz. Las cifras anteriores de 20 Hz describen
  la primera corrección, no el estado final.
- Salida encendida ocupa ambas columnas; Disparar queda en una fila propia.
  Control Q/Conectar/Demo son más compactos. Enlace y ADC tienen el mismo
  ancho. Fs muestra tasa y período, con los detalles ADC en tooltip.

[Prueba final FFT8192/125 kHz](../capturas/validacion_v12/20261004_211646_748311/informe.json):
FFT, heatmap y SINGLE aprobados; CSV de 512339 filas sin saltos y generador
restaurado exactamente. Render FFT mediano 4,72 ms, p95 9,60 ms. Espera de
lotes en FFT mediana 25,44 ms, p95 55,56 ms; persisten picos y no se promete
una latencia fija ni 30 FPS efectivos bajo cualquier carga. Qt offscreen,
dos canales y seno ~2 kHz. La ventana8192/125 kHz abarca 65,536 ms de señal.

Reproducir con `python diagnosticos/verificar_v12.py --fft-size 8192`.
La prueba registra por separado preparación de render y cola worker→GUI;
los tiempos del render no incluyen todo el pintado posterior de Qt.
Una prueba intermedia terminó con código139 después de guardar el informe;
las siguientes y la prueba final cerraron con código0. No se atribuyó ese
fallo intermedio a una causa confirmada. Una comparación con intervalo de
hilos de 1 ms no mejoró los resultados; no se aplicó ese ajuste a V12.
