# Arduscopio Q · imágenes de presentación

El README raíz es la landing del proyecto: conservar sus badges, capturas y explicaciones de módulos, conforme a `AGENTS.md`.

Las vistas principales `monitor_vt`, `monitor_fft_spectrum`, `monitor_heatmap`,
`monitor_bode`, `monitor_generator`, `monitor_filter`, `monitor_wav` y
`monitor_synth` se renovaron con V18 el 26/10/2026. Cada una tiene GIF breve y
PNG alternativo, generados sin conexión al Q por
`tools/capture_landing_v18.py`. Son demostraciones sintéticas; los paneles WAV
y Synth no representan reproducción física y Bode ilustra un RC calculado.
Por decisión del usuario, la presentación utiliza simulaciones en todos los módulos;
no se requiere reconectar el circuito para generar estas imágenes.
Los PNG anteriores se conservan en `historico/antes_v18_20261026/`.
El resto de variantes `monitor_fft_*` y `monitor_radio.png` permanece como
material histórico; no se usa como captura actual en la landing.

El antiguo `monitor_filter.png` (ahora archivado) y `monitor_radio.png` se
capturaron el 19/10/2026 con V17/Cocoa y una señal AM sintética. No se conectó
al Q para esas imágenes.

Las capturas de ensayos físicos permanecen en `diagnosticos/`; no confundirlas con estas imágenes de presentación.

## Radio V18 · 26/10/2026

| Archivos | Contenido y procedencia |
|---|---|
| `monitor_radio_710.gif` / `.png` | Simulación V18 con cinco portadoras AM, 710 kHz seleccionada, FFT16384 recortada, Generador Radio y barras LED, solapa Radio abierta. Sin Q ni salida A0. |
| `monitor_radio_equ.gif` / `.png` | Detalle del panel y sus indicadores, con audio sintético de demostración. |

La landing muestra GIF simulado y ofrece PNG alternativo. Los originales
históricos siguen disponibles. Hubo una captura física anterior, reemplazada
por la demostración simulada de mayor resolución; su ensayo y restauración están en
`diagnosticos/resultados_v18/radio_rate_check_20261026_201110/`.

## Calidad de exportación

PNG sin pérdidas a doble resolución de dispositivo (3.200 × 2.200 para vistas
completas), GIF a 1.600 × 1.100 con una paleta de 256 colores que reserva 64 tonos neutros para conservar
el suavizado de los textos y 192 colores de la vista. El detalle de Generador Radio conserva su
proporción y resolución correspondiente. No se amplían los archivos pequeños
anteriores: se vuelve a renderizar la GUI V18. La calidad tiene prioridad sobre
el mínimo tamaño del GIF; consultar dimensiones y pesos en el manifiesto.

## Alternativa estática y accesibilidad

Cada bloque principal usa `<picture>` con PNG para
`prefers-reduced-motion: reduce` y GIF por defecto. Se incluye un enlace
explícito al PNG para lectores sin soporte de `<picture>` o animación.
Los lectores que muestran un solo cuadro del GIF también ven una imagen
válida. No depender de JavaScript ni de un fallback automático ante errores
de descarga. El manifiesto `landing_v18_manifest.json` enumera las demostraciones.
