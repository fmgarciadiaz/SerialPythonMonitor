# Verificación del análisis FFT · 7 de octubre de 2026

[Uso](../monitor/v14/README.md) · [Algoritmos y límites](../docs/FFT_ANALISIS.md)

Astra planificó y revisó los estimadores; Sol 6.1 implementó la variante
independiente. No se operó el Q ni se cambió firmware.

## Pruebas

- 22 pruebas nuevas: normalización, Welch/CSD contra SciPy, tonos entre bins,
  armónicos, ruido, signo de fase/retardo, coherencia, huecos, controles y SINGLE.
  Resultado: aprobadas en 3,75 s.
- 121 regresiones del monitor anterior ejecutadas contra los módulos nuevos,
  adaptando imports y la expectativa del selector FFT: aprobadas en 31,02 s.
- 121 pruebas originales del monitor anterior: aprobadas en 30,10 s.
- Capturas Qt offscreen de los cuatro modos: métricas principales visibles.
  Power/Distortion utilizan tono, armónicos y ruido; Transfer utiliza ruido
  filtrado por un sistema digital de un polo. No son mediciones analógicas.

```sh
conda activate Python_3_13_DataScience
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests/v14 -v
```

Las regresiones adaptadas se ejecutaron desde una copia temporal de tests/v13;
las pruebas nuevas permanecen en tests/v14. Se conservaron los archivos de V13.

## Tiempos del motor numérico

8192 muestras, ocho segmentos como máximo para Spectrum/Transfer; Distortion
ajusta el último bloque con hasta diez armónicos. Siete repeticiones después
de una llamada de calentamiento. Spectrum/Distortion corresponden a un canal;
Transfer utiliza dos. Estos tiempos excluyen recepción, dibujo Qt y hardware.

| Muestreo (Hz) | Cálculo | Mediana (ms) | Máximo (ms) |
|---|---|---|---|
| 40000 | Spectrum | 1.33 | 1.78 |
| 40000 | Distortion | 16.95 | 18.09 |
| 40000 | Transfer | 2.27 | 2.68 |
| 125000 | Spectrum | 1.62 | 1.95 |
| 125000 | Distortion | 19.37 | 20.45 |
| 125000 | Transfer | 2.57 | 3.08 |

No se infieren FPS físicos ni latencia USB de estos números. Distortion y el
ajuste SNR de Power se limitan a cinco actualizaciones/s; las PSD y Transfer
pueden dibujarse a 30/s y Heatmap a 20/s. Se requiere comprobación con la placa
antes de concluir sobre fluidez y calidad instrumental.

## Panel de estadísticas por análisis

El panel inferior de Medición reemplaza sus valores temporales por las
estadísticas FFT del canal elegido. Se eliminaron los textos de estadísticas
de los gráficos y del lateral. Power usa siete tarjetas; los demás usan seis.
Transfer muestra la pareja fija OUT / IN. Cambiar de canal conserva SINGLE,
y V(t) recupera la selección anterior, incluso ADC_IN/ADC_OUT.

La batería nueva incluye ahora 26 pruebas: cuatro regresiones adicionales para
las tarjetas, la elección de entrada, los canales no dibujados y los selectores
en los encabezados FFT/Heatmap. Las capturas
se actualizaron con esta presentación; continúan siendo sintéticas.

## Marcas de distorsión

Distort muestra f₀ y armónicos detectados con amplitudes ajustadas y niveles
en dBc. Las marcas débiles se filtran según el residual y las etiquetas se
colocan arriba/abajo evitando superposición. Se comprobó el armónico H2 de
amplitud 3 %, su nivel relativo y las coordenadas en escala logarítmica.
27 pruebas nuevas y 15 regresiones de adquisición/render pasan.
