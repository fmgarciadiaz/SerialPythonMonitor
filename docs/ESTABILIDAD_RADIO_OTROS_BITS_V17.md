# Estabilidad RADIO + A0 — 18/10/2026

Matriz de versión instalada, firmware f3cab6f4. Sin cambios MCU/relay. Un propietario; Q restaurada a ADC14/599250 y generador OFF; 5.989.368 muestras de recuperación sin pérdidas/fatales. Cada pantalla60s; máximos que pasaron se repitieron120s. Sondeo, retune, volumen y Stop incluidos. No equivale a 60+3×120 por cada combinación.

| Bits | Tasa solicitada | Caso | Continuidad | Cola pico | Audio descartado por generación |
|---|---:|---|---|---:|---:|
|8|1600000|max40|OK|5|0|
|10|1250000|max40|FALLÓ|3|0|
|12|1066666|max40|FALLÓ|2|0|
|16|76226|max40|OK|1|0|
|8|1403508|mid40|OK|4|0|
|8|100000|low_gain40|OK|0|4187|
|8|1600000|filter20|OK|5|422|
|10|909090|mid40|OK|2|0|
|10|100000|low_gain40|OK|0|4276|
|10|1250000|filter20|OK|3|0|
|12|930232|mid40|OK|2|842|
|12|100000|low_gain40|OK|0|2820|
|12|1066666|filter20|FALLÓ|2|0|
|16|50000|mid40|OK|0|0|
|16|40000|low_gain40|FALLÓ|0|226|
|16|76226|filter20|OK|1|0|
|8|1600000|max120|FALLÓ|3|0|
|16|76226|max120|OK|1|0|

Informe: `diagnosticos/resultados_v17/estabilidad_radio_20261018_135128/report.json`.

Hallazgos: ADC12 máximo40 yFILTER20 fallan por índice fuera de rango en detectorloops; ADC10 máximo40 yADC8 máximo120 sufren underrunDAC; ADC16 máximo120 pasa pero caso40kconGain tieneWAV4/0. Los cambios deGain descartan audio de generaciones viejas; no confundir esta pérdida de audiohost con droppedADC.16bits a76226 mantiene transporte dual. Tasas100000bajas8/10/12 también duales; máximos CH1.

Corrección inicial: excluir extremo superior de np.arange del detectorloops; floatingpoint podía producir posición igual al final exclusivo del bloqueADC12.17pruebaslocales correctas. MatrizADC12 repetida conhostcorregido en curso. No afirmarresueltosunderruns ni promover cambios no medidos.


## Correcciones y repetición

El detector de loops excluye ahora el límite superior de `np.arange`: en ADC12/160MHz÷150, el redondeo podía generar exactamente el final exclusivo del bloque. Regresión local reproduce el borde y recorre100bloques.

Repetición ADC12: `diagnosticos/resultados_v17/estabilidad_radio_20261018_161158/report.json`, todos los casos correctos y Q restaurada: máximo40k60s, intermedio40k, Gain a100k, FILTER20k máximo y máximo40k120s. El caso120s llegó a cola4: continuidad correcta, sin aceptación completa de holgura. Ningún índice fuera de rango reapareció.

Con Astra se separó generaciónvisual de continuidadaudio. CambiosGain/offset preservan epochcontinuidad; sintonía,banda,FILTER,adquisición y reinicios cambianepoch. Cada lote lleva sesiónA0capturada al publicarlo. Resultadosantiguos delmismoepoch/sesión conservan audio y referenciaoffset originales; otros se rechazan. GUI mantiene rechazo de generacionesviejas. Saltosvariasgeneraciones porGain no reinician resampler.46pruebas locales correctas, incluyendo A→B→A,FILTER,Stop/Play y pipeline.

Prueba física de la correcciónGain: `diagnosticos/resultados_v17/estabilidad_radio_20261018_162103/report.json`.60s cada caso con cambiosGain cada2s,volumen,resintonía,Stop:8/100000,10/100000,12/100000,16/40000, todos sinerrores. Muestraspendientesconservadas:2905/1271/2182/4096. El descarte1006en8corresponde aresintonía estructural; demás0. No equivale a calificación sostenida de cada máximoconGain/AutoGain.

Pendiente: underrunA0 aADC8/1600000 en120s yADC10/1250000 en60s de matrizoriginal. No se atribuyen aUSBni se ocultan conautorestart. La mejoraGain yfixADC12 no prueban resueltosesosmáximos. No modificarfirmware ni whitelist sin nuevoensayoaislado.16/76226max120 sí pasó en matrizoriginal; transporte dual. ADC14/851063 referencia conjunta calificada en informe separado.

## 18/10 — seguimiento cortes A0 máximos8/10

Campaña `experimentos/radio_refill_8_10_v17/probe_20261018_164919/report.json`, restauradatrue. Se redujo perturbación deldiagnóstico: copiade3000trazas ahora1Hz enlugarcadaevento; contadores/máximossiguenporoperación. Astra midiócopiaprevia~11,3us/evento; noestablececausadelunderrun. Baselineactual10/1250000 y8/1600000pasaron120s (12,22%cola4 y16,79%cola5). No demuestraresoluciónintermitente.

CandidatoHighRateSource(ráfaga16+guardfueralock) aislado:10fallóscreen60pordropped1/EOF;8pasóscreen60+120+120perotercera120pierdiónodo,cola8. CRCcorrectos. Recuperado relayMCU, noincorporado.Ni10ni8usanHighRateenproducción.

Candidatoconservador10ráfaga8+guardfueralock: `experimentos/radio_refill_8_10_v17/guard_only_20261018_170401/report.json`.60yprimer120pasaron;segundo120underrunA0,ADCintacto cola3/margen11,83%,ACK285,62ms,pump155,57ms,decode119ms,generate1,93ms. Noincorporar. DemuestraquenobastaeliminarcontenciónguardnipicosdepreparaciónDAC; faltaaislarreposición/créditoscuandoACKtardamásde250ms. Nuevosensayosnoalteraronfirmware/relayproducción. Qrestauradaylibre,ADC14/599250generadorOFF,5.989.368muestrasrecuperaciónsinpérdidas. Identidadf3cab6f4conservada.

Pendientecorrección: revisarQUERYserializadodurantelive,créditosconfirmados/ACKtardíos yservicioaudioentretramas; no ampliarventanasinventandocapacidad ni aceptarpaquetesconpérdidas. Evaluarbursturgentedinámicosólobajocolaconfirmadaenvezde16continuo. Preservarratesyfirmware14calificado. Noautorestarthide. Diagnósticoaúnnecesitasnapshotfinaltrasworkerjoin para conservarúltimosegundo,mejoraplanteadaporAstra.

## 18/10 — A0 ADC10/1,25M: servicio entre tramas incorporado

`_process_decoder_events`ahoraatiendecréditosRADIOalterminarcadatrama sóloADC10/1250000;conserva token6ms,burst8,ventana30,huecosconfirmadosyQUERY/PLAY/STOPserializados. NoMCU/relayni tasas cambiadas. Campaign `experimentos/radio_frame_service_v17/probe_20261018_182636/report.json`:10pasó60+3×120sinpérdidas/underrun;~11,6–11,9%margen,cola4(noholguracompleta).8pasó60pero120underrunACK420,8ms>DAC360ms,ADCintacto;noaplicar a8.

21testsproduccióncorrectos. Verificaciónfinal `diagnosticos/resultados_v17/generador_radio_20261018_183831/report.json`:120s10/1250000RADIO→A040k,ok/restoredtrue,margen12,38%,cola3,4.709.280DAC. QlibreADC14/599250generadorOFF,firmwaref3cab6f4intacto;5.989.368muestrasrecuperaciónsinpérdidas. ReiniciarV17. Detalle `docs/SERVICIO_RADIO_ADC10_V17.md`.

PendienteADC8/1,6M; no declararresueltos todosloscortes. Candidatasráfaga16 yguardfueralocksolas fallaronyse restauraron. Diagnósticocopiatraces1Hz envezcadaevento; preservamaxeventos, snapshotfinalpendiente. Continuar soluciónespecífica8sinbajartasa.
