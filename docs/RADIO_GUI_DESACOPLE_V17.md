## Estado vigente: integración verificada — 19/10/2026

Los apartados iniciales de abajo documentan el experimento previo. La variante
ya se incorporó con controles adicionales en OutputWorker y DeliveryBudget.

- Admisión RADIO según pendientesDSP, no según entregasGUI. Otros modos mantienen
  su límite de8lotes; al apagarRADIO se permite drenar sus lotes anteriores.
- Presupuesto de retención:1s entre RFcoalescida y entregaspendientes; máximo
  1.600.000muestrasRF,64MiB de payloadestimado (RF+reservaoutputs),256objetos.
  Losbytes son presupuesto de arrays, no RSS del proceso ni deQt/Python.
- Créditoexactoporlote, liberaciónporidentidad, protegida contra dobleliberación;
  errores síncronos/asíncronos liberan crédito. Sin descarte latest-only.
- ContadorDSPindependiente,ACKtras trabajoanterior conservado, sesionesA0 y
  rechazo de generacionesviejas conservados. No cambia firmware ni ráfagasDAC.

Comparación integrada `radio_chain_audit/gui_stalls_20261019_093611.json`:
pausa500ms→hueco495,7msadmisiónantigua /33,1msintegrada;1.750.000muestrasRF
recibidas porGUIcadacaso. Modelodepausa/entregaQt,nodebloqueofísicodetransporte.

Pruebas reales Q con bloqueoGUI `time.sleep(.5)` mientrasA0reproduce:

| Caso | Informe | played antes/después pausa | Cola GUI/DSP pico | Presupuesto retenido |
|---|---|---:|---:|---:|
|14/851063 |us_multiscan_20261019_093623/report.json|1440→21600|24/1|12644320bytes|
|10/1250000|us_multiscan_20261019_093728/report.json|1440→21120|25/1|18928512bytes|

Informes bajo diagnosticos/resultados_v17. Ambos ok/restoredtrue,sinerroresworker,
ScanUSposteriorcorrecto (11/16marcas),FS/sintonía/RADIO/A0reanudados.
RecuperaciónexternaADC8/1600000genOFF,10s15990912muestras sindropped/fatal,
firmwaref3cab6f4igual,Qlibre. Son pruebas cortas de tolerancia, no calificación
prolongada global ni escucha/FPScertificados.

Tests de presupuesto/muestras/bytes/transiciónOFF/fallos+pipeline:31correctos.
51regresiones en bloque anterior también correctas, parcialmente solapadas.

---

# RADIO: presión GUI frente a continuidad DSP/A0 — 19/10/2026

Experimento aislado; sin cambios al OutputWorker de producción.
Script: `diagnosticos/benchmark_radio_gui_stalls_v17.py`.
Usa OutputWorker y BatchProcessor reales, Qt con conexiónQueuedConnection,
ADC10/1,25MS/s simulado, lotes20ms, demodulación y sink audio con marcas de tiempo.
No hay Q, SPI/TCP, DAC físico, reproducción sonora ni bloqueo real del hiloGUI:
se retiene la entrega de eventosQt mientras el productor simulado sigue activo.
Modela pausas de consumo/entregaGUI, no todos los efectos de un bloqueoQt real.

Admisión reproduce el criterio actualde run.flush: pending_batches≥4coalescea
RF. Cada caso1,4s con pausa0/50/100/250/500ms. El código deproducción no se cambió.

## Evidencia

Baseline `radio_chain_audit/gui_stalls_20261019_013712.json`.
Comparación `radio_chain_audit/gui_stalls_20261019_013749.json`.
Rutas completas bajo `diagnosticos/resultados_v17/`.

| Pausa GUI | Hueco audio actual | Variante aislada | Cola GUI variante |
|---|---:|---:|---:|
|0ms|36,6ms|24,3ms|1|
|50ms|22,0ms|24,0ms|3|
|100ms|42,7ms|24,1ms|5|
|250ms|228,2ms|25,5ms|13|
|500ms|510,3ms|42,3ms|25|

Son máximos de una corrida secuencial local; no garantía temporal ni estimación
estadística estable. El coldstart explica parte de máximos sinpausa.

La variante cambia exclusivamente en una subclase del diagnóstico: admisión por
pendientesDSP en vez de pendientesGUI; permite hasta50lotesGUI de20ms=1s en esta
prueba, manteniendo4deumbralDSP. Todos los lotes se entregan, sin latest-only.
Con pausa500ms, RFcoalescida acumulada actual440ms; variante20ms. DSPpendientepico2.
Confirmaelacoplamiento y demuestrauna direcciónposible; no demuestrauna solución
lista para producción. Simplemente elevar el límite global no es el cambio final.

## Criterios para implementación posterior

- Contadores separados: DSPpendiente, RF/audioGUI retenidos yedadmáxima.
- Límite por número de muestras/bytes ytiempo, no50lotes fijos. Lotes cambian con
  tasa, resolución, nodos y transiciones. Mantener fallo explícito al excederlo.
- MantenercontinuidadADC ydatoscompletos de registro/análisis; actualizaciones
  visuales pueden agruparse,sin descartarentrada ni audio válidos.
- ACKdeconfiguración debe quedar después de lotes del reloj anterior; resultados
  de generación anterior no deben reingresar a historias ni A0.
- Contar créditosDSP en éxito/error y apagar sinfugas/dobleconsumo.
- Medirmemoria/p95/p99/maxCPU; garantizar recuperación despuésde500ms y fallo
  explícito antepausas sostenidas mayores al presupuesto.
- Pruebasdirectas/US,FILTEROFF/RADIO/CH1,Gain/offset,Scan yStop/Play.
- CampañaQ separada, un propietario, snapshot y restauración, integridadADC,
  mínimosA0/ACK/played yholgura. Manteneraudio40k y políticasDAC existentes.

No se tocaron firmware, créditos, buffers ni clases de producción en esta ronda.


Repetición `radio_chain_audit/gui_stalls_20261019_013818.json`:10casos,
1.750.000 muestrasRF generadas yrecibidasGUI en cadauno. Elcampo`rf_continuity`
deesteinforme compruebaigualdaddecantidadesyloteRFpendientevacío, noCRCni
continuidadfísicadetransporte. Pausa500ms:actual498,4ms,variante35,2ms;colaGUI25,
DSPpendiente1. Refuerzaladirección,nolaaceptaciónparaproducción.
