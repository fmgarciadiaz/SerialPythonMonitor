# Zoom horizontal y rendimiento de V10

2 de octubre de 2026. Ventana ampliada de 50.000 a 250.000 muestras (4 s a
62,5 kHz), posición hasta −250.000 e historial de 510.000 muestras.

## Cambios

- Historial NumPy circular, ingreso de lotes y copias de ventanas; los cuadros
  congelados de trigger conservan sus datos al sobrescribir el historial.
- Lotes entre hilos como objetos Python; evita convertir cada diccionario a
  QVariant y conserva su propiedad: el productor no reutiliza el lote emitido.
- Reducción de muestras antes de crear escalones. Con muestreo uniforme se
  conservan primero, último, mínimo y máximo de cada grupo visual, en orden.
  Los huecos reales se separan antes de reducir. Al ampliar vuelve el detalle.
- Presupuesto según píxeles lógicos: Retina no duplica el costo del trazo.
- Mediciones completas a 10 Hz, búsqueda de cruces de trigger vectorizada.
  Adquisición y CSV conservan todos los pares recibidos.
- Al conectar, las muestras del perfil anterior se descartan hasta confirmar
  bits/tasa/destino. Corrige una mezcla inicial detectada durante los ensayos.

## Comparación local

[Resultados](resultados_render/20261002_v10_comparacion.json), Qt offscreen,
dos trazas Step, señal sintética, render y paint. Timer de render detenido
para evitar medir cuadros adicionales mientras se procesa el evento de paint.
25 cuadros medidos por escenario después de cuatro de calentamiento.

| Ventana | Antes, mediana | Después, mediana | Después, p95 |
|---|---:|---:|---:|
| 9.000 | 6,96 ms | 4,58 ms | 5,09 ms |
| 50.000 | 12,23 ms | 5,71 ms | 6,77 ms |
| 250.000 | No disponible | 11,60 ms | 13,07 ms |

Antes el historial tenía 110.000 muestras; después 510.000. La comparación
incluye la ampliación de memoria. El máximo se dibujó con unos 3.423 vértices
por canal en este tamaño de gráfico, en vez de casi 500.000 escalones.

## Placas y CSV

Con UNO Q y R4 reales, 14 bits, cambios 31,25 → 62,5 → 31,25 kHz y luego
SPI → UART → SPI. Grabación activa y verificaciones por cada muestra.

| Ventana | Render a 62,5 kHz | Pares totales del ensayo | Resultado |
|---|---:|---:|---|
| [250.000](resultados_usb/20261002_121152_685005_monitor_v10.json) | 48,16 FPS | 1.236.534 | Correcto |
| [9.000](resultados_usb/20261002_121259_752094_monitor_v10.json) | 58,53 FPS | 681.526 | Correcto |

Los seis CSV de ambos ensayos no tuvieron huecos de índice/timestamp ni errores
de conversión a voltios. La tasa calculada coincidió con el hardware.
Los FPS son el contador de callbacks de render con Qt offscreen; no garantizan
cuadros presentados por una pantalla real, que también depende del equipo.

El ensayo intermedio previo al cambio de señal entre hilos figura como
[fallido](resultados_usb/20261002_120740_595600_monitor_v10.json): detectó un
nodo del perfil anterior durante conexión. Se conservó el reporte y se añadió
una prueba de regresión, además de repetir las dos pruebas físicas finales.

**108 pruebas locales pasaron** con `python -m unittest discover -s tests`.

Las pruebas locales cubren picos, orden, cortes, detalle al ampliar, ventanas
históricas, wrap del buffer, ingreso por lotes, congelado y perfil inicial.
El Q terminó en 14 bits / 31,25 kHz / SPI, listo para V10. No cambió firmware.

## Selector de detalle

Se agrega un slider visual de 0 a 100 en Configuración, independiente de los
parámetros hardware. Usa un presupuesto progresivo de grupos por píxel; 100
omite la reducción y muestra el trazo completo. El valor inicial 50 conserva
más puntos que el ajuste fijo anterior. La ventana completa del último cuadro
permite redibujar en STOP sin avanzar captura ni cambiar mediciones. La prueba
Qt verifica restauración de todos los vértices, preservación de un pico y
posición invariable al cambiar el slider. Las cifras de rendimiento anteriores
corresponden al ajuste fijo anterior; la velocidad con el slider depende de su
posición y no se promete el mismo FPS al aumentar detalle.
