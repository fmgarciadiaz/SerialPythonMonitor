# Cortes variables WAV→A0 — 19/10/2026

Archivo audios/imperial.wav, GUI Cocoa, RADIO OFF, firmware/productivo sin
modificar, un propietario Q. Play real mediante WavPreparation→OutputWorker.

## Evidencia

- `wav_playback_20261019_122014/report.json`: seis combinaciones18 s correctas;
  ADC8/40k yADC14/100k, cada una con salida20/40/50k. No prueba estabilidad larga.
- `wav_playback_20261019_122317/report.json`: ADC14/100k→A050k, solicitó120s,
  underrun4/2 a59,1168s (played2955840), GUI máxima64,65ms, pendientes3.
  Última reserva mínima observada mientras PLAYING76,8ms, no medida exactamente
  en el instante del fallo. Sin traza de transporte en ese caso.
- `wav_playback_20261019_122459/report.json`: intento de traza falló antesdeADC
  por ausencia time.thread_time en estePython; restaurado. No contarlo como
  fallo de reproducción.
- `wav_playback_20261019_122520/report.json`: misma combinación120s correctos,
  con traza acotada en memoria. Reserva mínima observada86,4ms, GUImax81ms.
  Ring WAV cubre últimos20,79s: hueco máximo chunks34,66ms. Enringtransporte,
  readmax7,07ms, decode2,09ms, send6,73ms, generate0,63ms. No extrapolar esas
  máximas a toda la reproducción. CamposCPU usan process_time como fallback,
  no tiempoCPU exclusivo de hilo; análisis arriba sólo usa tiempos de pared.

Corte variable reproducido, causa todavía no discriminada. No atribuirlo al
selector ni al tamaño/decodificación del archivo por esta evidencia. No se
modificaron ventanas de créditos, colas, tasas admitidas ni firmware. La ruta
WAV conserva un único request pendiente; RADIO usa otra política, que no está
calificada automáticamente para WAV. Siguiente: repetir caso largo con ring
hasta capturar el fallo y correlacionar pausas de envío, ACK y reserva DAC.

Informes bajo diagnosticos/resultados_v17. Diagnóstico reproducible:
`diagnosticos/probar_wav_playback_v17.py` (matriz corta; --long --trace).

Restauración final exacta ADC16/76226, generadorOFF, identidadSHA256
f3cab6f48a0d6b45fb7c1329ceee7e485f6cf32baadac1c9578533d1f5090bf5idéntica.
Recuperación5s382752muestras, dropped/fatal0. Qlibre.


## ADC16/76226: variante aislada de dos créditos

Baseline `wav_playback_20261019_122909/report.json`: imperial.wav, RADIO OFF,
salida50k falla0,8448s,40k falla10,644s,20k pasa60s. GUI máxima50/37ms en
fallos. Reserva baja hasta3bloques; huecos máximos chunks46/61ms. Esto no
prueba una causa única, pero el contrato serial limita la reposición.

Experimento `--pcm-window2`: cambia sólo service_wav dentro del diagnóstico,
con una copia de función en memoria: PCM permite hasta2créditos confirmados
trasPLAY. Arranque yBEGIN/PLAY/QUERY/STOP siguen serializados; capacidadmáxima16,
chunk/tasas/firmware intactos. No incorporado a producción.

`wav_playback_20261019_123105/report.json`: salidas50/40/20k pasan60s cadauna;
reservamínima48/120/288ms. Evidencia favorable acotada;50k mantiene margen
ajustado. Faltan3×120independientes delcasocrítico yregresionesSTOP/seek/EOF
antes de incorporar. No declarar todosloscortesresueltos.
Comparación `diagnosticos/resultados_v17/wav_adc16_comparison_20261019.json`.

Q restaurado16/76226,generadorOFF,firmwareidéntico,5srecuperación382752muestras
sindropped/fatal. Sin cambios productivos en este bloque.


## Calificación larga del candidato: RECHAZADO

`wav_playback_20261019_123559/report.json`: ADC16/76226→A050k, imperial.wav,
RADIOOFF, Cocoa. Dos arranques independientes120s pasaron, tercero tuvo
UNDERRUN4/2 a4,2048s. Campaña detenida al fallar. ADCdropped/fatal0,cola1;
GUImáxima64ms en fallo. ReservamínimaPLAYING38,4ms, no reserva en instante exacto.

Traza del fallo: readmáxima53,34ms, envío socket42,28ms, hueco máximoentre
chunks86,76ms; huecoprevio79,01ms. No atribuir todo aGUI ni a latenciaACK;
lectura, envío y planificación pueden acumular pausas. El ring registra tiempos
de pared, no tiemposCPU exclusivos. Causa exacta de esas pausas sigue abierta.

Aclaración del experimento: además de ventana de2, el cambio local de `live`
reduce consulta por defecto de20 a4ms para PCM. La evidencia evalúa ambos
cambios juntos; no demuestra que sólo ventana explicase los pases previos.
No incorporado a producción. No se ejecuta aceptación de controles de un
candidato que falló continuidad. Próximo: investigar read/send bloqueantes y
reserva efectiva frente a capacidad30anunciada; no subir créditos a ciegas.

Resumen `wav_pcm_window2_qualification_20261019.json`. Firmwareidéntico,
Qrestaurado16/76226genOFF, recuperación5s sin dropped/fatal. Producciónintacta.


## Exploración posterior: capacidad negociada y procesamiento por trama

Todos experimentos aislados, sin editar producción/firmware, imperial.wav,
GUI Cocoa, RADIOOFF. Informes `wav_playback_20261019_*` bajo resultados_v17.

- 124249: sólo capacidad/objetivoPCM hasta30 (siempre min con slots anunciados),
  mantieneventana1/poll20ms.16/76226y14/100k→A050k pasan60s;reservas230,4/211,2ms.
- 124530: mismo candidato, prueba controles falla antes de ejecutar el primer
  salto:underrun a1,6704s. Noaceptar como prueba de controles. Métricareserva
  despuésdelsalto inválida porqueGUIplayedabsoluto yacceptedrelativo;señalada
  explícitamenteenreport y corregida en diagnóstico. NoesreservaDACnegativa.
- 124617: ventana2/poll4ms+capacidad30:16/76226 falla4,3872s;14/100k pasa60s.
  Durante4,36s,accepted crece205440 yplayed217440:reserva pierde12000muestras.
  Capacidadmayor no evita insuficienciaintermitente dereposición.
- 124818: agregando únicamente decoderportramas992 paraPCM al candidato anterior,
  16/76226→A050k pasa60s,reservamínima211,2ms,ADCsinpérdidas/fatal,cola1.
- 124942: mismo candidato pasóadelantar10s,retroceder5s,Stop/Play,saltohaciaEOF,
  DONEreal,reiniciotrasEOF yStopfinal, sinunderrun. Testcontrolessinaceptaciónlarga.

Hipótesisactual: el procesamientocompletodeunreadTCP antes de atenderACKpuede
retrasar reposición. El candidato procesa eventos tras cada trama comoRADIO,
conservando orden en cable. Unpase60s no prueba causalidad niestabilidadglobal;
faltanrepeticionesindependientes120s antes deincorporar. No aumentar créditos
adicionales ni extrapolar aRADIOque conserva rutaactual.

Resumen `wav_exploration_20261019.json`. Qrestaurado16/76226genOFF,
firmwareidéntico;últimarecuperación5s382536muestras,sindropped/fatal.
