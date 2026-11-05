# Perfilado privado de la sección crítica WAV · V19

Diseño y revisión offline con Astra. Los ensayos de cadencia anteriores no
alcanzaron holgura; éste mide la composición del costo, sin cambiar la lógica
de validación, DMA, caché ni propiedad de cola de la pareja aceptada.

## Contrato `wav-chunk-cycles-v1`

Transformaciones exactas de `wav.h`, `wav_dma.h` y `sketch.ino` generadas por
`tools/wav_timing_candidate_v19.py`. Un binding privado verifica cada fuente,
BIN/ELF, schema y control recompilado idéntico al firmware aceptado.

Sólo DATA20, dentro de `prepare_batch_half`, después de armar/copiar la trama y
antes del CRC, reemplaza los campos existentes40/44 de tiempos. No usa campos
reservados, no agrega transferencias, no cambia ACK ni validación de integridad.
Campo40 es `0xD7000000 | página<<16 | snapshot_id16`; campo44 contiene un valor32.
La marca por sí sola no autoriza el diagnóstico: se exige identidad privada.

| Página | Contenido |
|---:|---|
|0|Serial32 de CHUNK nuevos aceptados|
|1|Request ID|
|2|Sesión|
|3|Cantidad16, estado8, bit24 válido|
|4|Frecuencia real del contador Zephyr, Hz|
|5|Intervalo after-lock/before-unlock, ciclos|
|6|poll llamado desde submit, ciclos|
|7|Validación PCM, ciclos|
|8|Copia PCM, ciclos|
|9|Caché PCM, ciclos|
|10|descriptor completo, incluida su caché, ciclos|
|11|publish incluyendo queue.publish y barrera DSB, ciclos|
|12|Tiempo transcurrido desde entrada medida hasta después de unlock|
|13|Máximo de intervalo bloqueado de CHUNK aceptados desde boot|
|14|Request ID del máximo|

Al emitir página0 se congela el último CHUNK aceptado. No se cambia hasta la
última página. El hilo loop es el único escritor del snapshot: el timer de
`poll` no escribe sus estadísticas. El serial no aumenta por duplicados ni
rechazos. Las barreras de compilador delimitan las lecturas del reloj.

## Límites de interpretación

- Son capturas seleccionadas por cadencia de frames, no todos los CHUNK. Se
  informan primer/último serial, huecos entre observados, incompletos y detalles
  omitidos. El registro detallado limita4096; conserva aparte último snapshot y
  máximo acumulado. No presentar percentiles ni máximos seleccionados como globales.
- El intervalo bloqueado excluye las instrucciones lock/unlock y registro final.
  La inicialización de la instrumentación ocurre antes de lock y del inicio
  medido. Los timestamps perturban la ejecución y no se restan sin calibración.
- El elapsed puede incluir interrupciones pendientes después de unlock. `poll_main`
  sólo mide la llamada desde submit, no las ejecuciones desde timer.
- Los intervalos son anidados: publish contiene copia/caché/descriptor; IRQ los
  contiene a su vez. No sumarlos como costos independientes.
- `base_verifier.c` sigue acumulando40/44 como prepare/check: esos agregados son
  inválidos aquí. El observer privado los separa, invalida el resumen ordinario y
  fuerza aceptación de rendimiento/holgura a falso. No utilizar este firmware para
  promover tasas ni comparar FPS o margen con el aceptado.

48 tests locales pasaron: semántica C++ V19, snapshot congelado, contrato de
fuentes/identidad, rechazo de alteraciones, tramas fragmentadas, separación del
observer, pérdida de páginas y límite de detalle.

## Compilación y auditoría

Control BIN idéntico al aceptado (`37f049fa…`), diagnóstico `2c274c32…`, GCC14.3.0.
La compilación aislada restauró la pareja aceptada correctamente. Astra revisó
el desensamblado: validación2ec–316, copia488–4be, caché4be–4dc,
descriptor4dc–4ee; DSB4f0 incluido en publish, cierre540 después de la cola.
Timestamp previo a unlock b2, BASEPRI b8 y timestamp posterior c0.
Las posiciones son offsets hexadecimales dentro de `wav::submit` del objeto.
El compilador eliminó la inicialización completa de Sample, sin borrado60bytes
bajo lock. `elapsed` excluye prólogo, publicación final de estadísticas y retorno;
ese registro final sí afecta al servicio del transporte y no debe olvidarse.

[Auditoría](../diagnosticos/resultados_v19/wav_timing_build_20261031/disassembly_review.json).

## Primer sondeo físico

RADIO/A0 40kHz, RF8bits/1.860.465S/s, FFT16k,20,032s y801.600muestras DAC.
Exposición100%,614paint events. RADIO/WAV/FM,paradas y cierre funcionales,
sin errores. Son medidas instrumentadas, NO aceptación de margen o tasas.

556capturas seleccionadas durante PLAY, misma sesión:

| Intervalo | Media seleccionada | Máximo seleccionado |
|---|---:|---:|
|after-lock/before-unlock|50,10µs|51,59µs|
|poll desde submit|1,95µs|3,44µs|
|validación PCM|24,94µs|25,03µs|
|copia PCM|18,87µs|18,91µs|
|caché PCM|0,63µs|0,68µs|
|descriptor completo|1,02µs|1,05µs|
|publish+cola+DSB (contiene los anteriores)|21,51µs|21,57µs|
|elapsed medido, inclusivo tras unlock|57,00µs|310,64µs|

El máximo acumulado de IRQ desde boot reportado fue8.266ciclos=51,66µs,
conrequest3638696771. No confundirlo con el máximo elapsed310,64µs, que puede
incluir interrupciones o cambios de contexto después de desbloquear.

Reloj reportado160MHz. Seriales observados5…1699,575CHUNK únicos en detalle,
1.120saltados entre observados; los cuatro anteriores al primero no están en
ese contador.4.364snapshots completos,732sin muestra válida antes del primer
CHUNK,3.057repetidos,1incompleto al terminar,0omitidos por límite.

Validación+copia suman43,81µs, aproximadamente87% del intervalo IRQ seleccionado.
Esto justifica probar sólo la copia de bloque, no tocar DMA/caché/timer. El
máximo ahorro atribuible a eliminar por completo esa copia sería18,87µs por
CHUNK; no es una predicción de mejora equivalente del margen del transporte.

Restauración exacta10,023s,313.344muestras,0pérdidas/fatales; identidad,
fuentes,caché,snapshot,configuraciónrelay yCPU iguales.

[Resumen](../diagnosticos/resultados_v19/wav_timing_profile20_20261031/summary.json).
