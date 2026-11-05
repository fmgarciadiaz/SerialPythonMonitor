# V20: RADIO → WAV sintético → Synth, 2/11/2026

**Dos repeticiones funcionales y de restauración PASS**, después de corregir únicamente el reloj del ensayo Synth. V20 queda activa; V19 no se inició. Sol implementó las herramientas y fue único propietario Q durante las mediciones; root revisó el plan y no operó Q en ese intervalo.

## Qué pasó en el primer intento

El [intento anterior](../diagnosticos/resultados_v20/v20_audio_transition_campaign_20261101_213154_r1/report.json) pasó RADIO 60,0151 s y el WAV, pero falló `fm_playing`, `fm_progress` y `fm_stop_confirmed`. Se había solicitado Synth a los 72,3454 s y detenido a los 82,7386 s: sólo 10,3932 s desde la solicitud. La interfaz mostraba fuente activa, pero no hubo un nuevo BEGIN/PLAY ni ACK de sesión Synth. El último estado seguía siendo DONE del WAV anterior. Se detuvo la tanda sin repetir a ciegas; la configuración V20 se recuperó durante 10,0238 s con 313.344 muestras y cero pérdidas/fatales.

La preparación del producto es asíncrona: no emite BEGIN hasta que termina el Future y STOP cancela la solicitud pendiente. Las pruebas con Future controlado verificaron ese contrato sin modificarlo. Una [medición offline](../diagnosticos/resultados_v20/v20_transition_synth_analysis_20261102/offline_prepare.json) de spawn/preparación real tardó **14,7356 s** y después renderizó 480 muestras con 20 voces. Es otro proceso: **no mide cuánto tardó la preparación del intento fallido**. Reproduce una preparación legítima más larga que la ventana del ensayo anterior, coherente con la hipótesis del plazo insuficiente, sin probar su causa exacta.

## Cambio acotado a herramientas

`probe_working_v20_gui.py` admite `--wav`, `--fm` y `--voices 1..20`; conserva RADIO solo por defecto. El helper `synth_transition_scenario_v20.py` espera PLAY de una sesión nueva durante hasta 120 s, ignora ACK de RADIO/WAV previos y cuenta 5 s de hold **desde el PLAY confirmado**. Después solicita STOP una sola vez y exige confirmación en 10 s. Los ACK tardíos no pueden eludir el deadline y la GUI no cierra por el viejo reloj mientras la transición esté pendiente. Error o timeout sigue el cierre restaurador existente.

Se guardan snapshots escalares de preparación y metadatos del renderer, incluida cuenta remota de voces. No se añaden polls ni datos RF. No se cambiaron el producto de audio, sus timeouts, QoS, guard 88, buffers, tasas públicas, firmware, relay ni recibos de aceptación.

**14 tests focalizados PASS**: preparación demorada, ACK viejo/tardío, hold desde sesión nueva, STOP único/confirmado, deadlines y cancelación de BEGIN pendiente, más flags, diagnóstico y restauración del wrapper. Fuentes de escenario archivadas por hash en ambos informes y verificadas iguales después de la campaña.

## Matriz realmente medida

| Tramo | Adquisición ADC | Salida DAC | Alcance |
|---|---|---|---|
| RADIO/A0 | 8 bits, CH1, 1.860.465 S/s | 40 kHz | Hold confirmado de 60 s |
| WAV | 8 bits, dual, 40.000 S/s | 40 kHz observado en ACK | Seno temporal de 500 Hz; entrada PCM16 mono de 20 kHz, 80.000 muestras, 4 s; salida con 160.000 muestras reproducidas |
| Synth | 8 bits, dual, 40.000 S/s | **20 kHz observado en ACK** | 20 notas configuradas, pico remoto de 20 voces renderizadas y hold de al menos 5 s desde PLAY |

El WAV es sintético; no se probó Imperial, Vivaldi ni un archivo de música del usuario. WAV/Synth son tramos cortos y posteriores a RADIO: no es estabilidad larga, música estéreo, audio a 50 kHz ni Synth a 40 kHz con 20 voces. El pico de voces observado no demuestra 20 voces sostenidas durante todo el hold ni aceptación acústica.

| Medición | r1 | r2 |
|---|---:|---:|
| Hold RADIO | 60,0011 s | 60,0141 s |
| Solicitud Synth → PLAY nuevo | 2,5958 s | 1,8891 s |
| Hold Synth confirmado | 5,0640 s | 5,0062 s |
| STOP Synth → confirmación | 6,8461 ms | 16,7764 ms |
| Pico remoto de voces | 20 | 20 |
| ACK raw correlacionados / entrada al decoder | 5.582 / 5.582 | **5.578 / 5.577** |
| Correlaciones decode pendientes al cerrar | 0 | **1** |
| ACK raw máximo | 17,2893 ms | 18,7551 ms |
| Demora máxima hasta entrada al decoder | 9,7621 ms | 8,3370 ms |
| Gap CHUNK host máximo | 77,0987 ms | 78,4481 ms |
| `pending_timeout` | 0 | 0 |
| Recuperación de snapshot V20 | 10,0211 s | 10,0210 s |
| Muestras de recuperación | 313.344 | 313.344 |
| Pérdidas / fatales en recuperación | 0 / 0 | 0 / 0 |
| Exposición periódica GUI | 100 % | 100 % |

r2 conserva una correlación diagnóstica incompleta: un ACK observado raw no quedó correlacionado con entrada al manejo antes del cierre. **No se infiere pérdida de transporte ni se repitió hardware por ese contador.** PLAY, progreso y STOP de las tres fases, hold Synth, cierre y restauración sí se confirmaron. La campaña se presenta como dos PASS funcionales/restauración, sin afirmar que todo el diagnóstico ACK quedó completo.

Durante RADIO, margen medio 12,1441 % / 12,2226 %, cola pico 4/16 en ambas y `headroom_pass` legacy false. Los contadores de motivos abarcan todo el ciclo, incluidos arranque y recuperación; no equivalen a duración bloqueada ni prueban una causa del fallo anterior. Exposición 100 % no demuestra FPS visibles ni aceptación analógica/acústica.

## Estado final y evidencia

Ambas corridas recuperaron el snapshot inicial V20, con generador OFF. Identidad antes/después, recibo de trabajo e informe sellado de activación quedaron iguales. Verificación final instalada: pareja V20 52f933bd…/bf6893f5… activa, lock disponible y sin procesos GUI/receptor de prueba remanentes. Sol liberó propiedad Q; no hubo despliegue ni retorno a V19.

- [Resumen JSON de las dos repeticiones](../diagnosticos/resultados_v20/v20_audio_transition_confirmed_campaign_20261102_083132_summary.json).
- [r1: informe y fases](../diagnosticos/resultados_v20/v20_audio_transition_confirmed_campaign_20261102_083132_r1/report.json).
- [r2: informe y fases](../diagnosticos/resultados_v20/v20_audio_transition_confirmed_campaign_20261102_083132_r2/report.json).
- [Comprobación final instalada](../diagnosticos/resultados_v20/v20_audio_transition_confirmed_campaign_20261102_083132_final_state.json).

La evidencia amplía las transiciones funcionales de V20; no promueve tasas públicas ni declara resuelto un problema causal del transporte/audio. La estabilidad prolongada de WAV/Synth, archivos reales, otras tasas y aceptación analógica/acústica quedan fuera de esta tanda.
