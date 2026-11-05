# Combinaciones privadas RADIO/A0 · 30/10/2026

Se combinan candidatos previamente aislados a ADC8/1.860.465 S/s, FFT16k,
RADIO y A0 a 40 kHz. Ninguna combinación se incorpora al runtime ni habilita
tasas nuevas. V17/V18 permanecen intactas.

La combinación base reúne O2 sólo en `prepare_batch_half`, relay con espera
READY activa acotada a 250 µs y prellenado con ráfaga 4/8 ms. Al enviar PLAY,
se recupera la cadencia aceptada 8/6 ms. No se amplían reservas, buffers,
créditos ni tamaños de bloque. Las consultas de estado se comparan a 40,
30, 12 y 24 ms; cada bloque DAC de 480 muestras dura 12 ms.

## Criterio

Se exige integridad y audio, GUI visible, margen medio MCU ≥10 %, pico
acumulado de cola <4 y slack positivo. Un sondeo de 20 s no acredita
aceptación: requiere después 60 s y tres corridas independientes de 120 s.
Una extensión que falla detiene esa candidatura. El campo `report.ok`
acredita funcionalidad/restauración; revisar además `gui.headroom_pass`.

## Evidencia

Los resultados completos y el resumen de cada combinación se conservan en
[`combos_20261030`](../diagnosticos/resultados_v19/combos_20261030/).
| Caso | Audio | Margen MCU | Pico | Holgura | Restaurado |
|---|---:|---:|---:|---|---|
| `o2_ready250_startup4_20` | 20.02 s | 12.55 % | 3 | Sondeo PASS | Sí |
| `o2_ready250_startup4_60` | 60.09 s | 12.22 % | 5 | FAIL | Sí |
| `o2_ready250_startup4_query12_20` | 20.05 s | 10.81 % | 4 | FAIL | Sí |
| `o2_ready250_startup4_query24_20` | 20.06 s | 11.58 % | 3 | Sondeo PASS | Sí |
| `o2_ready250_startup4_query24_60` | 60.10 s | 11.52 % | 5 | FAIL | Sí |
| `o2_ready250_startup4_query30_20` | 20.00 s | 11.48 % | 3 | Sondeo PASS | Sí |
| `o2_ready250_startup4_query30_60` | 60.02 s | 11.62 % | 4 | FAIL | Sí |
| `ready250_startup4_20` | 20.09 s | 11.66 % | 4 | FAIL | Sí |

Todos los casos pasaron funcionalidad y GUI visible. Las extensiones de
40, 30 y 24 ms fallaron por pico acumulado (5, 4 y 5 respectivamente);
12 ms ya falló el sondeo (pico 4). No se ejecutaron las corridas de 120 s
ni se promovió ningún candidato. 24 tests de herramientas privadas PASS.

La última restauración verificó durante 10 s el snapshot original,
integridad y continuidad, hashes de firmware/relay, fuentes, configuración
del relay y estado CPU. La pareja aceptada quedó activa y el Q liberado.

## Siguiente diagnóstico

Las consultas más frecuentes redujeron las ráfagas CHUNK, pero no eliminaron
los picos. A 24 ms el peor envío por nodo alcanzó 1.307.578 ticks
(8,17 ms a 160 MHz), con media de margen 11,52 %. Antes de ajustar más
cadencias, correlacionar esos casos con los tiempos de servicio SPI y
preparación/copia MCU. El promedio favorable no acredita estabilidad de cola.
No liberar nodos antes del EOT ni aumentar buffers para rebajar artificialmente
el pico. La causalidad de las pausas sigue pendiente.

Los porcentajes son mediciones por corrida; no prueban causalidad ni mejora
estadística. No se combinó el envío TCP agrupado, descartado previamente por
UNDERRUN. La pausa intermitente del lector continúa siendo un diagnóstico
separado: [latencias SPI/ACK](LATENCIAS_RELAY_V19_20261030.md).
