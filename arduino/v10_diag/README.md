# V10 diagnóstico de tiempos SPI

App independiente **Scope SPI Timing V10 Diagnostic**, derivada de V9 Fast.
No usar el monitor V11 con esta app: requiere el receptor de diagnóstico.
Mantiene ADC, DMA, colas, CRC y 39 tramas por nodo originales. Agrega contadores
RAM y una instantánea TDG1 en el padding del último fragmento de cada nodo.

[Esquema, medición y resultados](../../experimentos/timing_spi/README.md).

```sh
python3 tools/unoq.py compile --version v10_diag
python3 tools/usb_stream.py build --firmware v10_diag
```
