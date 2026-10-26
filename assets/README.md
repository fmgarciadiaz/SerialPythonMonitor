# Imágenes de presentación

El README raíz es la landing del proyecto: conservar sus badges, capturas y explicaciones de módulos, conforme a `AGENTS.md`.

Las vistas principales `monitor_vt`, `monitor_fft_spectrum`, `monitor_heatmap`,
`monitor_bode`, `monitor_generator`, `monitor_filter`, `monitor_wav` y
`monitor_synth` se renovaron con V18 el 26/10/2026. Cada una tiene GIF breve y
PNG alternativo, generados sin conexión al Q por
`tools/capture_landing_v18.py`. Son demostraciones sintéticas; los paneles WAV
y Synth no representan reproducción física y Bode ilustra un RC calculado.
La captura real de Bode queda pendiente de reconectar referencia y circuito.
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
| `monitor_radio_710.gif` / `.png` | Recepción real CH1, 710 kHz seleccionada, FFT16384 recortada con zoom persistente, Generador Radio y barras LED, solapa Radio abierta. Captura de presentación; no certifica identidad de emisora. |
| `monitor_radio_equ.gif` / `.png` | Detalle del panel y sus indicadores, con audio sintético de demostración. |

La landing muestra GIF de recepción y ofrece PNG alternativo. Los originales
históricos siguen disponibles; no reemplazar demostraciones por supuesta
evidencia física. El ensayo de captura y restauración está en
`diagnosticos/resultados_v18/radio_rate_check_20261026_201110/`.

## Alternativa estática y accesibilidad

Cada bloque principal usa `<picture>` con PNG para
`prefers-reduced-motion: reduce` y GIF por defecto. Se incluye un enlace
explícito al PNG para lectores sin soporte de `<picture>` o animación.
Los lectores que muestran un solo cuadro del GIF también ven una imagen
válida. No depender de JavaScript ni de un fallback automático ante errores
de descarga. El manifiesto `landing_v18_manifest.json` enumera las demostraciones.
