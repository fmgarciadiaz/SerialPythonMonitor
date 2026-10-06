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

## Última comprobación de Chirp

Antes de corregir el cálculo de tiempo, uno de ocho disparos terminó a los
0,1 s. Tras cargar el firmware corregido, 24 Chirps seno de 20 Hz→2 kHz/2 s
completaron la duración. [Antes](resultados_autoload/20261006_chirp_repeticiones.json) ·
[Después](resultados_autoload/20261006_chirp_timer_corregido.json).
El usuario confirmó posteriormente que volvió a funcionar. La prueba física
repetida fue con seno; las demás formas comparten el cálculo corregido.

Las pruebas con placa requieren un solo cliente del relay y restauración del
perfil/salida indicada en cada ensayo. Los tests de interfaz sin placa están
en `tests/v13/` y no sustituyen la comprobación física.
