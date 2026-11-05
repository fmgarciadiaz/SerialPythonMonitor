# V20: contadores de servicio WAV/RADIO y prueba sobre la base activa

Diagnóstico implementado por Sol. Root probó primero 60 y 120 s; después Sol, como único propietario de Q durante la campaña autónoma, completó tres corridas independientes de 120 s. Todas pasaron funcionalmente y recuperaron la configuración V20. La instrumentación no cambia el servicio, créditos, tokens, orden, tamaño de buffers, tasas, relay ni firmware. El guard de atención entre cuadros sigue restringido a ADC8/88; la variante 86 continúa privada y sin aplicar. QoS queda pendiente de un experimento separado.

## Contadores opt-in

`MONITOR_V19_CHILD_STAGE_TIMING=1` habilita los timers existentes y `child_stages.wav_service`. Con diagnóstico apagado no se crea un objeto de contadores. Con diagnóstico activo sólo se acumulan escalares y diccionarios de claves fijas; no hay registros nuevos por frame ni listas crecientes. Las instantáneas copian los totales al solicitarlas.

| Campo | Qué cuenta |
|---|---|
| `calls`, `priming_calls` | Llamadas al servicio y llamadas con fuente presente antes de PLAY. |
| `reasons.no_source`, `no_status`, `session_mismatch` | Ausencia de fuente/estado, o estado de otra sesión. |
| `pending_timeout` | Timeout de confirmación en el camino ya existente. |
| `pending_control_ack`, `pending_chunk_ack` | Espera serializada de un comando/control o ventana de CHUNK sin confirmar agotada. |
| `credits` | Créditos libres insuficientes frente a los CHUNK reservados. |
| `token` | Token insuficiente en el limitador existente; no se consume PCM ni token. |
| `target_full` | La cola ya alcanza el objetivo; puede enviarse QUERY o PLAY por el camino existente. |
| `pcm_pending`, `no_chunk` | El generador no devolvió códigos y tiene una solicitud PCM pendiente, o no tiene solicitud pendiente observable. |
| `priming_ack` | Antes de PLAY aún quedan CHUNK reservados, sin agotar necesariamente la ventana. |
| `source_exhausted`, `poll_wait` | Fuente agotada o ausencia de trabajo de CHUNK y espera de sondeo. |
| `sends` | CHUNK, BEGIN, PLAY, QUERY y STOP cuyo `sendall` terminó correctamente. |
| `chunk_gaps`, `chunk_gap_last_ms`, `chunk_gap_max_ms`, `last_chunk_at`, `chunk_session` | Separación entre comienzos de envíos CHUNK del host con reloj monotónico, sin contar fronteras entre sesiones. |

Los motivos cuentan paradas del servicio, incluso al interrumpir una ráfaga parcialmente enviada. **No miden tiempo bloqueado ni son causas físicas confirmadas.** La separación CHUNK del host no es el intervalo entre aceptaciones MCU ni una medición del DAC. Un QUERY o PLAY puede coexistir con un motivo de no envío CHUNK.

Los totales llegan a `radio_a0_diagnostics.pcm_transport.child_stages.wav_service` por las instantáneas PCM existentes y también a `reader_stages.json`. No se añade otro canal ni se registra una fila por invocación.

## Wrapper para la base V20 instalada

[probe_working_v20_gui.py](../tools/probe_working_v20_gui.py) crea un binding privado nuevo desde el recibo de trabajo. Usa `installed_identity` default antes y después, con sus locks breves; durante la GUI el receptor hijo conserva la propiedad exclusiva y restaura su snapshot V20. El wrapper no importa el backend de despliegue, no inicia/detiene apps o relay y no devuelve Q a V19.

Comando de la corrida de 60 s ejecutada por el coordinador; su carpeta ya existe y no debe reutilizarse:

```sh
PYTHONPYCACHEPREFIX=/tmp/arduscopio-v20-check-cache \
/Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python \
tools/probe_working_v20_gui.py --serial 1060031107 \
--output diagnosticos/resultados_v20/v20_service_diagnostics_radio60_20261101 --hold 60
```

La carpeta debe ser nueva. El hijo usa ADC8/1.860.465, FFT16384, 710 kHz, sin retune, RADIO durante 60 s confirmados y duración nominal 65 s. WAV y Synth quedan fuera de esta prueba. Se habilitan ACK raw y timers de hijo mediante el entorno del proceso. El wrapper fija `ARDUSCOPIO_PRIVATE_RECOVERY_SECONDS=10`; `gui_private_v20` sólo acepta ese valor explícito para pasar `recovery_seconds=10` al receptor. Sin esa variable conserva el default previo, que puede ser 0,2 s. El override permite exigir aquí la recuperación real de al menos 10 s sin cambiar el monitor habitual.

Guarda `gui.log`, el progreso y la evidencia GUI, métricas de transporte, `reader_stages.json` y sesiones. El informe separa función de exposición; una GUI oculta no se presenta como aceptación visible. Exige recuperación V20 cerrada con `hardware_restored`, continuidad y cero pérdidas/fatales durante al menos 10 s, identidad inalterada, diagnósticos presentes y hashes del recibo de trabajo y del informe sellado de activación sin cambios.

Plazo: hold + 180 s. Si se excede o se cancela, envía SIGINT al proceso GUI y espera hasta 60 s de cierre restaurador. Si el hijo sigue vivo, deja constancia de su PID y no toma control administrativo ni lo mata. No modifica el informe sellado de activación ni el recibo público/privado.

## Verificación local

**34 tests PASS** con Python 3.13 habitual y caché temporal: diagnóstico de servicio, wrapper, guard/priming, reset WAV, observador ACK y recibo de trabajo. La comparación con diagnóstico apagado/encendido conserva bytes, orden y offsets CHUNK/PLAY, reserva de créditos, tokens y espera de ambos ACK; los casos de crédito/token no consumen audio ni tokens. Se comprueban clasificación de motivos, gaps monotónicos sin frontera entre sesiones, cierre por timeout sin kill, restauración V20 y exposición oculta separada de la función.

El `--help` del wrapper pasa y el recibo de trabajo real valida sus archivos locales después de los cambios. Los tests locales no constituyen aceptación física. Los probes anteriores que restauran V19 requieren adaptar su baseline antes de ejecutarlos sobre V20 activa.

## Corrida física de 60 s y repetición en progreso

[Informe RADIO 60 s](../diagnosticos/resultados_v20/v20_service_diagnostics_radio60_20261101/report.json): **PASS funcional**, hold confirmado 60,00955 s, sin errores de GUI y con parada/cierre confirmados. WAV, Synth y Scan no se solicitaron; sus aserciones de plantilla no los validan. Se mantuvieron el guard 88, firmware y relay originales de la base V20; los candidatos TCP/86 siguen sin incorporarse.

| Medición | Resultado |
|---|---:|
| ACK raw correlacionados / decodificados | 5.030 / 5.030 |
| ACK raw máximo | 20,60364 ms |
| Demora hasta decodificación máxima | 8,47319 ms |
| Gap CHUNK host máximo | 118,43241 ms |
| `pending_timeout` | 0 |
| Restauración del snapshot V20 | 10,02348 s / 313.344 muestras |
| Pérdidas / fatales durante recuperación | 0 / 0 |
| Fracción de exposición GUI | 0,2143; insuficiente para aceptación visible |

Identidad antes/después, recibo de trabajo e informe sellado de activación quedaron iguales. La recuperación restauró V20 y la dejó activa; no se volvió a V19.

El tracker acumuló 145.592 llamadas y 976 llamadas de priming. Los motivos registrados incluyen 96.680 `credits`, 33.372 `no_source`, 7.681 `pending_control_ack`, 5.835 `pcm_pending`, 170 `token` y 7 `priming_ack`; los restantes quedaron en cero. Estos totales abarcan **todo el ciclo de vida**, incluidos arranque y recuperación, no sólo el hold de RADIO. No convertirlos en porcentajes de duración bloqueada ni interpretarlos como causas de un fallo anterior.

La pasada no demuestra que el problema previo esté corregido: la carga visible no fue equivalente, sólo hubo 21,43 % de exposición y la instrumentación puede afectar los tiempos. No habilita tasas públicas, aceptación analógica/acústica ni un arreglo causal. Root está ejecutando 120 s con el mismo helper; resultado pendiente. Durante esa corrida se actualizó únicamente documentación, sin cambios de fuentes ni nuevos tests.

## Cierre de la repetición de 120 segundos

La corrida de120,036s pasó RADIO/A0 sobre ADC8/1.860.465S/s, con10.026ACK leídos y observados al entrar al procesamiento; máximo61,26ms hasta lectura y31,42ms hasta entrada al manejo. El mayor intervalo entre comienzos de envíoCHUNK fue216,31ms y no hubo timeout pendiente. Estos intervalos son del host, no del DAC ni latencia pura de cable.

La recuperación de la configuración inicial deV20 pasó10,022s,313.344muestras,0pérdidas/0fatales. Identidad, recibo de trabajo e informe sellado de activación permanecieron iguales; no se inició V19 ni se desplegó firmware/relay. V20 queda activa y sin sesión de prueba abierta.

Exposición de la GUI0% en120s y21,43% en60s: ambas son pasadas funcionales/diagnósticas, sin aceptación de dibujo visible. Margen medio duranteRADIO120s12,21%, colaMCUpico4/16; el campo legacy `headroom_pass` esfalse. No se declara calificación pública ni solución causal del fallo anterior. Los contadores son acumulados de todo el ciclo, incluyendo inicio/recuperación; no representan tiempo bloqueado.

- [Informe120s](../diagnosticos/resultados_v20/v20_service_diagnostics_radio120_20261101/report.json).
- [Resumen de60/120s](../diagnosticos/resultados_v20/v20_service_diagnostics_summary_20261101.json).

Siguiente bloque: reproducir con exposición/carga comparable y correlacionar las pausas con motivos de servicio. QoS reversible sigue como experimento separado del planAstra; no se activó.

## Campaña autónoma: tres corridas independientes de 120 s

Autorización del usuario: «dale más». Sol fue único propietario de Q durante las tres corridas; root no operó la placa en ese intervalo. Preflight: lock disponible, sin monitor/receptor del usuario detectado y pareja V20 de trabajo exacta. Se usó el mismo helper instalado, Python 3.13 habitual y caché temporal, sin compilar, flashear, resetear, desplegar ni iniciar V19. Sin cambios de audio, QoS, guard, buffers o tasas; guard 88 y relay/firmware originales permanecieron iguales.

**Tres de tres PASS funcionales**, RADIO/A0 40 kHz sobre ADC8/1.860.465 S/s, FFT16384 y 710 kHz sin retune. WAV, Synth y Scan no se solicitaron.

| Corrida | Hold RADIO | ACK raw / decode | Raw máx. | Decode máx. | Gap CHUNK host máx. | Margen RADIO | Cola pico | Exposición |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 120,0462 s | 10.025 / 10.025 | 34,8195 ms | 12,0172 ms | 136,6542 ms | 12,1945 % | 5/16 | 0 % |
| r2 | 120,0602 s | 10.028 / 10.028 | 47,5478 ms | 13,4263 ms | 114,8084 ms | 12,1977 % | 4/16 | 0 % |
| r3 | 120,0764 s | 10.031 / 10.031 | 39,6682 ms | 9,7235 ms | 119,9572 ms | 12,0346 % | 4/16 | 96,1538 % |

`pending_timeout=0` en las tres, sin ACK pendiente al cerrar. El campo legacy `headroom_pass` permaneció false en todas. r1/r2 no califican exposición visible; r3 sí supera el umbral de exposición del 90 %, pero eso por sí solo no demuestra FPS visibles, aceptación analógica/acústica ni que el fallo previo esté corregido. Los ensayos no fuerzan una carga visual equivalente y los timers pueden afectar los tiempos.

| Recuperación de snapshot V20 | Duración | Muestras | Pérdidas / fatales |
|---|---:|---:|---:|
| r1 | 10,0227 s | 313.344 | 0 / 0 |
| r2 | 10,0235 s | 313.344 | 0 / 0 |
| r3 | 10,0236 s | 313.344 | 0 / 0 |

Cada corrida restauró la configuración V20 inicial y verificó identidad, recibo de trabajo e informe sellado sin cambios. El snapshot inicial tenía generador OFF y así quedó restaurado. Comprobación final independiente: V20 activa con la pareja 52f933bd…/bf6893f5…, lock disponible y sin procesos de prueba GUI/receptor remanentes. V19 continuó sólo como respaldo; no se inició.

Los contadores de servicio se conservan completos por corrida en el resumen. Abarcan arranque, hold y recuperación; no convertir sus recuentos en duración bloqueada. La cantidad de `pcm_pending` fue 9.411/9.665/16.571 y la de `credits` 221.278/224.040/200.016. Son observaciones de caminos del host, sin diagnóstico causal ni ajuste aplicado a partir de ellas.

- [Resumen JSON 3×120 s](../diagnosticos/resultados_v20/v20_service_radio120_campaign_20261101_211008_summary.json).
- [r1: informe y evidencia](../diagnosticos/resultados_v20/v20_service_radio120_campaign_20261101_211008_r1/report.json).
- [r2: informe y evidencia](../diagnosticos/resultados_v20/v20_service_radio120_campaign_20261101_211008_r2/report.json).
- [r3: informe y evidencia](../diagnosticos/resultados_v20/v20_service_radio120_campaign_20261101_211008_r3/report.json).
- [Comprobación final instalada](../diagnosticos/resultados_v20/v20_service_radio120_campaign_20261101_211008_final_state.json).

Esta campaña amplía la evidencia funcional sostenida de la base V20 activa; no promueve tasas públicas ni demuestra un arreglo causal. La aceptación visible sostenida, analógica/acústica y una comparación de carga equivalente siguen separadas. No se ejecutaron nuevos tests locales ni cambios de funciones durante la campaña física.

## Continuación: transiciones WAV y Synth

El 2/11 se amplió sólo el wrapper para solicitar WAV/Synth y se corrigió el reloj de ensayo Synth. Dos repeticiones RADIO60→WAV sintético500Hz→Synth20 pasaron función/restauración. ADC cambia a40kdual para WAV/Synth; DAC RADIO/WAV40k y Synth20k. r2 conserva1 correlación ACK decode pendiente, sin inferir pérdida. Ver [transiciones y límites](V20_TRANSICIONES_AUDIO_20261102.md); no ampliar estas pasadas a música real, estabilidad prolongada ni aceptación analógica.
