# Diagnósticos y evidencia

Informes, herramientas de ensayo y resultados del proyecto. Los informes
fechados conservan el estado y las versiones probadas en ese momento.

| Área | Entrada |
|---|---|
| Conexión, recuperación y generador | [resultados_autoload](resultados_autoload) |
| Reproducción de audio | [resultados_wav](resultados_wav) y [tasas WAV](../docs/WAV_TASAS.md) |
| ADC16 y continuidad | [ADC16](ADC16_V12.md) |
| Comparación Qt | [Qt6](QT6_V13.md) y [resultados_qt](resultados_qt) |
| Puente UART/R4 | [resultados_r4](resultados_r4) |
| Bode y referencia | [Bode](BODE_V10.md) |
| SPI y USB | [resultados_spi](resultados_spi), [resultados_usb](resultados_usb) |
| Dibujo | [resultados_render](resultados_render) |

## Comprobación histórica de Chirp

Antes de corregir el cálculo de tiempo, uno de ocho disparos terminó a los
0,1 s. Tras cargar el firmware corregido, 24 Chirps seno de 20 Hz→2 kHz/2 s
completaron la duración. [Antes](resultados_autoload/20261006_chirp_repeticiones.json) ·
[Después](resultados_autoload/20261006_chirp_timer_corregido.json).
El usuario confirmó posteriormente que volvió a funcionar. La prueba física
repetida fue con seno; las demás formas comparten el cálculo corregido.

Las pruebas con placa requieren un solo cliente del relay y restauración del
perfil/salida indicada en cada ensayo. Los tests de interfaz sin placa están
en `tests/v17/` (y las versiones anteriores en sus carpetas) y no sustituyen la comprobación física.

## Seguimiento V17 · 19/10/2026

- [Estado vigente e incidencias abiertas](../docs/ESTADO_ACTUAL_V17.md).
- [Bode: referencia y dibujo](../docs/DIAGNOSTICO_BODE_SIN_CURVAS_V17.md), resultados en `resultados_bode/`.
- [Scan/GUI atrasada](../docs/DIAGNOSTICO_SCAN_GUI_V17.md) y [cortes WAV](../docs/DIAGNOSTICO_CORTES_WAV_V17.md).
- [Generador 150/200 kHz](../docs/GENERADOR_200K_V17.md), evidencia en su experimento aislado.
- [Limpieza de apps Q](resultados_v17/cleanup_apps_20261019_160438.json): exportaciones verificadas, sólo V17 instalada.
