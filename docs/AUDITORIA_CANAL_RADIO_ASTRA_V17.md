# Auditoría completa RADIO con Astra — 19/10/2026

Alcance: CH1, conversión numérica, transporte/IPC, demodulación, remuestreo,
FILTER, entrega GUI, cola de audio, detector de realimentación y A0.
Revisión Astra sólo lectura; medición local reproducible sin operar hardware.
No representa aceptación física, escucha, FPS visible ni holgura SPI.

## Medición inicial

Ejecutar `.venv-v13/bin/python diagnosticos/benchmark_radio_chain_v17.py`.
Evidencia inicial `diagnosticos/resultados_v17/radio_chain_audit/offline_20261019_013406.json`.
120 nodos por caso, excluir los10 primeros al resumir, AM sintética, banda8k,
A040k. FILTER activo=Butterworth2 lowpass1k fuenteRADIO; OFF sin filtro.
Tiempo de pared local medio por nodo; no confundir con coste CPU exclusivo.

| ADC / FS real | Duración nodo | DSP OFF | DSP con FILTER |
|---|---:|---:|---:|
| 8 /1,600M |2,16ms|0,584ms|0,844ms|
|10 /1,250M |4,45ms|0,688ms|0,830ms|
|12 /1,0667M|7,02ms|0,818ms|0,991ms|
|14 /0,8511M|6,99ms|0,698ms|1,077ms|
|16 /0,07623M|45,34ms|2,269ms|2,136ms|

Loscasossonsecuenciales,sinrepeticionesestadísticas: diferencias pequeñas no
atribuirlasal filtro. Incluye medias/p95/máximos por etapa en JSON.
Demodulaciónperfilesaltos0,395–0,527ms;remuestreo0,094–0,234ms.
ADC16remuestreo1,46–1,72msporlote,másgrandeentiempoaudio.
Serialización/deserializaciónpicklelocal0,107–0,209ms: NOmideelIPCentreprocesos,
planificaciónnitransferenciareal. CodificaciónDAC0,015–0,044msperfilesaltos.
Loopguardmedias0,027–0,055ms,peronoestimanelpeorcasocon4correlacionesricas.

No se midieron en esta ronda ADC físico, espera SPI/TCP, ACK DAC, latencia real,
pausasQt ni pintado. Esas etapas tienen evidencia histórica, no renovada aquí.

## Mejoras pequeñas incorporadas

1. ScanUS captura y valida196608puntos sólo al enviar su trabajo; mientras el
   futuro está pendiente no recopia/verifica las ventanas cada100ms.
2. Cancelación/fallo durante fadependiente detiene explícitamenteA0. Antes se
   podía limpiar contexto dejando la fuente activa con fade aplicado indefinido.
   No se reinicia audio tras fallo.
3. ColaA0 conserva directamente el array nuevo creado al restar offset, sin
   copiarlo otra vez. Sigue siendo propiedad privada: mutar el lote original
   después de feed_result no modifica los códigos ya pendientes.
4. No crear índices de muestras sin fade activo; fadein expira al llegar a su
   extremo. Fadeout mantiene silencio hastaStop.

20pruebas focalizadascorrectas: futurodemorado noleehistoria, fallo de fade
solicitaStop sinPlay,propiedaddelaudio,rampas,códigos,volumen,fragmentación.
48regresionesanteriorescorrectasparaScan/UI/A0antesdelúltimocambio copias/fade.
EstasmejorasnoalteranFSaudio40k,créditos,burst,umbrales,pérdidasni firmware.

## Plan priorizado siguiente

### 1. Instrumentación conjunta de extremos

Registrar edad RF al producir audio,esperaIPC,p95/p99/máximos demod/remuestreo,
feed_result,espera del lock,edad accepted→played,ocupación host/DAC y pausas GUI.
Reutilizar contadores acotados sin copiar trazas por evento. Snapshot final tras
worker.join para conservar el último segundo. Comparar máximos con reserva real.
No sumar mecánicamente prebuffer500ms ycolaDAC360ms: partedelprimerbufferse
reparteentrelasdoscolas.

### 2. Aislar GUI de continuidad de audio

OutputWorkerpending_batches incluye GUI; al llegar4 se coalescea RF antes del
DSP. A0 consume antes de emit,pero unaGUIbloqueadapuede frenarlossiguienteslotes.
Experimento aislado con pausasGUI50/100/250/500ms,verificando continuidadADC,
intervalosfeed,edadRF y mínimosDAC. Separar entrega visual agrupada deDSPserial
continuo,conlímitesdememoria;noocultarpérdidasniaceptargeneracionesviejas.
Es cambio estructural, no incorporado en esta auditoría.

### 3. Lock del detector de realimentación

RadioDacSource.observe_input mantiene lock durante FFT/correlación;
HighRateRadioDacSource ya correlaciona fuera del lock sólo14/851.
Medir esperas p99/máximas y revisar close/sent/cambiofuente antes de extenderlo.
Antecedente: experimento guard_only para8/10 falló continuidadA0 enADC10;
no presentarlo como solución ya comprobada ni repetirlo solo sin nueva hipótesis.

### 4. Remuestreo y copias grandes

AudioResampler materializa pesos y ventanas por indexing avanzado. A40k y128taps
cada matrizfloat64 representa40,96MB/s,~81,92MB/s juntas; no equivale a RAMresidente
ni a ancho de banda físico medido. Revisar uso de fallback sinc/Kaiser por ratio.
Probar kernel que consuma ventanas sin gather grande, con comparación de
particiones, continuidad exacta, alias/rechazo, amplitud/fase y primera muestra.
No cambiar FS deaudio para resolver coste.

### 5. Reservas, créditos y transporte: después

Conservar capacidadDACanunciada, créditosconfirmados yserializaciónQUERY/STOP.
No reducir reserva ni subir ráfaga como primer paso: candidatos previos fallaron
con ACKlentos y/o pérdidasADC aunqueCPUmedia tuviera margen.
Calificarcada cambio con captura real y restauración; separar integridad,
holgura, latencia, calidadanalógica y FPS visible.

Aspectos ya optimizados a conservar: mezcla integrada enFIRdecimador, sólo
outputsdecimados,tabla racionaldelresampler,FILTEROFFsinDSP,epochs/sesiones
contraaudioviejo,ACKdeconfiguración detrásdelDSPprevio,ScanpausaA0confirmada.
