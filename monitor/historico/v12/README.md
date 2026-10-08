# Monitor de adquisición SPI

Pareja anterior conservada con PyQt5, basada en P992 validado. Usa
exclusivamente [firmware V11 P992](../../../arduino/historico/v11_p992/README.md) y su
relay SCP1 V3/992. V11 y V10 se conservan en sus carpetas.

```sh
python3 tools/usb_stream.py start --firmware v11_p992
python monitor/historico/v12/app.py
```

También se puede iniciar app.py desde esta carpeta o desde cualquier cwd.
Requiere el entorno Python con PyQt5, pyqtgraph, NumPy y pyserial.
CSV en `capturas/v12/`, separado de otras versiones.

SPI admite hasta 125 kHz por canal en ADC nativo 8/10/12/14 bits; 16 bits
con oversampling ×16 admite 62,5 kHz y UART/R4 31,25 kHz. No se ofrecen
200/250 kHz. La validación sostenida y analógica de 125 kHz corresponde
específicamente a 14 bits: [evidencia P992](../../../experimentos/tasas_spi/opt125/README.md).
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
independiente cargada en Q. [Ensayo con USB real](../../../capturas/validacion_v12/20261004_204139_688307/informe.json):
14 bits / 125 kHz, V(t), FFT de 1025 bins, heatmap de 120 columnas, SINGLE
con seno de ~2 kHz / 2,46 Vpp y CSV de 511082 filas sin saltos de índices
ni timestamps. Generador restaurado exactamente a cuadrada de 2,5 Hz.
Qt offscreen; PNG y CSV en la misma carpeta. No se afirma validación manual
de pantalla ni nuevo barrido Bode físico.

Reproducción: `python diagnosticos/verificar_v12.py`, con A0 unido a A2/A3
y masa común. El script configura temporalmente la senoide y restaura el
generador; deja aplicado ADC14/125 kHz. Usar exclusivamente la pareja V12.

[Mejora de rendimiento FFT](../../../diagnosticos/FFT_V12_RENDIMIENTO.md):
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

## ADC de 16 bits a 62,5 kHz

PLL2 toma HSE de 16 MHz, divide por 2, multiplica por 25 y divide por 4:
ADC a 50 MHz para todos los perfiles. Se conservan 16 subconversiones de
14 bits por canal y shift derecho de 2 bits. 16 bits/62,5 kHz está permitido
sólo por SPI; UART conserva 31,25 kHz.

[Ensayo inicial](../../../capturas/adc16_rate/test62k5_20261005_002648/informe.json):
311.409 pares en 5 s, dropped=fatal=0.
[Regresión ADC14/125 kHz](../../../capturas/validacion_v12/20261005_003145_591574/informe.json):
FFT, heatmap, SINGLE y 507.565 filas CSV continuas. Estos ensayos no
certifican precisión absoluta, ENOB ni estabilidad prolongada.

El kernel ADC/DAC es compartido; ver [arquitectura MCU/MPU](../../../docs/UNO_Q_TECNICO.md)
y [relay](../../../docs/TRANSPORTE_TECNICO.md). Las calibraciones Bode previas
se obtuvieron con reloj ADC de 40 MHz y requieren nueva comprobación.

[Revisión y prueba sostenida ADC16](../../../diagnosticos/ADC16_V12.md): 7.495.680 pares en120s,
sin discontinuidades y con restauración exacta del perfil y generador.

## Escala temporal y estados

En eje de muestras la escala horizontal se edita en muestras. En eje de
tiempo se edita en milisegundos y se convierte al número de muestras usando
el período medido o el perfil confirmado antes de recibir datos. Se redondea
al período real y se respetan los límites de 50–250.000 muestras. La duración
se conserva al cambiar Fs mientras esos límites lo permitan; la posición
se muestra también en tiempo. La gráfica conserva su eje en microsegundos.

Mensajes de estado en capitalización normal: adquisición en vivo, pantalla
congelada por STOP o SINGLE. El cuadro de estado mide 34 px y el selector
se identifica como MUESTREO.

## Versiones y enlaces

- Esta carpeta: [Monitor V12](app.py), con [firmware V11 P992](../../../arduino/historico/v11_p992/README.md).
- [Monitor V13](../v13/README.md): aplicación usada actualmente, con PyQt6 y audio.
- [Histórico](../README.md).
