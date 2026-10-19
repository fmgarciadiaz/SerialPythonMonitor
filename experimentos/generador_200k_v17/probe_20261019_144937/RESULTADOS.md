# Medición física del generador — 19/10/2026

A0→CH2/A3 confirmado por usuario. ADC8 dual, FS nominal160000000/253 S/s.
17 casos, capturas cortas (~0,25s por caso) después de asentamiento150ms.
Niveles DAC1427–2668 (1,000Vpp nominal), no calibración absoluta.

| Onda | Solicitada kHz | Medida kHz | Fundamental Vpp |
|---|---:|---:|---:|
| Seno | 25 | 24.999997 | 1.017 |
| Seno | 50 | 49.999994 | 1.009 |
| Seno | 62.5 | 62.500000 | 1.009 |
| Seno | 73.333 | 73.260068 | 1.005 |
| Seno | 87.5 | 87.623210 | 1.000 |
| Seno | 100 | 100.000004 | 1.000 |
| Seno | 112.5 | 112.359549 | 0.989 |
| Seno | 123.456 | 123.456794 | 0.989 |
| Seno | 137.5 | 137.693634 | 0.980 |
| Seno | 150 | 149.812728 | 0.964 |
| Cuadrada 50% | 50 | 50.000000 | 1.290 |
| Cuadrada 50% | 87.5 | 87.527359 | 1.286 |
| Cuadrada 50% | 100 | 99.999998 | 1.284 |
| Cuadrada 50% | 123.456 | 123.456797 | 1.281 |
| Cuadrada 50% | 150 | 150.093808 | 1.276 |
| Cuadrada 50% | 175 | 175.054704 | 1.271 |
| Cuadrada 50% | 200 | 200.000002 | 1.265 |

Seno150k:6puntos/ciclo. La fundamental cae~5,2% frente a25k; residualRMS
respecto de seno ajustado sube19,5→82,7mV. Este residual incluye escalones,
ruido, cuantización y posibles componentes aliaseadas: NO es THD certificado.
ADC632k no resuelve todoslosarmónicos ni flancos de cuadrada200k.
La fundamental de cuadrada puede superar su Vpp entre niveles por serieFourier.

Frecuenciasmedidas relativas al reloj nominal del mismo MCU; no certifican
exactitud absoluta frente a referencia externa. Frecuenciasintermedias verificadas;
son discretizadas por timer, no limitadas a un listado fijo.

Corrección de análisis: el report inicial calculó fundamental_vpp usando ticks
TIM5 como microsegundos. Ese campo inicial no es válido. Los datos crudos y
frecuenciasFFT son válidos; usar analog_summary.json (tiempo índice/FS,refit
de16384muestras) para amplitudes. run.py ya corrige unidad para futuras capturas.

Producciónhost/UI noampliada todavía. Candidato queda aislado; falta integración
de límites por onda enhost/relay/UI yvalidación prolongada/sweep/dutyantesdepromover.

Restauración: True; identidad final idéntica: True. Recuperación10s: 15991776 muestras, dropped/fatal 0/0.
