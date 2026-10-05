# Monitor V12 · SPI P992, hasta 125 kHz

Nueva versión independiente basada en el candidato P992 validado. Usa
exclusivamente [firmware V11 P992](../../arduino/v11_p992/README.md) y su
relay SCP1 V3/992. V11 y V10 se conservan en sus carpetas.

```sh
python3 tools/usb_stream.py start --firmware v11_p992
python monitor/v12/app.py
```

También se puede iniciar app.py desde esta carpeta o desde cualquier cwd.
Requiere el entorno Python con PyQt5, pyqtgraph, NumPy y pyserial.
CSV en `capturas/v12/`, separado de otras versiones.

SPI admite hasta 125 kHz por canal en ADC nativo 8/10/12/14 bits; 16 bits
con oversampling conserva 50 kHz y UART/R4 31,25 kHz. No se ofrecen
200/250 kHz. La validación sostenida y analógica de 125 kHz corresponde
específicamente a 14 bits: [evidencia P992](../../experimentos/tasas_spi/opt125/README.md).
El control Q permanece conectado, tanto para salida SPI como UART.

Se conservan generador, V(t), trigger/SINGLE, CSV, FFT, heatmap y Bode.
Las referencias Bode copiadas conservan su metadato de perfil: no se
extrapolan al nuevo perfil 125 kHz. Validación física UART/R4 y precisión
absoluta con instrumento de referencia siguen pendientes.

A0/DAC0 salida, A2/V_IN y A3/V_OUT entradas. Para comparación de ADC,
A0 se conecta directamente a ambas entradas; para medir un circuito,
restablecer los puntos adecuados de entrada/salida y masa común.

## Validación de la integración

198 pruebas locales aprobadas. Firmware y relay ARM compilados, app
independiente cargada en Q. [Ensayo con USB real](../../capturas/validacion_v12/20261004_204139_688307/informe.json):
14 bits / 125 kHz, V(t), FFT de 1025 bins, heatmap de 120 columnas, SINGLE
con seno de ~2 kHz / 2,46 Vpp y CSV de 511082 filas sin saltos de índices
ni timestamps. Generador restaurado exactamente a cuadrada de 2,5 Hz.
Qt offscreen; PNG y CSV en la misma carpeta. No se afirma validación manual
de pantalla ni nuevo barrido Bode físico.

Reproducción: `python diagnosticos/verificar_v12.py`, con A0 unido a A2/A3
y masa común. El script configura temporalmente la senoide y restaura el
generador; deja aplicado ADC14/125 kHz. Usar exclusivamente la pareja V12.

[Mejora de rendimiento FFT](../../diagnosticos/FFT_V12_RENDIMIENTO.md):
se evita dibujar V(t) mientras está oculto, conservando mediciones, Fs,
SINGLE y muestras completas. 201 tests pasan; diagnóstico de espera de
lotes y nueva verificación real de FFT/heatmap/CSV a 125 kHz aprobados.

FFT8192: análisis completo, dibujo adaptado al ancho preservando extremos,
relleno integrado y cadencia objetivo de 30 Hz; heatmap conserva 20 Hz.
Nueva prueba real de 512339 filas CSV continuas, SINGLE y generador
restaurado. Para repetir: `python diagnosticos/verificar_v12.py --fft-size 8192`.
Salida encendida ocupa toda la fila; Enlace/ADC tienen igual ancho y
Fs presenta tasa/período compactos, con detalles en tooltip.

No mezclar con relay de V11/V9 Fast (SCP1 V2/512) ni con otros monitores.
Detener el monitor y relay activos antes de cambiar de firmware.
