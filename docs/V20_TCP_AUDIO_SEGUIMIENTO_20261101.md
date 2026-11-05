# V20: recuperación TCP y atención de RADIO · 1/11/2026

Estado: relay TCP candidato privado y cambio host de 86 ticks **NO incorporados**. El guard del host vuelve a 88 ticks. No se habilitan tasas públicas. V17/V18/V19 no se modifican.

Las corridas TCP y del candidato host 86 aquí cerradas restauraron históricamente V19. Después, el coordinador dejó V20 activa como base de trabajo; V19 queda como respaldo y recuperación si V20 resulta inoperativa o se solicita. La instrumentación posterior pasó RADIO 60 s funcional y tiene 120 s en progreso, sin incorporar TCP/86 y sin aceptación visible por exposición insuficiente. Ver [diagnóstico sobre V20 activa](V20_SERVICIO_RADIO_DIAGNOSTICO_20261101.md).

## Adquisición con relay TCP candidato

Se compiló ARM64 usando sólo el header aislado `experiments/v20/tcp_queue_recovery/frame_send_queue.h`. El resto del relay y el firmware permanecieron iguales. El wrapper archivó la pareja V19 y verificó su restauración al terminar.

| ADC8 CH1 | Duración | Muestras validadas | Margen medio | Cola pico |
|---|---:|---:|---:|---:|
|1.860.465 S/s|60 s|111.561.936|19,02 %|2/16|
|2.000.000 S/s|60 s|119.926.160|7,25 %|3/16|

Ambos pasaron integridad. 2 MS/s no alcanza el objetivo de margen medio del10%; sigue experimental. No se midió ocupación de FIFO TCP en este screen ni se demuestra una mejora causada por el header.

[Informe restaurado](../diagnosticos/resultados_v20/tcp_recovery_adc60_20261101/report.json).

## Fallo de audio bajo carga combinada

Con el candidato, RADIO/A0 a40kHz y ADC8/1,86MS/s no completó los60s. La ventana estuvo expuesta100%. A los57,4s de audio se agotó la reserva de DAC; WAV y Synth posteriores no llegaron a validarse. ACK leído máximo230ms. Hay un `chunk_gap` host de377,68ms, pausas tick de80,9/39,1ms con0,56/0,42msCPU y audio disponible en host (21.158muestras). El render máximo era2,49ms. Estos datos orientan hacia servicio/IPC/planificación; no prueban una causa única. `chunk_gap` no mide directamente el intervalo físico entre aceptaciones MCU. Reason2 es BUSY de un CHUNK tras underrun, no un código causal del agotamiento.

La repetición con relay anterior completó60s y luego WAV/Synth, ACKmáximo67,75ms, pero su exposición GUI no fue equivalente. No permite concluir que el candidato provoque o resuelva el fallo. Ambos restauraron V19 correctamente.

- [Candidato: fallo y restauración](../diagnosticos/resultados_v20/tcp_recovery_radio60_20261101/report.json).
- [Relay anterior: pasada funcional, exposición insuficiente](../diagnosticos/resultados_v20/tcp_baseline_radio60_20261101/report.json).

## Cambio host de 86 ticks: ensayo fallido y reversión

Astra identificó que `_process_decoder_events()` atendía `service_wav()` entre cuadros para ADC8/88 ticks/CH1/3488, pero no para 86 ticks, correspondiente al perfil 1,86 MS/s. La variante privada amplió únicamente ese guard a 86/88, manteniendo créditos, tokens, orden y límites. No incluyó 80 ticks/2 MS/s ni otras geometrías. La revisión de fuente y tests no produjo bloqueantes, pero no constituyó aceptación física.

El primer intento físico (`frame86_service_radio60_20261101`) no llegó a RADIO: arranque local demorado y cierre del flujo; restauró V19. Se observaron esperas de lectura de pyc con CPU nula y se capturaron pilas. La repetición local con caché temporal pasó 56 tests V20 **antes de revertir** el guard. No demuestra daño de caché ni explica el underrun previo. Un lanzamiento adicional falló antes de operar Q por una carpeta de salida creada prematuramente; su contexto quedó conservado aparte.

La repetición final con caché temporal y sin tests concurrentes **falló**: RADIO `state=4 reason=2` y `FlowLimitExceeded`, con RF pendiente de 1,00047 s frente al presupuesto de 1 s. No completó el hold de RADIO ni validó WAV/Synth posteriores. La exposición GUI fue 0 %, así que tampoco aporta aceptación visible. El máximo de ACK raw fue 33,9145 ms y el de demora hasta decodificación 6,1381 ms. Esos máximos no prueban una causa ni que el cambio corrigiera el problema. La integridad de esta prueba combinada no queda aceptada, aunque el screen privado de reserva fuera positivo. `restoration.ok=true`: V19 quedó restaurada con materiales e identidad verificados, lectura de 10,0235 s y cero pérdidas/fatales.

- [Primer intento, sin llegar a RADIO](../diagnosticos/resultados_v20/frame86_service_radio60_20261101/report.json).
- [Repetición final fallida y restauración](../diagnosticos/resultados_v20/frame86_service_radio60_retry_20261101/report.json).

Se restauró el guard original `period == 88` y su comentario. La variante queda sólo en [service_profile86.patch](../experiments/v20/tcp_queue_recovery/service_profile86.patch), un diff original→candidato que **no está aplicado ni habilitado por defecto**. El test de 86 ticks vuelve a esperar que no haya servicio entre cuadros; conserva los casos negativos y la prueba de priming que espera ambos ACK antes de PLAY. El relay TCP candidato tampoco se incorpora al producto.

Verificación final del host revertido: **14 tests PASS** en `tests.v20.test_radio_frame_service` y `tests.v20.test_wav_reset_confirmation`, con Python 3.13 habitual y `PYTHONPYCACHEPREFIX=/tmp/arduscopio-v20-check-cache`. No se creó otro entorno ni se operó Q en este cierre. Es validación local; no aceptación física.

## Preparación para dejar V20 como base activa

Se preparó [activate_working_v20.py](../tools/activate_working_v20.py) sin ejecutarlo sobre Q en este bloque. Usa exclusivamente la prueba restaurada `storage_lifetime_cycle_20261101` y el relay original medido. Verifica y conserva el respaldo pareado y una copia del recibo V19 antes de detenerla. Con un único propietario Q, exige identidad exacta, fuentes, snapshot, integridad continua, CPU y configuración del relay; si todo pasa deja V20 funcionando. Fallo o cancelación ejecutan rollback V19. No compila ni promueve aceptación/tasas.

El éxito genera un informe privado apto para el binding existente, sin campo `restoration`, y el recibo separado `monitor/v20/q_support/working_pair.json`. El monitor V20 habitual valida ese recibo, su informe sellado por hash, la prueba original, fuentes locales de firmware/relay, binarios e identidad de placa/app y contrato BSP. La conexión sigue siendo sólo a una pareja instalada: no arranca, programa ni carga aplicaciones. Las rutas privadas explícitas conservan su validación anterior. El recibo público de aceptación no cambia.

Validación local: **28 tests PASS**, incluidos workflow de activación, fallos/cancelación, recibo alterado, fuentes cambiadas, identidad y conexión sin despliegue, más las regresiones privadas de GUI y los 14 tests focalizados del guard/reset. Python habitual y caché temporal; no aceptación física. El coordinador revisará y ejecutará la activación y luego comprobará 10 s por `installed_connection` default en un informe separado, sin modificar el informe sellado de activación.

Los probes anteriores usan baseline V19 y la restauran al terminar: no ejecutarlos sobre la nueva base activa sin adaptarlos primero a V20. El recibo de trabajo valida estrictamente fuentes de firmware/relay; un cambio requiere nueva prueba y actualización verificada del recibo. El código host puede seguir desarrollándose sin cambiar esos manifests.

## Próximos experimentos separados

El siguiente plan de Astra debe separar contadores de por qué `service_wav` no envía y una evaluación de QoS reversible sólo en el thread propietario del receptor. No se incorporó QoS. Primero medir servicio/planificación con la base V20; no aumentar RAM en este bloque. El coordinador mantiene la propiedad exclusiva de Q.

Ampliar WAV a48/60bloques es otra alternativa, con216/360ms adicionales de cola nominal. No basta editar SLOTS: hay restricciones del parser16/30, descriptoresDMA y ventana64KiB; preservar waveform7200, guards y arena RF. Hay180.128bytes contractuales trasStorage hasta0x200c0000; una arenaWAV separada requiere contrato/inicialización y tamañosARM verificados. No se modifica RAM en este bloque.

## Base de trabajo activada al cierre

Por instrucción del usuario, **V20 queda activa**. Sol implementó el activador y recibo separado; el coordinador revisó y ejecutó Q. Activación verificada y lectura por conexión habitual:10,026s,313.344muestras,0pérdidas/0fatales. Firmware52f933bd… y relayoriginalbf6893f5…; sin TCPcandidato ni guard86. V19 respaldada/detenida, sin restaurarla al finalizar correctamente. No se cambia el recibo de aceptación pública ni las tasas.

- [Activación persistente y respaldo](../diagnosticos/resultados_v20/v20_working_active_20261101/report.json).
- [Conexión habitual verificada](../diagnosticos/resultados_v20/v20_working_active_20261101/default_connection_verification.json).

Los ensayos posteriores deben usar V20 como baseline y preservar su estado; los probes anteriores que restauran V19 no deben ejecutarse sin adaptación. El informe de activación está sellado por hash: las comprobaciones nuevas se guardan aparte.
