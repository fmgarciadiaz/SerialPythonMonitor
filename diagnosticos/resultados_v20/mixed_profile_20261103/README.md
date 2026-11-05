# Perfil local de vista mixta V20, 2026-11-03

Comando: `/Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python tools/profile_mixed_v20.py`.
Qt offscreen, widget 1280×800, RF 3.720.930 muestras a 1.860.465/s,
RADIO 80.000 a 40.000/s, detalle 50, CH1 medida, escalón de período 53.
`profile_ab.json` contiene calentamiento excluido y seis repeticiones medidas
por celda, alternando original/candidato y orden de los cuatro escenarios.
El contador `paint_count` registra eventos de Qt tras preparar cada cuadro;
no mide imágenes nuevas ni FPS visibles.

| Ring | Medición vencida | Original mediana / p95 (ms) | Candidato mediana / p95 (ms) |
|---|---|---:|---:|
| Contiguo | No | 14,84 / 17,48 | 15,76 / 19,23 |
| Contiguo | Sí | 28,12 / 33,57 | 28,45 / 33,37 |
| Envuelto | No | 13,80 / 15,87 | 13,64 / 14,49 |
| Envuelto | Sí | 36,04 / 70,25 | 37,46 / 46,05 |

La selección de extremos consume aproximadamente 9–10 ms por preparación;
el dibujo unos 3–4 ms. Una medición vencida agrega 13–15 ms en su cálculo.
`window_view` entrega vistas de la historia contigua y concatena las dos partes
del ring envuelto; esa copia se produce antes de `_update_live_measurements`
y explica parte del coste adicional del caso envuelto. La frecuencia usa sólo
la cola reciente, pero RMS/media/mínimo/máximo recorren toda la ventana.

El candidato sólo sustituye las listas Python de índices por arrays NumPy;
`candidate_equivalence.json` registra 72 igualdades de índices, incluidos
ring envuelto, ventanas parciales y NaN/±Inf. La mejora total no alcanza 15 %
en ninguna celda alternada y el p95 empeora en contiguo sin medición. No se
incorporó al monitor. `profile.json` y `profile_candidate.json` fueron pruebas
preliminares en procesos separados; la comparación válida es `profile_ab.json`.

No se modificaron cadencia, multiplicadores, timer, medición, firmware, relay
ni V19. Este perfil no sustituye un ensayo físico de pintura/exposición,
integridad o margen de transporte.
