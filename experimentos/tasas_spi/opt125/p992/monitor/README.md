# Monitor candidato P992

Copia independiente del monitor V11 y sus módulos necesarios; usa exclusivamente el receptor P992 V3/992. Ofrece hasta 125000 Hz como perfil experimental: gráfico, FFT, heatmap, trigger/SINGLE y CSV [probados con USB real](../../README.md). UART y 16 bits conservan sus límites. No promueve ni modifica V11.

Inicio desde cualquier cwd: `python /ruta/al/repo/experimentos/tasas_spi/opt125/p992/monitor/app.py` con el entorno Qt del proyecto. Capturas dentro de p992/capturas. Requiere pareja firmware/relay P992 y uso exclusivo de TCP8766.
