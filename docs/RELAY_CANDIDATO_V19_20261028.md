# Relay candidato V19 · build y transporte privado · 28/10/2026

El candidato añade diagnóstico sólo en errores de envío y permite intentar
vaciar la FIFO llena antes de rechazar una trama. Conserva capacidad, orden de
bytes y presupuesto de dos sends no bloqueantes. Sólo difieren de la fuente
aceptada `unoq_config_stream.c` y `frame_send_queue.h`. No cambia firmware ADC,
tasas públicas ni el recibo de producción.

## Binario actualizado

`tools/build_relay_candidate_v19.py` verifica la pareja aceptada, toma respaldo
de app, fuentes, caché completo, firmware y relay; después pausa y detiene la
pareja antes del build. Usa un contenedor temporal con imagen fijada por digest,
0,5 CPU, 768 MiB y 128 PIDs. Retira ese contenedor antes de reanudar adquisición.
Si no puede confirmar su detención, conserva la pareja parada y reporta estado
incierto en vez de arrancar adquisición con el compilador aún activo.

El build real pasó. Se obtuvo un ELF64 aarch64 de 73.976 bytes:

`6aaa6afe4313088be78d44f554bdf4ac7acdf010ea52dd7b9944f32f037c3a95`

Artefacto: `diagnosticos/resultados_v19/relay_candidate_build_20261028/relay-candidate.bin`.
Informe, hashes de cada fuente y log de compilación en la misma carpeta.
Restauración exacta posterior: 10,020 s / 313.344 muestras sin pérdidas ni fatales;
fuentes, caché, CPU, identidad y configuración del relay original verificados.

El viejo `candidate/relay/unoq_stream` sigue obsoleto; no usarlo. El artefacto
nuevo se referencia desde el manifiesto del candidato sin reemplazarlo ni
editar la aceptación de producción.

## Sondeo físico privado

`tools/probe_relay_transport_v19.py` acepta únicamente un artefacto ligado por
hash a un build con restauración verificada. Comprueba que las fuentes sigan
idénticas, conserva el firmware aceptado y carga temporalmente el relay nuevo.
Antes del perfil objetivo verifica identidad, política del contenedor, CPU y
10 segundos de adquisición. Después del ensayo restaura y verifica la pareja
original completa. Las fuentes y apps V17/V18 quedan fuera de la operación.

Primer sondeo ADC8 CH1 / 1.860.465 S/s: **60,033 s, 111.639.544 muestras,
dropped=0, fatal=0**, continuidad y restauración exacta aprobadas.
Evidencia: `diagnosticos/resultados_v19/relay_transport_screen_20261028/report.json`.

Las tres repeticiones independientes de 120 s se registran incrementalmente en
`diagnosticos/resultados_v19/relay_transport_qualification_20261028/report.json`.
Cada repetición parte de la pareja aceptada y la restaura antes de la siguiente.

**Resultado: las tres pasaron.**

| Corrida | Duración | Muestras | Dropped / fatal | Restauración |
|---|---:|---:|---:|---|
| Sondeo | 60,033 s | 111.639.544 | 0 / 0 | Exacta |
| Arranque 1 | 120,068 s | 223.264.264 | 0 / 0 | Exacta |
| Arranque 2 | 120,068 s | 223.263.392 | 0 / 0 | Exacta |
| Arranque 3 | 120,068 s | 223.266.008 | 0 / 0 | Exacta |

Total: **781.433.208 muestras**. La identidad final se volvió a consultar y
coincide con el recibo: firmware `37f049fa…`, relay `27da0bc4…`. El candidato
`6aaa6afe…` ya no está activo. No se promovió ni se modificaron las tasas.
Ocho tests dirigidos de transacción/build/rollback y el harness C pasaron.
El runtime del monitor sigue idéntico al de la validación anterior.

Esta campaña sólo mide integridad de transporte. No mide pico de FIFO ni margen
de envío, no dibuja la GUI y no reproduce RADIO/A0. No autoriza promoción por sí
sola ni demuestra que `sent=-1` estuviera causado por una FIFO llena. El siguiente
control debe comparar carga conjunta de GUI/RADIO/A0 con la pareja aceptada.

## Reproducción

```sh
python tools/build_relay_candidate_v19.py --serial NUMERO_ADB --output diagnosticos/resultados_v19/NUEVO_BUILD
python tools/probe_relay_transport_v19.py --serial NUMERO_ADB --build-report diagnosticos/resultados_v19/NUEVO_BUILD/report.json --output diagnosticos/resultados_v19/NUEVO_ENSAYO --seconds 60
```

Ambas herramientas requieren el Q libre, registran intención antes de cada
operación y mantienen el respaldo pareado. La cancelación solicita restauración;
no se debe matar al proceso mientras restaura.
