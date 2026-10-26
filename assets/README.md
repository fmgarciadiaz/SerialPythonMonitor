# Imágenes de presentación

El README raíz es la landing del proyecto: conservar sus badges, capturas y explicaciones de módulos, conforme a `AGENTS.md`.

`monitor_vt`, `monitor_fft_*`, `monitor_heatmap`, `monitor_bode`, `monitor_wav` y `monitor_synth` son capturas de presentación conservadas; varias muestran demostraciones de versiones anteriores.

`monitor_radio.png` y `monitor_filter.png` se capturaron el 19/10/2026 con la GUI V17/Cocoa, una señal AM sintética de 50 kHz modulada a 1 kHz y el perfil de demostración ADC8/1,6 MS/s. Se muestran CH1, RADIO y FILTER (bypass con fuente RADIO), con A0 detenido. No se conectó al Q para estas imágenes. Son ilustraciones de funciones, no evidencia física de recepción o audio.

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
