# Validación sostenida del desacople RADIO — 19/10/2026

**Resultado global: incompleto/fallido para estabilidad A0 ADC14/851.**
La mejora de tolerancia a pausasGUI está medida, pero no resuelve todos los
cortes de salida. No promover una afirmación de estabilidad global.

Campañas con una sola sesión propietaria, firmware instalado sin editar y
restauración individual/final. Qtminimal:sinaceptaciónFPSvisibles.
BandaRF8k,antenaCH1,A040k salvoFILTER20k,retune,volumen ypausasGUI50/100/250/500ms
cada10s;Gaincada2s en casos screen/otrosbits. DSPprecalentado antes de alta carga.

## Casos físicos

| Caso | Duración | Continuidad A0/ADC | Margen medio | Cola ADC pico |
|---|---:|---|---:|---:|
|14/851063 screen + Gain|60s|pasa|19,22%|2|
|14/851063 repetición1|120s|pasa|19,17%|2|
|14/851063 repetición2|solicitó120s,falló≈91s|underrunA0;ADCintacto|19,36%|2|
|10/1250000 GUI+Gain|120s|pasa|12,28%|3|
|12/1066666 FILTER→A020k+Gain|60s|pasa|13,60%|3|
|16/76226 dual+Gain|60s|pasa|72,00%|1|
|8/1403508 GUI+Gain|60s|pasa;sinholguracompleta|8,43%|4|

No se completó60+3×120deADC14 porfallo;ADC10tieneun120enestaronda,no3.
ADC8/1,6M no se calificó aquí;mantiene pendiente histórico. No confundir
continuidad de estos casos con recepciónanalógica,escucha o FPS certificados.

Informes:
- `diagnosticos/resultados_v17/desacople_campaign_20261019_105104/report.json`
- `diagnosticos/resultados_v17/desacople_campaign_20261019_105741/report.json`

Primeracampañacontiene14;segundalos4formatosrestantes. Eloktrue de lasegunda
sólo expresa continuidad/restauración de sus cuatro casos,no aceptación global
niholguraADC8. Cada fila enlaza su informe completo ylogs independientes.

## Fallo ADC14 analizado con Astra

`diagnosticos/resultados_v17/generador_radio_20261019_105442/report.json`:
WAVUNDERRUNreason2,aprox90,97sreproducidos;ningúnerrorADC,dropped0fatal0,
slackpositivo,margen19,36%,cola2. Es unfallo real, aunque los pasesprevios seanválidos.

Astra revisóeltrace:
- Hueco sinenviarchunks304,2ms entre918243.194964y918243.499173.
- Duranteelhueco:351eventos,4lecturas,~208,4mstiempo transcurrido en decode.
- Huecoprevio195,3ms.
- ReservaDACconfirmada accepted−played bajó288ms→120ms.
- Ráfagatardía16chunksseguida deUNDERRUN.

Readmax27,3ms;ACKmax200,7ms;pumpgap131,9ms;generate5,2ms. Unamáxima no
identifica causa;noatribuir304ms a unareadbloqueante. Decodeeswalltime,noCPU.
Mínimoglobalhost178samples=4,45ms,no tienetimestamp yno demuestra causalidad.
GUI/DSPpicosglobales tampoco prueban coincidencia. Hubo guardadosJSONcada15s,
cerca delsegundo90:posible perturbaciónporinstrumentación,aúnno demostrada.

Siguienteexperimentoacotado:14/851120smismosparámetros,sinJSONduranteensayo,
ringbufferenmemoria:feed_result/cola host,try_codesNone conmotivo, oportunidades
service_wav sinenvío porcréditos/tokens/pending/audio,accepted/played/inflight.
Volcartrasjoin. No tocarburst/prebuffer/guard/firmware simultáneamente.
Unpaseno demostraríaqueJSONfuera lacausa;requerirA/Bsiesaevidenciasurge.

## Incidencias de arranque e instrumentación

1. Primera ejecución se bloqueó leyendo un módulo local antesdeconectarQ;
   interrumpida sinoperarhardware.
2. `desacople_campaign_20261019_104818`:abortóQtporpluginoffscreenantesde
   adquisición;minimalcomprobadoyusado después.
3. `desacople_campaign_20261019_104852`:cierredelrelayporcliente lentodurante
   arranquefrío,read1,18s,pumpgap1,216s,antesdeaudio,recoveryrestoredtrue.
   ElDSPseprecalentópara separarestearranque deestabilidadsostenida. Noqueda
   validado elarranquefrío,nisepresentacomofalloADC.

No se reintentó uncasofallidoparaocultarlo;detuvo primeracampaña ysecompletaron
otroscasosindependientesdespuésderestauraciónverificada.

## Estado final

RestauradoADC8/1600000,genOFF,configuraciónoriginal exacta.FirmwareSHA256
f3cab6f48a0d6b45fb7c1329ceee7e485f6cf32baadac1c9578533d1f5090bf5igual.
Recuperaciónúltimacampaña10s:15991776muestras,sindropped/fatal;Qlibre.
Fuentesproductivasnoeditadasdurantecampaña;sólo diagnóstico mejoró precalentado,
stressGUIytrazafinal.El desacople sigue incorporado;no se modificaron créditos,
ráfagas,firmware nireservaspara hacerpasarelcasofallido.

RegresioneslocalesfinalesconQtminimal:119testscorrectos(presupuesto,ACK/lotes,
DSP,FILTER,RADIO,Scan/fadeA0,US,FFT,autogain,límitesysugerenciabanda).


## Diagnóstico de refill: dos controles de 120 s

Sin modificar producción ni firmware: ADC14/851063, RADIO→A0 a 40 kHz,
banda RF 8 kHz, pausas GUI hasta 500 ms, retune y volumen. Ring en memoria
limitado a 20.000 eventos; volcado al finalizar.

| Control | Resultado | Cola ADC pico | Hueco máximo entre chunks en ring | Reserva DAC mínima en ring |
|---|---|---:|---:|---:|
| Sin guardados periódicos | 120 s sin errores | 3 | 83,42 ms | 288 ms |
| Con guardados periódicos | 120 s sin errores | 2 | 67,45 ms | 312 ms |

Informes `generador_radio_20261019_111057/report.json` y
`generador_radio_20261019_111355/report.json`, bajo `diagnosticos/resultados_v17`.
Comparación: `radio_chain_audit/refill_comparison_20261019.json`.
Ambos rings cubren solamente los últimos ~66 s; no hubo `try_codes=None`
en ese tramo. Los huecos máximos de alimentación DSP fueron 63,24 y 71,28 ms.
El motivo de servicio `credits` incluye cola llena normal y no demuestra
agotamiento de créditos como causa.

**No se reprodujo el fallo previo y no se identificó su causa.** Estos dos
pases no prueban que el guardado periódico causara el underrun, ni completan
una nueva calificación independiente 60 + 3×120 s. Se mantiene el resultado
global pendiente por el corte observado anteriormente. Próximo bloque:
repeticiones con esta instrumentación acotada hasta capturar el fallo y
correlacionar alimentación DSP, reserva host y reserva DAC.

Restauración final verificada: ADC8/1600000, generador OFF, firmware idéntico
al SHA256 indicado arriba. Captura posterior de 10 s: 15.994.368 muestras,
sin dropped/fatal. Q libre. No se modificó código de producción en este bloque.


## Seguimiento 112404: tercer control de 120 s

`diagnosticos/resultados_v17/generador_radio_20261019_112404/report.json`:
ADC14/851063, A0 40 kHz, banda 8 kHz, pausas GUI hasta 500 ms y registro
diferido: 120 s sin errores. Margen medio de envío conjunto 19,39%, cola ADC
pico 2. En los últimos ~66 s del ring: hueco máximo entre chunks 66,42 ms,
reserva DAC mínima 300 ms, ningún `try_codes=None`. No se reprodujo el fallo.

Son tres controles consecutivos de 120 s correctos con instrumentación de
refill (dos diferidos y uno periódico). El fallo anterior se conserva y su
causa sigue abierta; estos controles no prueban una corrección causal ni una
aceptación analógica o de FPS visibles. Sin cambios de producción o firmware.
Q restaurado ADC8/1600000, generador OFF; verificación posterior 10 s,
15.994.368 muestras, dropped/fatal 0, identidad de firmware idéntica.
Resumen: `diagnosticos/resultados_v17/radio_chain_audit/refill_followup_20261019.json`.
