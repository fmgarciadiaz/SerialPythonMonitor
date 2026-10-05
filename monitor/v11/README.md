# Monitor V11 · SPI rápido experimental

Copia independiente de V10 para la app **Scope Fast SPI V9 Experimental**.
Conserva generador, V(t), FFT, heatmap, Bode, controles y CSV; incorpora
**100 kHz por canal en SPI a 8/10/12/14 bits**. No ofrece los candidatos
125/200/250 kHz. Oversampling de 16 bits sigue limitado a 50 kHz, UART a
31,25 kHz. No modifica el monitor V10 ni el firmware V8 estable.
A 100 kHz, FFT y heatmap actualizan la imagen hasta 20 veces/s; se conservan
todos los datos ADC y los pasos temporales del análisis espectral.

## Ejecutar

Con el monitor anterior cerrado:

```sh
python3 tools/usb_stream.py stop
python3 tools/unoq.py stop --version v8_config
python3 tools/usb_stream.py start --firmware v9_fast
python monitor/v11/app.py
```

Elegir **SPI**, resolución nativa y **Fs = 100 kHz**. La ventana de adquisición
sigue en 68 ciclos / 1,7 µs, igual que a 62,5 kHz: se acorta el período entre
pares, no la carga del capacitor en este perfil. El tiempo entre A2 y A3 sigue
siendo secuencial. La tasa mayor no implica más bits efectivos.

La referencia Bode de V10 se comparte sólo para su perfil exacto 16 bits / 50 kHz;
no se extrapola a 100 kHz. La precisión analógica a las nuevas tasas requiere
medición con ambas entradas conectadas directamente a A0.

[Resultados físicos, límites, respaldos y restauración](../../experimentos/tasas_spi/README.md).
[Funciones y controles heredados de V10](../v10/README.md).

## Volver al estable

```sh
python3 tools/usb_stream.py stop --firmware v9_fast
python3 tools/unoq.py stop --version v9_fast
python3 tools/usb_stream.py start --firmware v8_config
python monitor/v10/app.py
```
