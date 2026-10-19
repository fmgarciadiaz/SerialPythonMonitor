# Scan sin reproducción: atraso comunicado — 19/10/2026

Usuario reportó DSP/GUI atrasado al pulsar Scan, sin reproducción activa.
Bits/tasa yUS no confirmados. No atribuir aWAV.

Pruebas físicas, firmware intacto, restauración exacta posterior:
- us_multiscan_20261019_131526:16/76226Scan directo completó4candidatos sin
  errores. Ventananoexpuesta hasta captura final. ok=false por comprobación
  fijaerrónea de frecuencia en diagnóstico (esperaba500k frente a20k); nofalloScan.
- us_multiscan_20261019_131602:8/1600000ScanUS,ventanavisible,RADIO/A0OFF,
  perfiles1.6M/1.4035M/1.1189M,7hipótesis,restauración correcta. ColaGUIpico4,
  DSP0,GUImax129.7ms. Sin errores.
- us_multiscan_20261019_131647:8/1600000Scandirecto,ventanavisible,
  FFTRadio65536,8candidatos,colaGUI4,DSP0,GUImax358.4ms. Sin errores.

No reproducido elcorte,noresuelto. Hipótesisimportaciónndimage enGUI descartada:
ndimage ya está en sys.modules trasimportapp. Cambio preventivo retirado;
producciónconservada.17regresiones Scan/multiscan/fadeA0/presupuestocorrectas.
Diagnósticoahoraadmiteadc16,ventanavisible,FFT65536,midecolas yverificafrecuencia
realoriginal envezdeunvalor fijo. No modifica comportamiento deproducción.
Qrestaurado8/1600000genOFF,firmwareidéntico,10s15992640muestrassin dropped/fatal.
Siguiente: obtenerbits/tasa/US ytextoexacto delerror; distinguirlímite8lotes,
RFpendiente>1s ypresupuestodeentregaGUI. No ampliar límites paraocultarlo.


## Caso confirmado por usuario: US OFF, ADC8/1600000, sin reproducción

`us_multiscan_20261019_131839/report.json`: cincoScan directos consecutivos en
misma sesión,ventanavisible,FFTRadio65536. Todos terminaron,sin errores;
pendientesGUIpico4,DSP0,GUImax228,08ms. Candidatos14/11/13/13/9. No reproducido
elcorte. Qrestaurado8/1600000genOFF,firmwareidéntico,10s15992640sindropped/fatal.

Instrumentaciónincorporada: OutputWorker toma instantánea de presión en el
momento de la excepción de atraso, antesdeapagado/limpieza; GUI guarda una vez
el contextoScan/US/RADIO/A0/FFT/FILTER al recibir eseerror en
`diagnosticos/resultados_v17/gui_overload_*.json`. No registrocontinuo ni cambio
de límites; no se presenta como corrección de causa. ReiniciarV17paraaplicar.
Prueba local: snapshot conserva conteos tras vaciado yJSONsóloanteatraso.
RegresionesScan/multiscan/fadeA0/presupuesto/lotes:19correctas.


## Fallo real capturado: Scan → Play RADIO, sin A0

`diagnosticos/resultados_v17/gui_overload_20261019_132523_050832.json`:
ADC8/1600000,USOFF,RADIOON,A0OFF,Scanterminado,FILTEROFF,vistatemporal,
FFT2048. Error RFpendiente>1s. En instante del fallo:47lotesGUI,0DSP,
picoDSP2,1.571.616muestrasretenidas(0,98226s),28.512RFenrecogida,
45.263.136bytesestimados;GUImax1491,94ms. Esto ubica acumulación en entregaGUI;
no prueba qué callback/OS causó la pausa. No atribuir aDSP niA0.

Diagnósticoampliado --direct --scan-play: iniciaScanconRADIOOFF ydespuésPlay,
registra callbacks lentosrender_frame/_draw_display_frame/_deliver_worker_batch/
_radio_changed,60sRADIOsinA0. Intento canceladoantesdeconectarQ por monitorPID84414.
Pendientecierreavisadoparaensayoexclusivo. No se operóQ en este intento ni se
modificó producción. No confundir con repetición previa5Scan sinPlay posterior.


## Scan→Play repetido 132901

60s8/1600000USOFF,Scan28candidatos→PlayRADIOsinA0,vistatemporal:Cocoa pasó,sinfallo,colaGUIpico10,DSP2,GUImax243ms. Slowcallbacks:render_frame82msmax,draw36ms,deliver20ms;ringacotado512eventos,noCPUexclusiva. Qrestaurado8/1600000genOFFhashidéntico10s15992640sindrops/fatal. Noexplicaelcasoreal47lotes/1492ms. Instrumentaciónproductivaampliada:sóloRAMring128callbacks>=20ms(render,espectro,handle_batch),volcadoanteoverloadincluye detalle,canales,trigger,horizontal. Sinampliarlímitesnireiniciarautomáticamente. ReiniciarV17paraaplicar.


## US10/1250000 RADIO Play: fallo real 141112

Registro gui_overload_20261019_141112_707097.json:48lotesGUI,DSP0,0.9953s
retenidos,GUImax1679ms,A0OFF,USactivoenpausaRADIO,vistatemporalCH1+RADIO,
281250muestras,detalle50,triggerOFF. Callbackrendermax55ms:noexplicapausaentera.
Otroregistro140558 esdiferente:8/1.6M,DSP4,RFcoalescido1359936,GUImax126ms;
noatribuirambos al mismobloqueo sintraza.

Reproducción141246:mismoPython3.13VSCode,Cocoa,10/1.25M,CH1+RADIO281250,
RADIOPlayhasta80000muestrasantesScanUS. Pasó3perfiles,16hipótesis,restauró
RADIO/tasa/sintonía,GUImax166ms,pendientesGUI13,DSP1. Qrestaurado10/1250000
genOFF,firmwareidéntico,10s12495984sindropped/fatal. Noresuelto.

Captura productiva ampliada solamente en el fallo: worker toma pila del hilo
principal con sys._current_frames antesdequelGUIatiendaerror. Campo
`gui_thread_stack_at_failure` engui_overload*.json permite localizar bloqueo
que no aparece como callbacklento porque aún no terminó. Noamplíalímites,
nooperaQ,noregistrocontinuo. ReiniciarV17paraaplicar.
