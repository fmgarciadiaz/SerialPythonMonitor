# Comparación analógica A2/A3 · 4 de octubre de 2026

Cableado confirmado por el usuario: A0 directamente a A2 y A3, sin circuito
intermedio y con masa común. ADC de 14 bits; seno solicitado de 2000 Hz,
niveles DAC 500–3500, aproximadamente 1,616 V de offset y 1,216 V pico.
Cada perfil se capturó durante 10 segundos. Ajuste senoidal offline sobre
las últimas 16384 muestras; no se procesó el ajuste durante adquisición.

| Firmware | Fs (kHz/canal) | Amplitud pico A2 / A3 (V) | Residuo RMS A2 / A3 (mV) | Fase A3−A2 (°) | Pares |
|---|---:|---:|---:|---:|---:|
| v9_fast | 62.5 | 1.215964 / 1.215850 | 7.35 / 6.83 | 1.537 | 622592 |
| v9_fast | 100 | 1.215870 / 1.215927 | 7.24 / 6.88 | 1.526 | 997429 |
| p992 | 62.5 | 1.216056 / 1.215826 | 7.47 / 6.85 | 1.535 | 622705 |
| p992 | 100 | 1.215899 / 1.215898 | 7.38 / 6.83 | 1.528 | 997489 |
| p992 | 125 | 1.215857 / 1.215857 | 7.39 / 6.87 | 1.528 | 1247345 |

Los cinco perfiles aprobaron integridad y el criterio analógico del ensayo:
ambas amplitudes entre 0,8 y 1,5 V pico, residuo RMS inferior a 100 mV y
cociente de amplitudes A3/A2 entre 0,95 y 1,05. Cero huecos, valores ADC
fuera de rango, dropped o fatal. En estos ajustes la diferencia relativa
de amplitud entre canales fue inferior a 0,02 %; esto describe concordancia
observada, no exactitud absoluta ni garantía sobre otras frecuencias.

La frecuencia ajustada fue aproximadamente 1996,805 Hz, consistente con
el divisor entero del DAC. ADC y DAC comparten referencias: esta medición
no calibra el reloj ni la tensión contra un instrumento independiente.
El residuo incluye ruido, distorsión y error del modelo senoidal.
La fase relativa no es cero: se midieron aproximadamente 1,53°.
No se aplicó corrección ni se cambió la calibración Bode.

Evidencia:

- [V9 Fast: 62,5 y 100 kHz](resultados/analog_20261004_202834_045007/informe.json).
- [P992: 62,5, 100 y 125 kHz](resultados/analog_20261004_203001_770778/informe.json).

Cada carpeta contiene los binarios completos y previews CSV. Los informes
registran restauración exacta del perfil inicial de cada variante.
P992 sigue independiente de V11: no se promovió el protocolo V3.

[Restauración posterior al ensayo](resultados/restauracion_analogico.json)
aprobada: V9 Fast normal, ADC de 14 bits / 100 kHz y cuadrada de 2,5 Hz;
298709 pares en aproximadamente 3 s, sin dropped ni fatal. Los 38 archivos
originales conservan sus hashes.
