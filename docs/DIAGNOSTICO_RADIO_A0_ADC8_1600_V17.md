# Corte RADIO/A0 · ADC8 a 1,6 MS/s · 19/10/2026

## Incidente real

En `diagnosticos/resultados_v17/radio_a0_stops.jsonl`, entrada del 19/10/2026 a las 18:39:17 −03:00:

- ADC8/1600000, entrada de salida RADIO.
- DAC state=4 (UNDERRUN), reason=2, played=5988480, accepted=5988960.
- Al registrar el aviso, el host tenía 8881 muestras pendientes; mínimo observado 1141.
- Once cambios de sintonía; fuente sin error, detector de lazo con cero hits.

La diferencia accepted−played es 480 muestras. El registro se toma al atender el aviso: no describe por sí solo la reserva exacta en el instante físico del fallo. Tampoco distingue una demora DSP de una pausa en servicio/envío. No hay traza suficiente para atribuir una causa única. El registro original no incluye FS de salida; no convertir sus contadores en segundos asumiendo una tasa no registrada.

## Primer control sin cambios de producción

`diagnosticos/resultados_v17/generador_radio_20261019_184029/report.json`: Python 3.10, Qt Cocoa, ADC8/1,6 MS/s, RADIO→A0 a 40 kHz, banda RF 8 kHz. DSP precalentado, un cambio de sintonía y volumen, 120 s solicitados: sin corte, errores ADC ni error de fuente. No valida el arranque frío ni reproduce once resintonías.

Cola ADC pico 5/8: no declarar aceptación de holgura. Máximas de transporte del ensayo: lectura 47,89 ms, decodificación 33,16 ms, envío 32,09 ms, ACK 79,89 ms. En los últimos ~66,22 s del ring: hueco de chunks 92,36 ms, alimentación DSP 83,07 ms, mínimo accepted−played en estados PLAYING 9600 muestras. Esos mínimos/máximos del ring no cubren toda la sesión.

Q restaurado a la configuración previa exacta, ADC8/1,6 MS/s y generador OFF. Firmware idéntico antes/después, SHA256 `96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9`; recuperación posterior 10 s, 15993504 muestras, dropped/fatal=0.

## Instrumentación incorporada

La fuente RADIO ahora conserva un ring máximo de 64 episodios anómalos, máximos de hueco DSP/chunks, contadores de espera de audio y demoras de transporte. El informe de Stop incluye la tasa de salida y edad del último feed/chunk. Lectura/decodificación se añaden al ring si tardan al menos 20 ms; huecos DSP/chunks desde 50 ms. Los umbrales son de registro, no disparan ni ocultan fallos.

No se modificaron reservas, créditos, ráfagas, reloj, firmware ni reinicio automático. El registro se escribe al detenerse, no se vuelcan datos de audio ni ADC por evento. Pasaron 22 pruebas locales de fuente RADIO, trazas, servicio por tramas, créditos y detector de lazo.

El runner admite `--retune-stress`: alterna la sintonía cada 10 s. Se utiliza para contrastar sesiones con resintonías repetidas, sin presentarlas como reproducción exacta de la sesión original.

La causa y la corrección funcional siguen pendientes; un pase de 120 s no elimina el fallo real.

## Segundo control con el Python del usuario

`diagnosticos/resultados_v17/generador_radio_20261019_184313/report.json`: Python 3.13, Qt Cocoa, ADC8/1,6 MS/s, A0 40 kHz, banda 8 kHz y sintonía alternada cada 10 s: 120 s sin corte, 10 resintonías de la fuente, sin error de fuente ni dropped/fatal ADC. Cola pico 6/8; no se declara holgura. Instrumentación acotada de la fuente incorporada; la traza completa del runner aporta transporte. La versión cargada del runner aún no delegaba su override de transporte al observador de fuente, por lo que los episodios read/decode se analizan en transport_recent, no en la fuente. Esto ya quedó corregido para próximas corridas.

Configuración previa restaurada, ADC8/1,6 MS/s y generador OFF, firmware idéntico. Recuperación 10 s: 15991776 muestras, dropped/fatal=0. Los dos pases no identifican la causa ni constituyen una corrección del corte real. [Resumen de ambos](../diagnosticos/resultados_v17/radio_chain_audit/adc8_1600_underrun_followup_20261019.json).

Reiniciar V17 para cargar el registro ampliado en una sesión normal. No hace falta Preparar Q ni cargar firmware.
