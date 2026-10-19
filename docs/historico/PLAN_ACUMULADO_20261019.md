> Archivo histórico conservado el 19/10/2026. Las instrucciones y estados siguientes corresponden a sus fechas; para continuar usar el [estado vigente](../ESTADO_ACTUAL_V17.md). Los enlaces relativos Markdown se ajustaron desde la raíz original.

## Generador ampliado instalado — 19/10/2026

Seno150kHz/cuadrada200kHz con intermedias; restantes50k.3×120s poronda, comprobaciónCH2alfinal60s ySweep/Chirp pasados. Host/relay/MCU/UIintegrados,ajustesrestauradosgenOFF. [Resultado](../../docs/GENERADOR_200K_V17.md).

## WAV: candidato de dos bloques rechazado — 19/10/2026

Dos120s pasaron; tercero falló4,2048s en16/76226→A050k. No incorporado. Traza: read53ms,send42ms,huecochunks87ms. Investigar pausasread/send yreservaDAC. Qrestaurado,producciónintacta. [Evidencia](../../docs/DIAGNOSTICO_CORTES_WAV_V17.md).

## Seguimiento RADIO — tercer control de 120 s

ADC14/851→A0 40k pasó nuevamente: margen19,39%, cola2; tres controles recientes correctos. Corte previo no reproducido, causa abierta. Q restaurado8/1.6M genOFF, sin cambios productivos. [Evidencia](../../docs/VALIDACION_DESACOPLE_RADIO_V17.md).

## Diagnóstico refill RADIO — 19/10/2026

Dos controles ADC14/851 de 120 s pasaron con y sin guardado periódico; no se reprodujo el underrun ni se estableció causa. Producción intacta, Q restaurado ADC8/1.6M gen OFF. Mantener pendiente la aceptación global. Ver [comparación](../../docs/VALIDACION_DESACOPLE_RADIO_V17.md).

## Validación sostenida RADIO — 19/10/2026

[Resultado](../../docs/VALIDACION_DESACOPLE_RADIO_V17.md): **ADC14/851 no califica A0prolongado** (underrun~91ssegundo120,ADCintacto). ADC10max120,12FILTER20k60,16dual60pasaron;8/1.4035M60continuidadsinholgura. Siguiente:instrumentaciónrefill/try_codes/feed_resultsinJSONdurantecaptura. Qrestauradaylibre.

## Desacople GUI/DSP RADIO — 19/10/2026

[Experimento y criterios](../../docs/RADIO_GUI_DESACOPLE_V17.md): pausas de entregaGUI500ms generan huecoaudio510msactual; varianteaislada42ms,retención25lotesGUI. Incorporada con presupuesto1s/1.6Mmuestras/64MiB,contadoresDSP/GUI yliberaciónexacta. PruebasQADC14/851yADC10/1.25MconpausaGUI500ms+A0/Scanpasadas;validaciónprolongadapendiente.

## Auditoría canal RADIO con Astra — 19/10/2026

Ver [auditoría y medición](../../docs/AUDITORIA_CANAL_RADIO_ASTRA_V17.md). QuickwinsScan/copias/fade incorporados; siguientes: instrumentar latencia/colas y aislar alimentaciónDSP/A0 de pausasGUI. No reducir buffers/subirburstsinensayo.

# ETAPA IV: mejoras refinacion en RADIO

## Estado vigente — 18/10/2026

- [x] Salida de RADIO a 20/40/48 kHz en DSP/PC; A0 a 20/40 kHz.
- [ ] A0 a 48 kHz: resolver reloj efectivo y validar; no está implementado.
- [x] US / undersampling: dial combinado zonas1/2, DSP alias modular, Scan multitasa con RF estimada/ambigua y restauración; GUI/Q real validado193808. Escucha selectiva pendiente. Ver docs/RADIO_ANTENA_US_V17.md.
- [x] Gain 1–60 (manual y Auto), dial compacto con gradiente y volumen A0 con gradiente.
- [x] Auto gain con medición como máximo a 1 Hz y margen de 0,5 V por lado. Escucha prolongada pendiente.
- [ ] Información/nombre de emisora: definir qué puede obtenerse de la señal; sin detector implementado.
- [x] FFT → Radio: vista RF de CH1, marcas Scan blancas translúcidas, bandas laterales según banda RF y sintonía en cian; compatible con eje logarítmico. Prueba de escucha/uso físico pendiente.
- [x] Banda RF total seleccionable 6/8/10/12/20 kHz; predeterminada 8 kHz. Audio proporcional al ancho, sin tope fijo de 4 kHz.
- [x] Scan sugiere banda RF para el candidato sintonizado; opción «Sugerida» requiere selección manual. Estimación de contenido observado con persistencia bilateral y protección ante vecinos; no identifica el ancho nominal de la emisora. Validación sintética; pendiente señal real.
- [x] Sintonía máxima según FS real y banda RF; eliminado tope fijo de 600 kHz. Scan y DSP usan el mismo límite.

Prioridad funcional siguiente: escucha y recepción selectiva US; mejorar sugerencia de banda con confianza y ruido robusto. A0 a 48 kHz requiere un contrato de reloj y campaña física. La estabilidad de A0 a 8 bits/1,6 MS/s sigue abierta; no equivale a completar los puntos pendientes de esta etapa.

La lista original queda debajo como especificación del usuario; los cierres históricos posteriores no significan que toda la etapa IV esté terminada.

1) Agregar salida de radio a 20khz y 48 khz.
2) Boton OS tipo circulito en el selector de frecuencias, que elija modo undersampling: aprovechar el ALIASING para demodular frecuencias que estan arriba del NQYST; para ello, corregir el dial en base a la frecuencia de sampleo seleccionada (no recuerdo el calculo pero basicamente era la dif con nqyst sobre dos o algo asi?
3) Gain con dial pequeno, y tipo los de volumen que pusimos entre 1 y 50 escala gradiente a rojo. Idem dial volumen en generador radio.
4) Boton auto gain - llevar la senal sintonizada al maximo menos 0.5 de cada lado. leer datos auto gain no muy seguido, para no afectar otros procesos
6) La radio manda informacion sobre que radio es?? en el auto a veces la radio detecta y te dice tipo RADIO 10. 
7) En analisis agregar modo FFT Radio. Que en canal RADIO identifique los picos cuando doy escan en el panel de radio, con una linea traslucida blanca e identificar las bandas laterales proyectando el ancho de banda en bandas laterales traslucidas mas transparentes. Que la radio seleccionada se vea de otro color.
8) Permitir elegir ancho de banda en la solapa de RADIO, 4-5-6 khz.


## 14/10/2026 — RADIO: DSP separado y FFT visible medida

DSP en proceso único; FILTER OFF no crea proceso. Cola admitida limitada
a ocho, RF agrupable hasta un segundo ante pausas GUI, generaciones y ACK
ordenados. FFT/heatmap >=16384 con adquisición actualizan hasta 10 Hz;
SINGLE conserva resolución y ejecución explícita. Prueba física FFT65536
con RADIO40 + FILTER durante 120 s pasó: 168395328 RF, 4799234 audio,
cola pico3, DSP medio2,46ms/lote, 9,88FPS reales y 100% de exposición.
Vista temporal con trigger también pasó 120 s: 168448896 RF, 4800760 audio,
62,41 FPS reales con exposición 100%, DSP medio 2,319 ms y cola pico 3.
Informe: `diagnosticos/resultados_v17/radio_live_20261014_113834.json`.
Generador apagado: estabilidad del trigger con AM conocida pendiente.
Q restaurado a ADC10/909090 SPI y generador apagado. No aceptación analógica,
THRU/DAC, Scan concurrente ni holgura conjunta >=10% (envío medio8,69%).
Detalle: [eficiencia y evidencia](../../docs/AUDITORIA_EFICIENCIA_V17.md). Reiniciar GUI V17.
Este estado sustituye las menciones históricas a ausencia de prueba física.

## 14/10/2026 — Incorporación a producción completada

Seis perfiles CH1 ADC10/12/14 instalados y habilitados: 60 s + tres
arranques independientes de 120 s por perfil, sin errores de integridad.
Propuesta relay autorizada e incorporada; márgenes de integridad y holgura
separados. Q restaurado a ADC10/909090 SPI y generador apagado; firmware
nuevo permanece instalado. Detalles: [incorporación CH1](../../docs/INCORPORACION_CH1_V17.md).
Las secciones anteriores sobre ausencia de incorporación son históricas.

# ETAPA III : RADIO AM — V17

Decisión: toda la etapa III se desarrolla en V17, basada en la V16 actual.
V16 se conserva como referencia validada. Primera modalidad: AM convencional.
Plan de implementación y aceptación: [ETAPA_III_V17](../../docs/ETAPA_III_V17.md).

Vamos a incorporar posibilidad de recibir radio y mandarlo para A0.
Para eso hay que pensar con Astra un plan.
1) Agregar en Generador MODO: THRU que tome la salida de FILTER, CH1 , CH2 o RADIO (a implementar) y la mande por A0.
Este modo debe tener proteccion para evitar feedback peligroso si CH1 o CH2 o lo que sea esta leyendo A0; en cuyo caso lanzar advertencia y apagar.
2) Agregar en la solapa de trigger y filter otra mas que sea RADIO. RADIO debe leer CH1 o CH2, que van a venir de A2 y A3 desde una antena con adaptación, protección y filtrado antialias, poder elegir los picos, centrar ahi y sintonizar / demodular AM digitalmente, y mandarlo a canal RADIO o a FILTER. Empezamos por CH1, que ya adquiere a 1,4035 MHz, y cursamos al modo THRU para escuchar, grabar, etc.

3) Los modos de analisis deben aceptar tambien RADIO como input, igual que FILTER. RADIO seria la parte demodulada.

Entonces tendriamos: Por CH1 entran todas las freq entre 0 y 600 khz. Voy a poder ver los picos en el panel FFT. Panel RADIO permite elegir entre esos picos y demodular, mandar a RADIO. FILTER puede tomar RADIO como input. Puedo elegir FFT de la onda demodulada en RADIO o indirectamente en FILTER. Si se te ocurren mejoras decirme y lo vemos.



## 2026-10-13 — V16: ensayo8 repetido con holgura a1,4035MHz

Todos estos números son ordinales de ensayos de envío dentro deV16; no son
versiones del monitor. Se aclaró el nombre ante la confusión V9/V16.
Resultado: `experimentos/send1400_v16/RESULTADOS_CONTINUIDAD_1400.md`.
Ensayo9(CRC940bytes adelantado al productor): regresión, márgenes7,3/7,0%,
cola4 en repetición120s; detenido controladamente, restaurado, no aceptado.
Reporte descartado: `probe_1400_20261013_172129/report.json`, ZIP preservado.
Se recuperaron fuentes exactas del ensayo8. Repetición enfocada con observación
de cada trama: ADC8/CH1,114ticks/N3456, SPI solicitado38MHz, FIFO10, sin compresión.
Pasó60+3x120+600s, 1.430.754.624 muestras, CRC/seq/epoch/índices/timestamps/DMA,
dropped=fatal0; TODAS etapas cumplen margen>=10%, cola pico3/4 y slack>0.
Endurance:11,225% margen, slack1114,5us. Reporte `probe_1400_20261013_172922/report.json`
ok/headroom_accepted/restored/restore_integrity_ok=true. Picos3 aparecieron durante
medición; pico4 anterior sigue preservado, sin conocer cuándo ocurrió.
V16 estable restaurada ADC10/909090Hz SPI, generadorapagado, firmware idéntico,
9.088.408 muestras íntegras en10s; scheduler0/prioridad0,
CapAddNone y sinenv experimental. Fuentesactualesensayo8, runnerobservador
`qualify_margin.py`; ZIP `sources_spi38_pointer_observed_ensayo8.zip`.
No incorporación productiva/UI. Siguiente gate separado: analógico y GUI/FFT/
trigger/SINGLE/WAV bajo carga; considerar antecedente de cola4 antes de promover.

## 2026-10-13 — V8 aislada: 1,4035 MHz sostenidos

Resultado y evidencia: `experimentos/send1400_v16/RESULTADOS_SPI38.md` y
`experimentos/send1400_v16/probe_1400_20261013_165327/report.json`.
ADC8/CH1, ticks114/N3456, SPI solicitado38MHz (sin medir reloj físico), FIFO10,
READY acotado50us. Tres buffers alineados por referencia solapan armado y DMA;
sin copia adicional de payload ni compresión, con ACK final antes de liberar nodo.
Pasó60 +3x120 independientes +600s: 1,430,756,352 muestras recibidas,
CRC/secuencia/epoch/índices/timestamps/DMA y dropped=fatal0.
Prueba larga: margen11,209%, cola3/4, slack1122,3us; acepta integridad.
Campaña NO acepta holgura completa: ensayo60s llegó a cola4/4.
N6912/114 y N3456/115,N6912/115 sólo pantalla; N8192 cerró flujo.
Fuentes/runner actualesV8, ZIP `sources_spi38_pointer_v8.zip`, hashes verificados;
V7 permanece archivada. Pruebas locales y coordinación/fallo del pipeline pasaron.
No incorporado aUI/firmware/relay de producción; analógico/GUI/WAV sin validar.
Restauración exacta al snapshot actual ADC10/909090Hz SPI, generadorapagado,
firmware SHAidéntico, 9.088.408 muestras íntegras en10s. Scheduler normal0,
prioridad0, CapAddNone y sin SCOPE_EXPERIMENT_RT comprobados.
Siguiente trabajo separado: asegurar cola<4 en toda la aceptación antes de
promover holgura, y validar analógico/GUI antes de incorporación productiva.

## 2026-10-13 — SPI38 y esperas: aceptación aislada cercana a 1,4 MHz

Resultado en `experimentos/send1400_v16/RESULTADOS_SPI38.md`.
v7: ADC8/CH1, SPI solicitado a38MHz (reloj físico no medido), READY activo
hasta50us antes de poll, MCU sin busy_wait5us y relay SCHED_FIFO prioridad10.
Sin compresión. N3456/115ticks =1.391.304,348 muestras/s: pasó60s +3x120s
independientes +600s, CRC/secuencia/epoch/índices/timestamps/DMA y dropped=fatal0.
Márgenes medios~3,6%, cola pico4/4: acepta integridad, NO acepta margen10%.
A1.403.508,772, N3456 yN6912 pasaron60s pero fallaron en la primera repetición
independiente; NO aceptados. N8192 falló en ensayos cortos.
Fuentes actuales/runner=v7; fuentes previas y runners ZIP, hashes verificados.
No incorporación aGUI/firmware/relay de producción; precisión analógica no evaluada.
Reporte final: `experimentos/send1400_v16/probe_1400_20261013_161545/report.json`,
ok=true,restored=true,restore_integrity_ok=true. V16 restaurada aADC14 dual363636
SPI,generadorapagado con sus campos previos y hash de firmware idéntico.
3.634.688 pares íntegros en10s de recuperación. Política Linux normal0,
CapAdd=None y sin SCOPE_EXPERIMENT_RT confirmados. App experimental detenida.
Para1,4035MHz reproducibles: reducir coste por fragmento/superponer armado
conSPI mediante buffers por referencia, conservando controles y propiedad DMA.

## 2026-10-13 — Envío ADC8 CH1 aislado cerca de 1,4 MHz

Ver `experimentos/send1400_v16/RESULTADOS.md` y `PLAN.md`. Se ensayaron
cinco variantes (pipeline de paquetes; rearme DMA; validación O3/unroll;
optimización de salida; SPI solicitado a36MHz). v1 falló la referencia;
v2–v5 pasaron10s a1,221374MHz pero fallaron los24 casos objetivo de
1,391304/1,403509MHz con nodos3456/6912/8192: dropped1,fatal0,cola4/4,
slackpositivo. Ninguna aceptación sostenida ni promoción aUI/producción.
Mejor referencia corta: v5,13,68% envío medio,cola2/4,copia475,6us.
No convertir ese ensayo corto en tasa/margen aceptados.
Fuentes previas ZIP y hashes verificados; fuentes actuales/runner=v5.
V16 restaurada:ADC14 dual363636 SPI,generadorapagado con todos sus campos
originales,WAVIDLE; identidad de firmware exacta y10s de recuperación íntegra.
Último reporte:probe_1400_20261013_155821/report.json,restored=true,
restore_integrity_ok=true. App experimental detenida.
Siguiente investigación: tiempo entre fragmentos y pipeline por referencias
que superponga armado ySPI; el pipeline de copias v1 no mejoró la referencia.

# Plan de trabajo Etapa II 09-10-2026

## Prueba ADC8 CH1 a 1,4 MHz · 13/10/2026

Runner aislado probe_1400.py: ticks115/114 (1,391304/1,403509 MHz), nodos
3456/6912/8192, arranques independientes, caffeinate, respaldo y hashes.
Las seis combinaciones fallaron durante estabilización (<1s): cola pico4/4,
dropped=1,fatal=0, envío de nodo mayor al presupuesto. No aceptación larga;
no se habilita nueva tasa. Máximo de producción ADC8 CH1 sigue1,221374MHz.
Dos intentos de arranque fallaron por red Docker, no por ADC; se reparó sólo
red/contenedor experimental. Reportes preliminares conservados.
Q restaurado exactamente a ADC14 dual/363636 SPI y generador apagado con todos
los campos originales; firmware/relay previos, hash firmware idéntico.
Verificación10s:3634440 pares, sin errores de continuidad del decodificador.
[Evidencia](../../experimentos/maxfreq_v16/probe_1400_20261013_153113/RESULTADOS.md).
Para alcanzar1,4MHz hace falta mejorar envío/transporte y repetir la validación;
estos fallos no prueban un límite físico del ADC.

---

## Estado contrastado de Etapa II · 13/10/2026

Los cuatro puntos de Etapa II están implementados en V16: tramas compactas
CH1/CH2 con tiempo por fragmento; panel de filtros y canal FILTER; selección
de CH1, CH2 o FILTER en V(t), FFT, heatmap, medidas, trigger, Bode y Transfer;
y adquisición CH1 de alta tasa. Los cinco perfiles CH1 y los nueve duales
nativos están integrados en monitor, firmware y relay. La incorporación dual
y sus límites de margen constan en
[RESULTADOS](../../experimentos/maxfreq_dual_v16/RESULTADOS.md#incorporación-a-producción-completada).
Las notas de inicio y barrido que siguen documentan el estado de cada fecha;
sus frases «pendiente» sobre FILTER en Bode/Transfer y la integración dual
ya fueron superadas.

Pendientes actuales: validar precisión analógica, ambos canales y Bode/Transfer
con el cableado A0/A2/A3 confirmado; aceptación prolongada de los diez perfiles
intermedios (sólo cuentan con 60 s de integridad por perfil); grabación WAV
física sostenida en las nuevas tasas y resoluciones, con ventanas compatibles
con el límite de 30 s; enlace UART/R4; y, por separado, estudiar el coste del
DMA temporal y la estabilidad de la síntesis. El receptor numérico se midió
en ventanas físicas cercanas a 5 s; falta un ensayo prolongado de host con
continuidad y contadores, sin confundir frecuencia del timer con FPS pintados.
La GUI sí tiene medición real de paintEvent para 14 perfiles, de 5 s por caso:
[resumen FPS](../../diagnosticos/resultados_v16/fps_nativos_summary_20261012.json).

Ensayo del 13/10: el receptor numérico de producción completó 120 s en
ADC8 CH1/1221374 (146.473.056 muestras, cola pico 3) y ADC10 CH1/909090
(109.020.528, cola pico 2), con STATUS, CRC/secuencia/epoch/índice/timestamp
continuos y dropped=fatal=0. El Q volvió exactamente a ADC14 dual/363636,
generador apagado y WAV IDLE; se comprobaron 3 s de flujo restaurado.
[Evidencia](../../diagnosticos/resultados_v16/numeric_sustained_20261013_105929.json).
La GUI recibió otras ventanas de 120 s en ambos perfiles, pero no emitió
paintEvent observable en esa sesión; timer 62,51 Hz no equivale a FPS visible.
[Registro y hashes](../../diagnosticos/resultados_v16/fps_numeric_visible_20261013_110500.json).
Una prueba corta posterior sí observó pintado de PlotWidget y viewport.
En la repetición larga, ADC8 CH1 entregó 147.106.368 muestras en 120,45 s
y ambos contadores marcaron un promedio de 20,02 eventos de pintado/s
en esa sesión; timer35,82 Hz. La exposición de ventana no estuvo controlada
durante los 120 s, así que no se certifica FPS siempre visibles. ADC10 CH1
entregó 109.873.032 muestras en 120,94 s, pero quedó con cero eventos de
pintado y ventana no expuesta al cierre: su FPS sostenido sigue sin validar.
El Q se restauró. [Medición](../../diagnosticos/resultados_v16/fps_numeric_visible_20261013_111917.json).
La visibilidad de la ventana debe registrarse durante todo el ensayo antes
de atribuir diferencias de FPS a la carga del perfil.

La grabación WAV de producción cerró tres archivos por tasa ADC16/44101,
48004 y 76226, en ventanas de 29–30 s. Nueve archivos PCM16 estéreo tienen
cabecera/tasa/cuadros coincidentes con las muestras escritas y estado Guardado;
el validador de continuidad interno no informó cortes. En varias tomas actuó
el límite normal de 30 s. Q restaurado al perfil y generador previos, con 3 s
de continuidad. [Evidencia](../../diagnosticos/resultados_v16/wav_recording_live_20261013_111156.json).
Esto acredita grabación digital en esas tres tasas; siguen pendientes la
precisión analógica y el resto de las combinaciones WAV habilitadas.
Próxima campaña de tasas intermedias: runner con snapshot vivo completo,
resultados por caso y reanudación segura, un solo dueño Q, restauración en
finally y verificación de flujo. Para cada uno de los diez perfiles: 60 s,
3×120 s independientes y 600 s; exigir STATUS, CRC, secuencia, epoch,
índices/timestamps y dropped=fatal=0. Informar por separado integridad y
margen de cola/envío. El validador de 60 s anterior usa snapshot y salida
fijos del 12/10 y no debe ejecutarse como campaña nueva sin esa revisión.

## Compensación de fase ADC en Bode · 13/10/2026

Bode Tonos/Pulso/Sweep/Chirp muestra por defecto «Compensar retardo ADC».
Modelo por perfil: retardo entre ranks = repeticiones × (ciclos de muestreo
+ bits nativos + 3) / 54 MHz; ADC16 usa 16 repeticiones de ADC14.
Fuente: ST DS13086 rev10, tabla ADC1, página245, tCONV = ts + N + 3.
Se conserva resultado crudo; desmarcar permite compararlo. Cada curva conserva
su perfil y retardo, aun al agregar curvas de otra FS. FILTER hereda el instante
de su canal fuente; se mantiene la fase propia del filtro. Calibración medida
tiene prioridad en su banda, evitando descontar dos veces el retardo ADC.
Dos perfiles nuevos medidos: ADC14/40000 y ADC16/40000; se reutilizó el ensayo
ADC16/76226. Máximos residuales: 2,346° (ADC14/40, dispersión puntual),
0,470° (ADC16/40); repetición con GUI corregida ADC16/40: máximo0,241°.
ADC16/76226: máximo0,0362°. El resto de perfiles usa estimación del modelo,
no calibración física individual; no se promete fase cero exacta.
Todos los ensayos terminaron con continuidad y restauración exacta del Q:
ADC14/40000, SPI, generador apagado con campos previos.
[Resumen](../../diagnosticos/resultados_bode/phase_timing_summary_20261013.json).
Cinco tests nuevos pasan: fase de circuito conservada, origen FILTER, par
inverso, calibración sin doble corrección y toggles/historial GUI en los tres
paneles. 21/22 tests filter_ui pasan; falla WAV mono previamente observado
en el hilo anterior, fuera de Bode. No se modificó firmware ni calibraciones.

---

## Bode físico completado · 13/10/2026

A0 conectado directamente a A2/A3, ADC16 dual/76226 por SPI, seno de 1 Vpp
centrado en 1,65 V. Tres barridos CH2/CH1 de 20 Hz–5 kHz (11/11 puntos cada
uno), extensión 5–20 kHz (4/4) y FILTER Butterworth pasa bajos de orden 2,
fc=1 kHz (11/11). Sin errores de continuidad ni errores del worker.
Referencia formada con los dos primeros barridos y contrastada con el tercero:
error máximo 0,00325 dB y 0,04083 grados. FILTER frente al modelo: p95
0,02988 dB y 0,07902 grados. La fase cruda CH2/CH1 tiene sesgo creciente:
aproximadamente +11,72 grados a 5 kHz y +46,94 a 20 kHz; esta medición no
acredita fase absoluta sin corrección. No se escribió ni reemplazó calibración.
Q restaurado exactamente a ADC14/40000, SPI, generador apagado con sus campos
originales. Revalidación de 3 s: 119284 pares, 2036 STATUS, dropped=fatal=0.
Corregido el runner: restauración cuenta STATUS normales, no exige métricas
nativas «produced» en un perfil común. Informe final ok=true:
[Informe](../../diagnosticos/resultados_bode/20261013_120413_bode_v16_loopback.json).
Pendiente incorporar la nueva referencia por perfil y repetir de forma
independiente la extensión hasta 20 kHz antes de aceptarla como calibración.

---

## Integración dual terminada · 12/10/2026

Nueve perfiles dual incorporados y verificados junto con los cinco CH1.
14 perfiles nativos ×120s, ambos canales/timestamps NumericBatch,18 casos de
perfiles y transiciones, cero pérdidas/errores. RAM compartida entre modos
excluyentes:3012 bytes libres, cuatro slots, UART/WAV y referencia temporal
conservados. ADC10/495,36kHz y ADC12/410,26kHz mantienen integridad pero tuvieron
margen integrado9,03%/9,39%: etiquetas de margen retiradas. Flags restantes
verificados. 279 tests V16 y controles nativos pasan. Firmware nuevo instalado,
parámetros originales restaurados; integridad del perfil previo sigue fallando.
[Evidencia final](../../experimentos/maxfreq_dual_v16/RESULTADOS.md#incorporación-a-producción-completada).

## Cierre de barrido dual · 12/10/2026

Después de incorporar y verificar CH1, terminó el barrido dual con nueve perfiles
aceptados en 60 + 3×120 + 600s. Mayor tasa aceptada / tasa con margen por canal:
ADC8 632,41/597,01 kHz; ADC10 519,48/495,36 kHz; ADC12 437,16/410,26 kHz;
ADC14 363,64/355,56 kHz; ADC16 76,23/76,23 kHz. Integridad y hashes auditados.
Q restaurado al V16 integrado y campos originales; la integridad del perfil
previo sigue fallando como antes. Dueño host y caffeinate terminados.
Perfiles dual aún experimentales; integración MCU/whitelist/RAM y validación
física de producción pendientes. No todos los ticks intermedios tienen
aceptación larga. [Resultados y evidencia](../../experimentos/maxfreq_dual_v16/RESULTADOS.md).

Consideramos terminada la primera etapa
1) Vamos a mejorar la frecuencia de sampleo. Ahora estamos capturando timestamp muestra por muestra y perdemos tiempo ahi. Unifiquemos versiones de monitor, relay, sketch en V16, asi van a la par con monitor. Ver formas de mejorar sampleo; a) mandar un solo timestamp por bloque y calcular las demas, para ahorra tiempo en la captura y transporte. b) eliminar los canales adc 1 2, timestamp, etc. solo mandar v_in v_out ahora se van a llamar CH1 y CH2. hay que ajustar monitor, transporte etc.

2) Una vez concluido 1) vamos a eliminar el panel de seleccion de canales porque solo vamos a tener CH1 y CH2. Vamos a reemplazar ese espacio por un panel de filtros: low, band, hi, RC, butter, etc. Con selector de modo y perillas para el cut. El filtro tiene que poder elegir de que canal toma CH1 o CH2 y generar un canal nuevo que se llame FILTER.

3) En los paneles de analisis, todos, tenemos que poder elegir CH1 , CH2 o FILTER como entrada para los graficos, asi puedo ver por ejemplo CH1 y abajo el resultado del filtrado digital.

4) Una vez logrado esto explorar modo de super sampleo con un solo canal, para llevar la frecuencia al mango.



## Inicio de implementación · 9 de octubre de 2026

Astra revisó la Etapa II y Sol implementó el primer incremento aislado en
[Monitor V16](../../monitor/v16/README.md) y [Arduino/relay V16](../../arduino/v16/README.md).
SCP1 V4: timestamp por fragmento y CH1/CH2 compactos; 226 pares/trama,
diez tramas por nodo frente a diecinueve. Se conserva por ahora TIM5/GPDMA
como referencia independiente para validar los tiempos originales.
El monitor elimina canales ADC derivados y conserva índice/tiempo como metadata.
135 pruebas V16, validadores nativos y sketch UNO Q completo pasan; no se instaló firmware ni se
promovieron tasas nuevas. Filtros/FILTER y adquisición de un canal quedan en
los pasos posteriores. [Diseño, límites y aceptación](../../docs/ETAPA_II_V16.md).

### Validación física inicial V16

Instalados sketch/app/relay V16 en el Q. Tres ensayos de 120 s:
14 bits/40 kHz (4 796 416 pares), 14 bits/125 kHz (14 991 346) y
16 bits/62,5 kHz (7 495 666), sin errores ni dropped/fatal.
Generador y WAV20/40 con ADC14/100 kHz confirmados; todas las muestras WAV
reproducidas. Estado final V16 activa, ADC14/40 kHz y salida apagada.
No se subieron tasas ni se retiró el DMA temporal; UART y precisión analógica
pendientes. [Informe](../../docs/ETAPA_II_V16.md#ensayo-físico--9-de-octubre-de-2026).

### Filtros digitales V16 · 9 de octubre de 2026

Paso 2 implementado: panel Filtro digital, fuente CH1/CH2, RC, Butterworth,
Bessel, Chebyshev I/II y elíptico,
paso bajo/alto/banda y bypass, corte con perillas. FILTER conserva estado
entre bloques y se reinicia con cambios de configuración. Selector de trazas
V(t), FFT/heatmap, medidas y trigger permiten FILTER; CSV lo agrega, WAV
conserva las entradas originales. Paso 3 todavía requiere referencia/respuesta
seleccionables para Bode y Transfer, que siguen CH2/CH1.
[Uso y límites](../../docs/FILTROS_V16.md). No se modificó firmware ni se operó el Q.

# Etapa 1: Plan de trabajo para Osciloscopio Arduino*

Este es el plan de la app completa. Pero lo tenemos que ir haciendo paso a paso. Te paso todo asi cada paso no hacemos cosas que sean incompatbles con los proximos.

1) Una vez testeado el link viable MCU MPU de UNO Q via SPI con DMA y velocidad suficiente, integraremos a nuestros codigos pero de la siguiente forma, paso a paso:
2) Paso uno, una version con todo lo mismo que la anterior, pero con conexion de Python al UNO Q sin pasar por el R4
3) Paso dos: una version con todo lo mismo que la anterior, pero pudiendo elegir port Generador/Osciloscopio (Va a ser siempre el UNO Q) y transmisor (Puede ser el R4 via UART como antes o el UNO Q mismo via SPI directo al MPU). Esa eleccion implica que el IDE de Python se comunique con la App del UNO Q y le indique el modo de operacion, UART (al R4) o SPI (al MPU->USB). Es decir el UNO Q hay que conectarlo igual, aunque este con el R4 como puente, para poder controlar todo el sistema (ahora se conecta solo el R4)
4) Paso tres: poder configurar la adquisición, con opciones que dependan de los máximos de cada transmisor: bits, frecuencia de sampleo (usar sólo válidas). Para eso Python debe controlar la App del Q, y ademas adaptar su propia lectura a los datos que van a llegar; sobre todo los bits (la frecuencia de sampleo no le cambia nada en principio)
5) Paso cuatro: Agregar sección de generador de ondas a la izquierda del aparato. Actualmente solo genera on off, quiero un panel desplegable que permita hacer las operaciones tipicas de un generador: square, triangle, ramp, sine, ajustar frecuencia, hacer un swipe, un chirp, un spike.
6) Paso cinco: modo FFT, para analizar frecuencias. Espectro en cada t o evolucion en el tiempo por heatmap. Tambien trazar la curva de ganancia/transferencia en base al chirp, o swipe o spike.
7) Paso seis: panel para grabar sonido o reproducir sonidos grabados en formato wav.



## Estado al 2 de octubre de 2026

- **Paso uno:** implementado y validado en [V8](../../monitor/historico/v8/README.md), Q directo por USB.
- **Paso dos:** implementado en [V9](../../monitor/historico/v9/README.md): selector del Q de control, destino SPI/UART y puerto R4. Cambios en vivo y CSV continuo [validados con las placas](../../diagnosticos/MONITOR_V9.md).
- **Paso tres:** implementado en [V10](../../monitor/historico/v10/README.md): panel plegable, ADC de 8/10/12/14 bits y once tasas válidas de 1 a 31,25 kHz para ambos destinos, más 40/50/62,5 kHz exclusivas de SPI ([ensayo](../../diagnosticos/TASAS_SPI_V10.md)). [Validación física y CSV](../../diagnosticos/ADQUISICION_V10.md).
- **Paso cuatro:** [salida física implementada y probada](../../docs/GENERADOR_PASO4.md): DAC0 en A0, entrada V_IN en A2 y entrada V_OUT en A3. Firmware cargado y cuadrada de 2,5 Hz observada en el circuito; captura continua y perfiles SPI de 14/16 bits hasta 50 kHz verificados. Motor DAC con TIM6 + DMA4 y columna permanente a la izquierda: cuadrada, seno, triángulo, rampa, sweep lineal, chirp exponencial y pulso; rango ampliado 0,1 Hz–20 kHz, dial logarítmico, selector con dibujos de onda y valores numéricos. Generador SPI validado con señales reales, CSV continuo, STOP y SINGLE; reinicio DMA corregido; timestamps capturados en TIM5 CCR1 para evitar jitter de lectura CNT, con 40 perfiles repetidos de 14/16 bits sin discontinuidades ni intercambio de canales. Captura UART/R4 pendiente de comprobar el enlace físico.
- **Paso cinco (avance al 3 de octubre):** FFT en vivo y heatmap deslizante implementados en V10, con hasta dos canales apilados y controles de tamaño, ventana, solapamiento, escala, DC e historia. [Uso y pruebas locales](../../docs/FFT_V10.md). Agregados ejes de frecuencia logarítmicos y Bode automático mediante barrido senoidal por pasos: ganancia y fase V_OUT/V_IN, restauración del generador al terminar. Bode [validado físicamente entre 2 y 100 Hz; recorrido ampliado hasta 1 kHz](../../diagnosticos/BODE_V10.md) con ADC de 16 bits, CSV sin saltos y restauración exacta del generador. Control de puntos por década, opciones con checks neutros y escalas FFT enlazables con margen e histéresis. Asentamiento y ciclos de medición independientes, con tiempo mínimo estimado del barrido. Calibración relativa de ganancia/fase y recorrido hasta 20 kHz completados con ADC de 16 bits a 50 kHz; detalles en el avance de Bode al final del plan.
- Paso seis en V13: grabación WAV y reproducción por A0 implementada en candidato; validación física de reproducción pendiente.

### Último avance de Bode

- Marcadores en cada frecuencia medida y contador de puntos válidos de ganancia y fase.
- **Agregar** conserva hasta cinco barridos con colores de la paleta de entradas; **Repetir** borra la comparación e inicia un nuevo barrido.
- Sombra translúcida tenue agregada a las curvas y corrección instrumental por referencia de ganancia/fase implementada.
- Validación física y calibración relativa entre canales completadas entre 20 Hz y 20 kHz, ADC 16 bits / 50 kHz: 31/31 puntos, CSV sin saltos y restauración exacta. Referencia anterior invalidada por cableado incorrecto; reemplazada por el ensayo 20261003_123522_633848, con 581 579 filas CSV sin saltos. La repetibilidad de la nueva referencia aún no fue medida. [Evidencia y límites](../../diagnosticos/BODE_V10.md). Otros perfiles ADC requieren su propia referencia.


### Ensayo de adquisición rápida · 4 de octubre de 2026

- Conjunto estable V10/V8 config respaldado y fuentes conservadas.
- Nuevos [V11](../../monitor/historico/v11/README.md) y [V9 Fast](../../arduino/historico/v9_fast/README.md): SPI a 32 MHz, CRC más rápido y sellado único; 100 kHz por canal en 8/10/12/14 bits. 16 bits sigue hasta 50 kHz, UART hasta 31,25 kHz.
- 100 kHz / 14 bits pasó 120 s, casi 12 millones de pares sin huecos, rangos inválidos, dropped ni fatal. 18 segmentos verifican resoluciones, ida/vuelta a 16 bits y generador concurrente hasta 20 kHz.
- V(t), FFT y heatmap con USB real a ~100 000 pares/s; heatmap 30 s, CSV de 734 350 filas sin saltos. V11 limita el pintado FFT/heatmap a 20 Hz a alta Fs, conservando todas las muestras y pasos del análisis.
- 125 kHz perdió nodos; 200/250 kHz no se ensayaron después del fallo. No se ofrecen en V11.
- Validación analógica de ambos canales pendiente: A2 recibe una senoide limpia, A3 una señal muy pequeña; confirmar conexión directa para medir precisión. No se alteró la calibración de Bode existente.
- [Estudio, evidencia, límites y restauración](../../experimentos/tasas_spi/README.md). Este ensayo no adelanta el paso seis de WAV.

- Diagnóstico posterior de 125 kHz: [mediciones con y sin PC](../../experimentos/tasas_spi/DIAGNOSTICO_125.md) confirman atraso sostenido del consumidor (473/465 µs por trama frente a 420 µs disponibles). Cola llena, CRC correcto y fatal=0 en ambos; pendiente separar costos MCU/driver Linux. Firmware conservado.
- Medición MCU aislada de 125 kHz: [instantáneas con/sin DAC](../../experimentos/tasas_spi/resultados/mcu_20261004/README.md), cola 4/4 y envío de nodo 18,17–18,36 ms frente a 16,384 ms. Armado DMA ~20 µs; copia ADC ~432–434 µs/nodo. No se cambió V9 Fast. Sigue pendiente optimizar y validar la coordinación/preparación por fragmento antes de habilitar 125 kHz.

### Optimización P992 · cierre del 4 de octubre de 2026

- [Candidato P992 aprobado](../../experimentos/tasas_spi/opt125/README.md) a 14 bits / 125 kHz por canal: tramas SCP1 V3 de 992 bytes, 19 fragmentos por nodo. P512 no alcanzó el margen.
- Envío medio de 14,118/14,067 ms por nodo sin/con cuadrada de 2,5 Hz: margen medio medido de 13,83/14,14 %, cola máxima 2/4.
- Dos capturas normales de 120 s, 14989425 pares cada una, sin errores ni pérdidas; 119 comandos concurrentes con DAC activo y nueve etapas de transición aprobadas.
- Monitor experimental con USB real: V(t), FFT, heatmap, trigger/SINGLE y CSV de 507551 filas sin saltos; Qt offscreen. Precisión analógica de ambos canales y disparo relacionado al generador siguen pendientes.
- V9 Fast normal restaurado a 14 bits / 100 kHz y cuadrada de 2,5 Hz; 298762 pares verificados sin pérdidas. 38 archivos originales intactos y 185 pruebas locales aprobadas. [Aceptación y restauración](../../experimentos/tasas_spi/opt125/resultados/aceptacion_p992.json).
- P992 queda independiente; V11 conserva su límite de 100 kHz hasta una promoción posterior. Este ciclo de optimización queda cerrado.

### Comparación analógica posterior · 4 de octubre de 2026

- [A2/A3 aprobados con señal común directa](../../experimentos/tasas_spi/opt125/ANALOGICO.md): ADC de 14 bits, seno ~1996,805 Hz, cinco capturas de 10 s entre V9 Fast (62,5/100 kHz) y P992 (62,5/100/125 kHz).
- Amplitud ~1,216 V pico en ambos canales, diferencia relativa observada <0,02 %, residuo RMS 6,8–7,5 mV, fase relativa ~1,53°; cero saltos, rangos inválidos, dropped o fatal.
- Esta prueba cierra la comparación pendiente para ese estímulo y resolución; no calibra tensión/reloj ni valida todas las frecuencias o resoluciones. Calibraciones Bode conservadas.
- P992 aún no se promovió a V11. Firmware, relay y perfil anterior se restauran tras la medición.

### Integración en nueva versión · 4 de octubre de 2026

- Nueva pareja [Monitor V12](../../monitor/historico/v12/README.md) + [firmware V11 P992](../../arduino/historico/v11_p992/README.md), independiente de los experimentos. Receptor dentro de V12 y relay propio junto al firmware, SCP1 V3/992 a 32 MHz, hasta 125 kHz por canal.
- V10/V11 y V8 config/V9 Fast se conservan en sus carpetas. Nuevas entradas de VS Code, catálogo App Lab y selección explícita `--firmware v11_p992`; defaults de herramientas conservados.
- 198 pruebas locales aprobadas y firmware/relay ARM compilados. La evidencia sostenida y analógica de P992 corresponde a ADC14/125 kHz con los estímulos documentados; UART físico y calibración absoluta siguen pendientes.
- Verificación física de integración mediante `diagnosticos/verificar_v12.py`, con seno de 2 kHz, trigger/SINGLE, V(t), FFT, heatmap y CSV, restaurando el generador al terminar.
- [Integración aprobada con USB real](../../capturas/validacion_v12/20261004_204139_688307/informe.json): SINGLE con seno de ~2 kHz / 2,46 Vpp, FFT, heatmap y CSV de 511082 filas continuo. Generador restaurado a 2,5 Hz; nueva pareja activa en Q a ADC14/125 kHz. Sigue el paso seis de WAV; no se hizo un nuevo Bode físico ni se validó UART/R4.

### Optimización 16 bits · 5 de octubre de 2026

- Se implementó el **Camino A**: reloj de ADC acelerado a **50 MHz vía PLL2** (HSE 16 MHz / 2 * 25 / 4 = 50.000 MHz, dentro de los 55 MHz nominales del STM32U5).
- Desbloqueado **16 bits a 62,5 kHz** por canal conservando el oversampling $\times 16$ intacto (período 16 µs, tiempo nominal de conversión 14,08 µs, antes de latencias; margen nominal 12%).
- Validado físicamente en la placa ([informe](../../capturas/adc16_rate/test62k5_20261005_002648/informe.json)): 311.409 pares en 5 s a 62.275 pares/s sostenidos, dropped=0, fatal=0.
- Interfaz gráfica de [Monitor V12](../../monitor/historico/v12/app.py) actualizada para permitir 62,5 kHz en 16 bits; suite completa de tests aprobada (`OK`).


- Revisión posterior: [ADC16 V12](../../diagnosticos/ADC16_V12.md). Diagnóstico corregido para restaurar el perfil observado; 7.495.680 pares en 120 s sin discontinuidades, dropped ni fatal. Suite de 206 pruebas aprobada. El reloj ADC de 50 MHz afecta todos los perfiles y requiere comprobar las referencias Bode anteriores.

- Correcciones de reloj compiladas y cargadas: [120 s finales](../../capturas/adc16_rate/test_20261005_011511_251289/informe.json), 7.495.906 pares sin errores. Comparación analógica 50/62,5 kHz a 2/10/20 kHz: amplitud estable (<0,23%), residuo mayor a20 kHz; no certifica ENOB ni reemplaza calibración Bode. Perfil y generador del usuario restaurados.

### Evaluación V13 / PyQt6 · 5 de octubre de 2026

- V13 independiente conserva el receptor, assets y una copia de las referencias
Bode; requiere PyQt6 en entorno separado. Firmware V11 P992 sin cambios.
- V12 sigue disponible con PyQt5. Backend pyqtgraph seleccionado explícitamente;
pruebas Qt5 y Qt6 en procesos distintos.
- Ver [uso y evaluación](../../monitor/historico/v13/README.md). No se inició WAV ni se alteró
la adquisición; la mejora de rendimiento se evalúa por escenario.

- Validación V13:24 pruebas Qt6 y208 Qt5 aprobadas. [Comparación](../../diagnosticos/QT6_V13.md) con40 cuadros medidos por escenario: Qt6 más lento en el ensayo offscreen; V12 se conserva como referencia. Prueba manual de pantalla pendiente.


### Paso seis: grabación WAV · 5 de octubre de 2026

- V13 incorpora selector CSV/WAV junto al estado de grabación y conserva RECORD/STOP REC. WAV estéreo PCM16: A2 izquierda, A3 derecha; Fs confirmada, todas las muestras, centro ADC fijo sin filtros ni AGC.
- Archivos en capturas/v13, numeración compartida con CSV, máximo 30 s y cabecera finalizada al detener/cerrar. Las discontinuidades detienen WAV explícitamente; no se rellenan huecos. Demo continúa disponible en CSV.
- Astra fue solicitado para planificación, pero estaba indisponible por límite de uso; se siguió el alcance concreto autorizado con implementación/revisión Sol. No se operó hardware ni se cambió firmware.
- Pruebas locales Qt6 del grabador y regresiones anteriores aprobadas. Validación WAV con entradas reales pendiente; siguiente etapa: decidir botón de reproducción y salida física.

### Paso seis: reproducción WAV candidata · 5 de octubre de 2026

- Modo WAV en V13: archivo local, L/R/Mix, Reproducir y Detener; conversión antialias a 20 ksps, eliminación de media y ajuste Vpp/offset a códigos DAC12.
- Firmware aislado V12 Audio y relay MPU propio con créditos, buffers acotados y parada neutral ante falta de datos. V11 P992 sigue predeterminado.
- 51 pruebas locales Qt6/protocolo/firmware aprobadas; sketch compilado (107000 bytes flash, 192524 RAM). Respaldo V11 conservado. Carga y ensayo A0→A2/A3 pendientes de autorización.
- Ver [activación y restauración](../../arduino/historico/v12_audio/README.md) y [uso](../../monitor/historico/v13/README.md).

### V12 Audio cargado y ensayo físico inicial aprobado

Autorizado y cargado el 5 de octubre: firmware MCU V12 Audio y relay MPU propio
quedaron activos. WAV estéreo 44,1 kHz→20 ksps, L=997 Hz, R=2003 Hz,
Mix con ambos tonos comprobados en A2/A3; 40000 muestras por pasada,
sin underrun ni discontinuidades ADC14/31,25 kHz. Detener→IDLE y
restauración del generador confirmados. Falta ensayo sostenido y evaluación visual.
VS Code: «Monitor V13 — WAV A0 (V12 Audio)» habilita el protocolo nuevo.
Informe: diagnosticos/resultados_wav/20261005_fisico.json.

### Evaluación de mayor tasa WAV

Iconos vectoriales por modo y etiqueta Wav en V13. Siguiente candidato:
40 ksps y luego 50 ksps con tasa negociada; 20 ksps sigue vigente.
Ver [cálculos y pruebas necesarias](../../docs/WAV_TASAS.md).

### Tasas WAV negociadas probadas · 5 de octubre de 2026

V12 Audio MCU/relay actualizados y activos; selector Salida 20/40/50 kHz en V13.
Ensayos de 120 s aprobados: WAV40/ADC14-40k, WAV50/ADC14-40k y
WAV50/ADC14-100k. WAV50/ADC125 falló dos veces con integridad ADC;
Play bloquea ADC mayor de 100 kHz. STOP y restauración confirmados.
57 pruebas locales y regresiones Qt6 adicionales aprobadas. Respaldo previo
osciloscopio_20261005_181834_429412.zip y fuentes 20 ksps conservadas.
Ver docs/WAV_TASAS.md e informes diagnosticos/resultados_wav.

### 2026-10-06 — Preparación completa del Q desde V13

- Agregado botón **Preparar Q** para instalar/actualizar app V12 Audio, firmware
  MCU y relay en el dispositivo USB seleccionado, con respaldo si la app existe.
- Progreso en el estado, log completo, trabajo en segundo plano y confirmación
  de la primera trama SPI antes de declarar el Q preparado.
- Verificación local: 3 pruebas de preparación y 13 de autoinicio/controles Qt.
- Pendiente: validar instalación completa en un Q nuevo y tras apagado/encendido.

### 2026-10-06 — Corregir READY inicial del relay

Reproducido fallo real tras cargar MCU: app inicia, relay espera un flanco que
puede haber ocurrido antes de la espera. Se admite un único READY inicial alto,
con drenaje de eventos y validación íntegra; siguientes tramas requieren nuevos
flancos. Relay compilado e instalado; autoinicio físico confirmado. Pruebas
locales de firmware/protocolo/autoinicio: 11 OK. Nueva prueba de apagado/encendido
pendiente; evidencia de adquisición en resultados_autoload.

### 2026-10-06 — Valores iniciales del generador

V13: Wav 50 kHz (con reducción por capacidades), amplitud compartida 2 Vpp,
salida apagada y casilla centrada. Al conectar en Continuo se aplica el estado
preparado; modos finitos esperan disparo manual. 19 pruebas Qt/Wav OK.

### 2026-10-06 — Botón único de conexión

Eliminados checkbox Autoiniciar y botón Desconectar independiente. Conectar
abre el transporte existente primero; si no está disponible, verifica/inicia
la app instalada y el relay. Mismo botón cancela o desconecta según estado,
con tres iconos plug. Preparar Q ocupa el antiguo lugar de Desconectar.
32 pruebas de conexión/autoinicio, Qt y monitor pasaron.

### 2026-10-06 — Dial de amplitud Wav durante Play

Dial Wav 0–3,3 Vpp; amplitud aplicada en bloques pendientes, con transición
suave de un bloque. Preparación a escala completa permite subir desde cero sin
remuestreo ni reinicio. Cola de niveles conserva sólo el último ajuste y se
atiende durante playback. Más espacio entre icono y texto de conexión.

### 2026-10-06 — Recuperación de A0 tras Wav

Dial Wav reducido a 64 px. Corregido cierre: Stop con ACK antes de cerrar USB,
y recuperación de sesión anterior al conectar. UNDERRUN/FAULT conserva Stop.
Validación física: seno 1 kHz/2 Vpp en A2, Wav 50 kHz y dial 2→1 Vpp;
cierre sin excepción, salida final apagada. Evidencia en
resultados_wav/20261006_recuperacion_generador_dial.json.

### 2026-10-06 — Apagar salida al desconectar

Desconectar/cerrar libera Wav y confirma generador deshabilitado a 0 V antes
de cerrar USB. Pruebas locales de shutdown, monitor e instalación: 21 OK.

### 2026-10-06 — Reconexión tras corte de alimentación

Reproducido con contenedores detenidos: el socket del túnel ADB abre aunque
el relay remoto esté cerrado y después entrega EOF. Conectar ahora exige datos
por MSG_PEEK antes de validar el enlace; EOF/silencio activa comprobación e
inicio de app/relay. Nueve pruebas de conexión/autoinicio OK.

### 2026-10-06 — Corregido paso por cero al iniciar barridos

V12 Audio generator::apply detiene DMA con el primer valor de la nueva onda
si está habilitada; salida apagada mantiene 0 V. Compilado/cargado en Q con
respaldo osciloscopio_20261006_114127_867106.zip. Siete pruebas locales OK.
Tres arranques Sweep + tres Chirp, 20→2000 Hz/2 s, seno 2 Vpp/offset 1,65 V:
ventana inicial medida A2 a 40 kHz sin caída inferior a 0,5 V. Salida final
apagada. Evidencia: resultados_autoload/20261006_sweep_start.json.

### 2026-10-06 — FFT de SINGLE anclada al trigger

SINGLE en FFT/heatmap espera ventana FFT completa y calcula sobre copia del
bloque con 10 % pretrigger. STOP mantiene la captura y RUN sigue usando las
muestras recientes. Prueba sintética con pulso ya fuera del bloque más reciente
verifica conservación del espectro y regreso a FFT en vivo. Amplitud/offset:
texto de dos decimales y resolución interna 1 mV.

### 2026-10-06 — SINGLE: bloque FFT de mayor energía

Selecciona entre bloques próximos que contienen el trigger el de mayor energía
AC ponderada por la ventana FFT, sumando canales seleccionados. Copia fija del
bloque elegido; indicador SINGLE naranja dentro de los gráficos, borrado al
volver a RUN o rearmar. Prueba de pulso verifica ventana energética y marcador.

### 2026-10-06 — Chirp intermitente: fin prematuro

Reproducido antes de la corrección: el octavo Chirp de 20→2000 Hz/2 s
quedó detenido a los 0,1 s, con confirmación OK. generator::tick convertía
la diferencia de ticks directamente a uint64_t: una diferencia negativa
terminaba inmediatamente el barrido. Ahora conserva la diferencia signed
y descarta callbacks con tiempo anterior al arranque. Prueba nativa reproduce
ese caso y verifica también la finalización normal; siete pruebas locales OK.
La relación exacta entre el callback y el fallo físico es una hipótesis;
no se instrumentaron los ticks del MCU durante el fallo.

Firmware compilado y cargado, con respaldo
respaldos/unoq/osciloscopio_20261006_123319_510143.zip. Después: 24 Chirps
consecutivos, seno 2 Vpp/offset 1,65 V, ADC 14 bits/40 kHz; todos activos
a los 0,1/0,6/1,2/1,8 s y finalizados a los 2,1 s, sin errores de estado.
Salida apagada al terminar. Informes:
diagnosticos/resultados_autoload/20261006_chirp_repeticiones.json (antes) y
20261006_chirp_timer_corregido.json (después). La repetición sin fallos
no descarta otros problemas intermitentes.

### 2026-10-06 — Documentación y organización

Usuario confirmó que Chirp funcionó tras la corrección. README principal y
los índices describen el instrumento, audio y flujo MCU/MPU/relay; versiones
con enlaces al final. Guías activas apuntan a V13/V12 Audio; V12/V11 P992
continúa disponible y las herramientas de consola conservan sus defaults.
Cuatro sketches `.bak` agrupados en respaldos/historico, contenido conservado
y referencias actualizadas. Índices nuevos de diagnósticos y respaldos.

### 2026-10-06 — Presentación e imágenes del README

Portada con badges, especificaciones y capturas actuales de V(t), FFT,
heatmap y Bode; son demostraciones sintéticas, Bode ilustra filtros RC.
Secciones independientes Python, relay C/MPU y firmware C/C++ Arduino/MCU,
con enlaces a guías ampliadas de timers, DMA, IRQ, READY y propiedad de buffers.
Las versiones siguen al final. Capturas en assets/monitor_{vt,fft,heatmap,bode}.png.

### Formato del sistema y saltos Wav · 6 de octubre de 2026

Los controles, estados y ticks numéricos de los monitores V13/V12 usan
separadores del locale del sistema. CSV, protocolos y nombres de archivo
conservan formatos independientes del idioma para mantener compatibilidad.
En Wav, −10 y +10 junto a Play saltan diez segundos durante reproducción.
Se usa la posición reproducida confirmada, se limita al inicio/final y se
confirma Stop antes de comenzar una sesión DAC nueva desde el destino.
El estado muestra la posición absoluta en el archivo tras cada salto.
Hay una breve interrupción por parada y recarga de buffers; no es un salto
continuo sin pausa. Verificado con 34 pruebas locales; saltos en hardware
pendientes de probar con el Q.

### 2026-10-06 — Final de Wav en silencio

V12 Audio libera la sesión con el generador anterior deshabilitado, tanto
al finalizar como con Stop. Ya no restaura una onda continua activa.
Seis pruebas nativas verifican EOF y Stop con salida deshabilitada.
Firmware cargado con respaldo. Prueba física: generador seno habilitado antes
de Wav50/ADC14-40k; EOF confirmado y generador enabled=0/running=false después.
Evidencia: diagnosticos/resultados_wav/20261006_final_silencio.json. Salida final apagada.


### 2026-10-06 — Pulso experimental de microsegundos

Variante independiente arduino/historico/v13_pulse, app Scope Pulse US V13 Experimental.
TIM6 one-shot devuelve DAC al nivel bajo por hardware; DMA4 no se usa durante
ese pulso. Protocolo con duración µs y capacidad anunciada; V13 ofrece 100–65535 µs
sólo si el Q confirma soporte. Ancho inicial sigue equivalente a 1 ms (1000 µs).
V12 Audio mantiene el contrato ms y sus fuentes/app como respaldo.
18 disparos físicos ADC14/100 kHz: seis de 100, 200 y 1000 µs, anchos coincidentes
con resolución de 10 µs. Wav50 completó un segundo; salida final apagada.
La variante quedó activa, ADC14/40 kHz. Falta comprobar flancos y precisión con
osciloscopio externo. Detalles y vuelta a V12 Audio: arduino/historico/v13_pulse/README.md.
Respaldo previo: respaldos/unoq/osciloscopio_20261006_190836_603319.zip.


### 2026-10-06 — Bode con tres paneles

V13 incorpora Tonos, Pulso y Sweep/Chirp, con inicio manual e historiales
independientes. Los métodos transitorios usan FFT de ambos canales sobre
la misma captura, nivel previo y cola; rechazan discontinuidades, respuestas
incompletas y frecuencias sin referencia suficiente. El umbral relativo se
calcula dentro de la banda medida, excluyendo DC. 31 pruebas locales pasaron.
Con A0 conectado a A2/A3, Chirp y Sweep a ADC14/40 kHz cubrieron respectivamente
5117/5138 y 5128/5128 puntos entre 20 Hz y 2 kHz. Ganancia mediana próxima
a 0 dB; fase mediana cercana a 3 grados sin calibración instrumental.
El pulso de 100 µs pasó una vez a 40 kHz pero falló repeticiones por referencia
insuficiente, también a 100 kHz: no se considera validado de forma repetible.
Evidencia: diagnosticos/resultados_bode/20261006_barridos.json.
Al terminar se restaura ADC14/40 kHz y salida apagada.


### 2026-10-06 — Corrección de referencia previa en Bode Pulso

La captura rechazada contenía el pulso en ambos canales. A3 veía el flanco
una muestra antes que A2: esa muestra entraba en la estimación de ruido previo
y elevaba artificialmente el umbral FFT. Se excluye un margen de 1 ms (mínimo
dos muestras) sólo de las estadísticas de referencia; la FFT conserva toda
la captura y el desfase real entre canales. No se reduce el umbral de ruido.
32 pruebas locales pasaron, incluida regresión del flanco adelantado.
Seis pulsos físicos consecutivos de 100 µs a ADC14/100 kHz: todas las frecuencias
20–2000 Hz válidas, ganancia mediana -0,04 a +0,07 dB y fase dentro de ±0,3°.
Seis capturas a 40 kHz también completaron, con 93–97 % de puntos válidos;
la fase mediana varió hasta 9,1°, compatible con una muestra de 25 µs
a aproximadamente 1 kHz. Para fase con pulso de 100 µs se recomienda 100 kHz;
40 kHz conserva una limitación de resolución temporal. No se corrige esa fase
automáticamente ni se considera validada su precisión a 40 kHz.
Evidencia: diagnosticos/resultados_bode/20261006_pulso_corregido_100k.json
y 20261006_pulso_corregido_40k.json. Estado final ADC14/40 kHz, salida apagada.


### 2026-10-06 — Rango y atenuación de salida en Bode

Los tres paneles arrancan en 20–5000 Hz. Pulso y Sweep/Chirp ya no
descartan la ganancia por amplitud baja de V_OUT: la referencia válida
se determina con V_IN. Se conserva la ganancia estimada y sólo se omite
la fase si V_OUT no supera el umbral de ruido. Bajo ese umbral, la ganancia
puede representar el piso de ruido y no la atenuación real del circuito.
33 pruebas locales pasaron, incluyendo salida de -80 dB y salida sólo ruido.
No se realizó una nueva prueba física con filtro en este cambio.


### 2026-10-06 — Seis correcciones de revisión Bode

Se implementaron los seis hallazgos de docs/REVISION_BODE_ASTRA.md:
referencia histórica deshabilitada sin identidad instrumental verificada;
ajuste de tonos con todas las muestras, sin decimación; plazo de captura
no renovado por consultas; rechazo correlacionado mostrado con motivo;
redibujado de resultados al regresar a Bode; y bloqueo del inicio transitorio
con configuración ADC pendiente. 39 pruebas locales pasaron, incluidas
seis regresiones en tests/v13/test_bode_review.py. No se modificó firmware
ni se operó el Q. Sigue pendiente aceptación física 20–5000 Hz con filtro.


### 2026-10-06 — Nuevas referencias instrumentales Bode

A0 conectado directamente a A2 y A3. Tres capturas por método y perfil,
20–5000 Hz, ADC14/40 y 100 kHz; dos capturas para referencia y tercera
independiente para aceptación. Se aceptaron Tonos y Sweep a ambas tasas,
y Chirp a 100 kHz. Pulso 100 µs a ambas tasas y Chirp a 40 kHz no pasaron
la repetibilidad exigida para toda la banda; no se guardan como calibración.
El monitor identifica serie/app activa/hash del binario instalado por App Lab
y exige perfil/método compatible; resultados e historiales retienen identidad.
La identidad no lee flash MCU: una programación externa obliga a invalidar
la referencia. Dos nuevos barridos físicos de Tonos verificaron carga y
aplicación automática: error máximo 0,044 dB/0,40° a 40 kHz y
0,042 dB/0,16° a 100 kHz. 40 pruebas locales aprobadas.
Evidencia: diagnosticos/resultados_bode/20261006_referencias_validacion.json
y 20261006_referencia_tonos_validacion_monitor.json.
Estado final ADC14/40 kHz, salida apagada; firmware experimental sin cambios.


### 2026-10-06 — Chirp sin curva: aceptación de cola

Se reprodujo el rechazo de un Chirp de 5 s con cola de 0,5 s. El chequeo
de asentamiento tomaba el último 10 % de toda la captura, que incluía
estímulo; limitarlo a toda la cola todavía incluía el decaimiento legítimo
del circuito. Ahora se evalúa sólo el quinto final de la cola configurada
(mínimo 16 muestras), manteniendo toda la captura para la FFT y el mismo
umbral de ruido. Una salida que no termina sigue siendo rechazada.
14 pruebas locales aprobaron, incluidas cola con decaimiento RC y cola
realmente no asentada. Ensayo físico ADC14/40 kHz, Chirp 20–5000 Hz de
5 s + 0,5 s: captura completa, 27881 puntos en curva y 2948 puntos con
ganancia/fase finitas. Esa cobertura describe la salida medida, no valida
la exactitud de un filtro desconocido. Cuatro ensayos previos de 2 s
también dejaron curvas. Estado final 14 bits/40 kHz, salida apagada.
Evidencia: diagnosticos/resultados_bode/20261006_chirp_cola_5s_diagnostico.json.


### 2026-10-06 — Estados centralizados

Conexión y visualización contiene Adquisición, Generador y Análisis en
boxes de 34 px, con texto abreviado y detalles completos en tooltip.
Se retiran mensajes de generador, análisis/Bode y trigger de los laterales;
la espera de trigger/SINGLE permanece visible arriba. Leyendas de curvas y
datos del archivo Wav se conservan junto a sus controles. Las fuentes de
mensajes notifican cambios; se mantiene el comportamiento de adquisición,
Wav y Bode. Cuatro regresiones verifican actualización, aislamiento de
paneles, espera de trigger y cambios de modo Wav. No se operó el Q.


## 2026-10-06 · Promedio Bode pulso

Selector Pulsos de 1 a 64, predeterminado 8. Estimador H1 por espectros
cruzados, ventanas iguales respecto del flanco, asentamiento entre disparos,
progreso por captura y fase filtrada por coherencia. Sweep/Chirp conserva
su método. No se modifica firmware ni se reutiliza la calibración antigua
para H1. Seis regresiones nuevas; 51 pruebas locales aprobadas.
Comparación física con A0 directo a A2/A3: dos repeticiones de N=1,4,8,16
a ADC14/40 y 100 kHz. Ocho demora unos 7 s; reduce ruido de ganancia,
pero no elimina errores instrumentales de fase (especialmente a 40 kHz).
Evidencia: diagnosticos/resultados_bode/20261006_promedio_pulsos_fisico.json
y 20261006_promedio_pulsos_sintetico.json. Panel sin barra lateral verificado.
Al finalizar se restaura ADC14/40 kHz y se apaga la salida.


## 2026-10-07 · Calibración instrumental Bode

Se conserva la tanda previa de 8 bits y los perfiles completados de 10 bits
(27 referencias aceptadas). Por pedido del usuario se limita el foco final
a las opciones actuales desde 32 kHz: 14 bits a 40/50/62,5/100/125 kHz y
16 bits a 40/50/62,5 kHz. La opción anterior es 31,25 kHz y quedó fuera.
Se completaron los ocho perfiles × cuatro métodos, con tres mediciones
por método; 16 referencias nuevas aceptadas. Pulso H1 pasó en 16 bits a
40 y 50 kHz; no a 62,5 kHz. Chirp no generó referencias nuevas; se mantiene
la anterior de 14 bits / 100 kHz. Resultados y límites completos en
 docs/CALIBRACION_BODE.md y
 diagnosticos/resultados_bode/20261007_002031_calibracion_completa.json.
Herramientas reproducibles: tools/calibrate_bode.py y
 tools/calibrate_bode_matrix.py; esta última aísla conexiones por perfil.
Los intentos iniciales de 8 bits / 200 y 250 kHz (fuera de la interfaz)
fallaron por cierre/integridad del flujo. Se recuperó reiniciando la misma
app/relay; identidad de firmware verificada, sin cambios de fuentes MCU.
Finalización confirmada: ADC14/40 kHz, salida apagada.


## Monitor con cuatro análisis FFT · 2026-10-07

Nueva variante independiente en `monitor/historico/v14/app.py`: Spectrum, Power,
Distortion y Transfer seleccionables junto a Modo. Astra diseñó/revisó y Sol6.1
implementó. V13 se conserva. No cambia firmware ni se operó el Q.
22 pruebas nuevas y 121 regresiones adaptadas pasan. SINGLE conserva su bloque
al cambiar las vistas; coherencia/retardo N/A con un solo segmento.
Inicio: `conda activate Python_3_13_DataScience`, `python monitor/historico/v14/app.py`.
Documentación: `monitor/historico/v14/README.md`, `docs/FFT_ANALISIS.md` y
`diagnosticos/FFT_V14.md`. Pendiente: validación manual con hardware.

### Análisis con FILTER · 9 de octubre de 2026

Paso 3: FFT Transfer y Bode por tonos, pulso y sweep/chirp permiten seleccionar
referencia X y respuesta Y entre CH1, CH2 y FILTER. Conservan el retardo causal;
la calibración física de CH2/CH1 no se aplica a otros pares. Cambiar canales o
parámetros del filtro invalida las comparaciones afectadas. En transitorios se
mantiene CH1 como detector del estímulo A0. Validación numérica local del filtro
Butterworth: aproximadamente −3 dB y −90° en su corte. Sin cambios de firmware.

### Tasas altas V16 con timestamps conservados

ADC14 a 200 y 250 kHz pasó 120 s por perfil sin pérdidas ni errores; opciones
experimentales habilitadas en el monitor. Seno concurrente pasó a ADC250,
pero WAV cerró el flujo y requirió reiniciar app/relay. WAV20/40 a ADC200 pasó
cinco segundos por tasa. 16 bits conserva 62,5 kHz; audio del monitor conserva
ADC ≤100 kHz. Q restaurado a ADC14/40 kHz y salida apagada. Precisión analógica,
margen de cola y retiro del DMA temporal pendientes.
[Informe y evidencia](../../docs/ETAPA_II_V16.md#tasas-altas-con-dma-temporal--9-de-octubre-de-2026).

### Validación temporal por nodo

Simplificación del bucle del productor conservando captura temporal completa.
154 pruebas locales pasan y el sketch compila. No se atribuye mejora de tasa
sin medir el costo CPU real. [Detalle](../../docs/CAPTURA_TEMPORAL_V16.md).

Validador instalado y probado: 60 s a ADC14/200 y 250 kHz sin pérdidas ni
errores; seno y WAV20/40 concurrentes a ADC200 completos. Q restaurado a
ADC14/40 kHz, salida apagada. La variante optimizada permanece activa.

### Rendimiento del monitor a 200/250 kHz

Ingesta por columnas NumPy, evitando diccionarios/copias por muestra en la
ruta de recepción normal. Se conservan todos los datos, FILTER, registros y
trigger. Benchmark sintético: 8,93 → 0,36 ms por 4096 muestras; FPS reales por
USB pendientes de comparación. Mínimo horizontal de 8 muestras y µs para
ventanas menores de 1 ms. Sin cambios de firmware.


### Generador V16 hasta 50 kHz · validación física

Instalados firmware/relay actualizados. 12 condiciones a 40/50 kHz y Sweep/Chirp
en ambos sentidos: 22 501 122 pares sin errores, ADC14/250 kHz. Restauración
exacta del perfil anterior y salida apagada. Ver docs/ETAPA_II_V16.md e informe
20261009_172039_generador_50khz.json. Queda por validar forma analógica con
instrumento externo y excitación del piezo; ADC16 continúa en 62,5 kHz.


### Synth V16 · volumen, mezcla y 11 voces · 9 de octubre de 2026

Volumen máximo trasladado a Config con AmplitudeDial de color variable.
Mezcla independiente por Osc 1/2/3, conservando el balance de los presets.
Piano Virtual: ganancia 5,0 → 5,3 y refuerzo leve adicional del golpe grave/medio.
Límite 9 → 11 voces; reserva conjunta del acorde antes de crear voces,
priorizando retiro de voces no solicitadas. MIDI procesa toda la tanda antes
de retirar las notas más antiguas sostenidas sólo por pedal.
85 pruebas locales aprobadas; inspección visual local de Config y Osc 1.
Benchmark de 11 voces: máximo 5,1 ms/bloque de 24 ms a 20 kHz y
6,4 ms/bloque de 12 ms a 40 kHz, sin saturación DAC. No se operó el Q;
aceptación por USB y escucha pendientes. Detalles en monitor/v16/README.md
y diagnosticos/resultados_piano/revision_ataque_v16/once_voces.json.


### Piano V16 · liberación y armónicos · 9 de octubre de 2026

Liberación del preset 220 → 550 ms. Caída de cuerda conservada en 4 s
tras descartar una extensión global que se alejaba de las referencias.
Parciales superiores: hasta +12 % amplitud y +6 % duración, con transición
gradual desde el tercer parcial. Conservados los ajustes de martillo/subida.
Comparación local Do3/Do4/Do5: cola 100–200 ms tras note-off +14,5 a +19,6 dB
relativa al cuerpo; armónicos superiores +0,7 a +0,84 dB. Sin valores no
finitos; picos de audio por debajo de 0,43. 86 pruebas locales aprobadas,
incluyendo retiro de voces y cola audible. Sin operación del Q.
Referencias locales sin note-off aislado: ajuste de sonoridad, no nueva
calibración física. Audios/mediciones: diagnosticos/resultados_piano/revision_cola_v16.


### Piano V16 · resonancia identificada al soltar · 9 de octubre de 2026

Estudiadas las tres capas de liberación Salamander de Do3/Do4/Do5 y
su mapeo SFZ. Resonancia identificada en primeros dos parciales: T60
mediano extrapolado 2,16/1,88/1,62 s. Nivel ajustado a la relación RMS
release/sostenido para MIDI60 y 0,5 s de tecla, con factores de SFZ.
Motor: transferencia del estado simpático existente a colas del cuerpo
compartido, entrada 10 ms, expiración por reloj de muestra y reciclado
al reabrir la tecla. Pedal difiere la transferencia hasta levantarse.
Sin samples en el motor, sin nuevas voces de tecla ni cambios al ataque
o al sostenido; se mantiene la liberación modal de 550 ms.
88 pruebas locales aprobadas. Benchmark local con 53 colas y máximo
11 voces: 6,9 ms/bloque de 24 ms a 20 kHz y 6,6 ms/bloque de 12 ms
a 40 kHz, voces retiradas al final. Sin operación del Q.
Reproducible con diagnosticos/identificar_liberacion_piano_v16.py;
fuentes/límites en diagnosticos/referencias_piano/liberacion/README.md.
A/B y mediciones en diagnosticos/resultados_piano/revision_cola_v16.
Aproximación reducida de resonancia: no se identificó un apagador completo
ni todos los niveles/tiempos de tecla. Escucha y USB pendientes.


### Synth V16 · eficiencia y latencia con revisión Astra · 9 de octubre de 2026

Corregida inflación del buffer: target5 y cola4 es reposición normal,
no aumenta a7. Alarma ahora min(4,target-2), con recuperación target-1.
MIDI por señal, sin polling4ms; un update del motor por tanda y CC agrupados
con señales de dial/etiqueta conservadas. Ataque: FFT de exponenciales
reemplazada por recurrencia causal equivalente; colas: resonancia/fade
fusionadas en Numba; cache de bancos16 → 256.
Benchmark A/B local20k: ataque mediano1,71 → 0,65 ms;53colas0,80 → 0,22 ms.
A40k ataque2,23 → 0,78 ms y colas0,80 → 0,22 ms. Audios de12notas
20/40k antes/después difieren menos de4e-16; colas equivalentes a1e-12.
94 pruebas integradas MIDI/FM/piano aprobadas. Script reproducible:
diagnosticos/benchmark_synth_v16.py; evidencia en
diagnosticos/resultados_piano/eficiencia_v16/.
No se operó Q ni firmware. Se mantienen mínimos físicos120ms20k/192ms40k
y40k experimental. No se afirma latencia total física medida o menor;
primeros acordes fríos todavía pueden presentar picos.

### Virtual compacto y eficiencia host con Astra · 10 de octubre de 2026

Panel Virtual 249 → 212 px; Sala y Cola en dos columnas. Gradiente verde,
azul y violeta aplicado exclusivamente a sus seis diales según aclaración.
Etiqueta del eje temporal cacheada: A/B Qt offscreen con 250 mil muestras,
mediana 16–17 → 7–9 ms/frame. MIDI parseado por tandas, ADC evita checks
redundantes de posiciones calculadas y conserva rangos/CRC/época/fronteras.
Niveles DAC constantes evitan arrays. Nuevos tiempos diagnósticos host
MIDI→Qt y control→inicio de render, sin incluir DAC ni sonido.
Evidencia en diagnosticos/resultados_piano/eficiencia_v16/latencia_host.json
y qt_eje_ab.json; benchmark_latencia_host_v16.py reproducible sin Q.
Se mantienen pisos de cola 120/192 ms a 20/40 kHz; validación física pendiente.
Validación: 176 de 177 pruebas aprobadas contando repetición corregida del
test de etiqueta inicialmente igual a la ya visible. Pendiente ajeno a estos
cambios: test_high_rates_are_offered_and_16bit_limit_remains espera texto
«experimental», pero el selector muestra «200 kHz · 5 µs».

### Synth · filtro longitudinal por voz · 10 de octubre de 2026

Perfil local con 11 voces: filtro de deformación longitudinal preparaba
lfilter en cada bloque. Sustituido por recurrencia Numba con estado separado
por cuerda y calentamiento inicial. A/B 480 muestras: mediana16,1 → 2,3µs.
87 pruebas Synth/FM/ataque/cuerdas aprobadas más prueba de equivalencia
SciPy/continuidad entre bloques a1e-12. No cambia coeficientes ni buffers.
Evidencia: diagnosticos/resultados_piano/eficiencia_v16/strain_ab.json.
Sin operación del Q; latencia física pendiente.

### Synth · reposición y medidas de transporte · 10 de octubre de 2026

service_wav llena ambos créditos disponibles en una llamada; elimina espera
por otro pump para enviar el segundo bloque, sin ampliar ventana. Respeta
target/capacidad, offsets consecutivos y comandos serializados. WAV archivo
conserva una petición. Diagnósticos registran máximos generación de bloque,
sendall y envío→ACK por request_id. 64 pruebas FM/contrato/latencia aprobadas,
incluyendo límite target y reposición inmediata. No se operó Q ni se redujo
mínimo todavía: comprobar gaps ACK, cola mínima y cortes en acordes/pedal
con Q antes de ensayar 5→4→3 bloques a20kHz.

### Synth · ensayo físico de cola · 10 de octubre de 2026

Q libre confirmado: sin monitor local ni cliente8766. Ensayo headless30s
a20kHz/ADC14-100k, acordes hasta11voces y pedal simulado cada350ms.
Sin UNDERRUN, reason0 y dropped/fatal0, pero target5 creció a9; cola mínima
observada3. Peores tiempos: generación40,98ms, envío0,31ms, envío→ACK56,36ms,
gap ACK56,98ms. No aprueba mantener120ms ni reducir a96/72ms: casos4/3
omitidos por falta de margen. No mide Qt/MIDI real ni latencia acústica.
Restauración confirmada: ADC14/40k, generador previo deshabilitado y WAV IDLE.
Script diagnosticos/probar_cola_synth_v16.py; evidencia
diagnosticos/resultados_piano/eficiencia_v16/20261010_043344_cola_fisica.json.
max_render_ms del source permanece0 en esta ruta sin niveles DAC; usar
max_chunk_generation_ms del transporte como costo total de generación.

### Synth · preparación previa y repetición física · 10 de octubre de 2026

prepare_audio inicializa cuerpo/sala antes de BEGIN, sin generar notas ni
avanzar posición. Test demuestra códigos idénticos con/sin preparación;
22 pruebas instrumentos/contrato aprobadas. Perfil host11voces ~3–4ms medio,
con picos iniciales variables. Repetición física30s misma carga: sin cortes,
target5→7, generación máxima32,37ms, ACK38,67ms, gap56,80ms, dropped/fatal0.
Anterior5→9, generación40,98ms/ACK56,36ms; A/B no controlado, no atribuir
toda diferencia al cambio. No probar4/3 ante crecimiento con5. Restauración
confirmada ADC14/40k, generador previo y WAV IDLE. Evidencia:
diagnosticos/resultados_piano/eficiencia_v16/20261010_044206_cola_fisica.json.

### Synth · ACK atendido por trama · 10 de octubre de 2026

Durante Synth, pump procesa eventos después de cada tramo992B del lote TCP,
en vez de esperar hasta64KB decodificados para atender ACK. Conserva orden
de configuración/muestras y agrega statuses para no perder confirmaciones
PING de tramas anteriores. Fuera de Synth mantiene feed del lote completo.
77 pruebas FM/contrato/protocolo/latencia aprobadas, incluyendo reposición
antes de la siguiente trama y conservación de statuses.
Repetición física30s: sin cortes ni pérdidas, target5→7. Gap máximo ACK36,30ms
(previo56,80ms), envío→ACK36,27ms, generación32,50ms. Ensayos separados,
no A/B controlado; aún no aprueba cola5 estable ni probar4/3. Restauración
confirmada ADC14/40k, generador previo deshabilitado y WAV IDLE. Evidencia:
diagnosticos/resultados_piano/eficiencia_v16/20261010_044435_cola_fisica.json.

### Synth · filtros del ataque y calentamiento del ensayo · 10 de octubre de 2026

Ruido de ataque: SOS causal Numba con estado inicial cero, equivalente a
SciPy1e-12 y mismas bandas/coeficientes. Warmup prepara bandas y firma para
ambas tasas. A/B220ataques20kHz: mediana0,67→0,26ms, p952,70→0,77ms.
91 pruebas FM/instrumentos/ataque/contrato aprobadas. Se corrigió ensayo
físico: faltaba warmup fm_feedback, presente en interfaz; los máximos previos
incluían carga fría de envolvente y no representan exactamente el monitor.
Repetición30s: generación máxima21,09ms, ACK39,75ms, gap39,89ms, sin cortes
ni pérdidas; target5→7. Comparaciones físicas no son A/B controlado y también
cambió calentamiento, no atribuir toda reducción al filtro. No probar4/3.
Q restaurado aADC14/40k, salidas apagadas. Evidencia:
diagnosticos/resultados_piano/eficiencia_v16/attack_filter_ab.json y
diagnosticos/resultados_piano/eficiencia_v16/20261010_044729_cola_fisica.json.

### Synth · relay candidato pre-SPI rechazado · 10 de octubre de 2026

recv de comandos movido después de READY y antes de ioctl SPI. Compiló
con Wall/Wextra/Werror; ensayo30s sin cortes/pérdidas pero target5→7,
generación37,79ms/ACK55,49ms/gap57,09ms. No demostró mejora: aislado en
experimentos/synth_relay_pre_spi, fuente estable restaurada y comparada
byte a byte con fuente de binario previo. Contenedor previo y configuración
ADC14/40k, generador deshabilitado, WAV IDLE restaurados y confirmados.
Primer intento abortó por generador habilitado tras reinicio; preparación
del ensayo corregida para reponer estado previo antes de probar.
Evidencia20261010_045234_cola_fisica.json y relay_trial_restoration.json
en diagnosticos/resultados_piano/eficiencia_v16. Envío→ACK incluye trabajo
host intercalado: no se puede atribuir demora íntegra a relay/Q sin medir allí.


### Synth · traza de espera ACK host · 10 de octubre de 2026

Traza opcional acotada100000eventos: envío, generación, lectura, decode y
ACK por request_id; sin cambios de protocolo. 6 pruebas relevantes y
contabilidad sintética aprobadas. Ensayo30s relay estable, 4969solicitudes
WAV (incluye consultas): mediana4,51ms/p957,11ms/máximo73,35ms desde retorno
sendall hasta ACK atendido. Peor solicitud: decode71,47ms, read1,72ms,
generación0ms, resto0,15ms. Otro pico57,87ms incluye51,48ms en read.
Son tiempos de reloj: decode puede incluir GC/planificación; read incluye
espera y transporte. No se midió CPU thread ni latencia interna Q/relay.
Sin cortes/pérdidas pero target5→9; no reducir cola. Restauración confirmada.
Evidencia20261010_045638_cola_fisica.json y *_target5_trace_analysis.json
junto a traza cruda en diagnosticos/resultados_piano/eficiencia_v16.
Reproducible: probar_cola_synth_v16.py --timings y analizar_tiempos_synth_v16.py.


### Synth · CPU/GC y ensayo freeze · 10 de octubre de 2026

Decoder medido con thread_time y GC callbacks: pico63,31ms de reloj,
63,24ms CPU y63,19ms GC solapado. Otro pico16,95ms consume0,33ms CPU:
pausa compatible con planificación. Eliminada lista intermedia de pares ADC,
conservando chequeo de ambas columnas/todas muestras y continuidad.17pruebas
protocolo/latencia/contrato aprobadas. GC largo sólo cambió de ubicación:
en siguiente ensayo generación61,66ms con59,38ms GC solapado; target5→7.
Ensayo diagnóstico --freeze-startup, gc.collect+freeze de objetos existentes,
GC normal para objetos nuevos y unfreeze garantizado en finally: target5
estable30s, cola mínima4, sin cortes ni pérdidas; GC máximo1,45ms. Target4
falló UNDERRUN/reason2 a8,13s (target creció6); no probar3. No aplicar freeze
al monitor ni bajar defaults con este ensayo corto. Restauración Q confirmada
ADC14/40k, generador previo deshabilitado y WAV IDLE; GC descongelado.
Evidencia045931/050035/050153_cola_fisica y *_trace_analysis.json del10/10
bajo diagnosticos/resultados_piano/eficiencia_v16. Continúa pendiente medir
pausas del host/transporte noGC y validar política GC con GUI/memoria.


### Synth · worker experimental de generación · 10 de octubre de 2026

SynthProcess spawn separado, una solicitud de bloque pendiente, control FIFO
notas/pedal, respuesta asincrónica; no reserva crédito ni avanza offset hasta
que haya códigos. Bloque pendiente conserva nivel DAC solicitado; siguiente
rampa parte del nivel efectivamente entregado.7pruebas incluyendo equivalencia
exacta de códigos, notas/pedal/volumen, cierre y reposición diferida aprobadas.
No activado en interfaz; ensayo --process. Primer intento cerró sesión por
arranque bloqueante con ADC activo; se corrigió arranque async bombeando
recepción hasta READY. Q recuperado por conexión nueva y estado restaurado.
Repetición30s: sin cortes ni pérdidas, target5→9. Worker máximo30,51ms,
receptor al recoger bloque69,18ms; GC padre68,90ms confirmado por callbacks.
Separar generación sola no protege entrega al Q: ambas aún dependen del
receptor. No bajar cola ni promover esta variante a UI. Pendiente aislar
entrega/propietario Q y canal ADC/control con IPC acotado sin perder muestras.
Evidencia20261010_050855_cola_fisica y *_trace_analysis.json en carpeta de
 eficiencia. Restauración confirmada ADC14/40k, generador previo, WAV IDLE;
worker cerrado. Ensayo fallido previo050729 conserva restauración recuperada.

### Synth · proceso dueño Q/audio y ADC IPC · 10 de octubre de 2026

Variante diagnosticos/probar_audio_owner_v16.py: un hijo posee conexión Q,
Synth y reposición. Padre manda controles y recibe ADC en Queue32 acotada,
sin descartes: valida rango, índices/timestamps entre lotes, wrap e igualdad
de enviados/recibidos; canal lleno rechaza ensayo.2pruebas IPC aprobadas.
Padre fuerza GC y75ms de pausa adicional por segundo; hijo con GC normal.
30s target5 estable, 2.996.902muestras, padre135ms; target4 creció6 sin cortes.
120s target5 creció7, sin cortes y11.992.170muestras íntegramente recibidas;
padre158ms, gap53,37ms. Demuestra aislamiento frente a padre, no cola mínima.
Contraste120s freeze sólo hijo: target5→9, sin cortes,11.991.492muestras,
padre188ms, gap67,12ms, generación50,93ms/sendall19,11ms. No mejora demostrada:
no activar en GUI ni bajar defaults. Comparaciones no son A/B controlado.
Q restaurado en todos los ensayos válidos: ADC14/40k, generador previo,
WAV IDLE. Primero abortó por estado WAV inicialNone, guard corregida y
restauración confirmada. Evidencia133125/133345/133706_audio_owner.json bajo
diagnosticos/resultados_piano/eficiencia_v16. Descripción/límites en
experimentos/synth_audio_owner/README.md. Relay y firmware sin cambios.

### Synth V16: CPU y GC en proceso dueño del audio — 2026-10-10

Se agregó diagnóstico optativo `--timings` al ensayo audio-owner, sin activar
esta arquitectura en GUI ni modificar cola mínima, firmware o relay. CPU del
hilo y tiempo real de render/decode/read/send, controles e IPC ADC; GC y
crecimiento del target. Traza acotada y guardada después de restauración;
análisis mantiene separados intervalos anidados y acepta trazas antiguas.

Primer ensayo `20261010_134620_audio_owner.json`: UNDERRUN a0,167s,
5→7,14.788 muestras IPC íntegras, Q restaurado. GC máximo3,19ms, sendall
11,35ms con CPU0,09ms y pausa posterior sin instrumentar36,75ms; no se
atribuye esa pausa a una causa concreta. Se amplió medición de IPC/controles.

Repetición `20261010_134704_audio_owner.json`:120s sin cortes,11.991.718
muestras ADC/IPC exactas, dropped/fatal0, pero5→9: perfil fijo rechazado.
Traza100.000 eventos cubre sólo27,71s y el primer aumento5→7. Antes de
ese aumento, generación42,24ms con CPU42,22ms y GC39,70ms. Lectura llega
26,11ms con CPU0,31ms; IPC30,41ms con CPU1,67ms sin GC superpuesto.
No hay evidencia suficiente para atribuir esas esperas a red o scheduler,
ni para explicar el segundo aumento fuera de la ventana. El diagnóstico
mismo asigna objetos y puede influir en GC; no prueba mejora de rendimiento.
Q restaurado ADC14/40k, generador deshabilitado y WAV IDLE en ambos casos.
7 tests relevantes pasan, incluidos contabilidad temporal/GC/compatibilidad,
IPC, worker y contrato WAV. Próximo paso: reducir asignaciones del camino
del audio y verificar picos con traza que conserve episodios tardíos.

### Synth V16: quitar cierres creados por bloque — 2026-10-10

`FMSource._render` ya no crea funciones ramp/phase y sus celdas por voz en
cada bloque; se usan auxiliares compartidos con la misma aritmética. No cambia
cola mínima, timbre, síntesis, protocolo ni arquitectura de la interfaz.
Copia anterior usada para A/B: `/tmp/fm_source_before_alloc.py`.
`benchmark_alloc_synth_v16.py` compara11 voces, cambios cada15 bloques,
pedal, piano/FM y20/40kHz:576.000 códigos DAC idénticos en total. Informe
`20261010_alloc_shared_helpers.json`: piano20k mediana2,449→2,376ms,
p95 6,802→6,373ms. Comparación secuencial de host, susceptible
a cachés/planificación; no demuestra eliminación del GC ni menor latencia
física.72 tests FM/piano/feedback pasan.

Ensayo Q dedicado sin traza pesada `20261010_135340_audio_owner.json`:
120s,11.992.396 muestras ADC14/100k recibidas íntegramente en IPC,
sin cortes y dropped/fatal0, pero target5→9: cola fija rechazada.
Generación máxima15,94ms, sendall2,81ms, send→ACK51,31ms,
gap ACK53,93ms. Pausa máxima del padre118,60ms. Es un ensayo diferente
del anterior con traza y no permite atribuir diferencias exclusivamente
al cambio. Q restaurado ADC14/40k, gen off, WAV IDLE. La reducción de
asignaciones se conserva por equivalencia y menor trabajo; no se declara
resuelto el crecimiento de cola ni se activa la arquitectura experimental.

### Synth V16: ADC IPC sin pickle/hilo auxiliar — 2026-10-10

Variante experimental `SharedAdcRing` y flag `--shared-adc` en ensayo
owner. Memoria preasignada32x4096x4uint32, slots publicados por semáforo,
lector copia antes de liberar ranura, full/empty explícitos. El diagnóstico
sigue rechazando overflow y exige todos los índices/timestamps ADC y el
mismo conteo producido/recibido. No se activa en GUI ni se cambia cola.

Comparación local `20261010_shared_adc_local.json`: cuatro corridas alternadas,
2.048.000 registros por corrida exactos/en orden, con pausas GC+20ms del padre.
CPU productor Queue97,23/104,54ms→ring41,29/44,05ms (~58% menos).
put ring tiene más costo síncrono: Queue oculta serialización en feeder;
la CPU de proceso mide ambos hilos. Reintentos por cola llena sólo en este
benchmark de throughput, nunca en diagnóstico Q. No certifica latencia
ni margen de audio.10 tests IPC/preflight/traza/worker pasan.

Intento físico `20261010_142430_audio_owner.json`: se inició erróneamente con
monitor/v16/app.py abierto (PID63797). Conexión cerrada, cero muestras y
sin perfil previo capturado/restauración verificada. No usarlo como evidencia
ni operar el Q mientras lo usa la GUI. Se agregó comprobación de procesos
al CLI para rechazar el ensayo antes de conectar. Comparación física queda
pendiente hasta tener dueño exclusivo; se completaron pruebas locales.

### Synth V16: ensayo físico del anillo ADC compartido — 2026-10-10

Monitor cerrado confirmado antes de conectar. Primeros intentos143657/143742
rechazados sin muestras por estado WAV DONE previo. Se revisó firmware:
BEGIN acepta DONE; STOP con una sesión distinta produce ID_CONFLICT y no
es necesario para reemplazar una reproducción terminada. El diagnóstico
ahora acepta IDLE o DONE sin razón de error, con generador deshabilitado,
y sigue rechazando PLAYING/BUFFERING y estados fallidos. Test de aceptación
comprueba que no se envíe STOP a una sesión anterior.11 tests pasan.

Ensayo `20261010_143852_audio_owner.json`, shared_ring,120s sin freeze/traza:
11.993.780 registros ADC14/100k producidos y recibidos exactamente, índices
y timestamps íntegros, dropped/fatal0, sin cortes WAV. Target5→9,min3:
rechazado como perfil fijo. Generación máxima26,82ms, sendall0,324ms,
send→ACK52,17ms, gap ACK53,01ms; padre pausó122,07ms. Frente al ensayo
Queue135340 (5→9,gap53,93ms), no demostró menor cola o latencia sostenida;
la mejora CPU local no resuelve el cuello de botella de punta a punta.
Son corridas separadas; no atribuir diferencias de máximos a una sola causa.

Se restauró el perfil de ESTA sesión: ADC14/100k (no40k de ensayos viejos),
generador deshabilitado con valores previos exactos y WAV IDLE. La
reproducción anterior ya había terminado; no se reinicia ese archivo.
No se baja cola ni se integra el proceso dedicado/anillo en GUI. Próximo
paso requiere investigar esperas de transporte/planificación de~53ms y
preservar evidencia de episodios tardíos, en vez de seguir cambiando IPC.

### Synth V16: limitar adquisición ADC a40kHz — 2026-10-10

Petición del usuario aplicada aGUI: modo Synth deshabilita tasas ADC>40k,
reduce selección mayor automáticamente y aplica usando configuración normal.
Play rechaza iniciar hasta que adquisición<=40k esté confirmada y no haya
output_pending. Al salir restaura selección anterior reducida; configuración
espera STOP confirmado. No cambia tasa DAC ni límites UART/ADC16, ni activa
owner/ring enGUI. Evitar aplicar ADC repetidamente por cada status WAV IDLE:
sólo se agenda si selección y configuración aplicada difieren.

11 tests focalizados UI/límite, IPC y período ADC pasan. Corrida ampliada
UI19 tests:18 pasan,1 fallo previamente conocido test_high_rates_are_offered...
exige texto experimental en200k que la etiqueta actual no contiene; sin
alterar etiqueta o test para ocultarlo.

El diagnóstico owner admite --adc-rate40000/100000 y valida timestamps con
período25/10us según perfil. Ensayo120s shared_ring40k:
`20261010_144500_audio_owner.json`,4.796.416 muestras exactas, dropped/fatal0,
sin cortes, pero target5→7 (100k previo5→9). Generación máxima25,58ms,
gap ACK54,35ms, send→ACK52,04ms. Menor crecimiento en esta corrida no
certifica cola fija ni baja latencia acústica; siguen picos similares y
son ensayos separados. No bajar mínimo de audio. Q restaurado aADC14/100k
y generador previo off, WAV IDLE. La prueba física usa owner experimental,
no certifica GUI/MIDI/tecla→sonido. La política40k sí queda enGUI para
reducir carga ADC durante Synth.

### Synth V16: localizar espera de lectura con traza numérica — 2026-10-10

La traza optativa del owner ahora preasigna500.000 eventos numéricos (~20MB)
en vez de retener tuplas durante reproducción. Anillo conserva última ventana
con contador de sobrescritos, exportación JSON sólo después de restaurar;
reporte guarda todos los aumentos del target por separado. Analyzer acepta
listas antiguas/envelope nuevo, incluye IPC/controles en contabilidad y usa
búsqueda de intervalos GC, sin sumar pump sobre etapas internas.

Ensayo `20261010_145129_audio_owner.json`,ADC40k/shared_ring/trace:
UNDERRUN a20,855s (reason0 en respuesta de consulta no significa éxito),
833.536 muestras exactas IPC, dropped/fatal0 y restauración confirmada de
ADC14/100k, gen previo off y WAV IDLE. No ocultar corte ni certificar perfil.
Traza61.784 eventos cubre20,957s sin sobrescritos: mayor send→ACK89,831ms,
89,084ms dentro de lectura; read individual87,600ms con CPU0,0537ms y
sin GC superpuesto. Generación máxima15,948ms con CPU15,929ms; GC total
3 episodios, máximo2,597ms. Target permaneció5 hasta corte repentino.
Los datos localizan la espera en lectura (y un control12,074ms/CPU0,101ms),
pero no distinguen falta de datos de relay/ADB de desplanificación del host.
No atribuirla al cálculo de synth ni afirmar menor latencia por cambiar IPC.
Instrumentación sigue añadiendo trabajo.13 tests focalizados pasan.

Próxima prueba útil: correlacionar disponibilidad real de socket y tiempo de
reactivación del proceso/relay, con reloj independiente, conservando margen,
firmware y validación ADC. No acortar arbitrariamente timeout ni aumentar
créditos sin medir, porque no crea datos/ACK faltantes. GUI continúa con
límite ADC40k; no se integra arquitectura experimental ni baja cola mínima.

### Synth V16: observador de socket no consumidor — 2026-10-10

SocketProbe optativo con --timings: hilo separado observa select sin consumir
socket, registra readiness/gaps en array preasignado. Guarda tras restaurar
Q. Tests de socketpair comprueban payload intacto y cierre de hilo; análisis
separa observación de readiness y retraso del propio observador. No cambia
cola, timeout, protocolo o GUI. Se agregaron marcas start/end de pausas del
padre para ensayos futuros (no disponibles en145611).

`20261010_145611_audio_owner.json`, ADC40k/shared_ring/probe, rechazado:
UNDERRUN103,733s, target5→7.4.145.152 muestras exactas, dropped/fatal0,
restauración ADC14/100k, gen previo off y WAV IDLE confirmada. Traza306.398
eventos completa. Gen118,590ms/CPUhilo21,148ms/sinGC en máximo. GC5 episodios,
max2,841ms. Probe83.830 muestras, sin exceso/error, gap máximo43,451ms.
Mayor read50,126ms/CPU0,162ms:4 observaciones, gap máximo23,023ms, ninguna
readiness positiva antes de retorno. Falta de observación no prueba falta
de datos porque reader puede consumir primero y observador también se demora.

No atribuir todo a transporte: también falla dentro de generación con97ms
fuera de CPU del hilo, sin GC. Podrían ser desplanificación, espera interna
o trabajo en otros hilos; medir CPU del proceso completo/contexto de pausas
antes de modificar prioridades/timeout. Padre GC máximo173,675ms y pausa
253,698ms, sin marcas absolutas en esa corrida: no afirmar coincidencia.
No bajar cola ni promover arquitectura; límite ADC40k GUI sigue vigente.

### Synth V16: CPU del proceso y correlación de pausas — 2026-10-10

Traces optativas de read/decode/send/generate incluyen CPU de proceso además
de CPU de hilo. Array preasignado pasa a6 campos (~24MB/500.000 eventos),
exportación conserva CPU opcional y formatos anteriores. Analyzer --report
correlaciona máximos con intervalo de pausa y GC del padre separadamente;
superposición no implica causalidad. Tests cubren6 campos y contabilidad.

Ensayo `20261010_150300_audio_owner.json`,120s ADC40k/shared_ring/probe:
sin cortes,4.796.416 muestras exactas, dropped/fatal0, pero5→7,min3.
Restauración ADC14/100k y gen previo off, WAV IDLE. Traza354.874 eventos
completa. Gen máximo34,141ms/CPUhilo4,303ms/CPUproceso4,631ms, sinGC ni
pausa padre superpuesta. Gen21,636ms/CPUproceso4,439ms coincide enteramente
con GC padre, pero no demuestra causalidad. Read47,107ms/CPUproceso0,341ms
sinGC o pausa padre; por tanto picos principales no son CPU oculta de otros
hilos del owner ni exclusivamente GC del padre. GC hijo max11,510ms en
un decode11,592ms (CPU11,493ms): también existe esta fuente separada.

Tiempo no usado en CPU todavía puede ser desplanificación o espera interna;
no distingue red de scheduler en read. No declarar resuelta latencia, ni
bajar cola/promover owner.15 tests de instrumentación/IPC/worker pasan.
Los máximos de esta corrida no reexplican automáticamente el corte de118ms
de la corrida anterior que no tenía CPU de proceso. Próxima intervención
requiere ensayo aislado de prioridad/reactivación o espera interna, con el
mismo perfil y controles, no seguir microoptimizando cálculos ya rápidos.

### Synth V16: separar voces/postprocesado/DAC — 2026-10-10

FMSource incorpora audio_trace optativo, desactivado en GUI: etapas preparación
de voces, render de voces, post de piano, render total y volumen/limitador DAC,
con CPU hilo/proceso. Child voices sin callbacks para evitar multiplicar costo.
Analyzer no suma etapas anidadas a contabilidad ACK. Test de acordes/pedal y
release exige códigos DAC idénticos con/sin instrumentación.73 tests de
síntesis/ataque/feedback y equivalencia pasan;6 tests de traza/análisis pasan.

Ensayo150901,120s ADC40k/shared_ring: sin cortes y4.796.416 muestras exactas,
pero5→9. Preparación max2,156ms; render voces16,844ms; post6,581ms; read35,228ms.
Se detectó que todos los ensayos owner anteriores usaban __getitem__ directo
sin set_wav_levels: no incluían render_dac_codes/compresor/volumen del panel.
Conservan evidencia ADC/transporte del camino bruto, pero no certifican
la cadena GUI completa. No hay tiempos dac_convert en esa traza por este motivo.

Diagnóstico corregido: usa set_wav_levels(1.0,1.65) y registra estos valores.
Es la ruta GUI con amplitud fija1Vpp, no el valor inicial2,5Vpp del panel.
Ensayo151149,30s: sin cortes, target5 estable,min4,1.198.080 muestras exactas,
ADC timestamps25us/dropped0/fatal0, Q restaurado ADC14/100k, gen previooff y
WAV IDLE. Máximos preparación1,476ms/render voces16,511ms/post7,095ms/
DAC0,574ms/read25,022ms. Generación18,180ms; send→ACK29,986ms.
No atribuir estabilidad al limitador ni comparar30s con120s como mejora;
no bajar cola ni certificar GUI/MIDI acústico. La conversión DAC no domina
en esta corrida. Próximo candidato CPU: render/ataques de voces y post de
piano, preservando timbre; esperas de lectura siguen siendo fuente separada.

### 2026-10-10 — Plan Astra y ensayos de cola/reflexiones

Plan: conservar audio exacto, medir candidatos CPU en host y probar cola5→4
sólo después de estabilidad; distinguir owner experimental de GUI/MIDI real.
Reordenar resonadores conservó muestras/estado pero hizo el kernel1.5–2x
más lento: descartado y restaurado. Resultado20261010_astra_resonadores.json.

Baseline153649 con niveles1Vpp120s: sin cortes pero5→9; no admite bajar cola.
QoS154456: override reversible validado, base ya user_interactive; UNDERRUN
a89.8s, sendACK188.4ms, ADC3.588.096 muestras íntegras yQ restaurado.
Astra localiza142.15ms en decode y44.55ms controles, poca CPU, sinGC propio
ni pausa padre superpuesta; no atribuir a timeout100ms. QoS no se habilitaGUI.

Driver separa --timings y --socket-probe (antes eran inseparables); --qos
es optativo y sólo afecta al child. --amplitude1.0/2.5 registra ruta DAC real.
Sin instrumentación154724: target5 ytarget4 pasaron120s cadauno sincrecer
ni cortes, ADC íntegro yQ restaurado enambos. Target4=96ms vs5=120ms,
reducción experimental24ms; no certifica GUI ni atribuye causa a quitarprobe.

Reflexiones: normalización de pesos constante fuera del bucle de muestras.
ABBA calentado kernel mediana0.10846→0.03299ms; exactos salida,buffer,
posición y288.000 códigosDAC a20/40k. Fullsynth timing variable: no afirmar
70% menoslatencia global. Resultado20261010_astra_reflexiones.json.
48 tests QoS/resonadores/owner/instrumentos y29 finales reflexiones/owner/
instrumentos/audio_trace pasan. Synth/colaGUI no se cambian con este ensayo.

Ensayo final 165214, con normalización optimizada, sin instrumentación y
2,5 Vpp: target 4 permaneció estable durante 300,001 s, sin cortes ni
crecimiento. Se validaron 11.991.266 muestras ADC por índice y timestamps;
Q restaurado a ADC14/100 kHz, generador previo apagado y WAV IDLE.
Máximos: generación 24,414 ms; envío→ACK 11,805 ms; socket 0,301 ms.
Resultado: cola objetivo experimental 96 ms, 24 ms menos que target 5.
La mejora CPU de reflexiones sí queda aplicada al camino normal; el owner
separado y target 4 todavía requieren validación GUI/MIDI antes de promoverlos.
Reporte: diagnosticos/resultados_piano/eficiencia_v16/20261010_165214_audio_owner.json.

### 2026-10-10 — Optimización común y revisión de todos los instrumentos

Se ensayan los 13 presets del panel con sus mezclas reales, 11 notas, pedal,
release y cambios de drive/mix. `diagnosticos/synth_presets_v16.py` extrae
parámetros del FMPanel sin conectar MIDI ni hardware. El owner acepta
`--presets` y restaura/verifica el Q entre casos; aborta si falla restauración.

Mejora común aplicada en FMSource: curvas constantes del compresor y
transición del filtro con caché acotada e inmutable; transición calculada
sólo cuando se usa. Drive y wet estables reutilizan `_ramp`, manteniendo
interpolaciones al cambiar controles. No cambia ADSR, mezcla ni timbre.

Benchmark de 26 casos (13 presets × 20/40 kHz) conserva exactamente
2.246.400 códigos DAC. Suma de medianas: 20 kHz 28,72→28,22 ms;
40 kHz 24,09→23,66 ms. Son corridas secuenciales host, diferencia pequeña
y sensible a carga; no equivale a una reducción garantizada de latencia.
Resultado: 20261010_cache_instrumentos.json. Benchmark inicial general:
20261010_instrumentos.json. Los mayores p95 fueron piano, DX y guitarra;
Brass mostró picos aislados. Pasaron 72 tests FM/feedback/owner/límite ADC.
La cola GUI permanece en su valor previo hasta validar esa arquitectura.

Ensayos físicos 200843, ADC40 kHz, 2,5 Vpp y target inicial4, con presets
del panel y controles simulados: guitarra120s sin cortes pero target4→8;
DX Brillo UNDERRUN a70,738s (generación máxima31,402ms); Brass120s
sin cortes pero4→8. Guitarra/Brass tuvieron send→ACK máximos55,55/58,53ms.
ADC íntegro en los tres casos (4.796.416 / 2.826.240 / 4.796.416 muestras),
y Q restaurado entre todos los casos: ADC14/100k, generador previooff,
WAV IDLE. Resultado20261010_200843_audio_owner.json.
Conclusión: no promover cola4 a la GUI ni generalizar aprobación previa
de piano a otros presets. Sí conservar optimización común exacta; requiere
seguir investigando pausas de transporte/scheduling y margen de generación.

### 2026-10-10 — Guitarra y Brass: coeficientes y PolyBLEP

Guitarra: caché acotada de 512 combinaciones para coeficientes de pérdida
de la cuerda (rate/frequency/brightness/decay/bridge). No contiene buffer,
cursor ni estado de ruido. Controles nuevos invalidan por clave; comparación
de muestras/buffer/cursor exacta en cambios de brillo, decay y bridge.

Brass: nuevo `synth_oscillator.py` calcula PolyBLEP de sierra/cuadrada en
un kernel Numba sin fastmath, respetando orden de operaciones y evitando
arrays temporales y máscaras por voz. Warmup de las variantes de frecuencia
escribible e inmutable antes de BEGIN; fallback NumPy si Numba no existe.
También beneficia Lead, Bass Punch y Warm Pad, que usan esas ondas.

Benchmark calentado ABBA con parámetros reales del panel, 11 notas,
pedal/releases y cambios de drive/mix; 10 casos × 115.200 códigos DAC,
exactos entre cuatro corridas cada caso. Resultado20261010_guitarra_brass.json.
Medianas a20k: guitarra2,884→2,718ms (-5,8%); Brass2,096→0,991ms (-52,7%).
A40k: guitarra2,176→2,030ms (-6,7%); Brass1,650→0,848ms (-48,6%).
Lead/Bass Punch/Warm Pad también mejoran, aproximadamente49–61% según
preset/rate. Son tiempos de generación host, no latencia acústica total.
93 tests de oscilador/cuerda/FM/feedback/instrumentos/owner pasan.

Ensayo físico201809, mismo rig a40k/2,5Vpp, sin instrumentación,120s
por instrumento: guitarra sin cortes, target4→8; Brass sin cortes,4→10.
Cada caso validó4.796.416 muestras ADC y restauró Q aADC14/100k, generador
previo apagado yWAV IDLE. Guitarra sendACK38,916ms/generación31,633ms;
Brass sendACK82,870ms/generación33,763ms. Estos máximos de pared incluyen
pausas y no contradicen la mejora de cálculo host; no prueban menor latencia
física. Target4 rechazado nuevamente, colaGUI conservada. Optimización CPU
exacta aplicada; se necesitan pruebas de pausas/transport para bajar cola.
Reporte20261010_201809_audio_owner.json.

### 2026-10-10 — Segunda optimización guitarra/Brass

Perfil host: guitarra dominada por GuitarStrings.render y dos waveguides;
Brass por preparación de voces, fases/osciladores y wrappers de sosfilt.
No confundir ese perfil CPU con pausas largas del transporte.

Guitarra: calcular índice/fracción de interpolación para cada posición
del buffer una vez por delay, mediante el mismo cálculo escalar original.
Guardar una sola tabla por cuerda y regenerarla cuando cambia delay; estado
y contenido del buffer no se cachean. El kernel sustituye modulo de float
por acceso a tabla y wrap entero por comparación, con muestras/estado exactos.

Filtros internos: kernel SOS stateful directo sin fastmath, con salida y
estado final exactos respecto de SciPy en señales fragmentadas/strided y
órdenes2/4/8. Conserva semántica de no modificar zi de entrada; fallback
SciPy sin Numba. Warmup C/strided y coeficientes mutables/inmutables antes
de BEGIN. Limitado a filtros internos normalizados, no API general SciPy.

ABBA completo20261010_filter_table.json: a20k guitarra2,805→2,300ms
(-18,0%), Brass1,021→0,861ms (-15,6%); a40k guitarra2,126→1,827ms
(-14,1%), Brass0,856→0,711ms (-16,9%). Mejoras adicionales a la etapa
anterior. Lead a40k varió levemente hacia peor; no afirmar mejora uniforme.
Comparación26casos/13presets a20/40k conserva2.246.400 códigosDAC exactos
(20261010_filter_all_presets.json). 93 tests generales pasan; test SOS
corregido para usar copia escribible en referenciaSciPy también pasa.

Diagnóstico --scheduler opcional: getrusage antes/después de pump; sólo
guarda iteraciones>=20ms, hasta256 registros y contador de omitidos.
Incluye CPU proceso, faults minor/major y context switches; no permite
atribuir causalidad ni interpretar minor faults como disco. Sin hilo extra
ni traza de todos los eventos. No activado en GUI.

Fases sin uso: avanzar sólo estado final de portadora virtual y modulador
noFM, sin construir sus arrays; usar recorrido original cuando cambia el
pitch. Estados exactos, incluidos cambios de pitch y continuidad de fase.
Warmup de waveguide/tabla añadido a prepare_audio antes de BEGIN.
ABBA final20261010_filter_table_phase.json, frente a inicio de esta etapa:
guitarra20k2,769→2,092ms (-24,5%),40k2,085→1,646ms (-21,0%);
Brass20k0,997→0,805ms (-19,2%),40k0,848→0,671ms (-20,9%).

Ensayo202923, target4: guitarraUNDERRUN a12,447s, Brass120s sin cortes
pero4→8; ADC íntegro yQ restaurado en ambos. Pausa guitarra52,606ms
con CPU0,296ms, sin major/minor faults: no atribuir el corte a generación.

Con warmup/fases y target5,203451: guitarraUNDERRUN a25,597s tras
lectura138,494ms/CPU0,091ms; generación máxima10,675ms. Brass60s
sin cortes pero5→7; generación16,022ms. ADC íntegro yQ restaurado.
Diagnóstico --scheduler ahora también mide lecturas largas, sin hilo extra.
--read-timeout-ms5/20/100 optativo; restaura timeout antes de restaurarQ.

Comparativo203701 con timeout5ms: guitarra60s, target5 estable, ADC
2.398.208 muestras ysendACK9,845ms/generación12,423ms. BrassUNDERRUN
a5.634s. target5.224.136 muestras; sendACK145,894ms/generación6,383ms.
Dos lecturas61,330/62,488ms con CPU0,060/0,107ms, sin major faults,
aun con timeout5ms. Un timeout no limita toda demora de reactivación del
proceso. No atribuir mejora estable a5ms ni promoverlo aGUI. Q restaurado
en ambos casos. Quedan aplicadas mejoras CPU exactas; cola y política de
lectura de producción conservadas. Investigar transporte/reactivación
separadamente; no ocultar los cortes ni reducir validación ADC.


Ensayos 2026-10-10: observador independiente y ventana de créditos
----------------------------------------------------------------
ProcessSocketProbe usa un proceso separado y select sobre un duplicado del
socket: no consume datos ni cambia el timeout. Guarda muestras en memoria
compartida preasignada y cierra sólo el duplicado. Es diagnóstico optativo
(--probe-process), no se activa en GUI. Prueba verifica datos preservados,
readiness y que el socket original sigue abierto.
20261010_204406_audio_owner.json: Guitarra/Brass 60s cada uno, ADC40k,
synth20k, 2,5Vpp, target5→7; sin cortes, ADC íntegro y Q restaurado.
El proceso observador también demoró 43,335ms (guitarra) y23,771ms (Brass).
La ausencia de readiness observada no demuestra ausencia de datos: el owner
puede haberlos consumido antes de que el observador vuelva a ejecutarse.
No atribuir toda pausa al GIL del owner ni certificar causa de transporte.

--credits1/2/3/4 permite ensayar ventana acotada sin cambiar el target ni
las confirmaciones. Producción conserva2. BEGIN/PLAY/QUERY/STOP y WAV
siguen serializados; se respetan reservas y espacio libre confirmado.
20261010_204744_audio_owner.json, créditos3, target5, ADC40k/synth20k:
Guitarra120,002s sin cortes pero target5→9; 4.796.416 muestras ADC.
Brass UNDERRUN a94,247s, target5→9; 3.766.272 muestras ADC.
Ambos con ADC íntegro, cero dropped/fatal y restauración exacta del Q:
ADC14/100k, generador apagado, WAV IDLE. No promover créditos3 ni bajar
cola normal con estos resultados. 70 tests pasaron (FM, audio owner,
sondas y ventana de créditos); incluyen offsets, ACK, STOP y límites.


Comparativo de carga de voces, 2026-10-10
---------------------------------------
Driver agrega --voices0..11 (default11), conservando el patrón de controles,
intervalos, pedal y GC del padre. No cambia la aplicación ni el firmware.
ADC40k/synth20k,2,5Vpp,target5,créditos2,timeout100ms,--scheduler;
60s por preset, en serie sin benchmarks concurrentes.
20261010_205346_audio_owner.json, cero voces:
Guitarra cola5→7, generación máxima2,636ms, sendACK58,610ms;
Brass cola5→9, generación1,734ms, sendACK96,202ms.
20261010_205637_audio_owner.json, once voces:
Guitarra cola5→7, generación20,981ms, sendACK53,794ms;
Brass cola5→7, generación8,662ms, sendACK36,286ms.
Los cuatro casos sin cortes, 2.398.208 muestras ADC cada uno, continuidad
índice/timestamp válida, cero dropped/fatal y Q restaurado exactamente.
Ninguno acepta reducir cola fija: todos crecieron. Son ensayos secuenciales,
no prueban que once voces mejore transporte. Demoras persisten sin carga de
voces: síntesis no explica por sí sola el límite de cola. Revisar scheduling
host/Q, ADB/TCP y tramo SPI con tiempos independientes; no atribuir causa
única con estos máximos. Relay estable sin cambios: envíos no bloqueantes,
TCP_NODELAY y espera READY; no quitar sincronización para ganar latencia.


Serie alternada comparable, 2026-10-10
------------------------------------
20261010_210056_audio_owner.json. Seis casos secuenciales, parámetros reales
del panel, once voces/controles/pedal idénticos, synth20k/ADC40k,2,5Vpp,
cola inicial5,créditos2,timeout100ms,--scheduler. Driver ahora conserva
presets repetidos en --presets; snapshot por nombre, orden de ejecución
exacto. Restauración entre cada caso y sin benchmark concurrente.
Orden y resultado (tope60s):
1 Piano: UNDERRUN53,89s,cola5→7,gen máx15,434ms,sendACK53,899ms.
2 Guitarra:60s sin cortes,5→7,gen43,231ms,sendACK28,222ms.
3 Piano:60s sin cortes,5→7,gen25,040ms,sendACK50,543ms.
4 Brass:60s sin cortes,5→7,gen10,376ms,sendACK56,036ms.
5 Guitarra:UNDERRUN24,47s,cola5,gen31,411ms,sendACK70,901ms.
6 Piano:60s sin cortes,5→7,gen34,335ms,sendACK32,489ms.
Piano no es garantía de estabilidad a cola baja: mismo preset pasa y falla.
Guitarra también pasa y falla. Muestra pequeña: no estimar tasas de fallo ni
atribuir diferencias a preset o a un único componente. Máximos por etapa
no son una reconstrucción temporal del corte. En piano hay lectura23,660ms
con CPU0,135ms; en guitarra pump33,151ms/CPU4,559ms y23 cambios
involuntarios. Los tiempos sugieren investigar esperas/reactivación además
del cálculo, pero no prueban causalidad del corte.
Total12.722.176 muestras ADC válidas, continuidad índice/timestamp y IPC
sin pérdida, dropped/fatal0 en seis casos. Q restaurado exactamente cada
vez (ADC14/100k, generador apagado, WAV IDLE). Ningún caso acepta cola5
estable; conservar política normal. No modificar firmware/relay estable.


Generación asíncrona y despertar por audio, 2026-10-10
---------------------------------------------------
Driver --async-synth usa SynthProcess existente y lo cierra en finally.
--worker-wakeup implica async y multiplexa socket/pipe cuando un bloque está
pendiente. read_with_audio_wakeup no consume respuesta de worker; devuelve
vacío para que service_wav la retire, prioriza socket si ambos están listos.
Sin audio pendiente conserva Connection.read. Sólo diagnóstico, GUI normal
sin cambios. Test socketpair/pipe comprueba respuesta preservada, prioridad
de ACK y lectura normal. Audio DAC exacto de SynthProcess validado por tests.
20261010_210923_audio_owner.json: async sin despertar, target5;
Guitarra60s sin cortes5→7; BrassUNDERRUN14,970s; PianoUNDERRUN34,978s5→7.
20261010_211254_audio_owner.json: async con despertar, target5;
Guitarra/Brass/Piano60s cada uno sin cortes, targets máximos7/9/9.
Reposición del owner máxima0,952/1,097/1,454ms. No afirmar causalidad o
mejora estable entre series de una repetición; ventanas de ejecución difieren.
20261010_211644_audio_owner.json: target4 (96ms), despertar y margen
experimental3 en alarma; cortes Guitarra34,397s,Brass21,331s,Piano9,726s.
Los tres mantuvieron target4 hasta corte; NO aceptado.
Revisión de wav_queue.h: ready requiere4 bloques (salvo fin de archivo),
accepts en PLAYING requiereused>=2, guarded corta cuandoused<=1 para
proteger DMA. Margen experimental3 con target4 advierteused<=1: coincide
con corte preventivo del firmware y llega demasiado tarde. Retirados override,
CLI --low-margin y test experimental: umbral original min(4,target-2) intacto.
No concluir que crecer5→7 sea falsa alarma sólo por dos créditos pendientes:
las reservas host todavía no son datos publicados en el Q.
Los nueve casos: 14,201,058 muestras ADC íntegras, cero dropped/fatal,
IPC sin pérdida y restauración exacta (ADC14/100k, generador apagado,WAV IDLE).
No modificar firmware/relay ni promover async/despertar aGUI sin aceptación.
Próxima reducción requiere resolver tiempos de entrega y/o estudiar bloques
más cortos en firmware aislado; no reducir resguardo DMA para ocultar cortes.


WAV240 aislado (2026-10-10): experimentos/synth_wav240/README.md registra
compilación, nueve ensayos y restauraciones exactas.240p no aceptado paraGUI:
Guitarra pasó60s a96ms pero repeticiones cortaron96,085/65,956s; Brass yPiano
fallaron. Créditos4 tampoco sostuvieron96ms.19.761.152 muestras ADC íntegras.
Hostdefault480,firmware/relayV16 estables conservados. Appexperimental detenida,
V16 activa,ADC14/100k,generadorapagado,WAVIDLE. Primer arranque rechazado por
selección de relayantiguo no es evidencia de latencia; wrappercorregido y
restauración finalverificada. No confundir wallrender146ms conCPU delworker.


## PRUEBA RADIO V17 — pasos de 25 Hz, instalada y verificada

Resolución elegida por el usuario: 25 Hz. Tres diales de 64×64; flechas y ratón
ajustan a 25 Hz, Page Up/Down a 100 Hz. Portadoras distintas de 25 Hz a 50 kHz;
tono de 0 a 4 kHz. Lecturas: 750 Hz, 1.025 kHz, 20.525 kHz; Hz bajo 1 kHz.
Tabla fija de 5120 muestras (40 ms), repetida por DMA a 128 kS/s (TIM6 divisor
1250), reutilizando RAM de WAV/generador. Sin streaming ni síntesis en IRQ.
Stop inmediato a cero; preparación optimizada fuera de IRQ y constantes de
frecuencia precalculadas. 33 tests locales y C++ del generador normal aprobados.
Compilación Q: 121940 bytes flash, 258496 RAM, 3648 libres informados.
App, MCU y relay V17 activos; primera trama SPI verificada.
Prueba real con amplitud cero: ADC14/40k durante 10 s; ADC8/1403508 durante
60 s, 84.170.880 muestras; cambios a 750/20525 Hz sin modulación durante 10 s
y a 20.525/40.750 kHz con tono 4 kHz durante 10 s. Valores y running correctos,
continuidad sin dropped/fatal. Q restaurado exactamente a ADC8/40000 SPI y
generador apagado con sus campos previos; 399360 muestras íntegras en 10 s.
Informe: ok/restored/restore_integrity_ok=true. No aceptación analógica ni
campaña sostenida de holgura con DSP/FFT/Filter.
Variantes DDS de 1 Hz descartadas por pérdida de nodos; la tabla de 25 Hz
previa pasó 60 s pero falló al reconstruirse en cambios. Evidencia de fallos y
recuperación conservada; no atribuir fallos de READY exclusivamente a RAM.
Respaldo previo: respaldos/unoq/osciloscopio_20261013_234656_188899.zip.
Informe: diagnosticos/resultados_v17/radio_hz_installed.json;
identidad de fuentes: radio_25hz_deployment.json. V16 sin cambios en este
incremento. Reiniciar GUI V17; el firmware Q ya está actualizado.

## 14/10/2026 — DSP/FILTER V17 y máximos CH1 optimizados

Completada continuidad del hilo01a13897: FILTER OFF por defecto sin filtro,
DSP continuo en trabajador independiente con cola acotada/generaciones,
trigger audio fraccional, optimización de remuestreo/espectro y registros
uint32 de16bytes/muestra. 92pruebas locales aprobadas y ensayo offline120s
con6092lotes/168431616muestrasRF, sin errores. FFT/dibujo permanecenGUI;
aceptación física conjunta RADIO/FILTER/FFT y FPS visibles pendientes.
Evidencia: docs/AUDITORIA_EFICIENCIA_V17.md.

Barrido físico aislado CH1 ADC10/12/14:60s+3×120s por finalista,
sin600s por instrucción expresa. Integridad/holgura en muestras/s:
ADC10 1167883,212/1142857,143; ADC12 981595,092/930232,558;
ADC14 851063,830/833333,333. Sin modificación de perfiles productivos.
Campaña y restauración cerradas: ok/restored/restore_integrity_ok=true,
V17 ADC10/909090SPI,generadorapagado con campos exactos,firmware idéntico,
9087712muestras íntegras en10s. Reporte y límites:
experimentos/maxfreq_optimized_v17/RESULTADOS.md.

## FFT V17 ampliada hasta 65536 muestras

Agregadas opciones 16384, 32768 y 65536 a FFT y heatmap, con selectores
sincronizados; predeterminado 2048 conservado. A ADC8/1403508, 65536 muestras
cubren 46,695 ms y dan 21,416 Hz entre bins. SINGLE RF de 65536 probado con
señal sintética y pico conocido; 30 pruebas de espectro/RADIO aprobadas.
Sólo host: reiniciar V17, sin operación ni cambio de firmware Q. No ensayo
físico de carga GUI con esos tamaños. Scan mantiene su configuración propia.

### Pausa 17/10/2026 — solicitada para pruebas manuales

Campañas detenidas y Q restaurada al firmware estable23bc0e... con ADC8/1,6M, generador OFF y10s sin pérdidas. No se incorporaron las tasas ni el firmware experimental. No continuar14/16; usuario los pospuso. Retomar únicamente cuando lo pida, desde `experimentos/otros_bits_crc_v17/PAUSA_20261017.md` (evidencia completa, candidato12/N8064 sin medir, instrucciones y estado exacto).

### RADIO A0 estabilidad incorporada17/10

Instalación exitosa: `experimentos/radio_dac_headroom_v17/probe_20261017_125353/report.json`. BúferDAC30/360ms, PCM16→DAC32, CRC acelerado verificado; sin tasas nuevas.120s íntegros sin underrun,17,28% margen medio y cola pico4 (holgura completa pendiente). RadioTest correcto; identidad y ajustes conservados con10s finales íntegros. Agregado registro de causa de StopA0. Q libre.14/16 pospuestos; siguiente paso según prueba del usuario/log antes de retomar tasas10/12.

## Actualización final17/10 — RADIO/FILTER y tasas10/12 instaladas

Play del panelRADIO activa su visualización en V(t),FFT y espectrograma; no depende del Play del generador. FILTER conserva su selectorOFF/CH1/CH2/RADIO. GeneradorRadio permite IN RADIO/FILTER, este último exige fuenteRADIO del filtro;40kHz y volumen propio. Bandreject y presets50/60Hz,voz,audio5k,quitarDC incorporados. ReferenciaDC respeta gananciaSOS real.

ADC10 CH1 1.250.000 yADC12 CH1 1.066.666,667 incorporados:60s+3×120s sin pérdidas/fatales,cola3,margen19,4%/17,7%. ADC14/16 siguen pospuestos. Reportesqualification_20261017_131439 y132133 bajo experimentos/otros_bits_crc_v17.

Primera integración falló underrunA0 ADC10 pese a reservaPC; se revirtió y diagnosticó conAstra ACK241ms frente ventana16/192ms. Ajuste final ventana30 exclusivaRADIO limitada por capacidad anunciada y créditos confirmados,burst8/interval6ms.22tests finales correctos y25integración perfiles.

Instalación final: experimentos/otros_bits_crc_v17/deployment_20261017_134849/report.json ok/installed/settings_restored=true. Firmware42cff22046d3dbebc4678bd18c62b36e2ee8e4dc6d2d2eb39d69adf2cae30e29. Cuatro pruebas audio correctas:10/1,25M FILTER60s12,19%cola4;12/1,067M FILTER60s10,76%cola3;8/1,6M RADIO120s16,98%cola5;8/1,6M FILTER60s16,95%cola4. Sin underrun/pérdidas/fatales;PCM→RadioTest→PCM correcto. Holgura ADC aislado aceptada, conjunta8/10 no cumplecola<4. Escucha prolongada pendiente.

Q libre,ADC8/1600000SPI,generadorOFF;15.991.776 muestras finales10s sin pérdidas/fatales. Reiniciar monitorV17 para usar interfaz nueva. Detalle docs/TASAS_ADC10_ADC12_RADIO_V17.md y docs/GENERADOR_RADIO_V17.md. Checkpoints anteriores e8/23bc son históricos.

## Etapa IV — primer bloque: A0 a20 kHz

Se habilita GeneradorRadio IN RADIO/FILTER a20 o40kHz siguiendo FS SALIDA del panelRADIO.40k permanece predeterminado. La fuente calcula reserva y ritmo de envío por tasa; detector de retorno usa paso5 a20k y10 a40k. CambiarFS detieneA0 y exigePlay.20k ya está soportado por firmware instalado; no se modificó firmware ni Q.

48k del DSP/PC sigue disponible, peroA0 rechaza48k explícitamente: firmware anuncia20/40/50k y falta resolver timer/protocolo48k y medir físicamente. No mapear48k a50k. Bloque20k validado localmente, pendiente prueba física y escucha. Continuar etapaIV desde esta base, sin declarar completo el punto1.

## Etapa IV — revisión Astra y banda RF seleccionable

BANDA RF4/5/6/9kHz incorporada; representa ancho total del canal, cada banda lateral la mitad.9kHz permanece por defecto. Se propaga enProcessingSettings, claveDSP y ruta alternativa; cambiar banda reiniciaDSP y evita reutilizar audio de configuración anterior enA0. Pruebas de rechazo de bandas exteriores y cambio de generación correctas.48pruebas regresión previas más2específicas; suitefinal36 correctas.

Astra midió detector original~0,036ms/lote6400@1,6M. Halló falso negativo por fase fraccionaria; nueva búsqueda0/0,25/0,5/0,75 conumbral0,985 mantiene3ventanas. MediciónAstra finalpromedio0,080ms,p99 2,25ms,máx2,88ms bajo lock. No justifica moverlo a otroproceso. Sigue heurístico: fasesintermedias(.375/.625),distorsión,alias y tonospuros pueden escapar. No es confirmación física del cableado.

Primera validación20kHz: diagnosticos/resultados_v17/generador_radio_20261017_195222/report.json ok/restoredtrue,60sADC8/1,6M,FILTER50→A0,1.180.320 muestrasDAC, margen20,44%,cola3,ceroerrores. Firmware intacto y ajustes previosADC12/1066666 restaurados,10.661.184muestras recuperación sin pérdidas/fatales. Esa corrida precede la búsqueda fraccionaria final.

48kA0 requiere contrato de reloj: TIM6a160MHz/divisor3333 da48.004,80048Hz,+100ppm; no basta whitelist48k ni mapearlo a50k. Mantener bloqueado hasta decidir temporizaciónfraccionaria o remuestreo a tasaefectiva y medir. DSP/PC48k sigue disponible. Continuar luego controlesgain/autogain y demáspuntosETAPAIV.

Cierre físico versiónfinal: diagnosticos/resultados_v17/generador_radio_20261017_195401/report.json ok/restoredtrue.60sADC8/1,6M,FILTER→A0a20k,BANDARF6k,detectorfraccionario cargado:1.182.720muestrasDAC,sinunderrun/pérdidas/fatales; margen20,36%,cola4 (no holgura completa). Volumen,resintonía,Stop correctos; no se inyectó loop físico. Firmwareidéntico,ADC12/1066666 ygeneradorOFF restaurados;10.661.760muestras de recuperación sinerrores. Qlibre. ReiniciarV17para nuevaUI.48kA0pendiente,siguiente bloquegain/autogain.

## Etapa IV — gain y autogain,18/10/2026

RADIO Gain1–50× con dial56px, lectura decimal y arco verde→amarillo→rojo; dial de volumenGeneradorRadio conserva0–100% y usa el mismo gradiente. Valor inicialGain2×. Auto gain es botón checkable,OFFpredeterminado; tocarGainmanual lo desactiva. No toca adquisición,offset ni volumenA0.

ConRADIO encendida y resultados de generaciónactual, mide pico absoluto de audio respecto de offset como máximo1vez/s. Busca dejar0,5V por lado(0,5–2,8V),según offsetactual y límitesGain1–50. Baja inmediatamente,sube como máximo50%porpaso,con banda muerta5%/0,1. Ignora silencio<1mV referido a gananciaunitaria,NaN y offsetsinmargen. No discrimina voz/ruido ni garantiza ausencia de picos entre mediciones; no es limitadorinstantáneo. Procesa el bloqueaudio recibido,sin proceso/timer extra. Cambios deGain conservan estadoDSP mediante ruta levels_only existente.

66pruebas de regresiónRADIO/UI/A0/procesamiento correctas;2pruebas específicas autogain incluyen niveles,silencio,inválidos,límites,throttle,generaciónvieja,override manual y entregaDSPconactualizaciónGain. Sin cambiosfirmware ni operacionesQ en este bloque; falta escucha y comportamiento prolongado real. ReiniciarV17para aplicar. PendientesETAPAIV:48kA0 contrato reloj,undersampling,FFT Radio y otros puntos del encabezado del plan.

## RADIO+A0 ADC14 — mejora operativa y ensayo descartado18/10

Usuarioautorizó mejorar trasEOFreal dropped1 aADC14/851063. Qsinmonitor,relayexited1; recuperado conrespaldo eidentidadMCU42cff220conservada,configuradoADC14/599250generadorOFF. Los ajustes vivos de sesiónfallida no pudieron consultarse; no afirmar restauraciónexacta de esa sesión.

Experimentoaislado radio14_cpu_v17: sólo políticaCPU/envío aplicada14CH1,ticks188/192,N1984 (afinidadCPU2,performance,colaTCP; MCUySPIigual).350combinacionescomparadasenC: sólo2perfilescambian. Baseline59925060s pasó. Candidato851063:60s,120s,120s pasaron,sinADCpérdidas,márgenes18,5–19%,cola4. Tercera120s falló underrunA0 a~58s;ADCsinpérdidas/fatales. Sourceaudio disponible(min9180),ACK234ms,pumpgap170ms,decode131ms. No promover. Informe experimentos/radio14_cpu_v17/probe_20261018_121957/report.json. Restauracióntrue,relayoriginal,MCUidéntico,políticaoriginal,ADC14/599250,A0OFF;5.990.400muestrasrecuperación10s sinerrores.

Mejora host incorporada: GeneradorRadio rechazaPlay siADC14>599250,concausa visible ysin cambiarADC/perillas. Siunaconfirmacióntardía entraenperfilalto,detieneA0/desconectafuente/conservaRADIO;feed_resulttambiénrechazaconfiguraciónalta. Mantener bloqueoconfiguraciónyaexistente duranteWAVactivo.8/10/12nopierdenperfiles. Eslímiteoperativoconservador, noaceptaciónexhaustivade todas tasasmenores ni mejoradevelocidad.600/851kconRADIOsolo nocambia. No autoreconectarocultandopérdidas. CandidatosdeCPUyinstallerquedanaisladoseinactivos;nadainstaladoenrelay/MCU.

Siguienteoptimizaciónpendiente: reposiciónDACantepausasPC~170ms,bloqueosdelafuente yvalidaciónconjunta; no subirburst/relajarintegridad sincampañanueva. ReiniciarV17paraaplicarrestricciónvisible.

## 18/10/2026 — ADC14/851063 con RADIO+A0 incorporado

Objetivo alcanzado sin bajar la tasa: 851.063,83 muestras/s, N5952 en vez de N1984, ticks188. Calificación conjunta RADIO+A0 a40k:60s+3×120s sin pérdidas/fatales/underrun, margen19,39–19,48%, colas2/2/2/3, slackpositivo. Informe `experimentos/radio14_nodes_v17/probe_20261018_131346/report.json`, ok/restoredtrue.

Instalación final `experimentos/radio14_nodes_v17/installation_20261018_133339/report.json`:ok/installed/restoredtrue. Firmware f3cab6f48a0d6b45fb7c1329ceee7e485f6cf32baadac1c9578533d1f5090bf5.36pruebaslocales y6comprobaciones físicas60s correctas:14/833333,14/851063,8/1600000,10/1250000,12/1066666 a40k;14/851063 conFILTER→A0a20k. ADC8cola6 sigue sinholguracompleta.

HighRateRadioDacSource(ráfaga16 ycorrelaciónloops fueralockaudio) seelige sólo para14bits/851063; las demás combinaciones conservan fuente yráfaga8. Registro14ticks188 actualizado aN5952; protección599 retirada para tasaobjetivo. Primerainstalacióngenérica revirtió porunderrun8; no confundirsuinforme132501coneléxitofinal133339. CandidatosCPU/refill conN1984fallaron ynoestáninstalados.

Qlibre con firmware nuevo, ajustesprevios ADC14/599250 ygeneradorOFF restaurados.5.989.884 muestras finales10s sinerrores. ReiniciarV17 yseleccionar851063 parausar. Detalle legible: `docs/ADC14_851_RADIO_A0_V17.md`.No afirmar escucha/analogía/FPS certificados;14/851a40k sí tieneholguraconjunta medida. ADC16,48kA0 yrestoEtapaIV permanecenpendientes.

## Estabilidadotrosbits —18/10, cierre

Matrizcompleta `diagnosticos/resultados_v17/estabilidad_radio_20261018_135128/report.json`:18casos8/10/12/16, bajo/medio/máximo,RADIO/FILTER,A020/40,Gain; máximospasadosrepetidos120s. No aceptaciónglobal:underrun8/1,6M120s,10/1,25M60s;ADC12OOBloops;16/40kGainWAV4/0.

Fixproducciónloops: excluir endpoint np.arange enADC12fraccional. RepeticiónADC12 `estabilidad_radio_20261018_161158`:5casos60/120correctos,restoredtrue;max120cola4noholguracompleta.

FixconAstra producción: continuity_epochestructural independiente generationvisual; Gain/offsetnoreseteanDSPni descartanresultadospendientesdelmismoepoch; sesiónA0porlote impideaudioanteriortrasStop/Play. ComparaciónsettingsmantieneFILTER/adquisición/sintoníaestrictos;GUIcontinúarechazogeneraciónvieja.46pruebaslocalescorrectas. EnsayoGain `estabilidad_radio_20261018_162103`:8/10/12/16pasaron60scambioscada2s;audio preservado2905/1271/2182/4096samples. Qrestauradafirmwaref3cab6f4,ADC14/599250generadorOFF,5.990.900muestrasrecuperaciónsinpérdidas. Qlibre.

Pendienteoptimizarunderrunsdemáximos8/10 (no resueltos por estamatriz). No cambiarflagsaceptaciónni ocultarfalloconautorestart.16max76226dual120pasóbaseline;14/851calificadopreviamente. Detalle `docs/ESTABILIDAD_RADIO_OTROS_BITS_V17.md`. ReiniciarV17para2correccioneshost;firmware/relayinalteradosenestaetapa.

## 18/10 — seguimiento cortes A0 máximos8/10

Campaña `experimentos/radio_refill_8_10_v17/probe_20261018_164919/report.json`, restauradatrue. Se redujo perturbación deldiagnóstico: copiade3000trazas ahora1Hz enlugarcadaevento; contadores/máximossiguenporoperación. Astra midiócopiaprevia~11,3us/evento; noestablececausadelunderrun. Baselineactual10/1250000 y8/1600000pasaron120s (12,22%cola4 y16,79%cola5). No demuestraresoluciónintermitente.

CandidatoHighRateSource(ráfaga16+guardfueralock) aislado:10fallóscreen60pordropped1/EOF;8pasóscreen60+120+120perotercera120pierdiónodo,cola8. CRCcorrectos. Recuperado relayMCU, noincorporado.Ni10ni8usanHighRateenproducción.

Candidatoconservador10ráfaga8+guardfueralock: `experimentos/radio_refill_8_10_v17/guard_only_20261018_170401/report.json`.60yprimer120pasaron;segundo120underrunA0,ADCintacto cola3/margen11,83%,ACK285,62ms,pump155,57ms,decode119ms,generate1,93ms. Noincorporar. DemuestraquenobastaeliminarcontenciónguardnipicosdepreparaciónDAC; faltaaislarreposición/créditoscuandoACKtardamásde250ms. Nuevosensayosnoalteraronfirmware/relayproducción. Qrestauradaylibre,ADC14/599250generadorOFF,5.989.368muestrasrecuperaciónsinpérdidas. Identidadf3cab6f4conservada.

Pendientecorrección: revisarQUERYserializadodurantelive,créditosconfirmados/ACKtardíos yservicioaudioentretramas; no ampliarventanasinventandocapacidad ni aceptarpaquetesconpérdidas. Evaluarbursturgentedinámicosólobajocolaconfirmadaenvezde16continuo. Preservarratesyfirmware14calificado. Noautorestarthide. Diagnósticoaúnnecesitasnapshotfinaltrasworkerjoin para conservarúltimosegundo,mejoraplanteadaporAstra.

## 18/10 — A0 ADC10/1,25M: servicio entre tramas incorporado

`_process_decoder_events`ahoraatiendecréditosRADIOalterminarcadatrama sóloADC10/1250000;conserva token6ms,burst8,ventana30,huecosconfirmadosyQUERY/PLAY/STOPserializados. NoMCU/relayni tasas cambiadas. Campaign `experimentos/radio_frame_service_v17/probe_20261018_182636/report.json`:10pasó60+3×120sinpérdidas/underrun;~11,6–11,9%margen,cola4(noholguracompleta).8pasó60pero120underrunACK420,8ms>DAC360ms,ADCintacto;noaplicar a8.

21testsproduccióncorrectos. Verificaciónfinal `diagnosticos/resultados_v17/generador_radio_20261018_183831/report.json`:120s10/1250000RADIO→A040k,ok/restoredtrue,margen12,38%,cola3,4.709.280DAC. QlibreADC14/599250generadorOFF,firmwaref3cab6f4intacto;5.989.368muestrasrecuperaciónsinpérdidas. ReiniciarV17. Detalle `docs/SERVICIO_RADIO_ADC10_V17.md`.

PendienteADC8/1,6M; no declararresueltos todosloscortes. Candidatasráfaga16 yguardfueralocksolas fallaronyse restauraron. Diagnósticocopiatraces1Hz envezcadaevento; preservamaxeventos, snapshotfinalpendiente. Continuar soluciónespecífica8sinbajartasa.
