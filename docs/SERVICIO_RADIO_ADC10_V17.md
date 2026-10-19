# Servicio DAC entre tramas ADC — 18/10/2026

Se incorpora únicamente para **ADC10 CH1 / 1.250.000 muestras/s y fuente Radio A0**. `_process_decoder_events` atiende la reposición después de cada tramo decodificado, conservando QUERY/PLAY/STOP serializados, créditos confirmados, ventana y token bucket. No modifica firmware, tasas ni verificador. Otros perfiles y fuentes WAV conservan el comportamiento anterior.

## Evidencia de continuidad

Campaña: `experimentos/radio_frame_service_v17/probe_20261018_182636/report.json`. Un propietario, respaldo e identidad de firmware; ajustes restaurados y recuperación10s sin pérdidas.

| Bits | Prueba | Resultado | Margen medio | Cola pico |
|---|---|---|---|---|
|10|screen60 / 60s|OK|11.81%|4|
|10|acceptance1 / 120s|OK|11.63%|4|
|10|acceptance2 / 120s|OK|11.93%|4|
|10|acceptance3 / 120s|OK|12.00%|4|
|8|screen60 / 60s|OK|17.08%|4|
|8|acceptance1 / 120s|FALLÓ|16.49%|5|

ADC10 completó60s+3×120s sin pérdidas/fatales/underrun. Cola4 en calificación: aceptación de continuidad, no de holgura completa sostenida. ADC8 falló primer120 por underrunA0; ACKmáximo420,8ms,capacidadDAC360ms, adquisición sinpérdidas. No sepromueveparaADC8.

## Versión final instalada

21pruebas locales correctas (créditos,QUERY/STOP,fuentes,continuidadyscopeexacto);2regresiones aisladas comprobaronreposicióndeADC-only yreservas. Repeticiónfinal `diagnosticos/resultados_v17/generador_radio_20261018_183831/report.json`:120sADC10/1250000,RADIO→A040k,ok/restoredtrue,4.709.280muestrasDAC,sinerror,margen12,38%,cola3,slackpositivo. Este resultado no reemplaza elmáximocola4 de la campaña. Qlibre,firmwaref3cab6f4sin cambios,ADC14/599250generadorOFFrestaurados,5.989.368muestrasrecuperación10s sinpérdidas/fatales. ReiniciarV17paraaplicar.

## Limitación pendiente

8bits/1,6MS/s requiere solución específica para confirmar/reposiciónantesdeagotar360ms. No aplicar automáticamenteráfagas16: candidatasanterioresperdieronnodosADC. Noautorestart ni toleranciadeerrores. La instrumentación de trazas pasó acopia1Hz; máximos/eventos siguenactivos. Pendiente snapshotfinal deldeque trasworkerjoin para no perderúltimosegundo de captura.
