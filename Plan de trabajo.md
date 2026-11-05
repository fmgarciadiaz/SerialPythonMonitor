# 4/11 · Arranque real recuperado: archivos V20 dataless

- PIDusuario23037 V20app.pybloqueado>1minCPU0: sample889/889importFileIOread,lsofFD3radio_am.py compressed,dataless. MaterializaciónAPIoficialNSFileManager(sincambiarbytes/kill/restart) recuperó193/336archivosV20,5,3MB,0datalessfinal/0rechazos. MismoPIDdespuéssample827QApplication.exec→QEventLoop→NSApplicationrun: GUIeventloopalcanzado. App/panel/journalSHAigualesal smoke. SinQoperado/nuevoconnect/nipreferenciascloudcambiadas. [Evidencia](diagnosticos/resultados_v20/startup_hang_20261104/report.json) · [Informe](docs/V20_ARRANQUE_DATALESS_20261104.md). MantenerdescargadapermanenteproyectoFinderpendiente; noatribuirtodosfallosconexión. VSCodeapuntaV19perousuariolanzóV20directo: nofuecausa.

# 4/11 · Synth Play: ruta local validada, fallo usuario sin reproducir

- JournalPlayV20persistenteacotado64eventos(porsolicitud, metadata sinPCM/notas/parámetros), statusesperaespecífico;17testsPASS5,870s ybackupSHA `respaldos/host/v20_before_synth_start_journal_20261104`. UNsmokefísiconormalADC14/40kdualDXPiano20kPASS:prepare2,935s→PCM480→ACKPLAY2,990sdespuésclick,hold20,103s/402240DACmuestras ySTOPACKmisma sesión. Restoreexacto14/32dualSPIgenOFF/WAVIDLE10,018s/313344/0drop-fatal,SHAiguales/Qlibre. `diagnosticos/resultados_v20/normal_synth_journal20_20261104/report.json` y`synth_start.jsonl`. Sinanalog/audioaceptación; inerciausuariosinrepro/resolver. [Informe](docs/V20_SYNTH_PLAY_LOCAL_20261104.md).

- SinQ:15testsPASS5,401s, clickreal→ownerACKIDLE/BUFFER/PLAY ystatuscargando/Activo; solicitudfallidaBEGINvisible. SpawnrealpaneldefaultDXPiano20k prepara1,164s/PCM480842..3279; FMgenéricoprevio12,020s807..3288, NOcold/warmcontrolado. Sinproductpatch. Poolsnapshot2sfalsepreservado, inspecciónposteriorconfirma ningúntestPythonvivo. FaltaestadorealGUI/future/nueva sesiónPLAYdelusuario; noatribuirhardware/resuelto. [Informe](docs/V20_SYNTH_PLAY_LOCAL_20261104.md).

# 4/11 · Cuadrada: cortes falsos de frame RF reducido

- Reprolocal2kHz/40k: ventana80k/pixels400 preselecciona1200puntos yredetectagapsfalsos→400NaN;V19igual. Ventana9000NOreproduce. V20conservacontinuidadprobadasóloenreferenciaexactaframeRFpreseleccionado; evitaese recorte, gapreal/NaNsiguen, sinenvelope/badge.4testsPASS1,866s fases/ring/gaps/integración/mixed. Benchpreparación0,483→0,011ms NOFPSvisible. BackupSHA `respaldos/host/v20_before_reduced_false_gaps_20261104`;sinQ. [Informe](docs/V20_CUADRADA_CORTES_20261104.md). FPSgeneral/otrasventanaspendientes.

# 4/11 · Arranque: discovery USB fuera del hilo GUI

- FísiconormalreconnectPASS: ADC14/40kdualconecta2,952s→10,064s/401666muestras→disconnect→reconecta3,475s→10,088s/403456→cierre49,068s,errors[]. Cada sesiónrestaura snapshot14/32dualSPIgenOFF/WAVIDLE10,025/10,022s y313344/0drop-fatal, identidadesMCU/relayexactas+ownerliberado. SinRADIO/2M/override/deploy. Evidencia `diagnosticos/resultados_v20/normal_reconnect_20261104/report.json`; noafirmarresueltocuelgueintermitente. Qrestauradalibre.

- ReintentoGUIV20: reproducido antesFAIL workerfinishedsinconectar deja referencia/Conectando. Parchethread.finished→limpiezaasync existente sólosiesactual; finishedviejoignorando, Qsinconfirmarcontinúafallo.3testsretryPASS1,898s, grupo6PASS4,277s. BackupSHA `respaldos/host/v20_before_connection_retry_20261104`; evidencia `diagnosticos/resultados_v20/connection_retry_20261104`. SinQoperado/cambiosplazos; causacuelgueoriginal/hijovivoimportando siguenpendientes. [Informe](docs/V20_ARRANQUE_PUERTOS_20261104.md).

- Corregidobloqueoconcreto constructor/ActualizarV20: ADB+comports ahoraasync, slotGUIcondatos, progreso…/errorstatus, conexióninhabilitadamientrasbusca; preservaselección eignoraresultadostardíos/cierre/cambioworker. RutaanteriortambiénV19, noregresióndemostrada. Mismafakelatencia350ms: retornos354,5/354,9→0,23/0,21ms; primerheartbeat355,8/354,9→7,3/6,4ms offscreen, noFPSvisible.4testsPASS; backupSHA `respaldos/host/v20_before_async_ports_20261104`. SinQoperado. Bloqueointermitenteconexiónsiguependiente; importsstallsV19observados, noatribuircausa. [Informe](docs/V20_ARRANQUE_PUERTOS_20261104.md).

# 4/11 · Por qué el margen de 2M es menor

- DiagnósticoEOF: sesiónGUI manual11:32–11:36 (~4min), NOsegundocaso runnerpareado20s. Logrelay14:36:21.693UTC cierra cliente `sent=-1`,739msantesEOFhost; adquisiciónsigue~2M/drop0. Sinerrno no distinguir colaTCP64llena deerrorenvío; UNDERRUNposteriornocausa demostrada. Corregida pérdidaevidenciaV20: excepcionesEOF/CRC/seq capturan pendientes+decoderacotado antesrestore, appyaloconserva. BackupSHA `respaldos/host/v20_before_eof_snapshot_20261104`;11focalizadosPASS. Archivocompleto16PASS+1timeout noresuelto parentdeath fixtureV19; sinmodificarV19. Sinreproducciónciega20s nioperaciónQnueva; ver [informe](docs/V20_MARGEN_ADC8_2M_20261104.md).

- Comparación A0 normal incompleta: 1,860465M/20,082s PASS, exposición6/6, margen playing12,2657%/all14,4143%, cola4/16 (headroom_passFalse). Intento2M posterior terminó en EOF durantePLAY y receptor sinresultadofinal; no hay margen/exposiciónfinal pareados válidos. No repetir trasfallo sinhipótesis. Recuperación independiente desde snapshot de sesiónfallida: ADC14/32dual/SPI/genOFF/WAVIDLE,10,024s/313344muestras/0drop-fatal, identidadMCU/relayexacta yQlibre. CausaEOF ySIGSEGV120s abiertas. [Informe](docs/V20_MARGEN_ADC8_2M_20261104.md).

- ADCsolo pareado1,86→2M pierde130,8µs de presupuesto/nodo y aumenta100,0µs el servicio derivado; margen19,296→7,511%. Ambos perfiles usan N3488, SPI40/WORD/FIFO10/cola16. RADIO/A0 agrega carga; comparación 1,86playing12,224% vs2M0,8245% no es pareada por exposición/instrumentación. Último80s2M playing0,5264%, all1,2724%; conservar denominadores y SIGSEGV abierto. [Comparación](docs/V20_MARGEN_ADC8_2M_20261104.md).
- Se probó un solo proxy local `Os` vs `O2` del empaquetado/CRC: igualdad de bytes y CRC, sin mejora de tiempo en Mac y mayor tamaño ARM; descartado sin instalar. [Resultado](experiments/v20/adc8_2m_prepare_o2/result.json). Próximo candidato requiere medir con más precisión el coste extra MCU/relay antes de intervenir una sola variable; no confundir cola8 de otros bits con margen ADC8/2M.

# 4/11 · ADC8/2M incorporado sólo como opción experimental V20

- Catálogo/selector/estado/tooltip V20 muestran 2M ADC8/CH1/80ticks/3488pares/cola16 como EXPERIMENTAL. Guarda RADIO/A0 exacta y US con auxiliares previos. Sin despliegue ni priming; tasas aceptadas/default intactos. Backup `respaldos/host/v20_before_experimental_2m_20261104/`;13tests focalizados PASS Python3.13. Ver [diagnóstico](docs/V20_SIGSEGV_Y_COLA8_20261104.md).
- La caída SIGSEGV120s no reproducida sigue abierta;80s pasó funcionalmente pero exposición76,19% y margen playing0,53%. No declarar estable. Próximo: hipótesis específica de caída antes de campañas largas; cola8 permanece sólo en overlay local hasta tamaño/mapa ARM y binding privados.
- Smoke físico normal 20s del selector/A0 2M, sin overrides privados: PLAY/STOP/progresoPASS, exposición periódica6/6, restauración independiente10,025s sin pérdidas/fatales, identidadMCU/relay exacta; Q libre. [Reporte](diagnosticos/resultados_v20/experimental_2m_normal_smoke20_r2_20261104/report.json). Sigue siendo exploratorio.

# 4/11 · Próximo bloque V20: caída GUI antes de cola8 física

- Sol único ejecutor y dueño Q. La GUI 2M/US/A0 visible cayó por SIGSEGV a los65,86s, sin gui.json ni aceptación120s; la recuperación hija tardía y verificación nueva confirmaron V20 exacta, ADC14/32 dual, generadorOFF, WAVIDLE, SPI y10s/0dropped-fatal. Preservar informe fallido. El `.ips` nuevo ubica NumPy `logical_or.reduce` desde QTimer; no hay callsite Python ni causa ADC demostrada.
- Herramienta privada `--trace-numpy-any` registra callsites sólo durante diagnóstico; reproducción acotada80s pasó funcionalmente, pero exposición76,19% y margenradio_playing0,53% (all1,27%)/cola10/16. Todas2476llamadas registradas cerraron; SIGSEGV no se reprodujo. Mantenerlo abierto, no alargar campañas sin hipótesis específica.
- Cola8 local preparada para10/116/5568,12/140/7488,14/158/5952, con headers MCU/relay pareados y SHA base; arnés C++ local y pruebas de fuente5PASS. Falta mapa/tamaño ARM y binding privado de pareja antes de cualquier instalación/prueba física. No alterar fuentes/recibos sellados ni publicar tasas por campañas privadas. [Informe](docs/V20_SIGSEGV_Y_COLA8_20261104.md).

# 3/11 · En curso: confirmar 2M con instrumentación ligera

- Root únicoQowner. EN CURSO runner `installed_2000_fullui_priming_native_us60_r2_20261103`, despuésr3; primero leerreportes/restauración. Misma candidata privada depriming12ms (steady6), fullUI/G7+EQ+solapaRADIO, restartA0→US3tasas→60sdespuésreanudar; sin temporizadoresdetallados delhost, decoderestricto yWireMetrics nativos intactos.
- R1 de ese modo PASS (cola8/16,margen0.54%,60s,restauración10s/identidadigual). No latenciasACKdetailed; reportdiagnostics_completeFalse es esperado, diagnostics_requirement_metTrue para native-only. Se mantienen mode/métricas separados.
- Priming con instrumentacióndetallada NO suficiente: `installed_2000_fullui_priming_us60_r1_20261103` UNDERRUN13sdespuésUS,21CHUNKsinconfirmar~345ms,audiopreparado20k,cola7/16,RFíntegro/restorePASS. Detenidasrepeticiones. PrimerfullUIcontrol tambéntuvoEOF/restoreFalse, pero recuperaciónposterior sinreset/deploy confirmóbaseline10sPASS (`recover_fullui_control_20261103`).
- Astra eligió quitarinstrumentaciónantesdecambiarservicio; no activarframe-service ni nuevosbuffers. Solimplementóprivatepriming5tests; rootverificóPy3.13. El priming sigue privado; tasas públicas iguales.
- Solcorrigió unbug real de cierreScanactivo+EOF: `scan.finish()` conerror/restore_confirmedFalse ysinmodal durante_close_pending. Noexplicaelclose_timeoutfísico porqueese snapshot teníaScaninactivo. App+harness handlers únicamente; backups exactos verificadosconhashprevioreporte en `respaldos/host/v20_before_scan_eof_close_20261103/`.
- Suiteactual179PASS (`/tmp/arduscopio-v20-native-diagnostics-suite-20261103.log` pendiente copiar aevidencia). ADC10/12 RADIOA060sPASS previos a exigirG7/EQvisibles; repetir workloadcompleto antespromoción. FW/relay52f933bd/bf6893f5V20 intactos; NUNCArestoreV19.

# 3/11 · Tanda cerrada: estabilidad 2M y candidatos ADC10/12

- **2M/RADIO/A0:60s +3x120s PASS**, exposición100%, fuente activa hastaSTOP,0 interrupciones/pérdidas registradas. Márgenes reproducción0,82/0,69/0,60/0,62%;picos7/9/10/10 sobre16. NO reserva10%, NO promoción pública. ADCsolo2M60+120s tambiénPASS,7,57/7,67% y5/3 sobre16.
- ADC10/1.379.310:60s PASS82.708.464muestras,cola2/4,margen12,42%. ADC12sondeos1.111.111/1.126.760/1.142.857:3x20s PASS; máximo confirmado120s/137.056.896muestras/0drop-fatal/cola2/4/margen8,95%. Todavía ADCsolo, NO aceptaciónGUI/audio/analógica. ADC14>1M requiere candidato nuevo, no ensayado.
- **Q libre**: todas las corridas restauraron snapshotV20 >=10s/0drop-fatal, identidadMCU52f933bd/relaybf6893f5 igual; ADC14/31250dual,generadorOFF,ningún lector de prueba. V20 sigue activa, V17/V18/V19 intactas. No cambiosFW/relay/catálogo ni límites.
- SuiteV20 actual167PASS; log `diagnosticos/resultados_v20/stability_suite_20261103/unittest.log`. Implementación de cadencia equilibrada40k ya aceptada físicamente:~15→29imágenes nuevas/s; alta tasa/mixto largo conserva límites previos.
- Resumen y hashes `diagnosticos/resultados_v20/stability_campaign_20261103/summary.json`; informe `docs/V20_ESTABILIDAD_TASAS_20261103.md`. Primera GUI2M bloqueada por guard no es aceptaciónA0; posteriores usan excepción privada exacta, guardproducto intacto.
- Próximo bloque: otras cargas/ScanUS/transiciones a2M y GUI/audio de candidatosADC10/12 antes de ampliar catálogo; margen<10 NO bloquea explorar estabilidad, siempre informar reserva por separado. README landing sin cambios.

# 3/11 · Ensayos actualizados: 2M con RADIO/A0 y candidatos ADC10/12

- ADC8/2M solo:60s y120s PASS integridad; márgenes7,57/7,67%,picos5/16 y3/16. SnapshotV20 restaurado10s eidentidadesiguales.
- RADIO/A0 a2M: primera corrida no arrancó A0 por guard de perfil privado; NO aceptaciónaudio. Segunda `installed_2000_radio60_r2_20261103` PASS60,04s/2.399.040 muestrasDAC,exposición100%,fuenteactiva sinerror antesSTOP,cola7/16,margen reproducción0,82%. Muy poca reserva; NO tasa pública. Excepción sólo en arnés, guardproducto intacto.
- ADC10 privado ticks116/1.379.310:60s PASS,82.708.464muestras,0drop/fatal,cola2/4,margen12,42%. ADC12 ticks144/142/140:3x20s PASS, márgenes12,10/10,59/8,98%,cola2/4,0drop/fatal. Herramienta registra perfiles sólo en proceso y valida su presencia en fuentesMCU+relay vinculadas al binario instalado. No firmware/relay/catalog changes.
- SuiteV20 **167 PASS** fuera sandbox; errores previos de POSIX/nice fueron sandbox. Log `diagnosticos/resultados_v20/stability_suite_20261103/unittest.log`.
- Primera GUI2M/RADIO/A0120s PASS,cola9/16,margen0,69%,fuente activa4.797.120 muestrasDAC sinerror. ADC12max120s PASS137.056.896 muestras,0drop/fatal,cola2/4,margen8,95%. EN CURSO: `installed_2000_radio120_r2_20261103` y después r3 (runner secuencial, detener si falla). Leer reportes y verificar exclusión antes de tocarQ. Docs `docs/V20_ESTABILIDAD_TASAS_20261103.md`. Q permaneceV20; versionesviejasquietas.

# 3/11 · Cadencia RF recuperada y exploración sostenida de tasas

- Incorporada cadencia equilibrada sólo para V(t) RF <=40 kHz, ventana <=80.000 muestras, sin RADIO/FILTER/raster. Fórmula por coste con presupuesto visual del 60%, piso34ms, nunca más lenta que la política previa. Fuera de ese ámbito se conserva la cadencia anterior. Backup: `respaldos/host/v20_before_balanced_cadence_20261103/`.
- Físico limpio a40k: control20s 15,09 imágenes nuevas/s; candidata20s 28,82 y confirmación60,60s 29,14. Exposición100%, sin pérdidas/fatales; snapshot V20 restaurado y verificado10s. Informes `rf40k_physical_legacy20_r2_20261103`, `rf40k_physical_balanced20_20261103`, `rf40k_physical_balanced60_20261103`. Primera corrida legacy20 invalidada por traceback del arnés; no usarla para aceptación. No garantiza estos FPS en ventanas largas/alta tasa.
- Pedido actualizado: explorar estabilidad a2MS/s aun sin10% y luego candidatos de más bits, separando estabilidad de reserva. Cola16 sólo para ADC8 rápido; ADC10/12/14 actuales tienen4 nodos de tamaños distintos.
- ADC8/2M instalado,60s:119.928.776 muestras,0 pérdidas/fatal,cola pico5/16,margen medio7,57%,slack mínimo63.708ticks. PASS integridad, NO10% de reserva. Informe `installed_2000_sustained60_20261103/report.json`. Iniciada corrida independiente120s `installed_2000_sustained120_r1_20261103`; consultar reporte antes de operarQ.
- Herramienta `probe_working_v20_rates.py` conserva V20 y restaura snapshot; admite candidatos privados ya compilados ADC10 ticks116 y ADC12 ticks144/142/140, sólo en su proceso. No cambia manifiestos públicos/firmware/relay. ADC14 por encima de1M necesita candidato nuevo, no está probado.
- Astra planificó; Sol agotó cuota, root continuó ejecución y revisión como se informó. V17/V18/V19 intactas. README de presentación sin cambios en este bloque.

## 3/11 · Pérdida de FPS localizada a baja tasa

A40k RFpuro/V(t) normal V17/V18~60FPS, V19/V20~17–18. Ensayo causal mismaV20 timer16privado~45–47FPS peroCPU3x/picosdemora: no incorporar talcual. Diseñar cadencia con equilibriofluidez/reserva y validarfísico antes de tasas nuevas. Evidencia: `diagnosticos/resultados_v20/rf40k_comparison_20261103/README.md` y `rf40k_fixed_timer_20261103/README.md`. Sin cambios de producto/Q/versiones congeladas.

## 3/11 · Perfil Astra/Sol cerrado sin cambios de producto

Comparaciones alternadas descartaron vectorizar índices y quitar el reajuste desde pintura: no cumplen criterios globales. Evidencia en `diagnosticos/resultados_v20/mixed_profile_20261103/README.md` y `mixed_timer_20261103/README.md`. Siguiente foco: medición completa/copia del ring envuelto. Cadencia, precisión, límites y Q intactos; no probar tasas mayores aún.

## 3/11 · Recuperación antes de tasas nuevas

Implementado y validado retiro de envelope, recuperación de detalle V19, Play único Synth y menos copias en vista mixta. Ver [evidencia y límites](docs/V20_RECUPERACION_20261103.md). Pendiente: vista mixta2s a1.86M sigue ~5 eventos pintura/s; mejorar antes de tasas nuevas. V20 permanece activa; V19 congelada.

# 2/11 · V(t) envolvente automática incorporada; datos completos para cursores

- Usuario pidióenvolventecuandohaymuchasmuestras,volverapuntosalzoom ycartel env. Implementadoenmonitor/v20/temporal_envelope.py +temporal_raster.py;appmantienecapturacruda (reducciónanteriordeshabilitada). Sólo geometría delworker:min/max porcolumna/tramo, enlacesdeextremos, no puenteNaNs/gaps. Ningún cambioADC/DSP/firmware/relay/V19.
- Auto:≥100000visibles y≥8muestras/píxelfísico; salir<50000o<4ppx (histéresis). Cursorusaframeoriginalcompletoindependientedelaenvolvente. envpequeñogristopright,nointerceptaclics;ocultoalvolverapuntosuotrosmodos.
- 140testsV20PASSinclregresionesraster/cursor;trasNoButton/telemetría23focalizadosPASS. Integraciónworkerprueba raw200k+cursorrealpuntointerioryzoomvueltaapuntos. Benchlocal3.72M:mediana724→75ms pintor≈9.6x,excluyeIPC/visibleFPS.
- QV20yaactiva:2shistoria3.720930Mmuestras,detalle100,ADC8 1.86M +RADIOA040khold60.075s PASS,exposición100%. envvisible,capturaCH1full3.720930M/RADIO80000;worker mediano129msvsbaseline3092ms;imágenesnuevasobservadas0.264→2.518Hz. Comparaciónseparadabaseline20s/nuevo60s,nogarantíauniversalFPS.
- SnapshotV20≥10s0pérdidas/fatal,identidad/receipt/selloiguales;QquedaV20activa/generadorOFF/sinsesión. Nopromocióntasasniaceptaciónanalógica. Postevidencia sólo2docstringsactualizados, ejecutableigual(hashreconstruidoverificado).
- docs/V20_ENVOLVENTE_20261102.md · diagnosticos/resultados_v20/temporal_envelope_validation_summary_20261102.json. SourceproofArduino/informeselladointactos.V17/V18/V19quietas. Rootimplementó/midió(Solsincuota,Astranoejecutó).

# 2/11 · GUI: transición alta y V(t)2s/detalle100 PASS; raster~3s/imagen

- Root ejecutó sinAstra niSol(sincuota). Producto/firmware/relay/prioridades/buffers/flowlimits intactos; cacheDXprevia conserva. HerramientaexigeV(t)real con --radio-time-view separado deanalysis-only;16focalizadosPASS. NoQdeploy,noV19.
- Highrate1.86→WAV→DX40k20notas/30sPASS conexposición100%,recuperaciónV20≥10s/0drop-fatal eidentidad/receipt/seal iguales. No pausacapturada,no arreglocausalconfirmado.
- Intentoslongwindowanteriores completaron audio/recuperación pero fallaroncriterios setup(FFTnoraster; analysis-onlyA0off). Evidenciapreservada,noerroresdeproductoatribuidos.
- V(t)real2s(3.720.930muestras)/detalle100/RADIOA0/ADC8 1.86M:20.035sPASS,exposición100%,rasterpublicado/visible;recuperaciónidentidadesiguales. Worker3.294/3.069/3.115/3.006ms porimagen,limitadibujo. CallbackGUImax156ms,heartbeatgapmax737msinclinicio,stacks0bytes. No equivaler3sworkerablockGUI;pausa1.9s anterior sinreproducir.
- docs/V20_GUI_PAUSAS_20261102.md · diagnosticos/resultados_v20/v20_gui_stall_followup_summary_20261102.json. Próximo:rasterprivado preservandopíxeles/huecos,mediciónantesincorporar; noparalelismoextraniotrosbuffersporahora.
- V20sigueactiva,generadorOFFrestaurado,sinlectorprueba.V19respaldoquieto.

# 2/11 · Optimización host DX Piano: caché por nota, audio exacto y pase funcional40k

- Root ejecutó; Sol sin cuota y Astra no ejecutó. Perfil real del panel: DX40kmean4.636ms por480 frenteFMbásico1.209ms, sinIPC/Q. Costeprincipalvoice_render. CandidateLRU256sólo(brilloDX,profundidadgrave) estáticosporcarrier; fórmulasoriginales, sinfase/audio/envolvente mutable.
- Benchmark6repeticionesalternadas baseline/candidato: mediana4.332→4.065ms,mejoraLOCAL6.17%; noFPSniSPI. Candidato incorporado a monitor/v20/fm_source.py trasfloat exactoa20/40k,cambiosdeacordes/rampas/gate/release,DACygananciaigual ycacheacotada.18focalizadosPASS;21conwrapperPASS,últimametadatadehash9PASS. Backuphostrespaldos/host/v20_before_dx_note_cache_20261102/hashfe029ad…;nuevoec2f46b….
- FísicoDXPianoDAC40k/20notas/hold30s PASS,ADC40kdualdesdeinicio; presetpercusión,pico20no20sostenidas. Ventanaoculta0%,noaceptaciónvisible niarreglocausalconfirmado. PLAY/progreso/STOP/cierre yrecuperaciónV20≥10s0drop/fatal;firmware/relay/identidad/recibo/selloigual. V20continúaactiva,generadorOFF. NoV19ni tasaspúblicasnuevas.
- Herramientasnuevas tools/profile_dx_piano_v20.py y experiments/v20/dx_note_cache/benchmark.py sólooffline,Qnooperadoenbenchmark. Reports diagnósticos dx_render_profile_20261102/dx_note_cache_candidate_20261102/v20_dx_note_cache_physical_20261102_dac40k. docs/V20_DX_PIANO_CACHE_20261102.md.
- Pendiente: reproducciónconexposición/cargainicialequivalente ypausasGUI/RFconpilas; no atribuirunderrunanteriorresuelto porunpaseoculto. No QoS/buffers/gate86/firmware/relaymodificados.

# 2/11 · Controles FM básico sostenido 20 voces a DAC20/40k: 60 s PASS

- Sol agotó cuota; root continuó pruebas locales y fue único dueñoQ en este bloque. Astra no ejecutó. Cambios sólo tools/tests: --synth-profile sustained-fm (FMManual1oscilador,ADSRsustain0.7,20notas), paneldefaultintacto; criterio exige20en todasobservacionesPLAY.23tests perfil/escenario/wrapperPASS, más pruebasobserver/regresión y2scopegenéricoPASS.
- Nuevo --radio-rate40000 de diagnóstico para aislarSynth, frecuencia10k dentrodebanda; defaulthelper1.86M intacto. Observador permite explícitamente perfilno-nativo en ruta privadaV20; native_counters_expected/performance_acceptance_eligiblefalse. No fakecounters/aceptación pública.
- PrimerperfilaltoADC fallóantesSynth porentregaGUI1.604M/1.6M; aislado tuvoRFpending1s durantepreparación+GUIpausa1.923s. Ambos recuperaronV20; rastreodepilasposteriorno reprodujolapausa. Nodarporarreglado.
- Controles conADC40kdual: DAC20k/40k,hold60s desdePLAY, vocesobservadasmin=max20, exposición100%, recuperaciónV20≥10s/0pérdidas-fatal,identidad/recibo/selloiguales. V20quedaactiva/generadorOFF, sinV19. Perfilbásico NOequivaleDXPiano3osciladores.
- DXPiano previo20k sóloPCMsostenido(conmin0voces),40k underrun~2santesSIGINT; sigueabierto, sincausaexclusiva. No tocarproducto/firmware/relay/gate88/buffers/prioridades ni subir tasas por estoscontroles.
- docs/V20_SYNTH_SOSTENIDO_20261102.md · diagnosticos/resultados_v20/v20_sustained_fm_control_summary_20261102.json. Próximo: acotarDXPiano/render+IPC ypausasGUIconpilas,evidencianuevaantesoptimizar.

# 2/11 · V20: RADIO→WAV sintético→Synth20, dos PASS funcionales y restauración

- Primer intento falló Synth sin nuevo BEGIN/PLAY; STOP del smoke llegaba 10,3932 s después de solicitarlo. Se detuvo r2 y se preservó evidencia/restauración V20. Medición offline de otro spawn/preparación: 14,7356 s; no es el tiempo medido del intento fallido ni prueba su causa exacta.
- Sol ajustó sólo tools: esperar PLAY nuevo hasta 120 s, hold Synth 5 s desde ACK, STOP único/confirmado y no cerrar mientras pendiente; ACK tardío rechazado. 14 focalizados PASS. Producto/timeouts/audio/QoS/guard88/buffers/tasas/firmware/relay intactos; fuentes de escenario congeladas y hashes iguales en ambas corridas.
- Dos repeticiones PASS: RADIO 60,0011/60,0141 s con ADC8/1,86MS/s CH1→WAV500Hz sintético→Synth. WAV/Synth usan ADC8/40kdual. DAC: RADIO40k, WAV40k; Synth20k. WAV de entrada20kmono4s, no música de usuario. Synth hold5,0640/5,0062 s y pico remoto20 voces renderizadas; no significa20 sostenidas/acústica.
- ACK raw/decode: 5582/5582 y5578/5577; r2 deja1 correlación decode pendiente. Limitación diagnóstica explícita, sin inferir pérdida ni repetir por contador. Exposición100% ambas, no prueba FPS ni aceptación analógica. pending_timeout=0.
- Recuperación V20 10,0211/10,0210 s,313344muestras cadauna,0pérdidas/fatales. Identidad/recibo/informe sellado iguales; final V20 activa/generadorOFF,lock disponible,sin procesosprueba. Sol único dueñoQ en campaña; propiedad liberada. V19 no iniciada, landing intacta.
- [Informe y límites](docs/V20_TRANSICIONES_AUDIO_20261102.md) · [Resumen medido](diagnosticos/resultados_v20/v20_audio_transition_confirmed_campaign_20261102_083132_summary.json).

# 1/11 · V20: campaña autónoma 3×120 s RADIO PASS; Q queda V20 activa

- Usuario «dale más»: Sol único propietario Q durante la campaña; root no operó Q. Preflight lock/monitor/identidad PASS. Tres corridas independientes con helper instalado, ADC8/1.860.465 S/s, RADIO/A0 40 kHz, sin WAV/Synth/Scan. Sin nuevos cambios de código, QoS, guard 88, buffers, tasas, firmware o relay; TCP/86 siguen sin incorporar.
- r1/r2/r3 PASS: holds 120,0462/120,0602/120,0764 s; ACK raw/decode 10.025/10.028/10.031 correlacionados completos, máximos raw 34,82/47,55/39,67 ms, decode 12,02/13,43/9,72 ms; gap CHUNK host 136,65/114,81/119,96 ms. pending_timeout=0 en todas.
- Margen RADIO 12,1945/12,1977/12,0346 %, cola pico 5/16,4/16,4/16; legacy headroom_pass=false en las tres. Exposición 0/0/96,15 %: r1/r2 sin aceptación visible; r3 supera exposición, no prueba FPS/aceptación analógica ni arreglo causal.
- Recuperaciones V20 10,0227/10,0235/10,0236 s, 313.344 muestras cada una, cero pérdidas/fatales. Identidad/recibo/informe sellado iguales. Snapshot inicial y final con generador OFF. Comprobación final instalada PASS: V20 activa, lock disponible y sin procesos GUI/receptor de prueba; V19 no iniciada. Sol liberó propiedad Q.
- Contadores abarcan todo el ciclo (arranque/RADIO/recuperación); eventos no equivalen a duración bloqueada ni causa física. No promoción pública ni fallo previo declarado resuelto.
- [Campaña y límites](docs/V20_SERVICIO_RADIO_DIAGNOSTICO_20261101.md) · [Resumen medido](diagnosticos/resultados_v20/v20_service_radio120_campaign_20261101_211008_summary.json).

# 1/11 · Diagnóstico de servicio RADIO incorporado; 60 y 120 s PASS sobre V20 activa

- Sol implementó contadores opt-in en child_stages.wav_service y wrapper instalado tools/probe_working_v20_gui.py;34tests focalizados PASS. Diagnóstico OFF conserva comportamiento; ON comprobó mismos bytes/orden/offsets/créditos/tokens. Sin QoS, guard86, buffers, tasas, firmware ni relay nuevos. Astra sólo plan/revisión previo, no volvió a ejecutar.
- Root único dueño Q:60.010sRADIO/A0PASS,5030ACK,rawmax20.60ms,CHUNKgapmax118.43ms.120.036sPASS,10026ACK,rawmax61.26ms,decodeentrymax31.42ms,CHUNKgapmax216.31ms. Ningún timeout pendiente. Contadores de eventos whole-lifecycle, NO duración bloqueada ni causalidad.
- Ambos restauran sólo configuración V20 con10scontinuidad/0dropped/0fatal; identidad/recibo/informeactivación iguales. Q quedaV20activa,ADC14/31250dual,generadorOFF,sin lector de prueba; V19respaldo quieto.
- GUIexposed21.43%/0%: NO calificación visible. Campo legacyheadroomfalse enRADIO120s(margen12.21%,pico4/16). Causa del fallo anterior NO confirmada, tasas públicas intactas.
- Evidencia: diagnosticos/resultados_v20/v20_service_diagnostics_summary_20261101.json y docs/V20_SERVICIO_RADIO_DIAGNOSTICO_20261101.md. Próximo: carga comparable/pausas; QoSreversible sigue experimento separado, no incorporado.

# 1/11 · V20: diagnóstico de servicio RADIO 60 s PASS; 120 s en progreso

- Sol implementó contadores opt-in acotados y helper sobre V20 instalada; 34 tests focalizados PASS. Root revisó y es único propietario de Q. Sin QoS ni cambios de comportamiento, buffers, tasas, relay/firmware o guard 88; TCP/86 siguen privados sin incorporar.
- RADIO/A0 60,00955 s PASS funcional: 5.030 ACK raw correlacionados/decodificados, raw máximo 20,60364 ms, demora decode 8,47319 ms, gap CHUNK host máximo 118,43241 ms y pending_timeout=0. No se solicitaron WAV/Synth/Scan.
- Snapshot V20 restaurado: 10,02348 s, 313.344 muestras, cero pérdidas/fatales. Identidad, recibo de trabajo e informe sellado de activación iguales; V20 sigue activa, V19 sólo respaldo. Exposición 0,2143: NO aceptación visible ni prueba de arreglo causal.
- Contadores de motivos abarcan arranque, RADIO y recuperación; son eventos, no duración bloqueada. No inferir porcentajes temporales ni causa física.
- Root ejecuta repetición 120 s con el mismo helper; resultado pendiente. Durante esa prueba sólo documentación: no fuentes, Q adicional, tests ni otra revisión Astra.
- [Diagnóstico y corrida](docs/V20_SERVICIO_RADIO_DIAGNOSTICO_20261101.md) · [Informe 60 s](diagnosticos/resultados_v20/v20_service_diagnostics_radio60_20261101/report.json).

# 1/11 · V20 activa como base de trabajo; V19 queda de respaldo

- Instrucción vigente: no restaurar V19 después de cada ensayo normal. V20 se mantiene activa; V19 sólo recuperación ante fallo operativo o pedido del usuario. No correr probes legacy que restauran V19 sin adaptar su baseline a V20.
- Sol implementó activación persistente y recibo de trabajo separado; 28 tests focalizados PASS. Root revisó y operó Q como único dueño. Astra sólo plan/revisión, sin ejecución.
- Activación PASS: diagnosticos/resultados_v20/v20_working_active_20261101/report.json. V20 SRAM3 corregida firmware52f933bd… y relayoriginalbf6893f5… activos; TCPcandidato y host86 NO incorporados. V19 respaldada y detenida; sin borrado de biblioteca AppLab.
- Conexión habitual V20 (sin ENVprivado) PASS: default_connection_verification.json,10.026s,313344muestras,0dropped/0fatal,continua. QuedaADC14/31250dual, generadorOFF. Recibo working_pair.json identificaexactamenteV20 yno alteraaccepted ni tasas públicas.
- Report deactivación sellado: no modificarlo (hashenrecibo). Guardar nuevaevidenciaenarchivosseparados. Cambiosdefirmware/relay requierenpruebasyactualizarrecibotrabajo; no falsearaceptación.
- Pendienteaudio: diagnóstico de entregas/servicio y QoSreversible segúnplanAstra; implementaciónSol. 2MS/sintegridad60sPASSperomargen7.25%,nocalificado.

# 1/11 · V20: cierre TCP/RADIO; guard host de 86 ticks revertido

- Relay TCP candidato privado: ADC8 CH1 60 s pasó integridad a 1.860.465 S/s (margen 19,02 %, pico 2/16) y 2 MS/s (7,25 %, pico 3/16); 2 MS/s no cumple margen de 10 %. Sin promoción ni mejora causal demostrada.
- GUI con candidato TCP falló a 57,4 s de audio; baseline anterior pasó funcionalmente con exposición insuficiente para comparación visible equivalente.
- Host privado de 86 ticks: primer intento no llegó a RADIO. Repetición final falló con RADIO state=4/reason=2 y FlowLimitExceeded (backlog 1,00047/1 s); exposición GUI 0 %, ACK raw máximo 33,9145 ms y demora decode 6,1381 ms. Integridad combinada no aceptada; sin causa ni arreglo confirmados.
- Guard host restaurado a 88 ticks. Cambio 86 sólo en experiments/v20/tcp_queue_recovery/service_profile86.patch, NO incorporado/default; relay TCP sigue privado. Los 56 tests V20 pasaron antes de revertir; después de revertir, 14 tests focalizados PASS (radio_frame_service y wav_reset_confirmation), Python 3.13 habitual/caché temporal. Validación local, no física.
- Última restauración histórica Q: V19 exacta, restoration.ok=true. Nueva instrucción: continuar con V20 activa; V19 sólo respaldo/recuperación si V20 inoperativa o solicitado. El coordinador prepara la activación base V20. No se operó Q en este cierre; V17/V18/V19 y landing raíz intactas.
- Preparados activate_working_v20.py y recibo de trabajo separado para conexión habitual instalada: 28 tests focalizados PASS. Sin Q operado; root revisará/activará V20 y validará 10 s default en informe separado. No modificar el informe sellado por hash. Probes legacy restauran V19: adaptar baseline a V20 antes de usarlos. Cambios firmware/relay requieren nueva prueba y recibo actualizado.
- Próximo: plan Astra para contadores de servicio y QoS reversible, sin aumentar RAM; Sol implementa y el coordinador conserva propiedad exclusiva de Q.
- [Seguimiento y evidencia](docs/V20_TCP_AUDIO_SEGUIMIENTO_20261101.md).

## 1/11 · Revisión Astra completada; memoria, ACK WAV y rollback implementados en V20

- Astra (memoria y audio, sólo lectura) revisó fuentes/ELF/evidencia. Límite inicial de uso resuelto al reintentar. Sol implementó reset WAV acotado; root revisó/validó en Python3.13habitual y fue único dueño Q. No atribuir hardware a los agentes.
- Memoria: Storage sigue213088bytes [0x20060000,0x20094060), fuera del heapLLEXT terminado0x20053890. Ahora construcción explícita Samples en4slots, bindbool con guardas antes de modificar, fallo propagadoalarranque y static_assertcapacidad. Contrato exige nueve rutas BSPexactas. No reservaformal linker ni lecturaECC/kernelactivo; no afirmar RAMtotaldesaparecida por mover buffers.
- Firmware nuevo52f933bdb9c632544624e5d4188a740a9cdb429596bfe5a4d926900e7538aefe. Relay bf6893f5a0fbab8676120a5decd8c6109698fa852be02333918b1d6e4a2a909d sin cambios. Nuevo proof: diagnosticos/resultados_v20/storage_lifetime_cycle_20261101/report.json (usar éste, los anteriores ya no coinciden con fuentes).
- Física misma conexión16slots8/1.86→4CH1 14/1M→dual14/363636→16slots8/1.86 PASS,4ACKIDs distintos/datos válidos. ADC10s1.86/2MSintegridadPASS; no promoción2MS/holgura.
- BUG reset_wav_output corregido: timeout borraba pending y podía aparentar ACK. Ahora ACKnuevo/RIDexacto/reason0/deadline3s; STOP IDLE/DONE.12tests reproducenackviejo/timeout/tardío/rechazo. No cambió service_wav/créditos/reservas/timeout. Astra revisó sin bloqueantesGUI.
- Rollbacktool porpasos: logs/forward/socketerror no salta restauración; relaypropio por etiqueta+ID, stop→kill; no reinicio/undo sinquiescencia. Verifica cachecompleta(ELF/debug/options/enlaces/dirs)+BIN+fuentes, ausencia directorios sóloFNF tolerado. Rehearsal realcacheV20ensímisma PASS; no falloSDKrealinducido.
- ObservadorRawACK anteshookeabaV19: receptor/configV20explícitos, defaultsV19compatibles. GUI8RADIO60s+WAV+Synth20PASS:5740ACKleídos/observados,max42.31mslectura/20.25mseventos. GUI14RADIO20s+WAVPASS:2036,max37.35/8.55ms. Instrumentaciónno prueba causa666ms resuelta; sinScan/USestosensayos. WAV/Synthluegoa40kdual.
- 53testsV20PASS enPython_3_13_DataScience +regresionesfocalizadasV19. Cinco campañasrestauraronV19exacta;Q LIBRE,V19activa,V20corregidaconservadadetenida. V17/V18/V19intactas. Rasterparalelo NO incorporado.
- Pendiente: holguraADC10/RADIO y2MS, mayoraceptaciónsostenida/analógica. MejoraFIFO TCPllenoantesdedrenar detectadaAstra queda CANDIDATOSEPARADO, no cambiarordenACK/RF ni promoverlo por estesondeo. Cierregionalnativo mitigado sincausa confirmada.
- [Informe de revisión/implementación](docs/V20_REVISION_ASTRA_IMPLEMENTADA_20261101.md) · [Resumen](diagnosticos/resultados_v20/astra_implementation_summary_20261101.json).

## 1/11 · V20: coste raster medido; NO incorporar paralelo por defecto

- Misma ventana2s/100%, ADC8/1.860.465 y RADIO/A0 40kHz. Observador local 1Hz mide GUI+descendientes, CPU=1núcleo y RSSsumada (duplica páginas compartidas, NO RAM exclusiva). 29tests PASS. Producto/firmware/relay/tasas intactos.
- Worker original120s PASS: CPUmediana2,80núcleos,RSSsumada pico2,66GiB,raster1398ms,pintura1,19/s,margen12,15%,pico4/16.
- Dos procesos prioridad normal FALLÓ tras~23,55s audio: UNDERRUN state4/reason2; luego Q cerró flujo/relay PC too slow. PCM roundtrip máx18,79ms pero send→ACK666,47ms/9DAC inflight; margenRF12,25%,pico6/16 NO evitó corte. Cuatro prioridad normal NO ejecutado. Restauración externa V19 exacta PASS; no ocultar fallo por screen RF positivo.
- Hipótesis presión entrega/planificación, causa NO confirmada. Mitigación sólo privada: --raster-nice10 baja nice sólo en hijos gráficos propios. Repeticiones2y4procesos120s PASS; nice real10 verificado. No probar cura con un único pase.
- Baja prioridad2: CPU3,93,RSSsumada2,58GiB,raster1035ms,pintura1,39/s,GUI delaymáx300ms. Baja prioridad4: CPU5,48,RSSsumada3,59GiB,raster696ms,pintura1,87/s,GUI delaymáx421ms. ~doble CPU por~doble velocidad; ninguno piso8FPS. Mantener worker único normal; paralelo queda experimento privado.
- Cuatro restauraciones exactas PASS (incluida fallida). Q LIBRE V19 activa,V20 detenida. No nueva caída nativa; cierre original sigue mitigado sin causa confirmada.
- Próximo priorizar entrega audio/ACK y holgura ADC10/RADIO y2MS/s; no más integración raster hasta demostrar mejor coste y seguridad. Si se retoma paralelo: repeticiones y cursor/STOP/SINGLE/zoom/modos/gaps pendientes.
- [Informe](docs/V20_RASTER_RECURSOS_20261101.md) · [Resumen](diagnosticos/resultados_v20/raster_resources_summary_20261101.json).

## 1/11 · V20: candidato privado de raster paralelo medido, NO incorporado

- Producto/firmware/relay/tasas sin cambios. Benchmark offline: enteros descartados por píxeles distintos; chunk4096 mejora~6%. Franjas2/4procesos medianas1,75×/2,98×, todos los puntos. Rápido/Intenso exactos en fixtures; Suave tiene diferencias y usa worker original. X no finito/no monótono también fallback.
- Adaptador sólo tools/private_raster_tiles_v20.py; opt-in probe_v20_gui --raster-workers 2|4 con ventana larga100%. El monitor normal conserva worker único. 26tests PASS de píxeles/frame/token/fallback/untrabajo/cancelación/memoria/cierre/importsinbackendoculto.
- Primer GUI20 heredó offscreen del benchmark: funcional/restauración PASS pero NO validación visible. Corregido aislamiento; helper no fuerza entorno al importar. Informes nuevos guardan backend y excluyen offscreen/minimal de visible_gui_ok.
- Repetición Cocoa/DPR2 ADC8/1.860.465,2s,100%: datos/imagen/cierre PASS, exposición100%,raster650ms,2,1–2,2pinturas/s. Referencia anterior worker único1329ms/1,2pinturas/s, ensayos no apareados.
- Combinado RADIO/A0 40kHz60,013s: PASS,margen12,64%,pico4/16,slack68569,raster650–715ms,pintura~1,8/s,GUI delay máx~264ms. Legacy headroomfalse; screen privado PASS. Sigue SIN cumplir piso8pinturas/s. No confundir ventanas pintadas con imágenes nuevas ni inferir mejora MCU causal.
- Tres restauraciones V19 exactas PASS (incluidaoffscreen). Q LIBRE V19 activa,V20 detenida. Próximo: coste CPU/RAM,120s,2vs4bajoaudio,cursores/STOP/SINGLE/zoom/modo/estilos/gaps antes de incorporación. Holgura ADC10/RADIO y2MS/s pendientes. Cierre nativo sigue mitigado sin causa confirmada.
- [Informe](docs/V20_RASTER_PARALELO_20261101.md) · [Resumen](diagnosticos/resultados_v20/raster_tiles_summary_20261101.json).

## 1/11 · V20: seis pruebas de ventanas/bits; límites de rendimiento y ADC10 medidos

- 22tests locales PASS. Sólo herramientas: ventana/detalle seleccionables, raster aceptado como datos visibles, escala real registrada y reserva calculada por perfil. Producto/firmware/relay/tasas sin cambios en esta tanda.
- FFT16k12bits/1.103.448 y V(t)16bitsCH1/150.943: datos/dibujo/cierre PASS. RADIO/A0 10bits/1.355.932: funcional PASS, pero margen7,11% y pico3/4 NO holgura.
- V(t)8bits/1.860.465,2s,100% detalle: funcional/cierre PASS pero pisoFPS NO (dos corridas). Comparación misma escala real3.720.930muestras:50%=9,76–10,80eventos pintura/s;100%=1,20/s último intervalo,raster1329ms. Son eventos de ventana, no todos imágenes de señal nuevas; GUIpintado temporal máximo~38ms. No confundir aislamiento de recepción con fluidez.
- Corregido lanzador privado: capacidad16 hardcodeada era errónea fuera de ADC8/SPI40. ADC10 actualcap4; informe original conservado, resumen con reserva corregida(1libre al pico). No se tocaron colas del firmware.
- Seis restauraciones exactas V19 PASS. Q LIBRE V19 activa,V20 detenida. Sin nuevas caídas nativas; causa original de cierre sigue no confirmada.
- Próximo: benchmark offline raster completo con equivalencia antes de cambiarlo; mejorar reserva ADC10/RADIO y2MS/s de forma aislada. Más bits/dual/audio48/50 pendientes; no promover V20 ni tasas por estos sondeos.
- [Informe](docs/V20_VENTANAS_BITS_20261101.md) · [Resumen](diagnosticos/resultados_v20/matrix_long_bits_summary_20261101.json).

## 1/11 · V20: mitigación del reintento de desconexión validada

- Fallo nativo original NO reproducido ni causa confirmada. Tres V(t) previos con trazas cerraron bien: 10/10/11 singleShot en stop_input; todas las llamadas retornaron. La instrumentación puede alterar timing.
- Sólo monitor/v20/app.py: timer hijo persistente, single-shot100ms y slot estable para esperar al worker. Sin closures/timers transitorios en ese reintento. Se cancela al liberar worker; cierre sigue esperando restauración. Copia previa en respaldos/parejas/v20_monitor_before_close_timer_20261101/.
- 21tests PASS, incluidos3casos Qt reales sin Q (stop repetido, wait=False, cierre pendiente). V(t) y RADIO/A0 posteriores con Q PASS, visible, cierre/worker PASS y cero singleShot con instrumentación instalada. Hashes monitor/herramientas guardados en nuevos informes.
- Cinco corridas de esta tanda restauraron V19 exacta. Q LIBRE V19 activa,V20 detenida. Firmware/relay/tasas y V17/V18/V19 intactos.
- No declarar caída resuelta ni aceptación V20 por esto. Si recurre: faulthandler+última entrada sin retorno. Próximo: ventanas largas/matriz de bits y audio/RF conocida, luego holgura2MS/s. Scan anterior60+3x120 no se ejecutó (corrección previa); US real sí pasó después, sin candidatos.
- [Cambio y límites](docs/V20_CIERRE_TIMER_20261101.md) · [Resumen](diagnosticos/resultados_v20/close_owned_timer_summary_20261101.json).

## 1/11 · V20: US real y análisis probados; caída nativa de cierre pendiente

- Herramientas privadas ampliadas con --us, --scan-during-a0, --analysis-mode y bits/rate.18tests PASS. Sin cambios de producto/firmware/relay.
- US antes y durante A0: capturó1.860.465/1.600.000/1.403.509S/s, restauró FS y reanudó A0 con nueva sesión. Cero candidatos en ambos; no califica identificación real de emisoras/alias. Cierre y restauración V19 PASS.
- Corrección: Scan NO se solicitó en las corridas60s+3x120s anteriores. Su aserción opcional verdadera era vacua; corregidos documentos/resumen derivado, evidencia original preservada. RADIO/A0,WAV,Synth sí se ejecutaron.
- Análisis: V(t)8/1.860.465, FFT16k10/1.355.932, heatmap dual16/76.226 (ambos paneles con datos), Bode14dual/363.636 con curvas sintéticas: adquisición/dibujo visible/cierre PASS en casos finales. Bode no prueba medición analógica.
- IMPORTANTE: primer V(t) cayó al cerrar por SIGSEGV nativo PySide6 retrieveMetaObject/QTimer.singleShot; no guardó gui.json. Coordinador restauró V19 exacta. Repetición con PYTHONFAULTHANDLER=1 pasó. NO reparado: falta llamada Python exacta. Instrumentación activa y error sin informe ahora explícito.
- Todos los7intentos (6correctos+1caída) restaurados. Q LIBRE V19 exacta activa,V20 detenida. Próximo: aislar cierre intermitente; luego matriz completa/ventanas largas/RF conocida/otros bits/audio y holgura2MS/s. No promover aún.
- [Informe](docs/V20_US_ANALISIS_20261101.md) · [Resumen](diagnosticos/resultados_v20/sram3_tail_us_analysis_summary_20261101.json).

## 1/11 · V20 reparada: 60s + tres corridas120s RADIO/A0 completas

- Pareja idéntica en las cuatro corridas: ADC8/CH1 1.860.465S/s, FFT16k, RADIO→A0 40kHz. BSP y mapa corregido fijados.15tests locales PASS.
- Tres nuevas120s: márgenes12,05%/12,13%/12,02%; picos5/16,4/16,4/16; slack mínimo69204/70585/67387ticks. Ventana visible100%. Scan,WAV sintético,Synth20voces,paradas,cierre/worker PASS en cada corrida. WAV/Synth posteriores a8bits/40kHz dual.
- Screen privado de reserva PASS; legacy headroom_pass siguefalse por umbral absoluto<4. No aceptación pública ni analógica/acústica. No se cambian tasas públicas.
- Restauración exacta V19 PASS en cada repetición, lectura10s sin pérdidas/fatales y fuentes/caché/BIN/relay/config/CPU iguales. Q LIBRE V19 activa,V20 reparada detenida. V17/V18/V19 intactas.
- Pendiente: Scan US y matriz completa de análisis/bits/audio; luego mejorar margen de2MS/s (7,51% en sondeo ADC corto). No repetir la revisión de memoria ya documentada ni usar el candidato original solapado.
- [Campaña](docs/V20_RADIO_SOSTENIDO_20261101.md) · [Resumen](diagnosticos/resultados_v20/sram3_tail_fix_campaign_20261101.json).

## 1/11 · Prioridad V20: reparar mapa de memoria antes de ampliar campaña

- [Auditoría](docs/V20_MEMORIA_20261101.md): base original solapada con heap LLEXT. Reparación aislada en0x20060000, BSP fijado por hashes,15tests PASS.
- Sondeo físico10s a1,86/2MS/s PASS integridad, restauración exacta V19 PASS.2MS/s mantiene margen insuficiente7,51%; no promover.
- GUI60s RADIO/A0,Scan,WAV,Synth20,cierre PASS de la pareja reparada; margen12,30%,pico4/16. Restauración V19 exacta PASS. Próximo120s y matriz restante; conservar V19 congelada.

# 1/11 · V20: GUI visible y RADIO/A0 60s; WAV y Synth20 funcionales

- Binding privado exacto de la app candidata V20 y su relay medido. No se modificó el recibo de producción para sortear aceptación pendiente. El coordinador entrega el lock al receptor hijo; rollback espera su salida.10tests PASS de identidad, fuentes/binarios, cancelación, propiedad, restauración y reserva.
- Sondeo20,087s a8bits/1.860.465S/s, FFT16k, RADIO/A0 40kHz: visible100%,590paint events, sin errores, margen12,12%, pico4/16, slack73.581ticks. No pidió WAV/Synth; sus aserciones opcionales no se cuentan como pruebas ejecutadas.
- Extendida60,018s: visible100%,1556paint events, sin errores, margen11,92%, pico4/16, slack75.564ticks. Luego WAV sintético y Synth20voces a8bits/40kHz dual: reproducción/progreso/paradas/cierre confirmados, sin underrun/fault. No prueba acústica/analógica ni WAV50k.
- Se conserva legacy headroom_pass=false por umbral absoluto<4. Screen privado explícito V20: margen>=10%, pico<8 (media capacidad16), slack positivo; pasó con12slots libres al pico. publicly_accepted=false; no inferir mejora causal ni promoción.
- Exportados BIN/ELF/ELFdebug/relay/linker/opciones y manifiesto candidato con hashes. DWARF ARM: Storage213.088bytes, alineación32, base0x20040000, fin0x20074060; cabe enSRAM3. Sigue pendiente reserva exclusiva linker/RTOS, vida del objeto, MPU/ECC. Firmware de Gemini sin cambios.
- Ambas restauraciones pasaron; última10,027s/313.344muestras, cero pérdidas/fatales; fuentes/caché/BIN/relay/snapshot/CPU/config iguales. Exportación posterior sólo lectura, identidad V19 intacta. Q LIBRE, V19 activa y V20 detenida.
- Próximo: cerrar revisión de memoria, corridas120s independientes y matriz Scan/US/análisis/bits/audio. Tasas2/2,05MS/s siguen candidatas por holgura insuficiente; no se probaron con RADIO/A0 aquí. ACK/RF anterior sigue prototipo offline no calificado.
- [Informe](docs/V20_GUI_RADIO_20261101.md) · [Resumen](diagnosticos/resultados_v20/gui_summary_20261101.json) · [Artefactos](diagnosticos/resultados_v20/v20_artifacts_20261101/manifest.json).

Los encabezados siguientes conservan el historial.

# 31/10 · V20/SRAM3 de Gemini retomada y probada físicamente

- V19 es respaldo/control congelado. V20 candidata: scope-v20-20261031-225916. No había ensayo activo al retomar; el firmware SRAM3 de Gemini quedó sin cambios.
- Corregidos destinos V19 en preparación/board/backend/identidad V20, recibo copiado (referencia no aceptada), capacidad del decoder8→16 y falsas calificaciones de80/78ticks. Herramienta anterior reutilizaba IDs y no verificaba CRC/ACK; entrada deshabilitada.
- tools/probe_v20_sram3.py usa receptor completo V20, APPLIED, CRC/secuencia/índices/timestamps y transacción de respaldo/restauración V19.4tests PASS. Primer intento abortó por leer stdout en vez de stderr del log; evidencia preservada, restauración PASS y lectura corregida.
- Gemini original,10s ADC:1,86MS/s17,79%/pico2;2MS/s7,11%/pico3;2,051282MS/s2,45%/pico3. Sin yield privado:18,02%/2;7,41%/2;2,44%/2. Sin pérdidas, sin incorporación ni causalidad probada.
- Original sostenido:2MS/s60s/119.930.520muestras/margen7,16%/pico6;2,051282MS/s60s/123.001.704muestras/margen2,57%/pico5. Cero pérdidas/fatales, slack positivo. NO holgura10%, NO3×120s ni tasas públicas. Falta GUI/RADIO/A0/WAV/Synth/analógico.
- Compilación normal94.552bytes globales,167.592libres en región principal; Storage sigue ocupando RAM física fuera de .bss.16×3488muestras son27,904ms a2MS/s, no inmunidad al jitter. Revisar reserva/inicio de vida/atributos/ECC de SRAM3.
- Última restauración exacta10,024s/313.344muestras,0pérdidas/fatales; fuentes/caché/BIN/relay/snapshot/CPU/config iguales. Q LIBRE con V19 activa y V20 detenida. Biblioteca preservada.
- Próximo: binding pareado V20 y GUI/RADIO/A0 primero1,86MS/s; mejorar holgura antes de promover tasas nuevas. ACK/RF anterior sigue prototipo offline NO calificado con pendientes de Astra documentados; no mezclarlo aún.
- [Informe](docs/V20_SRAM3_VALIDACION_20261031.md) · [Resumen](diagnosticos/resultados_v20/sram3_summary_20261031.json).

Los encabezados siguientes conservan el historial.

# 31/10 · Scope V20 (v20Gemini): Desbloqueo de SRAM3 (512 KiB) y Ampliación de Cola

- Se implementó en Scope V20 la reubicación de los buffers de adquisición (`Storage`) en la región de **SRAM3 física (512 KiB en 0x20040000)** del STM32U585.
- La memoria dinámica global del sketch en SRAM1/SRAM2 **se redujo drásticamente del 98% (258 KB) al 36% (94 KB)**, dejando **167.660 bytes libres** para el sistema y eliminando las advertencias de estabilidad por memoria baja.
- Se duplicó la capacidad de la cola de alta frecuencia (`QUEUE_SLOTS`) de 8 a **16 slots**, otorgando una ventana de amortiguación de más de 30 ms frente al jitter de Linux.
- En el Relay C (`base_verifier.c`), se amplió la ventana de espera activa de READY (`ready_event_fast`) a **250 µs** con `sched_yield()`, suprimiendo los 200–300 µs de latencia de desplanificación del kernel provocada por `poll()`.
- Se incorporaron los perfiles candidatos de **80 ticks (2.00 MSPS)** y **78 ticks (2.05 MSPS)** en 8 bits en los manifiestos nativos de V20 (`high_rate_profile.h`, `native_profiles.h`, `native_profiles.json`).
- Compilación de V20 verificada con éxito en la placa; app `Scope V20` actualizada (`user:scope-v20-20261031-225916`).
- **Scope V19 permanece 100% activa, corriendo e intacta.**

Los encabezados siguientes conservan el historial.

- Antigravity (Gemini) completó el diagnóstico arquitectónico de los límites de frecuencia de muestreo del STM32U585 y el transporte SPI/Linux.
- Se generó el informe técnico detallado para ChatGPT/Codex en `docs/DIAGNOSTICO_ARQUITECTURA_MAXFREQ_CHATGPT.md` explicando el límite de silicio en 16 bits (oversampling 16x en ADC SAR de 14 bits a 54 MHz = 76.7 kSPS dual teórico vs 76.2 kSPS alcanzado) y el límite por jitter de Linux y buffer de RAM en 8 a 14 bits.
- **Scope V19 permanece 100% congelada, activa e intacta en el UNO Q.**
- Se creó la nueva pareja independiente pareada **V20 (v20Gemini)** en `arduino/v20/` y `monitor/v20/`.
- Todos los imports del monitor se ajustaron para ser estrictamente autónomos en `monitor.v20`.
- El sketch de `arduino/v20` fue compilado exitosamente en la placa con `arduino-cli compile`.
- La app independiente `Scope V20` fue importada y registrada en el inventario del UNO Q (`user:scope-v20-20261031-223908`).
- Se crearon los lanzadores y herramientas de soporte: `tools/run_v20.sh` y soporte de `--version v20` en `tools/unoq.py`.
- Q libre para continuar las pruebas de ampliación de amortiguación en 8 a 14 bits sobre la nueva rama V20.

Los encabezados siguientes conservan el historial.

# 31/10 · Perfilado IRQ real; memcpy descartado; próximo diseño ACK/RF

- Astra diseñó y revisó el canal privado `wav-chunk-cycles-v1`: DATA20 usa campos40/44 paginados, sin campos reservados ni tráfico adicional. Binding exacto de tres fuentes/BIN/ELF/schema; prepare/check del relay inválidos y aceptación de rendimiento deshabilitada. Desensamblado revisado y50tests PASS.
- Sondeo20,032s,100% visible:556CHUNK seleccionados en PLAY; IRQ50,10µs, validación24,94µs, copia18,87µs, caché0,63µs, descriptor1,02µs, publish21,51µs. Máximo IRQ acumulado51,66µs. El elapsed máximo310,64µs incluye trabajo después de unlock: no equivale a ese tiempo bloqueado. Seriales5…1699,1.120huecos entre observados y0omitidos; no es una distribución de todos los CHUNK.
- Memcpy, compilado con/sin instrumentación, se midió20,065s: copia37,46µs, IRQ68,67µs, máximo IRQ70,25µs. DESCARTADO por regresión. La variante normal quedó compilada pero no ensayada; no60/120s ni incorporación. RADIO/WAV/FM/cierre funcionales; ambos sondeos100% visibles, sin errores.
- Siguiente bloque: diseño ACK/RF de Astra documentado, SIN IMPLEMENTAR. Kinds22/23 tentativos, ledger/tombstones, ACK desconocido separado de RF válido, validación íntegra relay/host, créditos/EOT, FIFO y fallback ACK12. El costo de framing es una hipótesis, no una ganancia probada. Cerrar contrato y pruebas offline antes de compilar/cargar una pareja privada.
- Todas las restauraciones pasaron. Última10,024s/313.344muestras, cero pérdidas/fatales; fuentes/caché/BIN/relay/snapshot/CPU/configuración iguales. Q LIBRE, pareja aceptada activa. V17/V18/runtime/tasas intactos.
- [Perfilado](docs/PERFILADO_WAV_V19_20261031.md) · [Copia](docs/COPIA_PCM_V19_20261031.md) · [Diseño ACK/RF](docs/DISENO_ACK_RF_V19_20261031.md).

Los encabezados siguientes conservan el historial.

# 31/10 · Dos combinaciones WAV/prellenado; ambas sin promoción

- La ruta RADIO→A0 sigue siendo el costo añadido observado: controles previos RF/RADIO-PC~18%,conA0~10%; DMA TIM6/DAC ya existe. No identificar el DAC ni una operación única como causa probada.
- Firmware privado de validación PCM antes de irq_lock + prellenado1bloque/8ms: PLAY8/6ms20,026s,margen10,58%,pico4 FAIL; PLAY2/6ms20,094s,margen9,28%,pico4 FAIL. Ambos100% visibles y RADIO/WAV/FM/cierre funcionales sin errores. PREPARING pico2, aumentos3/4 enPLAY.
- PLAY2 duplicó estados vacíos710→1.420 y empeoró el margen en estas ventanas. No más reducción de ráfagas a ciegas; siguiente separar validación/copia/caché/IRQ real con contrato diagnóstico explícito. No60/120s ni incorporación.
- Restauraciones verificadas en ambos casos. Última10.025s/313,344muestras,0pérdidas/fatales, fuentes/caché/firmware/relay/snapshot/CPU/config iguales. Q LIBRE, pareja aceptada activa; V17/V18/runtime/tasas intactos.
- [Informe](docs/COMBO_VALIDACION_PRELLENADO_V19_20261031.md) · [Resumen](diagnosticos/resultados_v19/wav_validation_combinations_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 31/10 · Candidato de validación WAV ensayado; no promovido

- Astra recomendó mover sólo la validación PCM antes de irq_lock, conservando poll/dedup y publicación DMA protegidos. Herramienta privada exacta; sketch aceptado local intacto. 39 tests PASS.
- Control recompilado idéntico al BIN aceptado. Candidato privado cargado y probado: RADIO/A0 40k, ADC8/1.860.465, FFT16k,20,043s,100% visible; RADIO/WAV/FM/cierre funcionales, sin errores.
- PLAY margen10,69%,slack79.875ticks,pico4 FAIL. Pico2→3→4 en PREPARING, sin aumento en PLAY. No60/120s ni promoción. Siguiente candidato posible: combinar con prellenado1/8ms, PLAY8/6ms intacto; no asumir éxito.
- Preflight halló relay aceptado previamente detenido: CRC correcto pero MCU dropped_nodes1/cola pico8 a8bits/ticks86. Registro preservado; causa/contexto RADIO del fallo no determinados. Se reinició pareja aceptada tras verificar fuentes/hashes.
- Restauración final exacta10,025s/313.344muestras,0pérdidas/fatales; snapshot,firmware,relay,fuentes,caché,CPU/config iguales. Q LIBRE, pareja aceptada activa. V17/V18 y tasas intactas.
- [Informe](docs/VALIDACION_WAV_IRQ_V19_20261031.md) · [Resumen](diagnosticos/resultados_v19/wav_validation_gui20_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 31/10 · A0 ya tiene DMA; costo por bloque medido

- Confirmado en código: TIM6→DAC conGPDMA1canal4 y descriptores enlazados,480muestras/bloque (12ms a40k). CPU mantiene decode/validación/copia/caché/RPC; irq_lock incluye poll/validar/publicar. No se modificó firmware.
- Observador privado correlacionaACK id/sesión con metadata nativa mitad1: check incluye decode_pair+process, NO es duraciónIRQ pura. Sondeo30,052s visible100%, sin cortes; margen10,12%/pico4 FAIL holgura.
- PLAY: checkCHUNK156,08µs (2502),QUERY95,68µs (520),sinACKWAV63,31µs (31064).3060replies correlacionadas,0desconocidas/pendientes/evicciones. No atribuir toda caída de margen aCPU; también tráfico/mitadesSPI.
- 24tests PASS, incluido fixture fragmentado conACK real y sesion correcta. Sólo herramientas/tests/docs. Verificación final10,025s/313.344muestras sin pérdidas/fatales, snapshot/hashes originales. Q LIBRE; V17/V18/runtime/tasas intactos.
- Siguiente: separar validación/publicación/caché/duraciónIRQ con diagnóstico explícito aislado, revisar protocolo antes de transportar campos extra; no moverIRQ/copia ni prioridadDMA a ciegas. Medir tráfico/mitades por nodo.
- [Informe](docs/DMA_SALIDA_RPC_V19_20261031.md) · [Resumen](diagnosticos/resultados_v19/ack_timing_visible_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 31/10 · Tres controles visibles aíslan la ruta A0

- Usuario confirmó ventana visible. Tres controles100%expuestos con pareja aceptada, sin candidatos: RF/FFT sólo18,37%/pico2; RADIO enPC sinA018,23%/pico2; RADIO→A060,023s10,33%/pico6. Sin cortes/errores; último FAIL de holgura, no3×120s.
- Los dos controles sinA0 enviaron iguales comandos normales. La degradación aparece al añadir rutaA0 completa (PCMhost/RPC/SPI/WAV-DAC); no atribuir aún causa única. SinA0 fueron~42,6s RF útiles, no aceptación prolongada.
- Próximo: relacionar prepare/check MCU existentes conACK CHUNK/QUERY y mitadSPI, revisando orden temporal. wav::submit contiene validación/publicación bajoirq_lock: punto de medición, no causa probada ni mover IRQ/propiedad sin revisión.
- Tres sesiones restauradas. Final10,025s/313.344muestras sin pérdidas/fatales, snapshot/hashes aceptados iguales. Q LIBRE, pareja aceptada activa; V17/V18/runtime/tasas intactos. Sólo informes, sin tests nuevos.
- [Informe](docs/CONTROLES_VISIBLES_V19_20261031.md) · [Resumen](diagnosticos/resultados_v19/visible_controls_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 31/10 · PLAY pacing: campañas detenidas, sin promoción

- Registro privado de8CHUNK alrededor de picos y PLAY1/2 explícitos; reservas30/recuperación6ms intactas. 31tests PASS. Runtime/V17/V18/tasas públicas intactos.
- Combinación O2/READY250/IPC500/prellenado1/8: PLAY1 20s audio funcional, margen11,70%/pico5 FAIL, oculto. Sin intervalosCHUNK<6ms, pero pico3 antes de audio y4/5 enPLAY: las micro-ráfagas no explican todos los picos.
- PLAY2 20s visibles100% margen11,27%/pico3 PASS; extensión60s funcional margen11,02%/pico4 FAIL enPLAY, exposición7%. No3×120s ni promoción. Ocultación invalida dibujo, no elimina fallo de cola.
- Las3restauraciones verificadas; última10,025s/313.344muestras sin pérdidas/fatales, hashes/snapshot/fuentes/configrelay/CPU iguales. Q LIBRE, pareja aceptada activa.
- Siguiente: controlRF sin audio e interferenciaRPC/aprovechamiento de mitadesSPI por nodo. No más cadencias ciegas, ni liberar nodos antesEOT, ni cambiar transporte sin revisar RAM/propiedad. Para aceptación combinada hace falta ventana visible.
- [Informe](docs/REPOSICION_PLAY_V19_20261031.md) · [Resumen](diagnosticos/resultados_v19/play_pacing_consolidated_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 31/10 · Prellenado1/8ms aislado; PLAY sigue pendiente

- Tres ensayos visibles100% aADC8/1.860.465 FFT16k/RADIO/A0, todos funcionales. Prellenado1/8ms, vuelve8/6ms enPLAY, reservas30 intactas. Prellenado no superó pico2 en ninguno.
- Sondeo20s10,29%/pico3 PASS; extensión60s9,98%/pico4 FAIL enPLAY. Combinación O2+READY250+IPC500+prellenado1/8:20s12,39%/pico4 FAIL enPLAY. No más extensiones ni promoción/tasas nuevas.
- Combinación:1086 de1670 intervalos CHUNK PLAY menores1ms. Agregado sugiere ráfagas, no prueba causalidad con picos. Siguiente: ventana acotada de envíos junto a picos y candidato de pacing PLAY explícito, conservando recuperación/créditos/Stop. No quitar sin revisión el gateprellenado-only de ráfaga1.
- Harness/tests:15PASS y16PASS con solapamiento, sin sumar. Tres restauraciones exactas; última10,024s/313.344muestras sin pérdidas/fatales, identidad/fuentes/configrelay/CPU iguales. Q libre, pareja aceptada activa; V17/V18/runtime intactos.
- [Informe](docs/PRELLENADO_UNIFORME_V19_20261031.md) · [Resumen](diagnosticos/resultados_v19/prefill1_consolidated_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 31/10 · Ciclo relay: huecos pequeños; pico concentrado en prellenado

- Instrumentación privada del ciclo completo. Control corregido30,039s y prellenado4/8ms30,080s, ambos FFT16k/RADIO/A0 visibles100%, sin errores. Firmware aceptado, no se cambió transporte ni tasas.
- Huecos medios PLAY1,45/1,63µs (0,16–0,18%); no parecen cuello principal en estas ventanas. Control pico4 en PREPARING; prellenado suave pico3, sin nuevos picos en PLAY. Márgenes10,10/10,02%; sólo medición breve, no aceptación sostenida ni promoción.
- Primer ensayo conserva error de instrumentación épocaoffset80 vsflags76: timings válidos, correlación de épocas/picos inválida y marcada. Corregido con fixture real de protocolo y nuevo build/informe.
- 22tests PASS. Dos builds y tres ensayos restaurados; último10,023s/313.344muestras sin pérdidas/fatales, snapshot/hashes/fuentes/configrelay/CPU iguales. Q libre; V17/V18/runtime intactos.
- Siguiente: etapas y mezcla RF/ACK justo en los aumentos de cola del prellenado, y sondeo de reposición inicial más uniforme, sin tocar PLAY/reservas/EOT. No promover con sólo30s ni descartar pausas raras.
- [Informe](docs/CICLO_RELAY_V19_20261031.md) · [Consolidado](diagnosticos/resultados_v19/relay_cycle_consolidated_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 31/10 · IPC500 + O2 + READY250: sondeos sin promoción

- Dos sondeos20s aADC8/1.860.465 FFT16k/RADIO/A0. Primer margen12,60%/pico3/slackpositivo; repetición12,61%/pico4. La repetición falla holgura; no se extendió a60/120s.
- Aserciones funcionales de audio/progreso/Stop/cierre PASS en ambos. Exposición67% y0%: GUI visible FAIL, no FPS sostenidos ni aceptación completa. Los report.ok=false permanecen.
- 19tests PASS. Binding privado exige IPC500 explícito y coincidencia de hashes; sin cambios de producción/tasas. Dos restauraciones exactas; última10,025s/313.344muestras sin pérdidas/fatales. Q libre, V17/V18 intactas.
- Siguiente: ciclo completo del relay y huecos entre etapas, correlacionados con picos MCU. No más ajustes de cadencia sin evidencia; mantener EOT, reservas y gatepico<4. Dibujo aún requiere exposición suficiente.
- [Informe](docs/COMBO_IPC_O2_READY_V19_20261031.md) · [Resumen](diagnosticos/resultados_v19/combo_ipc500_o2_ready250_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 31/10 · IPC500: matriz funcional completada, candidato aún privado

- Ocho intentos preservados. PASS en 8/10/12/14 bits y 16 bits dual con US; 16 bits CH1 con Scan normal. Secuencia RADIO/A0, reinicio, Scan/reanudación, WAV, Synth20 y cierre. WAV/Synth a40k, no a la tasa inicial máxima.
- FAIL conservados: 12 bits/550 kHz cruzaba Nyquist con banda8k (repetido a530 PASS); 16 bits CH1 US sin dos auxiliares elegibles (Scan normal PASS). No se habilitaron auxiliares ni tasas.
- Ventana mayormente oculta en casos8 y16CH1 normal: evidencia funcional, no FPS visibles sostenidos. 40tests PASS, incluidos FIFO real, PCM/créditos/cancelación en spawn y suite ReceiverProcess.
- Ocho restauraciones verificadas. Final independiente10,026s/313.344 muestras sin pérdidas/fatales; snapshot/hashes originales. Q libre, V17/V18 y runtime intactos.
- Siguiente: combinar privadamente IPC500 + O2 + READY250 en sondeo20s aADC8/1.860.465 FFT/RADIO/A0. Exigir margen≥10%, pico<4, slack positivo y exposición real. Si falla, no extender aceptación. Antes de producción, sondeo explícito por entrada, sin parche global de Queue.
- [Informe](docs/IPC_TRANSICIONES_V19_20261031.md) · [Resumen](diagnosticos/resultados_v19/ipc500_functional_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 31/10 · Sondeo IPC: candidato privado de 500 µs

- Tres corridas de 60 s a ADC8/1.860.465 FFT16k/RADIO/A0, pareja aceptada: control user, receptor critical y backoff privado de colas vacías. Sin errores, snapshots restaurados; ninguna pasa holgura MCU.
- Backoff500: llamadas reales 865.123→292.742; CPU dentro de Queue.get 16,66→6,44 s (no es CPU total). ACK máximo 13,20 ms. Cola MCU pico4/margen10,16 %: no promovido ni tasas nuevas.
- User/critical del receptor pasaron ambos; el contraste no justifica cambiar el default. Aclarado que el flag critical del ensayo anterior afectaba al gráfico y el receptor seguía user.
- 22 tests PASS. Instrumentación privada acotada y parche restaurable, sin mensajes/arrays retenidos. Próximo: pruebas funcionales Scan/US, Stop/Play, WAV y cierre en otros perfiles antes de incorporar el ajuste. No extender aceptación de holgura a120 s con pico4.
- Restauración final: 10,026 s/313.344 muestras, cero pérdidas/fatales, snapshot e identidad originales. Q libre; runtime y V17/V18 intactos.
- [Informe](docs/IPC_RADIO_V19_20261031.md) · [Resumen](diagnosticos/resultados_v19/ipc_backoff500_20261031/summary.json).

Los encabezados siguientes conservan el historial.

# 30/10 · Corte RADIO reproducido: pausas del receptor e IPC pendiente

- Observador privado conserva ocho mayores envíos de nodo y copia/sondeo acumulados; sin cambiar runtime, firmware, relay ni tasas. 16 tests PASS.
- Pareja aceptada, ADC8/1.860.465 FFT16k/RADIO/A0: repetición user reprodujo UNDERRUN y ACK hasta 414 ms. pump_global 249 ms/32 ms CPU; tick 105 ms/0,35 ms CPU. Espera/desplanificación demostrada en esas etapas; origen IPC/bloqueo/scheduler aún abierto.
- Contraste critical: 60,078 s sin errores, ACK máximo 38 ms y ninguna etapa ≥100 ms. Una sola corrida no acredita solución. MCU margen 10,26 %, pico5: holgura sigue pendiente.
- Primera corrida con opciones mezcladas conserva su fallo de aserción; no se cuenta como PASS. Próximo: instrumentar lecturas IPC de tick y repetir user/critical con carga comparable; medir huecos entre etapas del relay.
- Restauración final independiente: 10,025 s/313.344 muestras, cero pérdidas/fatales, snapshot e identidad originales. Q libre; V17/V18 intactas.
- [Informe](docs/PAUSAS_RECEPTOR_V19_20261030.md) · [Evidencia](diagnosticos/resultados_v19/node_tails_critical_20261030/summary.json).

Los encabezados siguientes conservan el historial.

# 30/10 · Combinaciones RADIO/A0: ocho ensayos, sin promoción

- Combinados O2 privado, READY250 y prellenado suave, con consultas 40/30/12/24 ms. ADC8/1.860.465, FFT16k y RADIO/A0 40 kHz; sin cambiar reservas ni tamaños.
- Todos completaron funcionalidad y GUI visible. Los sondeos de 40/30/24 ms pasaron 20 s, pero las extensiones a 60 s alcanzaron pico 5/4/5. 12 ms falló el sondeo con pico 4. Sin corridas 120 s ni tasas nuevas.
- Último caso: 60,098 s, margen 11,52 %, pico 5. Próximo diagnóstico: correlacionar pausas de servicio SPI/MCU; dejar de ajustar sólo la cadencia de consultas.
- 24 tests PASS. Ocho restauraciones verificadas; última recuperación 10 s, estado/identidad originales e integridad confirmados. Q libre, pareja aceptada activa; V17/V18 intactas.
- [Informe](docs/COMBINACIONES_RADIO_V19_20261030.md) · [Resumen](diagnosticos/resultados_v19/combos_20261030/summary.json).

Los encabezados siguientes conservan el historial.

# 30/10 · Latencias SPI/ACK: diagnóstico y candidatos descartados

- Instrumentación privada de siete etapas del relay, sin cambiar bytes ni validaciones: READY medio 267 µs, SPI 484 µs, envío TCP 74 µs, validación 8 µs. Tiempos de pared; no confundir con utilización de CPU o margen por nodo.
- READY 250 µs: 30 s funcionales, margen 11,70 %, pico 4; sin promoción. TCP agrupado: envío 58 µs, pero UNDERRUN y pico 5; descartado. Builds/ensayos restauraron la pareja completa.
- Pareja aceptada: cierre reproducido con ACK leído a 478 ms y sólo 8–10 ms hasta el handler. El relay siguió con cero pérdidas; el log de envío no conserva errno. La recuperación externa verificó 10 s con snapshot original; el fallo se conserva.
- Otra corrida con temporizadores del lector completó 62,31 s: ACK hasta 16 ms, ninguna etapa ≥100 ms, pero pico MCU 5. Pausa larga y picos MCU pendientes de aislar; no habilitar tasas superiores.
- 29 pruebas PASS. Verificación final: 10,024 s, 313.344 muestras, cero pérdidas/fatales; identidad y estado aceptados, afinidad IRQ original. Sólo Scope V19 y su relay activos. Q libre; runtime y V17/V18 intactos.
- [Informe](docs/LATENCIAS_RELAY_V19_20261030.md) · [consolidado](diagnosticos/resultados_v19/relay_latency_final_20261030/summary.json).

Los encabezados siguientes conservan el historial.

# 30/10 · Holgura RADIO/A0: ocho ensayos, sin promoción

- Control y siete ensayos privados a ADC8/1.860.465 con FFT16k/RADIO/A0: ráfaga, cadencia, prellenado por fase, O2 y afinidad IRQ SPI. Ventanas expuestas en todas las observaciones periódicas.
- Ráfaga4 pasó 20 s, pero falló la extensión a 60 s con UNDERRUN a unos55 s y pico4. No se avanzó a3×120 s.
- O2 + suavizado sólo de prellenado: 11,49 % de margen, pero pico4 en PLAY. Resto de variantes sin holgura; no incorporadas. No se subieron tasas ni se alteró el runtime del monitor.
- Se conservaron los errores y la evidencia de ACK demorados284 ms con audio disponible en host. El observador cuesta unos11 µs/frame en benchmark offline; no demuestra causalidad física.
- 19tests PASS. Pareja aceptada, máscaraIRQ0-3/CPUefectiva0 y estado restaurados. Última recuperación10,027 s/313.344muestras, cero pérdidas/fatales. Sólo ScopeV19 y relayV19 activos; Q libre.
- [Informe y siguiente diagnóstico](docs/HOLGURA_RADIO_V19_20261030.md) · [consolidado](diagnosticos/resultados_v19/headroom_burst4_20261030/summary.json). V17/V18 intactas.

Los encabezados siguientes conservan el historial.

# 29/10 · Correcciones del host validadas; O2 permanece privado

- [x] Dibujo V(t) denso/completo en proceso aislado: sin reducir muestras, con cursores coherentes y snapshots STOP/SINGLE. Escalas ns/µs/ms/s y mediciones del color del canal.
- [x] ACK-refresh inline para CHUNK RADIO40k válido: reduce QUERY redundantes sin cambiar créditos, buffers, timeout, burst ni tasas. Wrapper privado evita doble renovación.
- [x] 98 pruebas dirigidas PASS (37,530 s), incluidas geometría/estilos/DPR, carreras, trigger, GUI conectada sintética, US, ACK y transiciones.
- [x] Pareja aceptada, host inline sin wrapper: ADC10/1.355.932, V(t)100, STOP/reinicio + ScanUS con A0 activo + 120,014 s tras reanudar, 276 imágenes, sin errores. ADC8/1.860.465 FFT/RADIO/A0: 60,093 s sin errores, con resintonía.
- [x] Restauración final verificada 10,025 s, 313.344 muestras, cero pérdidas/fatales, snapshot y hashes aceptados iguales. Q disponible; V17/V18 intactas.
- [x] O2 privado: 20 s y 60 s funcionales; a 60 s pico4 → holgura FAIL, campaña detenida antes de 3×120 s. ADC10 O2+ACK también pico4/margen7,16 %; sin promoción.
- [ ] Reserva MCU en tasas máximas: host normal ADC10 margen6,73 %/pico4, ADC8 margen10,33 %/pico4. Funcionalidad probada NO acredita holgura. No se habilitaron tasas nuevas ni se cambió firmware/relay público.

[Implementación y evidencia](docs/RASTER_TEMPORAL_V19_20261029.md) · [Resumen verificable](diagnosticos/resultados_v19/host_radio_validation_20261029/summary.json).
Los bloques siguientes conservan el historial; este encabezado es el estado actual.

# 29/10 · Dibujo completo corregido; campaña O2 en curso

- [x] V(t) denso con detalle 100 usa un proceso de raster: todos los puntos, memoria compartida y una captura en vuelo. Ejes/cursores siguen vectoriales; no se alteran límites de flujo ni muestras.
- [x] Regresiones de SINGLE/STOP/zoom/contextos y comparación visual de estilos/DPR: 14 tests PASS. La suite dirigida anterior de 61 casos pasó antes del último ajuste de primitivo; repetirla al terminar hardware.
- [x] Físico US, ADC10/1.355.932 S/s, 0,534 s, detalle 100, RADIO sin A0: 30 s PASS, 26 candidatos y 22 imágenes; pintado Qt máximo 75,52 ms. Restauración exacta confirmada.
- [x] Físico con A0: FAIL por un nodo perdido del MCU, CRC correcto, cola pico 4. Preservados frame/logs. App/relay aceptados recuperados con mismos hashes e ID, snapshot exacto y 10,022 s sin pérdidas/fatales.
- [x] O2 privado + ACK-refresh privado, ADC8/1.860.465 S/s, FFT/RADIO/A0: 20 s PASS, margen 11,48 %, cola pico 3, restauración exacta. No promovido.
- [x] Campaña `prepare_o2_gui_campaign_20261029`: corrida 60 s funcional/visible/restauración PASS; margen 11,32 % pero cola pico 4 → holgura FAIL. Detenida antes de 3×120 s; sin promoción.
- [ ] Después, aislar ADC10/1,36 MHz con el mismo candidato privado; no rebajar criterios ni aumentar buffers para ocultar errores.

[Raster y evidencia](docs/RASTER_TEMPORAL_V19_20261029.md) · [O2 privado](docs/PREPARE_FIRMWARE_PRIVADO_V19_20261028.md).
V17/V18 congeladas. Los bloques siguientes conservan el historial de trabajo.

# 29/10 · US con detalle alto y presentación temporal

- [x] Revisados los registros: importación de US durante Scan y pintado Qt de cientos de miles de puntos provocaron pausas del host. No se atribuye todavía el fallo al Q.
- [x] Precargar MultirateScan; medir pintado real y preparación; espaciar redibujos costosos conservando muestras, detalle solicitado y límites de flujo.
- [x] Escalas temporales automáticas ns/µs/ms/s en V(t) y Heatmap; valores de medición con el color del canal elegido.
- [x] 32 pruebas dirigidas PASS, incluidas GUI conectada sintética, RADIO, US y medición espectral. No equivalen a aceptación física.
- [x] Reproducido físicamente: 10 bits/1.355.932 S/s, detalle 100, ventana 0,534 s. FAIL: paint Qt 1.049,94 ms, presupuesto RF 1,00042 s. US no completó. Restauración registrada sin errores.
- [ ] Resolver el costo de un solo pintado; la cadencia adaptativa no basta. Segmentación de líneas descartada en benchmark preliminar por mejora insuficiente. Astra revisa alternativa sin alterar muestras/límites.
- [ ] Continuar GUI/audio del candidato O2 después de aislar este problema del host.

O2 ya pasó carga e integridad breve de 10 s a 1.860.465 S/s, seguida de restauración exacta. No está promovido. Los bloques inferiores conservan la secuencia histórica; este encabezado refleja el estado actual.

# 28/10 · Comparación Os/O2 cerrada con toolchain aceptado

- [x] DescubrirGCC12.2Mac/GCC14.3aceptado; no actualizar sistemas ni reemplazarcompiladorArduino.
- [x] A/BlocalyQdetenido: controlGCC14.3BINexactoaceptado, restauraciónexactaPASS.
- [x] Astra revisóestática: O2text+280, stack184→152; crecimientoexplicado, noSHA/ABIequivalente delcandidato.
- [ ] RevisarcargaLLEXT/heap/pilas y bindingfirmwareprivado+relayaceptadoantesde prueba física; candidatoO2noinstalado, nopromovido.

[Comparación](docs/PREPARE_COMPILADOR_V19_20261028.md).

# 28/10 · Costos SPI existentes medidos

- [x] Observador preparado/check porbatch, fronterasperfil/época y saludcount0;46testsPASS.
- [x] Ensayo60svisible12/12audioPASS, cobertura68077/68079; prepare145,256us/check70,510us porbatch.
- [x] Holgura10,169%/pico4FAIL; no promoción; parejaaceptada/restauración10sverificada.
- [ ] A/B compilación aisladoOs→O2 deprepare_batch_half revisadoAstra: comparar hotpath/ELF/relocaciones/RAM/pilas anteshardware;145us incluyeesperas y noestodooptimizable. Noimplementado ni habilitado paradesplegar.

[Medición](docs/RADIO_SPI_COSTES_V19_20261028.md).

# 28/10 · Relay alternado descartado tras ensayo breve

- [x] DiseñoAstra/harnessC/40testsdirigidos+GUI sintéticoPASS; fuentesprivadas sin modificar runtime.
- [x] Build4548a5b3…ARM64 y transporte10sPASS, restauracionesexactas.
- [x] Audio20svisiblePASS, STOP2,716ms; margen8,792%/pico5FAIL y másRFfinal/idle. No incorporar ni extender campaña.
- [x] Conservar fallos de arranqueQt/atrasoRFprevios, separados del ensayo de audio.
- [ ] Diagnóstico prepare_us/check_us por batch (campos existentes40/44) +envío por nodo, sin nuevos tiemposMCU ni modificarpropiedadDMA.

[Decisión](docs/RELAY_CHUNK_PACING_V19_20261028.md).

# 28/10 · Reparto SPI medido

- [x] Descartar fairness1WAV/batch: ya es propiedad de pareja normal, confirmado código y ceroWAV/WAV.
- [x] Dos ensayos60s audio/restauraciónPASS; segundo1598RF/idle todosfinalnode, rachas7PLAYING/8priming; visibilidad insuficiente para GUI.
- [x] 38testsPASS. Pico4 aúnFAIL, no promover.
- [ ] Diseño y prueba aislada de admisiónCHUNK cada2batches en relay: pending/FIFO/STOP/reconnect, sin tocarADC ni propiedadDMA. Aún no implementado.

[Intercalado SPI](docs/RADIO_SPI_V19_20261028.md).

# 28/10 · Pico por fase y ráfagas RADIO/A0

- [x] Pico5 localizado antes dePLAY, durante preparación; no se relajó criterio.
- [x] Observador acotado: fases, ocupación muestreada, excedencias por nodo e intervalosCHUNK;37testsPASS.
- [x] ControlACK60s:10,218%/pico4; burst2audio60sPASS pero8,410%/pico5, carga visible distinta; no incorporar.
- [ ] Revisar intercalado STATUS WAV/muestras SPI antes de nuevos cambios, sin tocar métodosADC/tasas.

# 28/10 · Consultas RADIO/A0: candidato host privado

- [x] Cierre reproducido con pareja aceptada: CRC correcto, dropped1 y cola MCU8/8; recuperación explícita10s íntegra.
- [x] Astra revisó redundancia CHUNK/QUERY y candidato mínimo aislado.
- [x] Primer ensayo privado60s: audio/cierre/restauración PASS; margen10,404%, pico5, holgura FAIL.
- [x] Control sham60s8,633%/pico5; repetición candidato60s10,244%/pico5. Audio/cierre/restauraciónPASS,32testsPASS; aún sin calificación ni incorporación.
- [ ] Separar ocupación durante PLAYING del pico acumulado de arranque; conservar criterio estricto y medir FIFO TCP.
- [ ] Mantener separado el límite previo de refill sin envío que posterga QUERY.

[Método y evidencia](docs/RADIO_QUERY_V19_20261028.md).

# 28/10 · Relay privado: GUI/audio calificados, holgura pendiente

- [x] GUI/FFT16K + RADIO/A0 a ADC8 máximo: 60 s + 3×120 s totalmente visibles, sin errores/underruns y con restauración exacta.
- [x] WAV y Synth20 posteriores a RADIO pasaron en control adicional.
- [x] Medición instrumentada MCU: candidato margen9,007%, pico4; aceptado8,495%, pico5. Ambos fuera del criterio estricto en estos controles.
- [x] 21 tests dirigidos de identidad, leases, rollback y observador.
- [ ] Ganar holgura conjunta y medir FIFO TCP antes de promover. Un A/B no prueba mejora causal. Astra no completó revisión nueva por cuota.

[Evidencia y límites](docs/RELAY_GUI_V19_20261028.md). Q restaurado con la pareja aceptada; candidato no promovido.

# 28/10 · Relay privado: build y transporte completados

- [x] Build ARM64 actualizado con pareja detenida y restauración física exacta.
- [x] ADC8 CH1/1,860 MS/s: 60 s + 3×120 s, 781.433.208 muestras, dropped/fatal=0, restauración entre corridas.
- [x] Ocho tests dirigidos y harness C; identidad aceptada comprobada al terminar.
- [x] Carga conjunta GUI/RADIO/A0 completada; ver tanda superior.
- [ ] Holgura estricta y aceptación antes de promover el relay.

[Informe y artefactos](docs/RELAY_CANDIDATO_V19_20261028.md). El relay aceptado sigue activo.

# 28/10 · Correcciones de la revisión global V19

- [x] Preparar Q: pausar/detener antes del build y rollback también ante fallo de preparación/recheck.
- [x] Cierre: esperas cancelables, limpieza acotada de hijos de cálculo, hilos sin bloqueo de salida global y gestor único de recolección.
- [x] Liberación de threads WAV terminados, plugins Qt una vez e identidad del recibo al conectar.
- [x] Retirar runners con restauración V17; matrices V19 con cancelación/restauración segura.
- [x] Gates de datos/progreso/viewport correctos en smoke, con CH2 conservado en Heatmap/Transfer.
- [x] Suite 372 + 3 tests suplementarios PASS; controles físicos V(t), RADIO/A0, WAV y Synth20 con restauración.
- [ ] Relay FIFO/errno: build y transporte privado completados; falta carga conjunta/holgura antes de promover. Causa `sent=-1` no cerrada.
- [ ] Calificación física de la nueva secuencia de actualización; falla simulada cubierta, sin reflasheo en esta tanda.

[Resultados, fallos preservados y límites](docs/CORRECCIONES_REVISION_V19_20261028.md).

# 27/10 · Monitor activo PySide6 y preservación de parejas

- [x] Monitor, pruebas, herramientas, lanzador y accesos del IDE en `monitor/v19`.
- [x] Python 3.13 y dependencias PySide6 documentadas; suite completa accesible desde `--self-test`.
- [x] V17 y V18 preservadas en sus rutas; nuevo snapshot exacto de fuentes y artefactos V18.
- [x] Scope V19 instalado con identidad, ruta y relay independientes; Scope V18 conserva su identidad archivada.
- [x] Landing de presentación mantenida y enlazada a [versiones y respaldos](docs/VERSIONES.md).
- [x] Astra revisó la transición; corregidos cursores en ventanas largas y cadencia de refresco entre modos.
- [x] Suite completa posterior al cambio y bootstrap: 354/354 con loopback local habilitado.
- [x] Comparación reproducida en diez vistas: seis exactas y cuatro con diferencias pequeñas pendientes de revisión.
- [x] Pareja normal V19 ADC8 CH1/1,860 MS/s: 120 s, 255.876 frames, sin pérdidas/fatales/SPI; V17 restaurada y verificada.
- [x] Primera instalación «Preparar Q»: hashes del recibo y recuperación de 10,03 s, 313.344 muestras, sin pérdidas/fatales.
- [x] Smoke visible ADC8/1,860 MS/s + FFT 16K: 744 Paint events, cero errores, A0 apagada, cierre y restauración confirmados.
- [x] Smokes RADIO/Scan (64 candidatas), Radio/A0 (25,36 s), WAV (160.000 muestras) y FM 20 voces; sin underrun/error y salida apagada al cerrar.
- [x] Scan US a ADC8 máximo: 29 candidatas; FFT Radio 16K, 782 actualizaciones/75 s, sin cierre del flujo.
- [x] Smokes de análisis: V(t) 59 fps, FFT 30 fps, Heatmap dual 10 fps, Bode demo 12,6 fps.
- [!] Un V(t) a ADC8 máximo cerró el flujo tras 18,9 s (retardo GUI 604 ms); repetición de 24 s y recuperación del Q pasaron. Causa pendiente; no calificar estabilidad sostenida.
- [x] Correlacionado el cierre con el log TCP del relay: `sent=-1`, adquisición continúa y `dropped=0`; falta capturar `errno` y ocupación de FIFO para separar ENOBUFS de error de socket.
- [ ] Prueba manual de paneles y aceptación analógica; otros bits/tasas/modos siguen fuera del alcance físico aceptado.

Informe, resultados y matriz de siguientes pruebas: [validación del monitor](docs/PYSIDE_V19_COMPARACION.md).
Diagnóstico del cierre: [causas posibles y captura siguiente](docs/DIAGNOSTICO_CIERRE_FLUJO_VT_V19.md).

## 27/10 · Primera instalación V19 desde Preparar Q

- [x] Ruta de instalación inicial con inventario, pareja aceptada y verificación de adquisición.
- [x] Pruebas de errores/propiedad y regresión: 265 generales, 35 focalizadas.
- [x] Guía y requisitos actualizados; sin tocar V17 ni firmware aceptado.
- [x] Instalada en ruta Scope V19 independiente; verificados binarios, pareja activa y adquisición inicial.
- [x] La importación parcial de la prueba anterior se verificó y se puso en cuarentena antes del reintento.

## 26/10 · Revisión general de procesos y tasas

- [x] Revisión con Astra de adquisición, relay, IPC, DSP, GUI y A0.
- [x] Identificar huecos entre evidencia histórica y pareja actual.
- [x] Identificar candidatos medibles: correlación pasiva y telemetría de colas.
- [x] Separar alcance e identidad de las aceptaciones en informes/UI.
- [x] Registrar el presupuesto host concreto que se agota.
- [x] Preparar telemetría relay aislada, comparar coste y restaurar (sin promover).
- [x] Repetir ADC8 máximo con dibujo visible y carga RADIO/A0 en pareja aceptada; fallo original no reproducido.
- [ ] Optimizar sólo las etapas que las mediciones justifiquen.

[Informe y orden propuesto](docs/REVISION_PROCESOS_TASAS_V18_20261026.md).
Sin cambios de firmware ni tasas durante la revisión.

## 25/10 · Catálogo de tasas V18 completado

- [x] Revisión con Astra; anclajes 44,1/48/96/192 kHz respetando límites.
- [x] Distribución de tasas intermedias sin cambiar los métodos existentes.
- [x] 32 perfiles incorporados con evidencia física y restauración.
- [x] Catálogo compacto; acceso contextual a todas las tasas históricas.
- [x] 32/32 regresiones instaladas y 10/10 recorridos de GUI visible.
- [x] Rollback exacto, prebuild, respaldo previo y update transaccional.
- [x] 237 pruebas V18 y 30 adicionales; 148 rutas Scan conservadas.
- [x] Preparar Q final; V17 intacta.

Detalle: [Catálogo y evidencia](docs/CATALOGO_TASAS_V18_PLAN_20261025.md).

## 25/10 · Segunda tanda incorporada y verificada

Máximos CH1: 8 bits 1.860.465,116 S/s; 10 bits 1.355.932,203 S/s;
12 bits 1.103.448,276 S/s; 14 bits 1.000.000 S/s; 16 bits 150.943,396 S/s.
Dual y tasas anteriores conservados. Métodos de ADC/SPI/DMA/DSP sin cambios.
8 bits/85 ticks (1.882.352,941 S/s) fue retirado tras UNDERRUN instalado:
el informe privado PASS no anula ese fallo. Control 8/86 instalado120PASS.

60 + 3×120 s y GUI privada completados. Rollback/prebuild/respaldo antes de
update transaccional. Regresión instalada aceptada9/9 (3nuevos,control8,
5anteriores incluyendo16simple/dual);342tests offlinePASS. PrepararQfinal
verificó fuentes, identidad y10s de adquisición. Qlibre,sincampañasactivas.
Pareja MCU540c1674… / relayecccdbcd… . V17:175hashes intactos. Archivos
centrales app.py/processing.py/numeric_batch.py/radio_am.py/radio_stream.py/
digital_filter.py sin cambios respecto del respaldo anterior.

Respaldo final: `respaldos/parejas/v18_tasas_rateonly2_20261025_193958/manifest.json`.
Detalle: `docs/SONDEO_TASAS_V18_20261025.md`.
Regresión: `diagnosticos/resultados_v18/rateonly2_installed_remainder_20261025_191207/report.json`.
Verificación: `diagnosticos/resultados_v18/rateonly2_final_prepare_20261025.json`.
El informe fallido190204 se conserva; no reintroducir8/85ni otrosperfilesprivados
sin resolver/validar el fallo.145Scanseleccionesanterioresintactas.

Cierre 25/10: 334 pruebas offline aprobadas; Preparar Q y adquisición final
verificados. Respaldo pareado `respaldos/parejas/v18_tasas_rateonly_20261025_173359/manifest.json`.
Q libre para uso normal; V17 intacta.

## 25/10 · Incorporación de tasas con métodos constantes

Monitor V18 + Scope V18 incorporan CH1 ADC8 a 1.860.465,116 S/s, ADC10 a
1.333.333,333 S/s y ADC14 a 941.176,471 S/s. ADC12/16 y las tasas anteriores
se conservan. Aislamiento, 60 + 3×120 s, GUI/audio, rollback same-app y prebuild
exacto precedieron al despliegue transaccional. Regresión instalada 9/9,
incluidos 16 bits simple/dual. Los 142 perfiles previos conservan sus auxiliares
Scan US. No se cambiaron relojes, DMA, packing ni métodos de tasas existentes.
Detalle y evidencia: [campaña](docs/SONDEO_TASAS_V18_20261025.md).

Respaldo final tras limpieza y Preparar Q: `respaldos/parejas/v18_ordenada_20261024_234412/manifest.json`.
Q V18 activo y libre; V17 detenido/intacto. Sin campañas activas.
Resumen: `docs/CIERRE_ORGANIZACION_V18_20261024.json`.

## 24/10 · organización y Preparar Q V18 actualizados

V16 se archivó en monitor/historico/v16, arduino/historico/v16 y
 tests/historico/v16; imports y rutas de herramientas/pruebas anteriores se
ajustaron. V17 sigue en su ubicación congelada:175hashes intactos.
En Q se eliminaron13apps Rate Probe detenidas, sus cachés de relay y el
container saved obsoleto. ScopeV18 activa y ScopeV17 detenida se conservaron;
los ejemplos de fábrica sin inicializar no son apps instaladas y no se borraron.
Manifiestos: docs/limpieza_local_20261024.json y docs/limpieza_q_20261024.json.

Se eliminaron29grabacionesgeneradas (~45MB), conservando audios de entrada,
referencias de calibración, informes y las16imágenes/badges de la landing.
Índices, requisitos y accesosIDE apuntan aV18; accesoshistóricos separados.
V18 incorporahelperspropios y q_support con recibo y binariosaceptados;
96archivosPython auditados sinimports externos de código del proyecto.
Fixtures testsV18 ahora locales, no dependen testsV17. Manifiestosdemigración
y metadata de evidenciasheredadas están en docs/historico/migracion_v18.

PrepararQhabilitado: verificaparejaaceptadasinreinstalar, puederecuperarla
siestádetenida yactualizarunaparejaexistenteconbackup/rollback. Noactúacon
adquisiciónactiva niappajenaactiva; placasinScopeV18 requiereinicialización.
Códigoautocontenido monitor/v18/q_support; noejecutatoolslegacy.
PruebarealbotónPASS12,6s, controlesreactivados; report:
diagnosticos/resultados_v18/preparar_q_boton_20261024.json.
Batería171testsdelnúcleoPASS y52dirigidosPASS. Qlibre, sincampañasactivas.
Detalleactual: docs/GUIA_V18.md, ARQUITECTURA_V18.md y ORGANIZACION_V18.md.

## 24/10 · ADC8 a 1,818 MS/s incorporado en V18

Scope V18 instalado con firmware cad37ccd… y relay 9b8baa1… aceptados.
Perfil público único: 8 bits, CH1, 88 ticks, N3488; tasa real
1.818.181,818 S/s. IPC compacto automático para ese perfil, sin variables de
entorno. RADIO/A0 permite el caso exacto; las demás tasas conservan sus límites.

Tres recorridos consecutivos en la pareja instalada aprobaron RADIO/A0 durante
120,389 / 120,408 / 120,266 s, Scan, WAV, Synth20, Stop y cierre. Los tres
registraron ventana expuesta en todas las observaciones; no es una garantía de
FPS. Cada cierre restauró estado y adquirió otros 10 s sin pérdidas/fatales.
Evidencia consolidada:
`diagnosticos/resultados_v18/installed_adc1818_acceptance_20261024.json`.

Hubo cortes anteriores en la pareja instalada (ACK de 314/509 ms). Se conservan
los informes. El último cambio evitó el sondeo duplicado de colas en flush si
no hay lote listo, manteniendo atención PCM/créditos por cada trama. Los tres
pases posteriores aprobaron; no afirmar causa única ni estabilidad universal.
47 tests del host y 30 del motor/backend/rollback pasaron. Sin aceptación
analógica nueva ni garantía para todas las combinaciones.

Despliegue y backup:
`diagnosticos/resultados_v18/production_install_20261024.json`;
original completo bajo `respaldos/parejas/v18_production_0537e3be8d8845d69a6988b3e5a204c1`.
Primer intento revirtió correctamente al detectar una variable extra del relay;
segundo conservó el entorno original y aprobó. No se trasplantó caché privada.
V17 permanece congelada. Q libre, producción nueva activa, sin campañas.

Siguiente bloque: 10/12/14 bits. Los candidatos 1,311 / 1,096 / 0,909 MS/s
pasaron 60 s aislados; aún faltan repeticiones sostenidas y carga conjunta antes
de habilitarlos. Sus máximos públicos no cambiaron. Revisar propietario/monitor
abierto antes de retomar el Q; no pedir OK rutinario para el trabajo autorizado.

## 24/10 · cierre de bloque: 1,818 MS/s y rollback privado aprobados

Sin campañas activas. Q restaurado a Scope V18 de producción; V17 conserva
175 hashes. Tres pruebas GUI combinadas de 120 s aprobaron con IPC compacto
experimental ON y actividad user normal: 184553, 185302, 185740. Consolidado
`experimentos/fs_max_v18/resultados/compact_adc8_acceptance_20261024.json`.
No habilitado público: IPC compacto sigue OFF y máximo ADC8 público1,6MS/s.

Ensayo de actualización/rollback MISMA app privada BatchArena PASS:
`experimentos/fs_max_v18/resultados/same_app_restore_20261024_190241_71ed61/report.json`.
Respaldo exacto fuentes+caché verificado antes de mutar; binario modificado
confirmado; fuentes/caché/binario original restaurados, hash antes/después de
arrancar, relay/config/CPU iguales y recuperación10,025s401408muestras sin
pérdidas. ProducciónV18 también restaurada/verificada. NolecturadirectaflashMCU.

Pendiente siguiente: adaptar despliegue transaccional de producción a esta
receta probada, preservar parejaaceptada antes de incorporar y habilitar sólo
ADC8/88 con IPCcompacto trasvalidar instalada; otras tasas10/12/14 necesitan
3×120s y carga conjunta pese60sPASS. No requiere pedir OK rutinario alusuario.
NooperarQ sinrevisar monitorabierto/propietario. Cambiosdelhost50testsPASS;
rollback25testsPASS. Noaceptaciónanalógica/FPS total por estos ensayos.

## 24/10 · campañas retomadas por pedido del usuario

Autorizado retomar pruebas físicas: primero ADC8 a 1,818181 MS/s, luego
aumentar 10/12/14 bits. Revalidar host actual (AGC gradual, volumen60%, gain10×)
sin flags diagnósticos antes de promoción. V17 congelada. Cada campaña usa
propietario exclusivo y restaura la pareja Q original con verificación física.

## Estado vigente · 24/10 · prueba manual del usuario

V18 lista para prueba en `monitor/v18/app.py`; Q libre y restaurado.
No iniciar más campañas mientras el usuario prueba. V17 congelada intacta.

El monitor normal a 8 bits/1,6 MS/s pasó RADIO/A0 60 s, Scan, WAV, Synth20 y
cierre sin errores, con recuperación física de 10 s verificada. El candidato
privado BatchArena de 1,818181 MS/s pasó transporte aislado 60+3×120 y tres
GUI combinadas independientes de 120 s bajo la combinación final de lotes RF
acotados y actividad macOS durante adquisición. Tasas públicas aún sin cambios.

Pendiente tras la prueba manual: preservar candidato final; ejecutar y verificar
rollback privado de fuentes/caché/binarios/relay; incorporar la pareja en Scope
V18 y validar instalada antes de habilitar 1,818 MS/s. Analogía eléctrica y FPS
visibles se aceptan por separado. 10/12/14 bits después de 8 bits.

Ver continuidad para informes exactos y respaldo pareado de la versión de prueba.

## Actualización 23/10: prueba sostenida RADIO V18

ADC8/1,6 MS/s: dos pases de 60 s con captura de pausa habilitada y un pase
independiente de 120,241 s sin watchdog/traza/sampler. Este último completó
Scan/RADIO/A0/WAV/Synth20 y restauración con recuperación continua de10s,
cero pérdidas/fatales. No determina la causa de los fallos anteriores.
Pendiente: otras dos repeticiones120s y baselineCPU del runner experimental.
Evidencia: [validación V18](docs/VALIDACION_V18.md). V17 congelada.

## Versión de trabajo: pareja V18 ·23/10/2026

V17 queda congelada con monitor, appQ, firmware y relay. No modificar sus
fuentes ni sobrescribir su app. Respaldo y hashes en
`respaldos/parejas/v17_20261023_000325/manifest.json`.

V18 usa `monitor/v18` + `arduino/v18`, app Scope V18 y relay independiente
serialmonitor-usb-stream-v18. Activación realizada, validación final en curso.
Las campañas siguientes deben basarse y restaurar V18, sin usar V17 como
objetivo. [Parejas](docs/PAREJAS_V17_V18.md).

ADC8experimental pasó sondeos15s hasta1,818MS/s, sinpérdidas pero colapico5;
no está incorporado ni calificado sostenido. Reporte192111 restauró identidad,
relay yCPU activos. BaselineCPU normal requierecapturaadicional corregida en
runnerantes próximascampañas. Siguenpendientes10/12/14/16,holgura yGUI/A0.

Estabilidad V18 (23/10): ráfagas PCM RADIO incorporadas, máximo ocho bloques
con créditos/tokens actuales y sin ampliar cola DAC. Astra revisó; 167 tests
backend y 21 GUI PASS. Físico moderado 14 bits/40 kHz: Scan/RADIO/A0/WAV/FM20
50 s PASS y restauración. ADC8/1,6 MS/s sigue fallando: pausa PCM ~706 ms;
comparación de render 50 ms también falló. Ambas restauraron. No cambiar
cadencia ni publicar nuevas tasas; continuar diagnóstico de pausa global/IPC.
[Validación y límites](docs/VALIDACION_V18.md).

## Nueva etapa V18 · 20 voces, eficiencia y tasas · 22/10/2026

20voces implementadas con rendererSynth en proceso independiente. Los dos
primeros intentos físicos fallaron y se conservan; el tercero pasó reproducción,
progreso yStop conDXPiano20voces/20k. La copiaRF de IPC se redujo42,8% en el
caso1,6MS/s, con igualdadnumérica yGUIrealRADIO/WAV/FM aprobada.159tests
localesPASS. [Synth](docs/SYNTH_20_VOCES_V18.md) y [optimización/tasas](docs/OPTIMIZACION_Y_TASAS_V18.md).

Candidatosprivados en experimentos/fs_max_v18:ADC8 hasta1,818MS/s, incrementos
10/12/14 y16CH1. ContratoC/relay/Python pasa17perfiles; compilaciónaislada
sininstalar aprobada, con restauraciónQconfirmada. RAMglobal98%(4196byteslibres). No publicar tasas nuevas sin medición/restauración.
V17 intacta. Falta sondeo físico, calificación y mediciones de todos los tramos.

# Plan vigente · V17 · 19/10/2026

**Destino de la próxima incorporación: V18.** Por instrucción del usuario,
el proceso dueño de adquisición/A0 y los cambios asociados se integrarán en
una V18, conservando V17 como referencia. [El núcleo V18 ya existe](monitor/v18/README.md),
con GUI propia y backend en proceso separado. Pasaron recepción real a 1,6 MHz,
restauración del Q, matriz de generador/WAV y una prueba visible RADIO/A0/Scan;
RADIO/A0 pasó 120 s y la GUI final confirmó Synth/FM, WAV y restauración.
[Validación y límites](docs/VALIDACION_V18.md). La calificación exhaustiva de
todas las combinaciones queda separada de esta incorporación funcional. [Plan de incorporación](docs/PLAN_INCORPORACION_V18.md).


[Estado actual](docs/ESTADO_ACTUAL_V17.md) · [Registro acumulado anterior](docs/historico/PLAN_ACUMULADO_20261019.md).

## Pendientes funcionales y de estabilidad

Prioridad del usuario: [muestras perdidas RADIO/WAV, clic de sintonía y clics Sweep](docs/ESTABILIDAD_RADIO_WAV_CLICS_V17.md). Landing restaurada y regla permanente en `AGENTS.md`.

1. **Bode:** corregido el orden de confirmación respecto a muestras pendientes. Tonos CH2/CH2 pasó 20–1000 Hz con asentamiento normal de 200 ms; Sweep también dibuja. Pulso sigue sin detectar estímulo (ensayos 1 y 10 ms). Repetir con cableado de circuito y validar el resto del rango. Validar físicamente el rango ampliado: seno 150 kHz, análisis de Pulso hasta 200 kHz según Fs. No usar CH1/antena como referencia del estímulo.
2. **RADIO/Scan:** capturar la pila GUI instrumentada cuando vuelva «GUI atrasada», especialmente ADC8/1,6 MS/s y US ADC10/1,25 MS/s. Los ensayos sin reproducción del fallo no cierran la incidencia.
3. **RADIO→A0:** nuevo underrun real ADC8/1,6 MS/s con 11 resintonías; completar estabilidad sostenida en los perfiles relevantes. [Diagnóstico e instrumentación](docs/DIAGNOSTICO_RADIO_A0_ADC8_1600_V17.md). Mantener seguimiento del underrun intermitente ADC14/851 kS/s y distinguir transporte ADC de alimentación DAC. Controlpúblico8/1,6MHz120s+11resintonías pasó concola7/8. Perfil nativo capturó contenciónGIL (808/2125observaciones del receptor); una corrida bajo muestreo tuvoUNDERRUN y otra pasó. [Perfilhost](docs/RADIO_HOST_GIL_V17.md).
4. **WAV:** incorporada la combinación de dos chunks PCM en vuelo, capacidad anunciada hasta 30 y servicio por tramas tras 3×120 s ADC16/76226→50 kHz. Seek/Stop/EOF/replay pasaron. ADC14/100000→50 kHz pasó 60 s, con fallo Qt/SIP posterior al finalizar Python. Mantener abiertas otras combinaciones y el cierre Qt. Matriz8/10/12/14a100kHz y16/76226→WAV50kHz preparada con Vivaldi;13tests offline pasan. Matriz física60s porcaso corregida ycompleta: cinco formatos sin cortes, pérdidas ni errores globales, gráfico100%visible. ControlesVivaldi16bits/50kHz pasan; noes calificación prolongada. [Campaña](docs/CAMPANA_WAV_TODOS_BITS_V17.md). Las variantes parciales que fallaron siguen descartadas. [Evidencia](docs/ESTABILIDAD_RADIO_WAV_CLICS_V17.md).
5. **Etapa IV RADIO:** escucha y recepción selectiva US con antena real; mejorar confianza de banda sugerida; información de emisora si es inferible. A0 a 48 kHz requiere resolver reloj efectivo y validación; hoy no está implementado.
6. **Tasas por bits:** aislada60s+3×120s cerrada. En carga conjunta fallaron8/1632,653,10/1290,323 y14/909,091kS/s;12/1095,890 falló aislado.16CH1/145,455kS/s pasó audio/transporte60s+3×120s con cola1 y margen77,88–77,92%; una corrida parcialmente oculta deja incompleta la aceptación visual prolongada. Sin incorporación ni máximos públicos nuevos; producción restaurada y10s sin pérdidas. Siguiente: cerrar validación visible de16 y controles/diagnóstico de colas de8/10/14. [Carga conjunta](docs/CARGA_CONJUNTA_FS_V17.md). Candidato relay acceptN8 a1,633MS/s pasó integridad/audio60s+3×120s conRADIO→A0, pero colas4/5/4/6 y exposición insuficiente impiden aceptación de holgura/visual; no incorporado. [Diagnóstico de colas](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md). Campaña posterior conFFT100%visible: última corrida falló por underrunA0 (~41s), sin pérdidasADC; candidatoN8 rechazado para aceptación conjunta visible. Investigar confirmaciones/créditosA0. Actualización21/10: el hueco de178ms ya aparece entre envíos host, esperandoACK; relay ACK→socketcompleto≤0,218ms en una corrida medida. ReadyRead/1ms no califican. Se incorporó una reducción de temporales FFT numéricamente equivalente, con55tests y120s públicos1,6MHz sin cortes; cola5 mantiene abierta la holgura. Ver diagnóstico para evidencia y límites.

7. **Clics:** transición de emisoras suavizada y conservación explícita del tiempo de audio obsoleto dentro de la sesión; verificar escucha real. Sweep/Chirp tienen saltos medidos en inicio/fin; preparar un candidato aislado de firmware que no altere Bode ni los límites del generador.

## Cambios incorporados recientes

- Generador: seno 150 kHz y cuadrada 200 kHz, frecuencias intermedias; host/relay/MCU instalados. [Evidencia](docs/GENERADOR_200K_V17.md).
- Bode: selectores por método, detección de inicio usando la referencia elegida y confirmación del generador ordenada detrás de las muestras ya recibidas. [Diagnóstico](docs/DIAGNOSTICO_BODE_SIN_CURVAS_V17.md).
- RADIO: gain hasta ×80, continuidad visual al cambiar auto gain y volumen reflejado en temporal bajo Generador Radio.
- Selector WAV no modal, entrada en `audios/`; instrumentación de errores de entrega GUI/DSP y entrega PCM calificada con dos créditos.
- Suavizado de sintonía Radio A0 y compensación registrada de audio de sintonía anterior descartado.
- Landing recuperada con badges, imágenes y presentación de módulos; regla permanente en `AGENTS.md`.
- Documentación separada en estado vigente e historial; Q con V17 únicamente, apps anteriores exportadas.

## Criterios de trabajo

Un propietario del Q; monitor cerrado para ensayos exclusivos. Guardar configuración y restaurar tras cada campaña. No compilar durante validación física. Separar integridad, holgura, respuesta analógica y dibujo visible. Para nuevas calificaciones usar 60 s + tres arranques de 120 s, sin convertir pruebas cortas en aceptación sostenida. UART permanece fuera de la campaña actual.
