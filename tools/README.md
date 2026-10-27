# Arduscopio Q · herramientas del proyecto

La aplicación actual se inicia con `python -m monitor.v18 --gui`.
Las herramientas de esta carpeta conservan rutas estables porque también
se importan desde pruebas y campañas.

| Uso | Entrada |
|---|---|
| Preparación y recuperación de Scope V18 | `prepare_q_v18.py`, `prepare_q_v18_backend.py` |
| Administración del Q | `unoq.py` |
| Verificación GUI con adquisición real | `gui_live_smoke_v18.py`, `probe_gui_live_v18.py` |
| Comprobación RADIO/A0 con restauración | `probe_radio_rate_v18.py` |
| Catálogo y evidencia de tasas V18 | `probe_catalog_gui_v18.py`, `build_rate_evidence_v18.py` |
| Calibración Bode | `calibrate_bode.py`, `calibrate_bode_matrix.py` |
| GIF/PNG de presentación V18, sin Q | `capture_landing_v18.py` |

Los nombres con V17 y los sincronizadores antiguos son soporte histórico;
no usarlos para actualizar la pareja V18. Las pruebas físicas requieren
un único propietario del Q y restauración verificada. La generación opcional
de GIF en el smoke usa `MONITOR_V18_RADIO_GIF`; captura cuadros acotados y
codifica después de cerrar la adquisición. No es una medición de rendimiento.

[Guía V18](../docs/GUIA_V18.md) · [Organización](../docs/ORGANIZACION_V18.md)
