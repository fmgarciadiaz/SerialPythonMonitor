# Cierre de flujo durante Scan US ADC10 — 18/10/2026

Log del relay observado tras fallo del usuario: `Dual acquisition/control integrity
failure at seq=16032213`, CRC recibido/calculado76d2f0a2, expected_bits10,
expected_period536871088 (ticks176 yflagreloj160MHz), nodo recibido con dropped1,
fatal0. El relay rechaza correctamente la trama; no es un resultado vacío deScan.
La transición destino era ADC10/909090 tras perfiles altos con cambios CPU/SPI.

Primer intento de diagnóstico `us_multiscan_20261018_194957/report.json` encontró
el flujo ya cerrado antes de obtener snapshot; no modificó configuración.
Se recuperó con `tools/usb_stream.py start --firmware v17`. Esta herramienta
reinicia la app instalada; AppLab ejecutó compilación/carga del sketch existente.
No se cambiaron fuentes remotas. SHA256 final f3cab6f48a0d6b45fb7c1329ceee7e485f6cf32baadac1c9578533d1f5090bf5,
igual al previo. No afirmar conservación de ajustes del fallo: el reinicio dejó
ADC14/31250 y generadorOFF (valoresdearranque).

Corrección host: OutputReceiver.configure pasa por ADC14/40000 y drena150ms
al cambiar entre dos perfiles nativos >400k si cualquiera usa transporte
optimizado. Las muestras y el ACK de esa preparación no se publican como destino
GUI; el destino sólo se publica tras su APPLIED. Camino especial ADC8/1.6M
conserva preparación existente. No ocultar dropped ni reintentar Scan fallido.
La pausa reduce exposición al cambio de CPU/SPI; no prueba una causa exclusiva.

Error de worker durante Scan ahora cancela la transacción y muestra restauración
no confirmada antes de cerrar. Restauración normal exige100ms de muestras nuevas
además de ACK.

Dos pruebas GUI/Q independientes correctas:
- `diagnosticos/resultados_v17/us_multiscan_20261018_195122/report.json`
- `diagnosticos/resultados_v17/us_multiscan_20261018_195151/report.json`

Ambas: ADC10 1250000→1167883→909090→1250000, sintonía1MHz preservada,
sin errores de worker. Restauración externa posterior aADC14/31250/genOFF,
recuperación10s311296muestras sindropped/fatal. Q libre, identidad igual.
Pruebas unitarias verifican perfil intermedio invisible y ausencia de cambios
cuando destino=origen. Dos repeticiones correctas no prueban ausencia definitiva
de cortes intermitentes ni estabilidad A0, que estaba apagado.


## Scan con RADIO encendida — 18/10, seguimiento

Se separó pausa interna deScan (`_set_radio_scan_playback`) deStop/Playmanual.
Antes, el toggle ejecutaba `_radio_changed`→`_filter_changed`, reiniciaba preset
FILTER y podía autoseleccionar canales. Ahora sólo resetea época DSP/audio y
actualiza estadoPlay; conservaGain,offset,sintonía,FILTER ycanales. DuranteUS,
lasconfirmacionesdeperfilnoreinicianelindicadordepresetFILTER. Scannormal
noreactivaRADIOsiadquisicióncambiómientrasfutureestabapendiente.

ConA0activo,Scan pide detener salida antes de iniciar, igual queUS; antes
ScannormalpodíadetenerA0silenciosamenteynodevolverPlay. Reanudaciónautomática
A0duranteScannoseimplementaenestealcance.

Pruebasrealesconantena,ADC10/1250000,RADIOencendidaantesdeScan:
- `us_multiscan_20261018_200441/report.json`: US,19hipótesis y19marcas;
  radio_resumed/scan_restored/frequency_restoredtrue.
- `us_multiscan_20261018_200515/report.json`: normal,36candidatos y36marcas;
  mismosindicadorestrue.
Ambossinerroresworker,restauraciónexternaADC12/40000genOFF,recuperación10s
399360muestrassindropped/fatal,firmwaref3cab6f4igual.Qlibre.
36regresioneslocalescorrectas,incluyendopresetFILTERconservadoypausa/reanudación.


## ADC14/851 — corrección de cobertura de la transición

Fallo usuario: relayseq1395229,kind16,expectedbits14,period267,CRCfd4903d1
correcto;dropped4fatal0aldestino599250. La condición de preparación exigía
queambosperfilesfueran_native.599250esCH1legacycon_nativeNone,yseomitíaelpaso
porbajacarga833333→599250y599250→851063. Seeliminóesaexigencia: cualquier
transición>400kconcualquierextremooptimizado pasa por14/40k150ms.

Recuperaciónconusb_streamstartv17:AppLabrecargósketchinstalado,hashf3cab6f4
igual,sinfuentesremotasmodificadas. Ajustesdearranque14/31250genOFF;noafirmar
restauracióndelestadofallidoprevio.42regresionescorrectas;testnuevocubreambas
direccioneslegacy↔optimizadoyACKintermedioinvisible.

PruebaGUI/Q `us_multiscan_20261018_200937/report.json`:14/851→833→599→851,
RADIOon,11hipótesis/11marcas,reanudación/sintonía/FSrestauradas,sinerrores.
Recuperaciónexterna10s311296sindropped/fatal,final14/31250genOFF,hashigual.

Repeticiónindependiente `us_multiscan_20261018_201001/report.json`:ok/restoredtrue,10hipótesis/10marcas,RADIOreanudada,mismarecuperación311296sindropped/fatal,identidadigual.Qlibre. Dosrepeticionesnosonaceptaciónprolongada.


## 19/10 — Scan durante reproducción Radio A0

Se reemplaza el bloqueo deScan por pausa automática deA0: cerrar fuente,
solicitarStop,esperarconfirmación_idle (hasta8s),hacerScan yreanudarconfuente
nueva,mismoIN/rate/volumen,sóloenfinalcorrecto. No se reanuda si cambiaworker,
modo/IN/tasa,siScan falla oaldesconectar. ColaDSP/sesiónA0 siguen separadas;
noautorreintentoocultandoerrores. UIdeGeneradorRadioquedadeshabilitadadurantepausa.

45regresionescorrectas,testsespecíficosverificanesperadeACKyquenoreproduce
trasfallo. GUI/QADC14/851,A040k,US `us_multiscan_20261019_012259/report.json`:
oktrue,played1440antesy1440enfuente nueva después,11marcas,ScanrestauróFS/sintonía.
RestauraciónexternaADC8/1600000genOFF,recovery10s15993504sindropped/fatal,
firmwaref3cab6f4igual.

Intento012048noinicióA0porselectoresdeldiagnósticoen40k;corregidosaperfilobjetivo,
restauracióncorrecta. Intento012330normalreprodujoantes/después,peroassert
frecuencia500kfueraNyquistADC14/851falló;repetirconsintoníaválida300k.

NormalA0repetición `us_multiscan_20261019_012355/report.json`:oktrue,played1440antes/después,22marcas,FS/sintonía/RADIOrestauradas;externaADC8/1.6MgenOFF,15990912muestras10ssindropped/fatal,hashigual.Qlibre.
