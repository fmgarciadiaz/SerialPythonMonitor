# Generador Radio V17

Nuevo modo **Radio**, separado de **Radio Test**. Envía a A0 el audio ya
sintonizado y demodulado por el panel RADIO, sin otro sintonizador ni remuestreo.
Para esta primera etapa, seleccionar **FS SALIDA: 40 kHz** en RADIO y pulsar
Play en Generador → Radio. El volumen de A0 es independiente; la salida DAC
está centrada en 1,65 V. Stop detiene A0 y mantiene RADIO disponible.

Play acumula 0,5 s de audio en la PC antes de alimentar A0 para absorber
demoras de procesamiento. Cambiar la sintonía sustituye el audio pendiente
de la emisora anterior por silencio, conservando la reserva temporal. Los
bloques ya entregados al DAC conservan su latencia. El gráfico no espera
esta preparación.
Cambiar FS SALIDA o apagar RADIO detiene A0. No se habilita salida a 48 kHz.
La adquisición se conserva; el modo admite CH1 hasta 1,6 MS/s.
Las primeras pruebas conjuntas fallaron con consultas DAC cada 4 ms; Radio
usa ahora consultas cada 40 ms sobre su búfer de 16 bloques (192 ms),
conservando confirmación de cada bloque, límites de créditos y Stop.
Los otros modos mantienen sus intervalos previos. No se cambió firmware.

Pruebas locales: tests.v17.test_radio_output, test_radio_ui,
test_processing_pipeline, test_adc1600 y test_board_owner: 70 pruebas pasadas.
El diagnóstico físico está en diagnosticos/validar_generador_radio_v17.py;
sus informes incluyen cambios de volumen/sintonía, Stop y restauración.
La continuidad digital no certifica por sí sola la fidelidad analógica o la
escucha de una emisora.

La campaña de tasas ADC10/12/14/16 quedó pausada y guardada en
experimentos/otros_bits_cpu_relay_v17/checkpoint_before_radio.json.

Cierre físico 17/10: diagnosticos/resultados_v17/generador_radio_20261017_024325/report.json:
ok=true, sin errores, 742.560 muestras DAC reproducidas, cambio de volumen,
resintonía y Stop correctos; ADC14/599250 conservado. Restauración exacta de
ADC8/1600000 y generador apagado; firmware idéntico y 15.990.912 muestras de
recuperación sin pérdidas ni errores fatales. No constituye ensayo prolongado
ni aceptación de fidelidad analógica.

Regresión ampliada: 80 pruebas pasadas y una prueba de instrumentos Synth
no ejecutable por ausencia de Numba en .venv-v13 (Virtual requiere Numba).
Pruebas específicas de Radio/créditos tras añadir reserva: 11 pasadas.

## Adquisición 1,6 MS/s con salida Radio 40 kHz

Se retiró el límite provisional de 599,25 kHz. El modo acepta adquisición
CH1 hasta 1.600.000 muestras/s y conserva esa configuración al iniciar,
resintonizar, cambiar volumen y detener A0.

Transporte final: consultas cada 40 ms, hasta ocho bloques en vuelo limitados
por créditos confirmados, separación mínima de 6 ms entre bloques y reserva
inicial de 20.000 muestras de audio. Los modos previos conservan sus límites.
La reserva agrega aproximadamente medio segundo de latencia al audio.
Stop invalida los bloques pendientes y conserva su confirmación independiente.

Las variantes con dos créditos tuvieron underrun incluso con audio preparado
en la PC; las trazas registraron confirmaciones de hasta 191 ms. Reducir las
consultas a 20 ms empeoró ese ensayo. Con ocho créditos pasaron 120 s tanto
sin separación entre bloques como con la separación final de 6 ms.
La separación no demostró reducir el pico ADC: ambas corridas llegaron a 8/8.
No constituye aceptación de holgura o de calidad analógica por escucha.

Informe del candidato final: diagnosticos/resultados_v17/generador_radio_20261017_030024/report.json.
Resultado: ok=True, restored=True; 196,730,208 muestras RF,
4,716,960 muestras DAC reportadas, cola pico 8/8,
sin pérdidas ni errores fatales ni underrun. Firmware idéntico antes/después;
recuperación de 10 s con 15,990,912 muestras íntegras.
Pruebas locales de Radio y créditos: 13 pasadas.

## Mejora en evaluación (17/10, posterior a la corrida anterior)

RADIO procesa CH1 en adquisiciones simples o dobles de 8/10/12/14/16 bits; limita la sintonía a la banda disponible. La salida A0 sigue a 40 kHz. Estas transiciones pasaron pruebas locales de procesamiento y gráfico; la matriz física por resolución sigue pendiente.

El host usa un acumulador temporal para recuperar entregas demoradas (6 ms por bloque, ráfaga máxima de cuatro), hasta 16 créditos y capacidad negociada. Un firmware anterior conserva sus 16 bloques. La reserva PC sigue en 0,5 s; el volumen es independiente.

Candidato de firmware aislado: CRC acelerado con comparación inicial contra software y fallback; PCM almacenado en 16 bits y escrito al DAC en 32 bits mediante relleno con ceros. Búfer de 30 bloques: 360 ms a 40 kHz, 28.800 bytes compartidos con tablas de generador. No se modifica el formato de muestras ni el CRC de los paquetes. El prototipo con escritura DAC de 16 bits falló y fue descartado.

Ensayo de 60 s `experimentos/radio_dac_headroom_v17/probe_20261017_110901/report.json`: correcto, 2.314.080 muestras DAC reportadas; margen medio conjunto 16,97%, cola ADC pico 5, sin pérdidas/fatales. Pasó transición PCM → Radio Test → PCM; firmware original restaurado y 15.990.912 muestras de recuperación íntegras. Cola pico 5 impide certificar holgura completa. Falta cerrar ensayo de 120 s y matriz física antes de promover este firmware.

Regresión local posterior: 75 pruebas de Radio/interfaz/procesamiento/créditos/propietario y pruebas adicionales de protocolo, CRC y memoria correctas. Sin aceptación analógica por escucha ni certificación de FPS visibles.

## Incorporación para estabilidad de A0 — 17/10/2026

Estado vigente: instalada la mejora de audio, sin agregar tasas ADC. Informe: `experimentos/radio_dac_headroom_v17/probe_20261017_125353/report.json`, `ok=true`, `installed=true`, `settings_restored=true`. Firmware SHA256 `e8d8411bec6a9aebef0ffc58b21448c14cd8503cd8209a4f28bd6fb852c0e1a9` y relay de producción con identidad de sus fuentes. Respaldos local y Q conservados junto al informe.

PCM16 almacenado en RAM y escritura DAC32 con relleno cero: 30 bloques/360ms a40k. CRC acelerado conservando el algoritmo y comparación inicial contra software. El host negocia capacidad y mantiene compatibilidad con firmware16 bloques.

Repetición física120s: 4.708.800 muestras DAC reportadas, sin underrun, pérdidas ni fatales; margen medio conjunto17,28%, cola pico4 (no aceptación de holgura completa). Pasó volumen, resintonía, Stop y PCM→RadioTest→PCM.20 pruebas locales de producción correctas. Tras reiniciar MCU y relay juntos, identidad conservada, ajustes restaurados y15.991.776 muestras de recuperación en10s sin pérdidas/fatales. La instalación anterior falló por reiniciar sólo relay ante una época de adquisición avanzada; fue revertida y la secuencia final quedó corregida.

El corte informado por el usuario no se reprodujo en el baseline120s del firmware anterior; no se afirma eliminación definitiva del fallo. Cada Stop de A0 ahora registra causa, ADC, reservaPC y estadoDAC en `diagnosticos/resultados_v17/radio_a0_stops.jsonl`, antes de liberar la fuente. Los logs no reinician Play automáticamente. Una prueba de escucha prolongada sigue pendiente.

Las propuestas de tasas ADC10/12 continúan aisladas. ADC14/16 pospuestos por el usuario; esta instalación no los califica bajo carga RADIO.

## IN RADIO / FILTER y presets

Generador→Radio mantiene salida40k y volumen propio. IN=RADIO toma audio demodulado; IN=FILTER toma el resultado del filtro cuando FILTER tiene fuenteRADIO. FILTER conserva su selectorOFF/CH1/CH2/RADIO; no se cambia automáticamente. Si su fuente no esRADIO, Play en IN=FILTER indica qué falta y no envía una señal distinta. CambiarIN detieneA0 y permite reanudar conPlay. Cambiar el filtro descarta audio pendiente de la configuración anterior conservando la reserva con silencio; no mezcla filtros. La referenciaDC se calcula con la gananciaDC real de las seccionesSOS para evitar desplazamiento deA0 con pasaaltos/pasabanda o ripple.

Play del panelRADIO habilita su visualización enV(t),FFT y espectrograma; seleccionaRADIO y, siFILTER tiene fuenteRADIO, FILTER, para no mezclar tasasRF/audio en el espectrograma. Cambiar sintonía respeta elecciones posteriores de canales. Play del generador controlaA0.

Band reject admite Butterworth/Bessel/ChebyshevI/II/Elliptic con dos límites; RC no ofrece ese modo. Presets: rechazo50Hz(49–51), rechazo60Hz(59–61), voz300–3400Hz, audio hasta5kHz y quitarDC20Hz. Preservan fuente y no activanFILTER si estáOFF. Los bordes de rechazoButterworth son puntos−3dB; no prometen rechazo uniforme dentro del intervalo.

Prueba física nueva ruta: `diagnosticos/resultados_v17/generador_radio_20261017_131243/report.json`,60s conADC8/1,6M yFILTER preset50→A0: ok/restoredtrue,2.370.240 muestrasDAC reportadas, sin errores. ColaADC4; no holgura completa. Pruebas locales incluyen arranque con audio vacío, referenciasDC, presets sin activarOFF, visibilidad y respeto de selección al sintonizar.

## Actualización final17/10 — RADIO/FILTER y tasas10/12 instaladas

Play del panelRADIO activa su visualización en V(t),FFT y espectrograma; no depende del Play del generador. FILTER conserva su selectorOFF/CH1/CH2/RADIO. GeneradorRadio permite IN RADIO/FILTER, este último exige fuenteRADIO del filtro;40kHz y volumen propio. Bandreject y presets50/60Hz,voz,audio5k,quitarDC incorporados. ReferenciaDC respeta gananciaSOS real.

ADC10 CH1 1.250.000 yADC12 CH1 1.066.666,667 incorporados:60s+3×120s sin pérdidas/fatales,cola3,margen19,4%/17,7%. ADC14/16 siguen pospuestos. Reportesqualification_20261017_131439 y132133 bajo experimentos/otros_bits_crc_v17.

Primera integración falló underrunA0 ADC10 pese a reservaPC; se revirtió y diagnosticó conAstra ACK241ms frente ventana16/192ms. Ajuste final ventana30 exclusivaRADIO limitada por capacidad anunciada y créditos confirmados,burst8/interval6ms.22tests finales correctos y25integración perfiles.

Instalación final: experimentos/otros_bits_crc_v17/deployment_20261017_134849/report.json ok/installed/settings_restored=true. Firmware42cff22046d3dbebc4678bd18c62b36e2ee8e4dc6d2d2eb39d69adf2cae30e29. Cuatro pruebas audio correctas:10/1,25M FILTER60s12,19%cola4;12/1,067M FILTER60s10,76%cola3;8/1,6M RADIO120s16,98%cola5;8/1,6M FILTER60s16,95%cola4. Sin underrun/pérdidas/fatales;PCM→RadioTest→PCM correcto. Holgura ADC aislado aceptada, conjunta8/10 no cumplecola<4. Escucha prolongada pendiente.

Q libre,ADC8/1600000SPI,generadorOFF;15.991.776 muestras finales10s sin pérdidas/fatales. Reiniciar monitorV17 para usar interfaz nueva. Detalle docs/TASAS_ADC10_ADC12_RADIO_V17.md y docs/GENERADOR_RADIO_V17.md. Checkpoints anteriores e8/23bc son históricos.

## Detector de realimentación del generador Radio — 17/10

Protección pasiva habilitada para IN RADIO y FILTER. Compara CH1 a4kS/s con hasta2s de códigos A0 enviados; normaliza ganancia y offset y busca retardos. Requiere correlación>=0,985 en3 ventanas de512 muestras y contenido espectral suficiente. Ignora silencio y tonos puros, que no permiten identificar un cable de retorno sin ambigüedad. No inyecta señales. Al detectar posible retorno bloquea nuevos bloques, activa Stop del panel (sondeo200ms), muestra causa y registra diagnóstico loop_score/loop_hits. Rearme manual conPlay; puede quedar audio previamente encolado hasta procesarStop. Es heurística: no garantiza detectar todo loop, especialmente con distorsión o tonos puros.

Implementación host solamente; firmware sin cambios. Pruebas sintéticas de retorno con retardo/ganancia, no-loop, silencio, tono, error enclavado yStop visible; sin prueba física de cableA0→CH1 en esta etapa. ReiniciarV17 para aplicar.

Siguiente bloque: ETAPA IV al inicio de Plan de trabajo.md: salida20/48kHz,undersampling,controlesgain/volumen,autogain,informaciónemisora,FFT Radio con bandas y ancho4/5/6kHz. Primero mantener esta protección y estabilidad como base; no asumir esos puntos implementados por este cambio.

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

## 18/10 — A0 ADC10/1,25M: servicio entre tramas incorporado

`_process_decoder_events`ahoraatiendecréditosRADIOalterminarcadatrama sóloADC10/1250000;conserva token6ms,burst8,ventana30,huecosconfirmadosyQUERY/PLAY/STOPserializados. NoMCU/relayni tasas cambiadas. Campaign `experimentos/radio_frame_service_v17/probe_20261018_182636/report.json`:10pasó60+3×120sinpérdidas/underrun;~11,6–11,9%margen,cola4(noholguracompleta).8pasó60pero120underrunACK420,8ms>DAC360ms,ADCintacto;noaplicar a8.

21testsproduccióncorrectos. Verificaciónfinal `diagnosticos/resultados_v17/generador_radio_20261018_183831/report.json`:120s10/1250000RADIO→A040k,ok/restoredtrue,margen12,38%,cola3,4.709.280DAC. QlibreADC14/599250generadorOFF,firmwaref3cab6f4intacto;5.989.368muestrasrecuperaciónsinpérdidas. ReiniciarV17. Detalle `docs/SERVICIO_RADIO_ADC10_V17.md`.

PendienteADC8/1,6M; no declararresueltos todosloscortes. Candidatasráfaga16 yguardfueralocksolas fallaronyse restauraron. Diagnósticocopiatraces1Hz envezcadaevento; preservamaxeventos, snapshotfinalpendiente. Continuar soluciónespecífica8sinbajartasa.

## Máximo RADIO según FS y auditoría etapaIV —18/10

Se eliminó tope fijo600kHz de radio_tuning_max. Máximo=ceil(FSreal/2−BandaRF/2)−1Hz:1,6MS/s con9kRF→795499Hz;con4k→797999Hz. Dial/entrada,Scan,validaciónDSP yA0siguenelmismocriterio; cambiarbandaactualizarango yrecortaelecciónsólo sifuerabanda. Bandwidthdefault9kconservado.47testsregresióncorrectos; testnuevoScan750k ysintonía segúnFS/banda,picoaudio1kdesdeAM750k. Sólohost;sinQ/firme.

Plan de trabajo.md tiene ahora checklistvigentealprincipiodeETAPAIV. Pendientesexplícitos:FFT Radio/marcasScan/bandaslaterales,OSundersampling,48kA0contratoreloj,identificaciónemisora. SiguienteprioridadfuncionalFFT Radio;no declarar etapaIVcompleta por pruebasdeestabilidad.8/1,6MA0sigueabierto;10/1,25Mservicioentretramasincorporado. ManteneraltoRADIOcompacto289px.
