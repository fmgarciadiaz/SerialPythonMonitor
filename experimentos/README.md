# Experimentos aislados

Cada carpeta conserva fuentes, configuración, capturas y resultados de su campaña. Las rutas permanecen estables porque los runners y los informes las referencian. Un candidato aquí no se considera incorporado por existir ni por pasar una prueba corta.

[Uso actual V18](../docs/GUIA_V18.md) · [Validación V18](../docs/VALIDACION_V18.md) · [Plan](../Plan%20de%20trabajo.md).

| Entrada | Uso |
|---|---|
| [Generador 150/200 kHz](generador_200k_v17/README.md) | Campaña incorporada; evidencia e instalación conservadas |
| [Arranque RADIO](radio_start_v17/README.md) | Ensayos aislados de arranque |
| [Transporte RADIO dual](radio_dual_transport_v17/README.md) | Investigación específica, no aceptación general |
| `adc8_*_v17/` | Sondeos históricos de reloj, DMA, cola, integridad y holgura |
| `*_v16/` | Campañas sobre la versión anterior |

Los resultados de WAV y Scan recientes también están en `diagnosticos/`; seguir los enlaces del estado productivo para identificar el último candidato y su alcance. No ejecutar campañas sobre el Q ocupado por el monitor. Mantener un único propietario y verificar restauración al finalizar.
