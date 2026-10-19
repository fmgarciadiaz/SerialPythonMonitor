# Selectores y combinación RF/RADIO en FFT — 15/10/2026

Problemas reportados: los desplegables de canales se tapaban o abrían mal;
seleccionar CH1 y RADIO simultáneamente hacía desaparecer los espectros.

## Cambios

- Los selectores conservan su ubicación sobre cada gráfico, pero ahora son
  widgets nativos del viewport. Una fila gráfica reserva el espacio; su
  geometría posiciona el encabezado nativo. El desplegable deja de depender
  de QGraphicsProxyWidget y de su gestión de popups dentro de la escena.
  Ninguno sigue ocultando el gráfico sin ocultar el selector.
- FFT Spectre/Power/Distort admite paneles RF y audio simultáneamente. Cada
  canal usa su historial, tasa, número de segmentos disponible y frecuencias
  correspondientes. La falta de audio no borra el espectro RF. La actualización
  observa los contadores de ambos dominios, por lo que audio nuevo se analiza
  aunque no haya llegado RF nuevo.
- En combinaciones RF/audio los ejes X conservan bandas independientes,
  incluso con bloqueo de ejes. Se puede compartir el rango de amplitud.
- Los ajustes de distorsión usan la tasa de cada canal y conservan el trabajador
  único con generaciones. Los huecos temporales invalidan el ajuste anterior.
- Transfer y SINGLE multicanal siguen requiriendo señales del mismo dominio
  temporal; no se introduce remuestreo para fingir alineación. Heatmap conserva
  su restricción previa de dominio común.

No se cambian resolución FFT, slider de detalle, muestras ni firmware.

## Verificación

115 pruebas de FFT/UI, RADIO/UI, análisis espectral, procesamiento, CH1/render,
reductor y trigger pasaron en 44,880 s con Python 3.13 del proyecto.

Tres regresiones nuevas verifican:

- Clic real, desplegar y elegir con teclado en los dos selectores, cambios
  FFT→Heatmap→FFT y resize. Los controles son alcanzables y no pertenecen
  a un proxy gráfico.
- CH1 a 1,4035 MHz junto con RADIO a 40 kHz: ambos espectros, picos de
  50 kHz/1 kHz, Nyquist independiente y paneles invertidos, en Spectre,
  Power y Distort.
- RF visible durante preparación de audio, actualización de audio sin RF
  nuevo, FILTER proveniente de RADIO y rechazo explícito de Transfer mixto.

El caso de desplegables se ejecutó también en una ventana nativa Cocoa de
macOS: pasó (1 prueba, 3,309 s). Las muestras son sintéticas; no se operó el Q
ni se declara aceptación física. Reiniciar V17 para cargar los cambios.

## Definición de FFT al ampliar — 15/10/2026

El trazo se reducía respecto de la banda completa y el zoom ampliaba esa
representación ya reducida. Se conserva ahora una referencia a los arrays
completos del último análisis y se reconstruye sólo el dibujo respecto del
intervalo X realmente visible y del ancho actual del panel. Se incluye un
vecino fuera de cada borde para mantener continuidad de línea/relleno.

El cambio de rango X y el resize actualizan el trazo sin recalcular FFT,
también en STOP y SINGLE. Cuando hay pocos bins por píxel se dibujan todos
los bins visibles. Al volver a zoom out se mantiene la reducción existente.
El slider y la FFT numérica no cambian; no se agregan muestras ni interpolación
espectral. El cache de dibujo se limpia al reiniciar el contexto.

Dos regresiones de FFT65536 verifican recuperación exacta de los bins y
magnitudes visibles en lineal/log, sin nueva adquisición ni nuevo análisis,
y la conservación del espectro SINGLE aunque cambie el historial vivo.

86 pruebas de FFT/UI, RADIO/UI, análisis espectral y reductor pasaron en
37,377 s con Python 3.13. Compilación Python aprobada. No se operó el Q.

## Límites del dial horizontal de FFT

La ventana horizontal se limita a la banda completa de cada panel. Su escala
máxima es 1× y el desplazamiento permitido es ±(1−escala)/2 de esa banda.
El dial y el indicador numérico reflejan esos límites. Volver a 1× centra
la posición en cero; ya no se permite desplazar la banda completa hacia un
margen vacío. En lineal los límites son 0 y Nyquist; en log se conserva como
extremo inferior el primer bin positivo. Heatmap, Bode y ejes verticales
mantienen sus controles anteriores.
