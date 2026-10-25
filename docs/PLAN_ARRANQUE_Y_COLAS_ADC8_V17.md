# Arranque y colas ADC8 · plan revisado con Astra

## Problemas separados

El gráfico puede esperar por preparación deliberada, confirmación de configuración, arranque DSP o entrega/render. La pérdida de nodos a tasa elevada es otro problema: un promedio de envío favorable no limita las demoras puntuales. No atribuir ambos a una única causa sin medición.

## Bloque1 · instrumentación por Sol

Traza opcional, acotada y monotónica por solicitud. Diferenciar arranque con reinicio del Q, conexión al stack activo y cambio de perfil en vivo. Medir las operaciones existentes sin consultas administrativas adicionales ni escritura por frame.

Conservar las guardas actuales: asentamiento5s de autoload tras reinicio, preparación ADC14/40k→ADC8/1428571→2s de bombeo→ADC8/1600000, y transición150ms entre otros perfiles rápidos. Los10s de ACK GUI son un timeout, no una espera fija. Registrar también configuración idéntica/no-op.

Primer lote entregado a GUI no equivale a dibujo visible. STOP, SINGLE, trigger y exposición de ventana se investigan por separado; no acreditar primer Paint con datos nuevos contando un Paint vacío.

Validar localmente que la traza apagada preserve el comportamiento, que solicitudes/lotes obsoletos no completen la nueva medición y que las guardas/orden de callbacks sigan intactos. Revisar cambios antes de hardware.

## Bloque2 · medición física de arranque

Un único dueño del Q; comprobar que no haya monitor abierto. Medir frío y cambio activo hacia1,6MS/s, con un perfil inferior de control. Conservar todas las trazas y tiempos hasta primera entrega; registrar visibilidad si se mide pantalla. No reducir esperas en esta primera medición. Restaurar configuración y verificar integridad al terminar.

## Bloque3 · A/B de transporte

Comparar1,6 y1,632653MS/s primero dentro del mismo binario candidato y relay, con igual políticaCPU, DSP y GUI. El control con firmware original se informa aparte. Escalones: adquisición; RADIO/FFT; RADIO→A0 a40kHz. Fijar condiciones de parada antes de iniciar; conservar fallos y no repetir buscando un pase.

Medir cola MCU y ciclo consumidor, SPI/relay, pausas host read/decode y pendientes DSP/GUI. No sincronizar causalmente relojes MCU/host sólo por sus timestamps. Una operación read/decode lenta puede incluir desplanificación; no es coste puro de CPU.

Optimizar únicamente el tramo identificado; no agrandar colas ni reducir guardas como sustituto de evidencia. Un candidato final requiere60s+3×120s, integridad, margen medio≥10%, cola pico<4 y slack positivo, además de restauración verificada. La aceptación analógica y de dibujo se informa aparte.

[Resultados anteriores](CARGA_CONJUNTA_FS_V17.md). Tasas públicas sin cambios durante esta investigación.

## Cierre del bloque1

Sol implementó la traza y el coordinador revisó los cambios.41tests de arranque, ADC1600, pipeline y lotes acotados pasan. [Activación y snapshot](DIAGNOSTICO_ARRANQUE_V17.md). La instrumentación llega hasta primera entrega GUI; no mide primer Paint ni el tiempo previo del debounce/cola de solicitudes. No se operó el Q ni se redujeron las esperas. El bloque2 queda pendiente de medición física.

## Avance bloque2 · stack activo medido

Prueba física sin reinicio: control1403508 entregó en69,8ms;1600000 en2064,9ms, con2000,13ms de espera programada. Sin errores en ventanas10s; restauración exacta y10s de integridad final. [Informe y límites](DIAGNOSTICO_ARRANQUE_V17.md). Quedan arranque frío y otras cargas; siguiente candidato sólo modificará la duración de asentamiento en un ensayo privado.

## Cierre de candidato e incorporación

Tres entradas120s conRADIO y tres ventanas120s conRADIO→A0 pasaron integridad/audio. Cola3 sinA0 y5 conA0: no se acepta holgura estricta. Se incorporó0,5s exclusivamente para cambio con modo activo; primeraentrada2s y guardade5s conservadas.41tests locales pasan. [Evidencia](DIAGNOSTICO_ARRANQUE_V17.md). Sigue pendiente el A/B de transporte y arranque frío; no aumentarFs.

## A/B ADC solo · primera comparación20/10

Runner aislado `experimentos/fs_max_all_bits_v17/adc8_ab.py`, candidato firmwarecc46 sin cambios y relay certificado. Igualados nodo3456, cola8, SPI40/WORD, FIFO10, CPU2performance y preparación privada del host: ambos usan14/40000→8/1428571→0,5s→objetivo. No se modifican perfiles JSON públicos ni fuentes MCU certificadas. Tests locales verifican perfiles/copias y compilan los contratos C de transporte.

Las dos ventanas60s pasaron integridad:1,6MS/s95944608muestras, cola pico2;1,632653MS/s97905024muestras, cola pico4. Por lo tanto la tasa mayor sigue sin holgura estricta incluso sin RADIO/A0. Es una pareja de corridas, sin inversión de orden ni garantía estadística. No promueve tasas ni sustituye el fallo de nodo previo con carga conjunta.

El promedio de envío heredado muestrea estados porpump y puede ponderar repetidos del mismo nodo; no usarlo como aceptación final de margen. Los picos de cola sí se conservan. El próximo bloque debe deduplicar por producción y medir las colas/latencias al sumar RADIO/FFT antes de cambiar el consumidor. No atribuir aún la demora a Linux, TCP o GIL.

[Informe físico](../experimentos/fs_max_all_bits_v17/adc8_ab_20261020_150826/report.json).

Restauración final verificada: identidad original antes/después igual, ajustes ADC/generador previos exactos y control10s con399360 muestras, dropped=fatal=0.

## RADIO/FFT · comparación de adquisición y DSP20/10

[Revisión de ambas corridas](../experimentos/fs_max_all_bits_v17/adc8_radio_fft_review.json). Se conserva la corrida1600000 aunque no aprobó visibilidad; sólo se midió después la tasa pendiente1632653, sin repetir la anterior. Ambas usan el mismo firmwarecc46, relay certificado, nodo3456/cola8 y preparación igualada. La versión del diagnóstico cambió entre corridas para separar integridad de visibilidad y registrar la sintonía efectiva; los informes conservan ambos hashes del child. No se cambiaron algoritmos DSP ni fuentes MCU.

| Tasa MS/s | Ventana s | Muestras entregadas | Cola pico | Margen medio observado | Mayor ciclo consumidor observado | Exposición FFT |
|---|---:|---:|---:|---:|---:|---:|
| 1,600000 | 60,002 | 96066432 | 3 | 23,69% | 2,768ms | 71,2% |
| 1,632653 | 60,000 | 98065728 | 5 | 22,09% | 3,384ms | 38,9% |

Ambas pasaron adquisición y procesamiento de audio, sin pérdidas ni errores. **No** pasan aceptación visual completa; además, la exposición diferente impide tratarlas como una comparación de carga gráfica idéntica. El promedio usa observaciones únicas(epoch,produced), no un censo completo de nodos. Los picos de cola y duración se conservan incluso en estados repetidos. La tasa mayor sigue sin holgura estricta y no se incorpora.

Pausas host máximas read/decode:74,08/83,55ms a1,6 y121,83/61,39ms a1,633. Son duraciones observadas que pueden incluir desplanificación: no prueban dónde nació el atraso del consumidor MCU. Estas ventanas sin pérdidas tampoco eliminan el fallo anterior conA0.

La sintonía solicitada fue20kHz, pero la preparación base40kHz la limita. El segundo diagnóstico registra el valor DSP efectivo15999Hz y banda8000Hz; el primero aún no guardaba ese campo. No afirmar20kHz efectivos. A0 permanecióOFF y ambos produjeron unos2,4millones de muestras de audio DSP.

Ambas campañas restauraron firmware original y ajustes previos exactos y pasaron10s de integridad final. Siguiente: instrumentar la esperaREADY/SPI y el trabajo de control en un relay aislado, conservando tiempos acotados y sin escritura por trama, antes de atribuir el atraso a un componente o subirFs.

## Relay instrumentado READY/SPI · 20/10

[Informe](../experimentos/adc8_relay_timing_v17/adc8_timing_20261020_154456/report.json) · [Resumen de histogramas](../experimentos/adc8_relay_timing_v17/adc8_timing_20261020_154456/review.json) · [Experimento](../experimentos/adc8_relay_timing_v17/README.md).

Copia aislada del relay con histogramas acotados y emisiónJSON sólo en baja/exit. FirmwareMCUcc46 y perfil de transporte conservados; binario relay diferente y hash registrado. Heartbeat original10s intacto. CompilaciónLinux real con-Wall-Wextra-Werror pasó; pruebas locales2OK. Calibración de pares de reloj enQ:41,09ns medios,53ns máximo; esto no mide el costo completo de toda la instrumentación.

Las dos ventanasADC-only60s pasaron sin pérdida. ColaMCU pico4 a1,6MS/s y3 a1,633MS/s: orden diferente de la pareja anterior2/4. Una pareja no establece una relación determinista ni atribuye la variación a la instrumentación. No se incorporan tasas nuevas.

| Etapa | Media µs1,6 | Máximo µs1,6 | Media µs1,633 | Máximo µs1,633 |
|---|---:|---:|---:|---:|
| READY | 172,23 | 3129,85 | 168,87 | 3060,58 |
| Preparación/política comando | 0,33 | 47,71 | 0,32 | 70,47 |
| ioctlSPI | 278,90 | 470,52 | 279,46 | 530,99 |
| Validador/política posterior | 7,49 | 536,88 | 6,97 | 493,80 |
| Socket/control/envío | 73,51 | 796,98 | 65,95 | 349,58 |
| Chequeo/heartbeat | 0,38 | 55,42 | 0,28 | 72,03 |
| Ciclo completo | 539,91 | 3918,61 | 529,04 | 4104,23 |

113229 y115533 ciclos completos registrados respectivamente; colas de envíoTCP observadas en0. Los histogramas cubren el perfil activo, incluida su entrada/salida, no exactamente la ventanaADC60s. READY tuvo77/50 esperas mayores a1ms; los máximos por etapa no necesariamente pertenecen al mismo ciclo. READY incluye espera legítima de producción y posible atención tardía del host: **no prueba todavía que el MCU o Linux sean culpables**. El siguiente experimento debe conservar la marca de tiempo del flancoGPIO y separar recv/accept/send antes de optimizar.

Restauración exacta de firmware/relay/entorno/política y ajustes previos, identidad antes/después igual y control10s sin dropped/fatal. El relay instrumentado no queda instalado como producción.

## READY con timestamp de kernel · 20/10

[Informe](../experimentos/adc8_relay_edge_v17/adc8_edge_20261020_155538/report.json) · [Eventos correlacionados](../experimentos/adc8_relay_edge_v17/adc8_edge_20261020_155538/review.json).

Dos ventanasADC-only60s pasaron integridad; firmware/relay/configuración originales restaurados y10s finales sinpérdidas. La copia del verificador sólo conserva timestamp de flancos ya aceptados: no cambia guardas de secuencia ni antigüedad. Marcas GPIO de kernel y CLOCK_MONOTONIC comparten dominio; no son una medida externa del flanco físico ni de latenciaIRQ previa al timestamp.

**La interpretación anterior de máximosREADY queda acotada:** los mayores~2,86ms de ambas tasas terminaron en paqueteskind7 de cambio de configuración; los~2,06–2,09ms correspondían al primer nodo. Las otras esperas largas guardadas~1,03ms tenían cola actual1 y recepción13–27µs después del timestampkernel. No acreditan un atasco de atención sostenido. Los histogramas incluían entrada/salida del perfil; no asumir que sus máximos eran tráfico estacionario.

La edad máxima del eventoREADY al atenderlo fue~0,59/0,64ms. No se guardaron los ocho máximos de esa edad, sino de espera total: no son las mismas muestras. Un flanco ya encolado puede esperar durante trabajo posterior alSPI antes de comenzar la siguiente espera.

recv/accept/send quedan separados. `accept` se consulta por trama aun con cliente activo: Astra recomienda probar cadencia1frentea8 en una copia nueva, con recepción/envío intactos y aceptación inmediata cuando no hay cliente. El ahorro es una hipótesis; no se incorpora sin medición y restauración.

## Primer candidato de optimización: accept cada8 tramas · 20/10

Revisión Astra: reducir únicamente `accept` redundante con cliente activo en perfiles ADC8CH1 exactos100/98,node3456. Sin cliente y en otros perfiles se conserva la cadencia original. Se mantienenrecv/send, colaTCP, validación de comandos, READY, prioridades y rechazo de conexiones nuevas sin reemplazar la activa. Ocho tramas representan~4,2ms nominales, no un plazo garantizado de reloj.

[Informe de la pareja](../experimentos/adc8_relay_accept_v17/adc8_accept_20261020_160438/report.json) · [Revisión](../experimentos/adc8_relay_accept_v17/adc8_accept_20261020_160438/review.json).

Mismo binario relay (hash real comprobado antes deN8) y MCUcc46; runtimeenv1/8 leído al arrancar. Cada variante reinició a baja carga y tuvo control previo. No se cambió producción. Pruebas locales de cadencia, guardas y cola de envío pasaron; compilaciónLinux real pasó.

| Cadencia accept | Ventana ADC | Resultado | ColaMCU pico | Llamadas / tramas observadas | Tiempo accept por trama |
|---|---|---|---:|---:|---:|
| Cada1 | 60s a1,633MS/s | Sin pérdidas | 6 | 115533/115533 | 21,008µs |
| Cada8 | 60s a1,633MS/s | Sin pérdidas | 3 | 14698/115533 | 6,541µs |

Reducción de tiempo de pared enaccept por trama~68,9%. La media por llamada pasó21,0→51,4µs: por eso se compara el total por trama y no se selecciona la media por llamada. La fracción efectiva0,1272 incluye tramas sin cliente/handoff donde se consulta inmediatamente; el test del flujo activo verifica1/8. El segmento total socket bajó75,07→54,77µs/trama; READY medio aumentó161,23→183,00µs mientras el ciclo total siguió~529µs, coherente con mantener una tasa fija y tener más espera disponible, sin demostrar por sí solo másFs.

Una única pareja no garantiza que el cambio causara toda la diferencia de cola6→3. El promedioMCU heredado aún remuestrea estados; no se usa como calificación final de holgura. FaltaRADIO/FFT, RADIO→A0 y estabilidad60+3×120s del candidato. No incorporar ni aumentar tasas todavía.

Restauración exacta de firmware96685…, relay/montajes/entorno/política y ajustes previos; control10s sin dropped/fatal. Quedó instalado el relay original.

## N8 con RADIO→A0 · calificación60s+3×120s · 20/10

[Informe padre](../experimentos/adc8_relay_accept_v17/radio_qualification_20261020_162658/report.json) · [Revisión de cuatro etapas](../experimentos/adc8_relay_accept_v17/radio_qualification_20261020_162658/review.json).

Candidato relayN8 de hash2253ee67… yMCUcc46 idénticos a la parejaADC anterior. RADIO→A0 a40kHz, fuente ordinaria burst8, FFT65536CH1+RADIO, banda8kHz, cambio de sintonía/volumen y stop; FILTEROFF. Cada etapa usó sesión nueva desde baja tasa, preparación inicial2s conservada y controlADC bajo10s entre etapas. Hash real del relay y firmware verificados. No se cambiaron colas, prioridades, SPI o READY.

| Ventana | Integridad/audio | Cola pico | Margen envío observado | Reserva mínima host | Exposición |
|---|---|---:|---:|---:|---:|
| 60s | Pasa | 4 | 15,28% | 188,675ms | 25,2% |
| 120s número1 | Pasa | 5 | 15,45% | 184,525ms | 15,1% |
| 120s número2 | Pasa | 4 | 15,37% | 231,425ms | 19,4% |
| 120s número3 | Pasa | 6 | 15,36% | 189,825ms | 0% |

**Integridad y alimentación de audio aprobadas en estas ventanas. Holgura estricta no aprobada:** ninguna cola estuvo por debajo de4 en toda su etapa. **Validación visual no aprobada:** la exposición fue insuficiente y la última ventana no tuvoPaint visible. Esta carga gráfica reducida limita además cualquier extrapolación al monitor totalmente visible. No se repiten etapas para seleccionar pases ni se afirma calidad acústica/analógica.

El candidato reduce trabajo medido deaccept, pero la cola3 del primer screeningADC no se sostuvo conA0. No hay controlN1pareadoRADIO/A0 bajo idéntica exposición; no atribuirle causalmente toda diferencia respecto al fallo anterior. No se incorpora el relay ni la tasa1,633MS/s. Siguiente: medir la cola/tiempo de producción de comandosA0 frente a la transmisiónADC y ensayar una mejora aislada; conservar por separado el resultado de integridad alcanzado.

Restauración final exacta de firmware96685…, relay/montajes/entorno/política y ajustes previos. Identidad antes/después igual; control10s399360muestras enADC16/40kHz sin dropped/fatal. Producción quedó instalada, no el candidato.

## Carga visible N8 · fallo de audio conservado20/10

El usuario dejó la ventana visible. Se ejecutó una campaña nueva con igualcandidatoN8/MCUcc46 yRADIO→A040kHz+FFT65536; las corridas ocultas previas permanecen separadas. [Informe](../experimentos/adc8_relay_accept_v17/radio_qualification_20261020_164619/report.json) · [Revisión](../experimentos/adc8_relay_accept_v17/radio_qualification_20261020_164619/review.json).

| Etapa | Resultado | ColaMCU pico | Exposición | PaintFFT/s |
|---|---|---:|---:|---:|
| 60s | Integridad/audio pasan | 7 | 100% | 19,00 |
| 120s número1 | Integridad/audio pasan | 4 | 100% | 19,02 |
| 120s número2 | Integridad/audio pasan | 6 | 100% | 19,14 |
| 120s número3 | **Underrun A0 antes de completar** | 4 | 100% | 18,55 |

El último caso cerró tras41,126s de ventana, WAVestado4/reason2, played1604640 yaccepted1605120. Campo periódicoelapsed_audio_seconds30s no representa el instante exacto. ADCseguía dropped=fatal=0; no hubo cierre de flujoADC, error de fuente niGUIatrasada. No se reintentó la etapa fallida. **El candidato queda rechazado para aceptación conjunta visible; no incorporarlo ni subirFs.**

La reserva host mínima fue6450 muestras (161,25ms); el final del anillo conserva más audio disponible (hasta20763muestras). Se repitióservice reasoncredits con13chunks en vuelo yfree_blocks13, estadoACKplayed1596960/accepted1605120 sin avanzar mientras audiohost crecía. LatenciaACK máxima267,29ms; pausas máximasread90,13ms/decode81,26ms ygapentre pumps135,44ms. Son observaciones, no un orden causal probado. `service_wav` calcula cola anunciada másreservados conestadosconfirmados; explorar envejecimiento de estadoACK y política de créditos sin reenviar offsets ni exceder capacidadMCU.

Esta evidencia dirige el siguiente bloque al reabastecimiento/confirmaciones de A0. No se atribuye el underrun a falta de muestrasDSP ni se supone queacceptN8 lo corrija. La ventana visible agrega carga y el fallo no invalida retroactivamente los pases de las ventanas ocultas; limita su extrapolación.

Restauración exacta de producción y ajuste previoADC16/40kHz genOFF, identidad antes/después igual y10s399360muestras sin dropped/fatal. No quedó corriendo la campaña ni instalado el relay experimental.

## Auditoría de créditos y traza por comando · 20/10

[Auditoría offline del fallo](../diagnosticos/resultados_v17/generador_radio_20261020_165538/offline_a0_credit_audit.json). Se descartó doble reserva en esta evidencia: los treceRID pendientes5401–5413 cubren muestras[1605120,1611360), exactamente13×480, todas posteriores aaccepted1605120. El MCU avanzó7680muestras entre el últimoACKPLAYING y elACKUNDERRUN siguiente sin aceptar másaudio. No liberar créditos por estimar consumo ni retirar comandos pendientes: aquí no recuperaría bloques yaaceptados y arriesga exceder capacidad.

Se preparó una copia nueva del relay conring128comandos, timestamps localesQ de primer byte observado/completo/SPIinicio-fin/ACKrecibido/retorno de entregaTCP y snapshot congelado anteprimerUNDERRUN. No cambia protocolos ni algoritmo de créditos y no imprime durantealta. La entrega a colaTCP no se etiqueta como flush físico. [Experimento](../experimentos/adc8_a0_command_trace_v17/README.md).

[Informe físico120s](../experimentos/adc8_a0_command_trace_v17/command_trace_20261020_171131/report.json) · [Revisión acotada](../experimentos/adc8_a0_command_trace_v17/command_trace_20261020_171131/review.json). **No reprodujo el fallo:** audio/integridad pasan, FFT100%visible y19Paint/s; cola6, reserva host mínima8166muestras (204,15ms). No pasa holgura estricta ni cierra el underrun intermitente previo.

Se observaron12835comandos y12707sobrescrituras delring; no hubo freeze. Los últimos128, incluidos controles finales, mostraron máximos: primerbyte→completo0,0097ms; completo→SPIinicio1,0062ms; SPIfin→ACKrecibido0,7515ms; ACK→retorno de entregaTCP0,1286ms. **No son máximos de toda la corrida** ni explican el evento que no ocurrió. RelojesQ/host no se restan entre sí; correlación únicamente porRID y duraciones locales.

Restauración exacta de firmware/relay/ajustes previos y10s sin pérdidas, identidad original verificada. No se incorporó este relay ni se modificaron créditos. La investigación sigue abierta: ampliar el registro acotado a máximos porcomando/etapa y repetir una campaña con instrumentación hasta capturar el fallo, antes de aplicar una corrección al tramo responsable.

## Máximos de comandos en3×120s · 20/10

[Informe](../experimentos/adc8_a0_command_tails_v17/command_tails_20261020_204213/report.json) · [Revisión por sesión](../experimentos/adc8_a0_command_tails_v17/command_tails_20261020_204213/review.json). Copia nueva: sóloheader de estadísticas cambia respecto al relay de traza previo, sin nuevas llamadas de reloj ni modificación de créditos. Retiene top8 por etapa, contadores y muestras incompletas, además delring128 del primerunderrun.

Tres sesiones120s conRADIO→A0/FFT pasaron adquisición/audio y criterio visual; exposición96,4/100/100%. Colas4/4/4: **no aprueban holgura estricta**. No se reprodujo el underrun, no se declara corregido. Reserva host mínima117,25/233,25/185,25ms.

| Sesión | Comandos completos | Completo→ACK enrelay máximo | ACKhost máximo |
|---|---:|---:|---:|
| 1 | 12761 | 1,822ms | 212,050ms |
| 2 | 12783 | 1,833ms | 53,786ms |
| 3 | 12794 | 1,838ms | 85,959ms |

Se conservaron38338comandos; todas las etapas tuvieron igualcount, sinrechazos, unknownACKs ni censuras poroverwrite. Esto permite usar los máximos de todasestas sesiones, no sólo susúltimos128comandos. El resumen padre conserva la últimasesión; la revisión deriva las anteriores de suslogs propios, preservadosporcaso.

El tiempo recibido-completo→SPIinicio nunca superó1,042ms; SPIfin→ACKrecibido1,231ms; ACKrecibido→retorno de entregaTCP0,566ms. Son máximos distintos, no sumar como si fueran un único comando. El “ACKhost” incluye desde la petición del host hasta su procesamiento de respuesta; los relojesQ/host no se restan entre sí ni se afirma causalidad por el RID de máximos diferentes. Aun así, en estas corridas la gran demora observada queda fuera del intervalo local del relay registrado. Falta separar llegadaUSB/ADB, retorno y atención del procesoPython. No extrapolar esta ausencia de demora al fallo de otra corrida.

Restauración exacta de firmware/relay/entorno/política y ajustes previos, identidad antes/después igual y10s finales sinpérdidas. No se incorporan relay ni tasa. Próximo bloque: medir tiempo de pared yCPU del hilo/proceso duranteread/decode y capturar losRIDdeACKlentos junto alread de llegada, sin cambiar aúncolascapacidad ni estimar consumo.

## CPU del host e intervalo de Python · 21/10

Se instrumentó read/decode con tiempo de pared, CPU del hilo y del proceso, y top8 de ACK por RID. Las pausas largas usaron poco CPU del receptor; algunas coincidieron con CPU de otros hilos locales. Es compatible con interferencia de planificación o contención, sin identificar un hilo ni demostrar espera de GIL. Los contadores incluyen preparación y limpieza, no sólo reproducción.

[Comparación y trazas](../experimentos/adc8_a0_host_timing_v17/host_timing_20261021_082241/comparison.json). Una pareja secuencial de120s por caso, ADC8/1,632653MS/s privado, RADIO→A0/40k y FFT65536 expuesta100%. Mismo MCU y relay instrumentados; sólo el hijo experimental cambia sys.setswitchinterval de5 a1ms y lo restaura en finally.

| Intervalo | ACK máximo | Read máximo | Decode máximo | Reserva mínima | FFT | Cola pico |
|---|---:|---:|---:|---:|---:|---:|
| 5ms | 83,740ms | 44,497ms | 23,463ms | 213,525ms | 18,97FPS | 4 |
| 1ms | 26,852ms | 23,782ms | 22,905ms | 195,875ms | 18,90FPS | 4 |

Ambos pasan audio/integridad y visibilidad. El candidato reduce máximos observados de ACK/read, pero no mejora cola ni reserva mínima: **sin holgura estricta**. Una pareja no demuestra mejora sostenida ni corrige el underrun anterior. No se cambian créditos, producción ni tasas públicas. Próximo bloque: comparación repetida con orden alternado antes de decidir incorporar el intervalo, manteniendo carga visible y restauración por sesión.

Ambas sesiones restauraron firmware/relay/entorno y ajustes previos: ADC16/40k, generador OFF, identidad original96685… igual antes/después y recuperación10s399360muestras sin dropped/fatal. Intervalo del hijo confirmado restaurado de1 a5ms.

## Repetición en orden inverso1/5ms · 21/10

[Cuatro corridas y trazas](../experimentos/adc8_a0_host_timing_v17/host_timing_20261021_084256/comparison_four_runs.json). Se completó el orden5/1/1/5ms,120s por corrida. Las dos nuevas pasaron audio/integridad, FFT100%visible a18,90/18,98FPS, sin errores y cola4 en ambas.

| Nueva sesión | ACK máximo | Read máximo | Decode máximo | Reserva mínima |
|---|---:|---:|---:|---:|
| 1ms | 73,886ms | 53,377ms | 34,484ms | 196,825ms |
| 5ms | 291,757ms | 26,091ms | 95,013ms | 224,225ms |

En ambas parejas el máximoACK fue menor a1ms, pero los máximos varían mucho y read no mejora consistentemente. Las reservas mínimas a1ms fueron inferiores a sus controles y todas las colas llegaron a4. No demuestra causalidadGIL ni holgura, y no reproduce el underrun. Se conserva el ajuste como candidato aislado, sin modificar producción ni promover1,633MS/s. Antes de incorporarlo: calificación60s+3×120s a1ms, captura del tramo lento porRID y revisión de las pausas post-read/decodificación; mantener separación entre máximos del lifecycle y reproducción.

Ambas repeticiones restauraron exactamente MCU/relay/entorno/configuración previa, ADC16/40k y generadorOFF, identidad original igual antes/después. Cada recuperación final:10s399360muestras,dropped=fatal0. El intervalo del hijo se restauró en ambos casos. Tests de instrumentación:3/3 pasan.

## Calificación1ms detenida porUNDERRUN · 21/10

[Informe](../experimentos/adc8_a0_host_timing_v17/host_timing_20261021_094100/report.json) · [Cruce porRID](../experimentos/adc8_a0_host_timing_v17/host_timing_20261021_094100/failure_review.json). El runner aislado agrega `--qualify`:60s+3×120s con reinicio independiente, digest verificado y parada ante primer fallo. Tests de instrumentación3/3 pasan.

Screen60s pasa audio/ADC/visual, cola3, ACKmáximo32,493ms, FFT19,05FPS100%visible. Primera120s falla: WAV4/2UNDERRUN y luego4/0; elapsed_audio_seconds105,062 es el último muestreo periódico, no timestamp exacto de transición; observación gráfica113,347s. ADCdropped=fatal0, cola6; FFT100%visible18,87FPS. Reserva hostmínima7638muestras190,95ms: había audio disponible en el host. ACKmáximo265,833ms, read84,505ms, decode117,952ms. **No aprueba calificación; no ejecutar las dos sesiones restantes ni reintentar.**

RingQ congelado enRID2619281318. Último comando exitoso2619281317: accepted4490880, played4484640, diferencia6240muestras156ms. Siguiente comando completo llega178,221ms después y devuelveUNDERRUN conaccepted sinavanzar. Es un intervalo del mismo relojQ; no restar tiempos host/Q. La reserva es un snapshot del protocolo, no una medición analógica.

Todos los comandos observados completo→ACK enrelay: máximo2,806ms. RID2619281303, ACKhostmáslento265,833ms, tuvo completo→ACKQ1,173ms y ACK→retornoencolado0,045ms. En este fallo se acota demora fuera del procesamiento local medido del relay. No distingue aún envío host, idaUSB/ADB, retorno ni scheduling antes de atenciónACK; entregaencolado no equivale a flush físico. El mayorread consumió0,218msCPUhilo/23,099msCPUproceso en84,505ms de pared; mayor decode7,225/68,379msCPU en117,952ms: tampoco pruebaGIL como causa única.

**Decisión: no incorporar1ms ni promover tasa.** La reducción previa de máximos no resolvió reabastecimiento sostenido. Próximo bloque: reconstruir último envío/refill y comandos pendientes alrededor delRIDfallido para separar host sin enviar de comando enviado pero demorado, sinliberarcréditosestimados.

Restauración exacta verificada: MCUoriginal96685…, relay/entorno/ajustes previos ADC16/40k genOFF, identidad antes/después igual y10s399360muestras sin dropped/fatal. El intervalo del hijo se restauró a5ms.

## Auditoría offline: pausa entre envíos confirmada · 21/10

[Auditoría reproducible porRID](../experimentos/adc8_a0_host_timing_v17/host_timing_20261021_094100/host_send_gap_audit.json), generada con `audit_failure.py`. Último éxitoRID2619281317 y fallo2619281318: intervalo entre inicios de sendall del host177,803ms; entre retorno previo e inicio siguiente177,759ms. El intervalo entre comandos completosQ fue178,221ms. No se restan relojes distintos: se comparan dos duraciones locales. El hueco ya existía entre llamadas de envío del host, no fue creado íntegramente después por transporte de esos dos comandos. Retorno sendall no acredita entrega física.

Cuatro observaciones service en el hueco estaban bloqueadas porcréditos: free/inflight18/18 y16/16, conaudiohost10861–13338muestras. Una lectura abarca84,505ms (157605,178147→157605,262652); el envío se reanuda157605,269323. No se detecta falta de audio fuente; la reposición espera ACK. ParaRID2619281303 la latenciahost265,833ms contrasta con1,173ms completo→ACKQ. Confirma la demora fuera de ese tramo local, sin distinguir ida/retornoUSB/ADB ni scheduling de recepción. Las observaciones service no son un registro continuo.

No liberar créditos por estimación: los pendientes representan offsets posteriores alaccepted observado. Próxima instrumentación aislada: registrar disponibilidad de bytes del socket antes/después de lecturas lentas, progreso de salidaTCP y flush del relay porRID; separar explícitamente encolado de envío físico y no atribuir el bloqueo aGIL. No hubo acceso ni cambios al Q en este bloque; conserva la restauración final verificada de la campaña.

## Instrumentación socket preparada · 21/10

[Copia aislada](../experimentos/adc8_a0_socket_trace_v17/README.md). Host: FIONREAD antes/después de read original,128recientes/top8lentos enresultadohijo, excepcionespreservadas ypatchrestaurado. Relay: ack_socket_complete_ns porRID alaceptarúltimobyte, trasparciales/EAGAIN ycamino directo; etapacompleta→socketacotada enCtStatistics. Se conserva la anotación deACKpendientes trasfreeze. Noes llegadafísica alhost.

Tres tests locales pasan; harnessC compila conWall/Wextra/Werror y verifica parcial+EAGAIN/freeze/deduplicación. Fuentesheredadas verificadas:14archivos, diferencias permitidas sólocmd_trace/frame_send_queue/unoq_config_stream. Runner exigehashLinuxrevisado antesdecampaña, sinreusarhashanterior. CompilaciónLinuxcompleta yensayofísico120s pendientes; no hay nuevaevidencia deQ ni promoción. Costemediciónhost:dosioctlporread, considerarperturbaciónexperimental. Producción/créditos intactos.

## Socket Linux probado y lectura rápida experimental · 21/10

BuildLinux -Wall/-Wextra/-Werror pasó; binario4aa0b54e9f64ed61f3a4da42e0a51833eb4501edb4a61d14e0884ee85a34d421. [Build/restauración](../experimentos/adc8_a0_socket_trace_v17/build_20261021_102740/report.json).

[Base120s](../experimentos/adc8_a0_socket_trace_v17/socket_trace_20261021_102928/report.json): audio/integridad/criterio visual y holgura de esta corrida pasan; cola3, FFT96,26%visible18,80Paint/s, hostreserva207,75ms, ACKmáximo113,488ms. Los12817comandos tienen todaslasetapas, sincensura/rechazos; ACKQ→socketcompleto máximo0,218ms. Lecturahost36,804ms con1984bytesyaencolados antes y72416después. No puede atribuirse íntegramente a esperar datosnuevos, pero no identificaGIL frenteascheduling. Medicioneslifecycle incluyenpreparación/limpieza.

Candidatoaislado ReadyRead: dup del socketpositivetimeout, recv inmediato sinselectprevio; EAGAIN vuelvealreadoriginal, sin cambiar socket original/sendall/timeout/créditos. Prototipoinicial cancelado porcoordinador aldetectarretención deconexión porduplicado; se agregóhookConnection.close ytest deEOF inmediatoenpeer. [Nota decancelación](../experimentos/adc8_a0_socket_trace_v17/socket_trace_20261021_103546/cancellation_note.json): novalidación nipérdidahardware. Qrestaurado.

[ReadyReadoculto120s](../experimentos/adc8_a0_socket_trace_v17/socket_trace_20261021_103956/report.json): audio/integridadpasa, cola4, ACK40,021ms, exposición0%: inválidoparacompararcargagráfica. Nuevaopcióndiagnóstico --keep-visible activaWindowStaysOnTopHint sólodelhelper. [ReadyReadvisible120s](../experimentos/adc8_a0_socket_trace_v17/socket_trace_20261021_104543/report.json): pasa audio/ADC/FFT100%visible20,17Paint/s, cola5, ACK59,373ms, reserva207,70ms. No holgura, no incorporar.

[Control conGUItrace120s](../experimentos/adc8_a0_socket_trace_v17/socket_trace_20261021_105233/report.json): audio/ADC/visualpasan, cola4, ACK77,726ms, FFT100%visible19,37Paint/s. GUIentregabatchmáximo5,150ms; render84,966ms pared/16,816msCPU enpeorcallback. CPUtotalrender17,070s ybatch2,884s en120s; noincluyeQtpaintasíncrono. Falta descomponer antesoptimizar.

Todaslas sesionescompletas ycancelada verificaronrestauración exacta identidad/relay/configuraciónprevia ADC16/40kgenOFF y10s399360muestrassinpérdidas. Ningúncandidatopromovido. Elusuario pidió continuarautónomamente entrebloques, sinpedirOKrutinarios.

## Descomposición GUI y optimización FFT incorporada · 21/10

[Control por etapas](../experimentos/adc8_a0_socket_trace_v17/socket_trace_20261021_105920/report.json): 120 s sin cortes ni pérdidas, FFT 100% visible, cola pico 5. La etapa `_render_fft_analysis` consumió 13,882 s de CPU; dibujo de curvas 1,911 s, anotaciones 0,962 s. Los tiempos de etapas anidadas no se suman como trabajos independientes. El GC más largo durante A0 activo en esta evidencia fue 2,328 ms; hubo una colección de 43,278 ms antes de A0. No cambiar su política basándose en esta corrida.

Se aisló una optimización de `_fft`: copiar a un único buffer privado y aplicar allí resta de media y ventana. Conserva entradas de sólo lectura y evita el segundo temporal grande al quitar DC. [Benchmark alternado de 100 pares](../experimentos/adc8_a0_socket_trace_v17/fft_workspace_benchmark.json): media CPU 3,565→3,218 ms, mediana 3,449→3,067 ms para preparación de4×65536. No es una mejora porcentual de todo el monitor.

[Candidato físico120s](../experimentos/adc8_a0_socket_trace_v17/socket_trace_20261021_110701/report.json): audio/ADC/visual pasan, FFT100% visible19,85Paint/s. Etapa FFT13,111sCPU y render16,709s frente a13,882/17,542 del control. Una comparación no permite atribuir cambios de colas o latencias a esta optimización. Cola5: no holgura ni promoción de1,633MS/s.

Optimización incorporada en `monitor/v17/spectral_analysis.py`, sin cambiar resolución, muestras, créditos ni temporización. Pasaron15tests numéricos (incluida referencia SciPy y entradas strided/Fortran de sólo lectura) y40tests de interfaz FFT. [Validación pública ADC8/1,6MHz](../diagnosticos/resultados_v17/generador_radio_20261021_111319/report.json):120s RADIO→A0/40k, FFT100% visible19,91Paint/s, sin cortes ni pérdidas; cola5, ACKmáximo80,134ms y reserva190,375ms. El fallo intermitente no se declara resuelto.

Todas estas corridas restauraron identidad original96685…, ajustes ADC16/40k genOFF y10s399360muestras sin dropped/fatal. Sólo se incorporó el cálculo numérico equivalente; ReadyRead y1ms continúan aislados. El helper añade `--keep-visible` exclusivamente para diagnóstico y registra el hash de spectral_analysis.py.

## Nivel de servicio del hilo receptor: sólo diagnóstico · 21/10

Qt instalado6.11 ofrece `setServiceLevel`. Se añadió el flag diagnóstico `--receiver-qos-high`, sin cambios al inicio normal de V17. [Corrida pública120s High](../diagnosticos/resultados_v17/generador_radio_20261021_111730/report.json): audio/ADC/visual pasan, FFT100%visible19,88Paint/s; ACKmáximo58,565ms frente a80,134ms del control; reserva218,075ms frente a190,375ms. Cola5 enambos. No prueba mejora sostenida ni resuelve holgura: no incorporarQoS aproducción. El reporte confirma la propiedadQt High, no garantiza planificación concreta del sistema operativo. Identidad original y10s399360muestras sinpérdidas verificados al restaurar ADC16/40k genOFF.

Estado al cerrar el bloque: única optimización funcional incorporada es el workspaceFFT equivalente. Prioridad, ReadyRead y1ms siguen siendo experimentos. No hay nuevas tasas públicas. Pendientes de estabilidad: capturar de nuevo el underrun con traza de socket completa; separar transporte/atención del host en el fallo y medir cola bajo carga conjunta. Continuar entre bloques sin pedir confirmación rutinaria; preservar un único propietario del Q.
