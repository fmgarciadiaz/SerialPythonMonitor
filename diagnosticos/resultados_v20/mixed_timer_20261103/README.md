# QTimer y vista mixta V20, 2026-11-03

Se ejecutaron dos pruebas locales con
`/Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python`:

1. `tools/probe_mixed_timer_v20.py`: QTimer real y pintura diferida, sin
   `processEvents` dentro de callbacks. `timer_reset_probe.json` muestra
   timeout a 204,516 ms, `setInterval(120)` en preparación a 204,537 ms y
   `setInterval(180)` en pintura a 204,627 ms. El `timerId` cambió de
   33554433 a 50331649 y `remainingTime` volvió a 180 ms. Por tanto, un
   cambio de intervalo desde pintura sí reinicia el temporizador.
2. `tools/benchmark_mixed_timer_v20.py --seconds 5 --pairs 6`: ventana
   1280×800, CH1+RADIO, RF 3.720.930 y audio 80.000 muestras iniciales,
   detalle 50 y CH1 medido. Ring contiguo y envuelto, un par de calentamiento
   excluido y seis pares A/B alternados de 5 s por ring. La candidata es un
   monkeypatch del observador: registra máximo/decaimiento de pintura pero
   omite `_refresh_render_cadence` allí; preparación y controles mantienen
   su actualización. El monitor no fue editado.

| Ring | Variante | Cuadros nuevos / 5 s | Intervalo mediano (ms) | p95 (ms) | Coste GUI total / 5 s (ms) | Mediciones / 5 s | Pico render (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| Contiguo | Base | 50 | 99,82 | 119,82 | 1732 | 38 | 33,98 |
| Contiguo | Candidata | 49 | 100,13 | 125,61 | 1732 | 37,5 | 41,79 |
| Envuelto | Base | 28 | 168,04 | 238,58 | 1555 | 28 | 78,73 |
| Envuelto | Candidata | 31 | 151,24 | 201,85 | 1599 | 30,5 | 54,52 |

Los valores de la tabla son medianas de las seis corridas por celda; los
intervalos y p95 se calcularon dentro de cada corrida a partir de cuadros
preparados con nueva época RF y luego pintados. `timer_ab_raw.json` guarda
timeout, preparación, pintura, ID/intervalo/tiempo restante y épocas;
`timer_ab_summary.json` contiene los agregados por corrida. Hubo un repintado
sin nuevo cuadro en la base contigua; los demás eventos contados fueron nuevos.

En el caso real mixto el observador de pintura cambió el intervalo sólo
2 veces en 469 pinturas base medidas (0/297 contiguas, 2/172 envueltas).
La preparación lo cambió en 453 de 468 timeouts base. El segundo reinicio
es causalmente posible, pero raro en esta carga. La candidata no alcanza
10 % de mejora de cadencia en el ring contiguo; empeoran allí p95 y pico.
No cumple el criterio global y no se incorpora.

El avance sintético fue de 2.000 muestras RF y 43 audio cada 40 ms
(aproximadamente 50 kS/s y 1,075 kS/s de ingreso simulado). La ventana
inicial tiene tamaño de 2 s a las tasas nominales, pero esta prueba no
reproduce el volumen de transporte ADC 1,86 MS/s ni demuestra FPS físicos,
integridad, exposición o margen en el Q. No se tocaron firmware, relay,
límites, workers, cadencia 3/4/500/.85 ni versiones congeladas.
