# Carga conjunta de candidatos FS V17 — 20/10/2026

Resultado: ADC14/909,091 kS/s yADC16CH1/145,455 kS/s pasaron el screening conjunto. Los incrementos de8/10 bits no se aceptan para carga conjunta. Las tasas públicas siguen intactas.

## Matriz y alcance

Audio demodulado de la entrada real CH1; salidaA0 a40 kHz. Por finalista: ventana60 s RADIO→A0 conFFT 65536 y CH1+RADIO,60 s FILTER→A0 con rechazo50 Hz y CH1+FILTER enFFT, y30 s temporal con CH1+RADIO+FILTER y FILTER→A0. Cambios de volumen y resintonía incluidos. Cada caso usa procesoQt/Cocoa propio; un único dueñoQ conserva el bloqueo durante la campaña. No se generaron capturas de pantalla.

Las duraciones son ventanas de la cadena desde la creación de la fuente: incluyen prebuffer y arranqueDAC; los informes guardan los contadores reales played/accepted. No equivalen a calidad analógica, escucha o aceptación conjunta prolongada. Los eventosPaint se cuentan en el viewport realmente visible; no son un contador de cuadros con datos nuevos.

## Resultados

| Bits | Candidato kS/s | Entrada/vista | Ventana s | Resultado | Margen envío | Cola pico | Paint/s vista activa |
|---|---:|---|---:|---|---:|---:|---:|
| 10 | 1290.323 | RADIO / FFT | 60.00 | Pasa integridad/audio, sin holgura | 7.15% | 4 | 19.62 |
| 10 | 1290.323 | FILTER / FFT | 59.97 | Corte de flujo | 7.39% | 4 | 19.38 |
| 8 | 1632.653 | RADIO / FFT | 40.17 | Corte de flujo | 14.45% | 8 | 18.82 |
| 14 | 909.091 | RADIO / FFT | 60.00 | Pasa con holgura | 15.15% | 3 | 19.75 |
| 14 | 909.091 | FILTER / FFT | 60.00 | Pasa con holgura | 14.96% | 3 | 19.58 |
| 14 | 909.091 | FILTER / Temporal | 30.00 | Pasa con holgura | 15.25% | 2 | 62.13 |
| 16 | 145.455 | RADIO / FFT | 60.00 | Pasa con holgura | 77.85% | 1 | 19.48 |
| 16 | 145.455 | FILTER / FFT | 60.00 | Pasa con holgura | 77.85% | 1 | 19.60 |
| 16 | 145.455 | FILTER / Temporal | 30.00 | Pasa con holgura | 77.82% | 1 | 62.46 |

La exposición fue100% en estos casos. ADC14 pasó con14,96–15,25% de margen, colas3/3/2 y reserva host mínima5654 muestras (141,35 ms). ADC16 pasó con77,82–77,85%, cola1 y reserva mínima15985 muestras (399,63 ms). Son métricas de estas ventanas, no garantía global.

### Fallos conservados

- **ADC8/1,633 MS/s:** cierre a40,17 s. El frame rechazado tieneCRC correcto, dropped1, fatal0 y cola pico8/8. La reserva de audio host todavía era al menos8584 muestras; no se atribuye a falta de audio ni a GUI atrasada. [Frame y métricas](../experimentos/fs_max_all_bits_v17/joint_20261020_094801/adc8_failure_frame_summary.json). Los otros casos de esa resolución se omitieron tras el fallo; no se reintentó la misma prueba.
- **ADC10/1,290 MS/s:** RADIO→A0 pasó60 s con margen7,15% y cola4. FILTER→A0 cerró el flujo cerca de60 s; el error quedó guardado, incluyendo el fallo de regreso a baja tasa. No se determina una causa inferior específica sin una trama rechazada preservada. No se reintentó ni se acepta el incremento para uso conjunto.
- **ADC12/1,096 MS/s:** excluido de esta matriz por dropped1 en la calificación aislada anterior.

No hay un A/B conjunto contra los máximos de producción en esta campaña: se rechazan los candidatos observados, sin atribuir causalmente todo el fallo al incremento deFs.

### Por qué perdió un nodo ADC8

El productor intenta reservar una posición sin esperar: si no hay posiciones libres, incrementa `dropped_nodes`. El frame conservado acredita ese caso: CRC correcto, un nodo perdido, ningún fatal y pico8 en una cola de8. No fue una comprobación falsa del decodificador.

A1,632653MS/s, cada nodo de3456 muestras llega cada2,1168ms. El último ciclo de consumidor informado duró2,316875ms: abarca desde tomar el nodo hasta liberarlo, incluyendo su transmisión física y trabajo de control. Ese ciclo superó el período de llegada. El margen medio14,45% no limita las demoras puntuales; varias demoras pueden acumular cola aunque el promedio sea favorable. Las ocho posiciones representan unos16,93ms nominales, sin demostrar una única pausa de esa duración.

El anillo reciente del host también registra operaciones read/decode de hasta16,38/15,97ms. Pueden incluir desplanificación del hilo; no son medidas exclusivas de CPU ni prueban causalidad con el desborde MCU. La reserva de audio host era al menos214,6ms y no apareció GUI atrasada. La causa confirmada es la falta de posiciones de adquisición; queda por aislar qué demora del consumidor/transporte la inició. [Cálculos y eventos](../experimentos/fs_max_all_bits_v17/joint_20261020_094801/adc8_timing_analysis.json).

### Validación prolongada de finalistas

El modo privado `joint.py --sustained` prueba únicamente14/16 después de comprobar su screening restaurado. Por resolución ejecuta FILTER→A0 a40kHz con FFT65536 visible: una ventana60s y tres ventanas independientes120s, cada una en un proceso GUI separado y con control a baja tasa entre etapas. Conserva el binario calificado, verifica SHA del relay y restaura producción al terminar. No repite los fallos8/10 ni habilita tasas públicas. RADIO directo y temporal conservan por ahora sólo su evidencia corta anterior.

## Correcciones del diagnóstico

La primera versión extendió la guarda de tasa sólo en el panel; la comprobación de feed seguía bloqueando8 bits antes dePlay. Esos intentos quedaron conservados como bloqueados y se excluyen de la aceptación. La corrección temporal abarca ambas referencias sólo para el perfil privado exacto; un test alimenta la fuente real y verifica que el perfil vecino siga bloqueado y que producción se restaure al salir del contexto.

El primer chequeo visual exigía pintar temporal mientras FFT ocupaba el stack. Se conservan los informes originales y la revisión aplica el umbral a la vista activa, con evidenciaPaint/exposición real. Temporal se midió aparte. El casoADC10/RADIO se revisa como paso de audio/FFT, pero no de holgura; no se lo repite ni se oculta el posterior falloFILTER.

Para el candidatoADC14 se usó la claseHighRateRadioDacSource ya vigente en producción para851 kS/s, extendida sólo durante el ensayo privado a909 kS/s. Se conservan burst16 y correlación fuera del lock; no se cambió la clase de producción ni se desactivó la protección de lazo.

## Restauración y continuidad

Ambos informes padre verifican rollback de fuentesMCU/firmware, relay/montajes/entorno/políticaCPU y ADC8/632411SPI dual con generadorOFF y todos sus campos previos. SHA256 original antes/después: `96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9`. La última recuperación midió6321024 muestras en10 s, dropped=fatal=0. Tras el fallo8, el único dueño reinició el mismo candidato a baja carga, verificó su identidad y continuó otras resoluciones; no repitió la etapa fallida.

Candidato físico compartido con la calificación aislada: `cc46e4f798a39edfb8e5bd2db8ecd510dd40fee3f10e89c69978de4191156223`. Los límites públicos y los máximos publicados no se alteraron.

## Evidencia y siguiente bloque

[Resumen auditable](../experimentos/fs_max_all_bits_v17/joint_summary.json) · [Primer intento](../experimentos/fs_max_all_bits_v17/joint_20261020_094007/report.json) · [Continuación](../experimentos/fs_max_all_bits_v17/joint_20261020_094801/report.json) · [Calificación aislada](EXPLORACION_FS_MAXIMA_V17.md).

El screening dejó pendiente completar estabilidad conjunta prolongada de14/16 con el mismo binario/política; el resultado posterior se detalla debajo. Para8/10, investigar colas y cierres con controles comparables antes de intentar nuevos perfiles. La precisión analógica, escucha,Scan/US y otros modos de análisis quedan fuera de este screening.

## Campaña prolongada · 20/10/2026

FILTER→A0 a40kHz con FFT65536, mismo firmware candidato y mismos hashes del host que el screening. Se conservan [primera parte](../experimentos/fs_max_all_bits_v17/joint_20261020_101254/report.json) y [continuación](../experimentos/fs_max_all_bits_v17/joint_20261020_102101/report.json). La primera secuencia se detuvo por exposición insuficiente, sin fallos de audio; la continuación ejecutó únicamente etapas no intentadas, después del rollback verificado. El usuario confirmó que había quitado la ventana. No se repitieron etapas ni se descartaron fallos reales.

| Bits / tasa | Etapa | Audio/integridad | Margen envío | Cola pico | Exposición |
|---|---|---|---:|---:|---:|
| 14 /909,091kS/s | 60s | Pasa | 14,97% | 3 | 3,1% |
| 14 /909,091kS/s | 120s número1 | Pasa | 14,64% | 3 | 100% |
| 14 /909,091kS/s | 120s número2 | Pasa | 14,71% | 3 | 100% |
| 14 /909,091kS/s | 120s número3 | **Cierre antes de completar** | 14,29% | **4** | 100% |
| 16CH1 /145,455kS/s | 60s | Pasa | 77,92% | 1 | 100% |
| 16CH1 /145,455kS/s | 120s número1 | Pasa | 77,88% | 1 | 63,6% |
| 16CH1 /145,455kS/s | 120s número2 | Pasa | 77,89% | 1 | 100% |
| 16CH1 /145,455kS/s | 120s número3 | Pasa | 77,90% | 1 | 100% |

**ADC14 no se acepta:** en la última etapa el Q cerró el flujo cerca de71,55s de ventana; A0 había reproducido2825280 muestras. El campo de progreso elapsed_audio_seconds quedó en60,05s porque sólo se actualiza periódicamente: no usarlo como instante exacto de fallo. La trama rechazada tiene CRC correcto, dropped1, fatal0 y cola4/4. Último ciclo consumidor7,2381ms frente a período de nodo6,5472ms. Reserva host4965 muestras (124,125ms), sin fuente_error ni GUI atrasada. [Trama y métricas](../experimentos/fs_max_all_bits_v17/joint_20261020_102101/adc14_failure_frame_summary.json). Además, una corrida aprobada había bajado a975 muestras de reserva host (24,375ms). No repetir el fallo para seleccionar un resultado favorable.

**ADC16 pasa estabilidad de audio/transporte60s+3×120s** en esta carga, con margen77,88–77,92%, cola1 y reserva host mínima17325 muestras (433,125ms). Una corrida120s estuvo parcialmente oculta; no se acredita por eso una calificación visual completa60s+3×120s. Las dos corridas120s totalmente visibles también pasaron el dibujo. Quedan fuera escucha, precisión analógica, Scan/US y otros modos. Los límites públicos no se modificaron.

El auditor `audit_sustained.py` verifica rollback, identidad, fuentes, SHA real del relay y hashes del host; conserva todos los casos, rechaza etapas duplicadas y separa audio, visibilidad y holgura. [Resumen](../experimentos/fs_max_all_bits_v17/sustained_summary.json).

Ambas partes de la campaña prolongada verificaron restauración exacta. La última recuperó firmware `96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9`, ADC8/632411SPI dual y todos los campos previos del generadorOFF; control10s con6321024 muestras y dropped=fatal=0.
