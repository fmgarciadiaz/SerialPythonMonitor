# ADC14/851063 RADIO+A0 — reposición DAC

Objetivo mantener851063samples/s,40kA0,sin pérdidas/underrun. AntecedenteCPU14solo pasó60+120+120 yfallótercera120 underrunDAC,ADCintacto; noincorporado. ACK234ms,pump170ms,generate47msmedidos; el tiempo wall no prueba causaCPU.

Candidatoaislado: relayCPU14idénticoalcandidatoanterior; hostburst16(interval6ms/ventana30/huecosconfirmadossin cambios); correlaciónguardse ejecutafuera lockaudio ysnapshotoutputtienelockbrevepropio. No hay espera deFFT bajo lockconsumidor. Una solapropiedadDSP para entrada/hits. gate599se levantasóloenclaseprivada hasta851063. Produccióncontinúaprotegida.

Dos regresiones: correlaciónbloqueadanoimpide try_codes/feed/Stop; pausa170msrecupera16bloques sininventarcréditos ySTOPserializado. MCUinalterado,pruebas60+3×120 RADIO+A0,resintonía/volumen/Stop. Hasheshostysecongelanjunto fuentesrelay. Restauraciónobligatoriaantescierre inclusoantefallo. Integridadyholguraseparadas. Sóloincorporarsi calificación completa; retirar límiteprovisionalcon evidencia.
