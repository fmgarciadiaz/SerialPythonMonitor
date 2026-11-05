# RADIO/A0: consultas y holgura · 28/10/2026

Se mantiene la pareja V19 aceptada (firmware `37f049fa…`, relay `27da0bc4…`).
V17/V18 y el runtime de V19 no se modifican. El experimento anterior del relay
no se combina con este candidato host.

## Reproducción del cierre

El control `diagnosticos/resultados_v19/radio_query_baseline_20261028/` usó
ADC8 CH1 1.860.465 S/s, FFT16K, RADIO710 kHz y A0 40 kHz. No completó los
60 segundos: la última fila periódica registra 42,83 s de reproducción.
El cierre y la falta de confirmación de STOP/restauración se conservan como fallo.

El relay rechazó un frame con CRC correcto. La decodificación guardada en
`rejected_frame.json` reporta dropped=1, fatal=0, cola/pico=8/8 y último envío
322.868 ticks frente a un presupuesto de299.968. Esto demuestra saturación
de la cola MCU en este cierre; no prueba el origen de otros cierres anteriores.
Antes del rechazo, el observador midió margen medio8,292% durante PLAYING.
Contó1.053 QUERY y3.563 CHUNK enviados durante ese estado. No se infiere
causalidad del conteo por sí solo.

La recuperación explícita posterior pasó10,026 s,313.344 muestras,
dropped=fatal=0, con identidad aceptada exacta (`recovery.json`). El registro
original del receptor mantiene `hardware_restored=false`; la recuperación
posterior no reescribe ni convierte en éxito la corrida fallida.

## Revisión de Astra y candidato A

Astra verificó que `wav::submit()` supervisa DMA antes de cada comando, y
CHUNK devuelve el mismo estado actualizado de créditos que QUERY. Cada
respuesta WAV ocupa una mitad prioritaria del batch SPI. Propuso renovar el
plazo de consulta exclusivamente tras un ACK de CHUNK correlacionado, válido,
sin error, PLAYING y RADIO/A0 a40 kHz.

`tools/radio_query_candidate_v19.py` aplica esa única diferencia dentro del
proceso diagnóstico, con restauración del método al salir del contexto.
Se activa explícitamente mediante `gui_accepted_metrics_v19.py
--private-ack-refresh`. No cambia reservas, créditos, tokens, bloques, ADC,
firmware ni relay. Los contadores en `relay_wire_metrics_v19.py` registran
comandos enviados con éxito y tipos de respuestas, sin relojes nuevos en Q.

40 ms es elegibilidad para QUERY, no una garantía de respuesta en40 ms.
Si no hay nuevos CHUNK, la consulta vuelve a ser elegible. Los comandos
pendientes conservan su serialización y timeout originales.

Problema previo independiente: si refill entra pero no envía por falta de
tokens o porque `try_codes()` devuelve `None`, el `elif` actual puede impedir
evaluar QUERY vencido. No se modifica aquí para mantener una sola variable.

## Aceptación pendiente

Primeros controles físicos (no constituyen calificación):

| Variante | RADIO PLAYING | Audio reproducido | QUERY / CHUNK | Margen MCU | Pico |
|---|---:|---:|---:|---:|---:|
| A, renovar tras ACK |60,058 s|2.401.440|1.091 /5.002|10,404%|5|
| Control sham, mismo wrapper sin renovar |60,026 s|2.400.480|1.460 /5.000|8,633%|5|
| A, segundo arranque |60,040 s|2.400.960|1.074 /5.001|10,244%|5|

Ambos completaron audio, STOP, cierre y restauración confirmados sin errores.
Los directorios son `radio_query_candidate_20261028` y
`radio_query_sham_20261028` bajo `diagnosticos/resultados_v19/`.
La repetición se guarda en `radio_query_candidate_repeat_20261028`, con
STOP/restauración confirmados e identidad final aceptada exacta. No cambió
ningún archivo runtime incluido en los hashes de la revisión global.
La reducción observada de QUERY es25,3–26,4%, con audio equivalente. No son
repeticiones suficientes para atribuir toda la diferencia de margen a QUERY.
Los picos5 incumplen el criterio. La primera corrida baseline sin wrapper
se mantiene como fallo independiente, no entra en una media de éxitos.

Astra también revisó el código privado y no encontró defecto bloqueante.
Pidió control sham por el costo del wrapper en frames ADC, que se agregó sin
cambiar el primer ensayo en curso. Se ejecutaron32 tests dirigidos, incluyendo
restauración tras excepción, varios ACK, alcance RADIO40k, errores, timeout sin
ACK, reservas y consulta al vencer el plazo con cola llena.

Comparar control y A con pareja, observador y carga iguales. Reducir QUERY
no basta: conservar audio entregado, integridad, reservas y cierre; medir
margen por nodo, cola MCU y slack. Exigir margen≥10%, pico<4 y slack positivo.
Primero descartar fallos; sólo una señal consistente justifica campaña larga.
La FIFO TCP sigue sin medición de holgura. Ningún candidato está promovido.

Siguiente paso: separar el pico acumulado de arranque de la ocupación durante
PLAYING usando las métricas existentes, sin cambiar el criterio de aceptación.
No aumentar la reserva ni cambiar ADC/tasas para maquillar el pico.

## Observación por fases y ráfagas

`radio_queue_phases_20261028/` completó60,036 s y2.400.480 muestras de audio,
STOP/cierre/restauración confirmados. Sólo5 de14 filas periódicas tenían
ventana expuesta: sirve para diagnóstico, no aceptación de dibujo visible.

El pico pasó2→3→4→5 durante preparación de audio, antes de la respuesta PLAYING.
El último RF previo al envío PLAY ya contenía pico5. En PLAYING no apareció
un récord mayor; la ocupación muestreada máxima fue4 y el margen medio10,358%.
Se observaron3.195 nodos cuyo envío previo excedía299.968 ticks, con máximo
690.642. El promedio favorable no elimina esas demoras ni aprueba la cola.

Los eventos se limitan a128; las épocas a32. Se conservan el pico acumulado,
ocupación observada, primer RF por nombre de fase/época y excesos de presupuesto
en nodos deduplicados. No hay consultas adicionales al MCU ni reinicio de
contadores. La ocupación muestreada es un límite inferior, no el máximo real.

Astra revisó el observador y confirmó estos límites: las fases provienen de
observación host, las respuestas de estado pueden quedar pendientes al enviar
STOP, se agrupan reentradas de igual nombre/época y un estado IDLE inicial
denomina `stopped` al audio aunque RF siga adquiriendo. `send_previous` describe
el nodo anterior. El observador no sustituye el validador de integridad y no
pondera frames sin muestras. No comparar pequeños cambios de margen con el
observador anterior como si su costo host fuera idéntico.

El siguiente experimento privado conserva el candidato ACK y reduce solamente
`chunk_burst`8→2 para RADIO40k. Mantiene480 muestras por bloque, intervalo6 ms,
reserva/objetivo30 bloques y ventana de créditos. Hipótesis: distribuir respuestas
de control prioritarias sin agrandar buffers. Riesgo a medir: recuperación más
lenta tras un bache. El launcher lo selecciona con `--private-ack-burst2`.
Antes se mide un control ACK con el mismo observador de intervalos CHUNK.
Los relojes añadidos se ejecutan sólo al enviar CHUNK en el host diagnóstico.

Control con instrumentación equivalente (`radio_burst_control_20261028`):
60,023 s,2.400.480 muestras reproducidas,12/12 observaciones PLAYING expuestas,
sin errores y restauración confirmada. Margen10,218%, pico4, ocupación muestreada3,
reserva mínima observada8.887 muestras. De4.998 intervalos CHUNK durante PLAYING,
3.158 fueron menores a1 ms; máximo176,47 ms. Esto confirma envíos agrupados,
sin demostrar por sí solo que causen el pico. El pico4 sigue fuera del criterio.

El límite privado de ráfaga se aplica antes de procesar el primer ACK de BEGIN.
Al salir del contexto se restaura el atributo de la fuente, incluso si era
heredado, además del método y callback.37 tests dirigidos pasan, incluyendo
esa restauración tras excepción. No equivale a limitar comandos pendientes:
sólo limita los tokens acumulados; la ventana de créditos sigue igual.

Resultado `radio_burst2_20261028`:60,041 s,2.400.960 muestras de audio,
sin errores y restauración confirmada;6/12 observaciones PLAYING expuestas.
Los intervalos menores a1 ms bajaron a740/4.999, pero margen8,410%,pico5,
ocupación muestreada4 y4.886 envíos por encima del presupuesto. Reserva mínima
observada11.614 muestras, máximo intervalo CHUNK152,73 ms. QUERY718/CHUNK5.000.
La carga visible difirió del control: no atribuir causalmente toda la diferencia
de margen a burst2. Esta corrida no justifica incorporarlo; queda descartado
como mejora demostrada, aunque el audio funcionó. Se mantiene el candidato ACK
por separado, aún sin aceptación de holgura.

Próximo diagnóstico: evaluar cómo se intercalan respuestas WAV prioritarias y
muestras en SPI, con una sola variable y contadores existentes antes de tocar
firmware. No relajar el límite de pico ni combinar los experimentos fallidos.

Cierre de tanda: `radio_burst2_20261028/final_recovery.json` verifica identidad
aceptada y10,025 s/313.344 muestras continuas, dropped=fatal=0. Q queda con
firmware/relay aceptados, sin candidato activo. Hashes runtime de la revisión
global sin cambios; V17/V18 intactos.
