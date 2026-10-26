## 26/10 · Calidad HD y presentación totalmente simulada

Por pedido del usuario TODAS las imágenes principales de landing son ahora
simulaciones V18, incluida Radio710. No esperar cambio de cables para Bode
de presentación. PNG3200x2200 y GIF1600x1100 (detalle Radio proporcional),
paleta256 con64 grises reservados para texto, 12,5FPS, PNG alternativo.
Diez pares verificados, script `tools/capture_landing_v18.py`, manifiesto
`assets/landing_v18_manifest.json`. README/guía/procedencia actualizados.
Sin Q, fuentes runtime ni V17 modificados en esta tarea. No confundir
los medios simulados con la evidencia física histórica conservada.

## 26/10 · Landing renovada con V18

Ocho pares GIF/PNG nuevos generados offline por `tools/capture_landing_v18.py`;
manifiesto `assets/landing_v18_manifest.json`. Diez bloques de landing con
PNG para reducir movimiento y enlace estático explícito. Radio710 sigue
siendo captura real; el resto son demos V18. Bode RC simulado, pendiente
captura física cuando el usuario reconecte A0 a CH1/A2 como referencia y
salida del circuito a CH2/A3, masa común. No iniciar ese ensayo sin aviso
del usuario. Imágenes antiguas en `assets/historico/antes_v18_20261026/`.
V17 y Q sin cambios en esta renovación; sin campañas activas.

## 26/10 · Orden local y presentación Radio

Animación real 710 kHz con FFT16384, paneles Radio y zoom persistente en
`assets/monitor_radio_710.gif`, PNG alternativo. Captura/restauración PASS:
`diagnosticos/resultados_v18/radio_rate_check_20261026_201110/report.json`.
Se borraron ocho imágenes temporales de pruebas, cachés regenerables y seis
carpetas de capturas vacías; inventarios en `capturas/limpieza_20261026.json`
y `docs/orden_archivos_20261026.json`. Índices actualizados sin mover fuentes
ni evidencia. V17 y firmware V18 sin tocar. Sin campaña activa. Los cortes
intermitentes RADIO/A0 siguen pendientes, no afirmar resolución.

## 26/10 · Repetición RADIO/A0 19:08

120 s ADC8 máximo + FFT65536 recortada + RADIO/A0: funcional/visible PASS,
exposición 100%, restauración exacta PASS y salida apagada confirmada.
Sin cambios de código ni firmware. Evidencia: `diagnosticos/resultados_v18/
radio_rate_check_20261026_190845/report.json`. No reprodujo el corte; sigue
pendiente localizar la demora extrema en una captura fallida. No afirmar
resolución. No hay campaña activa.

## 26/10 · CIERRE FPS físicos y política conservadora de audio

Q aceptado preparado/restaurado, sin ensayos activos. ObjetivoFPS validado sólo
para FFTrecortada sola (sin reproducciónRADIO/A0): ADC8/86,65536,avg4,Scanreal,
60scada:9.995FFT/s fijo10 ->12.674adaptativo,visiblePASS. Evidencia
`diagnosticos/resultados_v18/fft_no_a0_20261026_184142/report.json`.

POLÍTICAFINAL: FFTlarga>=16384conreceiver activo empieza10,max15 tras8costes
<=25ms,sólo sin reproducciónDAC. Conowner._wav_activeTrue conserva10.
Se arreglóphasebypass trasbacklog con_resume_pending/_last_fft_started;
guardpendingGUI>1 intacto,resetcostesyrespetaintervalorealalreanudar.
CostessóloresultadosnuevosnoNone, incluido validacióntimestamps. Cacheeje
crop porlayout,invalidaciónconfigurepara no rehacerlabelsestáticas.

FALLOSNORESUELTOS: primerfijo10_180641UNDERRUNparentPCM19709ACKmax498ms;
matrizpostphasefix182105:fixed9.717PASS,adaptive10.144PASS,crop_182606FAIL
MCUdropped1queue8/8CRCcorrecto. RestauraciónPASS; noatribuircausalidadcrop.
Diagnóstico relayV4 privado fft_crop_diagnosis_20261026_183300 pasó120visible;
148601SPIcompletos,backlog1,sinerrores,no reprodujo. Retirado/restaurado original.
Finalacceptedpolicyaudio10,cropcache_183757PASS120visible/restauración.
No darporresueltoADCnounderrun original, ni subirFPSconA0 por estos datos.

251regresión+36focalesPASS;175V17y47ArduinoV18intactos. Informeactual
`diagnosticos/resultados_v18/fft_adaptive_20261026/report.json`.
Doc FFT_CADENCIA_V18_20261026.md,finalPrepareQPASS enmatrizsinA0.
Herramientasguismoke/probe_radio aceptanfft_size,fixed10,crop yfft_only;
fft_onlydiferenciaasserts, no finge reproducción. Próximo: diagnóstico pérdidas
concarga combinada, no anunciar15sostenidos conaudio.

## 26/10 · ACTIVO: FPS físicos con adquisición/A0, no tocar Q

Usuario autorizó continuarvalidaciónreal. FFT65536/avg4 Radio CH1,ADC8/86,
RADIOA0salida40kHz,120s. Primercontrolfijo10 (radio_rate_check_20261026_180641)
fallóUNDERRUN~44saudio: parentPCM19709samples,ACKprocesadohasta498ms,
sourceaudio_waits0,RFcontinuó/restauraciónPASS. No atribuiralobjetivo15FPS.
RepeticiónconMONITOR_V18_CHILD_STAGE_TIMING1 181116funcionalPASS peroexposure73%,
fixedreal~8.7FFT/s global; 181441adaptivePASS120visible100%;181744cropPASS120visible100%.

Se detectódefectoreiniciofase0trasbacklog: permitíabypasspresupuestofijo10.
Corregido flag_resume_pending y_last_fft_started; respeta intervaloantesde
reanudar yreiniciafase ennow. Costessólocuentanlast_endnoNone.7testsfocalesPASS.
NOcompararFPSanteriorescomobaseline válido; informesconservados.

Trescasoscomparablesconhasheshostfijos en exec33229:
`/private/tmp/v18_fft_final_physical_matrix.log`,primeralínea directorioinforme.
Script `/private/tmp/v18_fft_final_physical_matrix.py`: fixed10/adaptive/crop,
120scada,diagnósticotemporalactivo,restauraciónpropietarioúnico,stopporfallofuncional.
No editar spectrum/cadence/harness mientrasactivo; notcompilar/leerQparalelo.
Despuésauditar,fullregresión250+GUI31,PrepareQfinal,documentarestosresultados.
V17/ArduinoV18intactos; no tasa/reloj/firmware cambiados. Audiointermitentesiguependiente.

## 26/10 · FFT adaptativa calibrada y validada offline

Pedido seguir revisiónFPS y menor espaciofrecuencias/título. LongFFT>=16384:
10Hzinicial ->15Hzmax tras8resultadosnuevos<=25ms completos (incluyevalidación
reloj+análisis/preparación,nopinturaQtposterior). Guardpending_batches>1 conserva
aplazamiento; ahora borracostesyfase FFTpara recalentamiento alrecuperar.
Heavyframe>25ms vuelve10; noops/SINGLEnocuentan. Heatmap sin cambio de cadencia.

Comparación sintéticaQt65536/4promedios: fixed10~10FPS,adaptativo~12normal,
~13recortado. Muestrascortasoffscreen, noFPSfísicoQ.20msinicialdemasiadorestrictivo,
ambosinformespreservados. 250regresión y30focalesGUI/cadenciaPASS.
Evidencia `diagnosticos/resultados_v18/fft_adaptive_20261026/report.json`.
Ejeverticalcropaltura70antes100,separación6pxlíneaejeintacta.

V18abiertaPID52315durantecambio,nointerferida; noQoperado.NuevaUIrequiere
reiniciarusuario cuandoquiera.175V17y47ArduinoV18intactos.Noafirmar15FPSsostenidos
conaudio/adquisición,siguependientefísico. DocFFT_CADENCIA_V18_20261026.md.

## 26/10 · FFT larga adaptativa y eje recortado compacto

Usuario pidió revisarFPS/subirmoderado yluego reducir espaciofrecuencias/título.
Spectrum usa fft_cadence.py: longFFT>=16384conreceiver arranca10Hz, permite15Hz
tras8resultadosnuevos consecutivos<=20ms de análisis/preparación; uncostepesado
vuelve10hasta salirventana. Noops/SINGLEnocuentan,resetlimpiacostes. Guard
pending_batches>1 intacto, heatmapmismo límiteprevio. NoQni audio/firmware/tasas.
AxisTickRotation altura70antes100, espaciadofrecuenciarespectoeje6px intacto.

Benchmarklocaloffscreen65536promedio4mediana11–12msp95~15ms; noFPSfísico.
250regresiónPASS y27focalesPASS. Evidencia
`diagnosticos/resultados_v18/fft_adaptive_20261026/report.json`.
Doc FFT_CADENCIA_V18_20261026.md. V18abiertaPID51356durantecambio,nointerferida.
No afirmar15FPSsostenidos: pendientevisualconadquisición/audio; cambiolocal
aplica alreiniciarapp. Mantenercriteriosfallosniocultarpérdidas.

## 26/10 · FFT Radio recortada incorporada en V18

Nuevo tick «Recortar radios» en FFT→Radio. Sólo visual/CH1, sin Qni firmware.
Candidatos válidosScan obligatorios; sinScan/CH1deshabilitadoyautodesmarca.
Módulo radio_fft_crop.py: columnasigualesordenadasRF, bandasugeridaScan o
bandaseleccionada, NanYenbordesnosaltenhuecos. USmapea aliasyorientación.
Tickoffrestauravista/axis/logpreferido,inclusopausadoconcachecompatible.
ClicencolumnasintonizaRF,hueconosintoniza. Dragdetunehabitualdesactivado
sólocrop. CursoresbankseparadoRadio recortada yreadRFcorrecto.

Docs FFT_RADIO_RECORTADA_V18.md. testsGUItest_radio_fft_crop.py yscope_cursors:
24casos focales (logúltimo /private/tmp/v18_crop_validation.log).
RegresiónV18 previa247PASS en /private/tmp/v18_crop_full_tests.log.
Sintéticoinspeccionadovisualmenteconportadoraylaterales. NingúnQoperado.
Fuentes modificadas spectrum.py,scope_cursors.py; nuevopurecropmodule.

## 26/10 · CIERRE pruebas relay telemetría A/B

Q aceptado restaurado y preparado, libre de ensayos. No promover candidatoV4.
`experimentos/relay_telemetry_v18/closure_20261026.json` yRESULTADOS_20261026.md.
BuildLinuxPASS conbombeoADC/restauración. RF A/B12/12PASS:
comparison_20261026_151628/report.json. ADC8máximo120scadarelay,otros5x30s.
Colas2salvo16cola1; márgenes similares sin degrado observable, no equivalenciaestadística.

Audio A/B ADC8/86120scadarelay2/2funcional/restauraciónPASS:
audio_comparison_20261026_152755/report.json. AcceptedGUIvisiblePASS100%2417paint,
instrumented100%2393paint<2400:visualFALSEpreservado, no erroresfuncionales.
Historialaudio sin overwrite:SPI148811intentostodoscompletos,max808.6us,
servicegap3550.4us,READY2948us,backlog1,sinEAGAINparcialesnierrorTCP.
No inferirholguraconjuntanicausadelincidente delos máximos. ACKde salida
perteneceperfilprevio. PrimeraA/B151023falseporstartupdesincronizado,
recovery.jsonPASS ycontrolladorcomparecorregidoreiniciaappidéntica+hash.
FinalPreparePASS10s;175V17 y47fuentesArduinoV18intactas.12testsfocalesPASS.

rate_evidence.json/buildtool enlazan acceptedGUI120visible152756 paraADC8max;
noinheritcandidate. Testsevidencia/selectoractualizados. Fallooriginalsigue
sinreproducir/explicar; no subir tasas ni borrar criteriospor estetanda.

## 26/10 · ACTIVO A/B relay telemetría, Q único propietario

Usuario autorizó avanzar todos testeos sinpreguntar. Build privado exitoso
`experimentos/relay_telemetry_v18/build_20261026_150815/report.json`:
compilaciónLinux -O2-Wall-Wextra-Werror, adquisiciónbaja bombeada yrestauración10sPASS.
CandidatoV4 sin cambiosfuentesArduino/MCU. Primera A/B comparison_20261026_151023:
6controlesacceptedPASS, candidatoarranqueFAIL porqueMCUseguíavivoepochantiguo.
Originalcontainerrepuesto, restauracióninicialFAIL por sincronización. Recovery.json
viaPrepararQ PASS exactapareja y10s. Informeoriginalpermanecefalse.

Controller compare.py corregido: b.start appaceptadaidéntica paraepochstartup
antescandidatoyrestauración; hashfirmwareverificado. Finallybest-effort,
originalcontainerpreservado, rereadidentity+snapshot. NO segundo lector.
Reintento exec26719 log `/private/tmp/v18_telemetry_compare_retry.log`.
Leerprimeralínealog paradirectorioreport. Casosporrelay8/86=120s,8/104,
10/118,12/145,14/160,16/1060=30sc/u, sinRADIO para costeRF. Luego falta
medicióncombinadaaudio instrumentada si RF/restauraciónpasan. No publicar.
Fuenteshostcambiadas diagnóstico anterior, Qrecibosaceptadosintactos, V17congelada.

## 26/10 · Relay telemetría V4 vigente, sin despliegue

V4 `experimentos/relay_telemetry_v18/candidate_v4/` y manifiestopropio.
AstraV3sinbloqueantes,observóprintclientfailure quecontinuabaADC;V4loquita.
Sólo nuevoprintalintegfalloquesale yexit. Restov3identidadporperfil/epoch,
ring8,attempts/completed/failedSPI. 2pruebasampliadasPASS. NoQ ni fuentes
producciónmodificadas. Pendiente controlador seguro relayonly,compilarLinux,
medircoste yrestaurarantesdepromover. No cambiar tasas/relojes/políticas.

## 26/10 · Relay telemetría V3 preparado, pruebas offline PASS

Candidato vigente `experimentos/relay_telemetry_v18/candidate_v3/`, manifiesto
candidate_v3.manifest.json. Separación porbits/modo/períodocodificado/epochprevios
aSPI;ACKdecambioquedaenperfilprevio, siguienteiteraciónnuevoperfil. Historial
8intervalosenmemoria+overwritten,sinprintsdecambio. IntentosSPI/completadas/
fallidas y duraciónfallidamedidas,preservandoerrno. Resumenfault/exitúnicamente.
2pruebasC PASS con escenarios ampliados, noQ ni producción modificados.
RevisiónAstra V3 solicitada, pendiente respuesta. No declarar coste/compilación
Linux ni aceptaciónfísica. Falta controlador relayonlyconbackup,buildprivado,
comparaciónoverhead yrestauraciónexacta. No instalar directoenPrepararQ.
V17 congelada;tasas/reloj/buffers/políticasintactos.

## 26/10 · Telemetría relay preparada sólo offline, NO desplegar aún

Candidato aislado `experimentos/relay_telemetry_v18/candidate_v2/`.
Preparador prepare.py, header telemetry.h, manifest candidate_v2.manifest.json,
2 pruebas C aprobadas (send parcial/reintentos/cola/errno/orden y alcancefuentes).
No Q ni producción modificados;47fuentesArduinoV18 intactas.

Astra review detectó logperiódico potencialmentebloqueante y duraciónSPIfallida
omitida. V2 elimina diagnóstico periódico (progresooriginaligual), midetambién
intentoSPIfallido preservandoerrno. candidate/ conserva primera revisión.
NO aceptar ni instalar todavía: faltasepararmétricasporperfil/epoch y distinguir
intentosSPI/completadas. Lifetime mezcla startup y transiciones, documentado.
Añadir pruebas para esoscaminos antesfísico. Luego prepararcampañarelaysolo,
backup/propietarioúnico/medircoste/restaurarparejaexacta. No cambiar tasas.
README experimento documenta alcance ylimitaciones. FalloADC8noresuelto.

## 26/10 · Diagnóstico host y evidencia por pareja implementados

Bloque autorizado tras revisión con Astra: sin operar Q, firmware, relay,
tasas, límites ni permisosA0. Regresión247/247PASS y selector5/5PASS.
Informe `diagnosticos/resultados_v18/host_diagnostics_20261026/report.json`.
Se conserva un timeout aislado de arranque previo; familia10PASS y suite
completaPASS al repetir. V17:175 y fuentes ArduinoV18:47 intactas.

Nuevos flow_limits.py, rate_evidence.py/json, builder tools/build_rate_evidence_v18.py.
DeliveryBudget registra recurso/previo/proyectado/límites/picos y no muta al
rechazar; receiver_process captura detalles antes decleanup. App snapshotincluye
los límites y motivos. Tooltip tasas distingue hash+geometría parejaaceptada,
ADCsinAudio15/60s, RADIOA0funcional30/120s, visible y holguraconjuntapendiente.
Flags históricos y políticaA0 intactos. No se declara resuelto dropped1ADC8.

Próximo bloque: preparar relayaislado con telemetría SPI/READY/backlog y coste
medido; no instalar directamente. Guía docs/DIAGNOSTICO_HOST_V18_20261026.md.
Trabajo pendiente de GUIvisibleADC8 y comparaciónparejas si reproduce.

## 26/10 · Revisión general con Astra completada, sin implementación

Usuario pidió revisar procesos y tasas. Revisión read-only de cadena completa,
fuentes, ELF y evidencia; sin operar Q ni modificar fuentes de producción.
Informe `docs/REVISION_PROCESOS_TASAS_V18_20261026.md`.

Prioridades: separar aceptación histórica/pareja actual; identificar presupuesto
host agotado; instrumentar latencias/backlog relay en candidato aislado;
repetir ADC8 máximo visible; optimizar correlación pasiva sólo si se mide que
domina. El detector hoy ocupa callback serial antes de liberar crédito IPC.
No culpar TCP del dropped MCU: cola de envío es no bloqueante y cierra cliente,
fallo distinto del dropped1 que termina el relay. No cambiar tasas ni aumentar
buffers sin evidencia. Arquitectura mantiene propietarios, límites y generaciones.

Resultados anteriores conservados:32nuevas×30s y5máximos×120s funcionales;
sólo6/37GUIvisibles, noADC8máximo. No declarar resuelto cierre original.
V17 intocable. Próxima fase propuesta: trazabilidad y diagnóstico host primero;
la implementación no se inició en esta revisión.

## 26/10 · CIERRE: revisión de todas las tasas nuevas con RADIO/A0

Q preparado y libre. Campaña cerrada sin fallos funcionales:32/32 perfiles
nuevos con RADIO/A0≥30s y5/5 máximos anteriores con RADIO/A0≥120s. Control
inicial ADC8 máximo adicional120s aprobado. Misma pareja37f049fa…/27da0bc4…;
no se cambiaron firmware, tasas ni métodos durante estas pruebas.

Informe: `diagnosticos/resultados_v18/radio_rates_review_20261026_130257/report.json`.
Auditoría: `audit.json`; verificación final Preparar Q: `final_prepare.json`,
ambos del mismo directorio. Restauración e identidad correctas por caso.
175 archivos V17 intactos y47 arduino/v18 idénticos al respaldo catálogo.

Usuario dejó ventana en segundo plano: sólo6/37 califican GUI visible.
NO declarar resuelto el fallo original (dropped1, cola8/8, relay salió1).
ADC8 máximo aún pendiente de repetir con dibujo visible; si reproduce,
A/B de parejas completas antes de cambios. Nueva campaña no midió holgura.
No modificar V17. Diagnóstico: `docs/DIAGNOSTICO_ADC8_MAX_20261026.md`.
Las secciones ACTIVO siguientes corresponden a historial previo a este cierre.

## 26/10 · ACTIVO: verificar todas las tasas nuevas con RADIO/A0

Usuario reportó cierre ADC8 máximo con RADIO/A0 y pidió verificar todas las
nuevas tasas y si cambió algo. Fallo real decodificado: dropped1, cola pico8/8,
CRC correcto, fatal0; relay terminó1. Diagnóstico en docs/DIAGNOSTICO_ADC8_MAX_20261026.md.

Control inicial ADC8/86/N3488 120s en exec63908:
`/private/tmp/adc8_control_before_matrix.log`, evidencia
`diagnosticos/resultados_v18/adc8_max_radio_20261026_130130/`.

Supervisor exec6974, log `/private/tmp/verify_radio_rates_v18.log`.
Campaña `diagnosticos/resultados_v18/radio_rates_review_20261026_130257/report.json`.
Espera restauración del control inicial; luego32catálogo×30s RADIO/A0 y5máximos
previos×120s (8/86,10/118,12/145,14/160,16/1060). GUI pública sin inyección.
Usa `tools/probe_radio_rate_v18.py`; scriptsupervisor /private/tmp/verify_radio_rates_v18.py.
No tocar Q mientras siga activo. Un solo propietario, sincompilar ni instalar.
Stop ante fallo funcional/restauración; ocultación se registra aparte y no
calificaGUI visible. Usuario confirmó que ahora debe quedar en segundo plano;
seguir audio/transporte y dejar dibujo visible pendiente.
La primera corrida anterior120s pasóaudio/restauración,peroGUIoculta13%.

Astra revisófuentes+ELF: tablas extendidas y3comparaciones extra por nodo en
predicadoshighrate/spi40, receta86idéntica; evidenciainsuficientepara culparlas.
No cambios de firmware ni tasas durantecampaña. V17 congelada.

## 25/10 · CIERRE: catálogo V18 incorporado y validado

Q libre; no quedan campañas activas. Scope V18 instalada y preparada.
Catálogo: 17 opciones en 8/10/12/14 bits, 15 en 16 bits. Audio aproximado
44,1/48/96/192 kHz; 16 bits sin 192 y con 96 sólo CH1. Históricas accesibles
por clic derecho; máximos y métodos existentes conservados.

32/32 perfiles instalados con holgura, cola máxima 2 y sin pérdidas/fatales;
10/10 recorridos GUI pública visibles, aprobados y restaurados; 237 pruebas
V18 + 30 adicionales aprobadas. 148 rutas Scan históricas idénticas.
Preparar Q final e identidad verificados. V17: 175 archivos protegidos intactos.

Pareja: firmware `37f049fa029ad62a10767c56dc586b2c3697f8d250a0b8a7396570ce8e0c7060`,
relay `27da0bc4860401df27eef50429f2ec881bfd3b51b1893d1fe3bacb9e922f56ae`.
Respaldo final: `respaldos/parejas/v18_catalogo_20261025_230123/manifest.json`.
Evidencia y límites: `docs/CATALOGO_TASAS_V18_PLAN_20261025.md`.
Stage: `experimentos/fs_max_v18/release_catalog_20261025_222651/`.
La landing conserva sus 16 imágenes y la presentación del proyecto.
Las secciones ACTIVO siguientes son historial anterior a este cierre.

## 25/10 · ACTIVO: catálogo instalado, regresión física en curso

Único propietario del Q: matriz instalada, exec **84246**.
Log: `/private/tmp/catalog_installed_screen_fixed.log`.
Buscar el directorio de informe en la primera línea del log. No iniciar otro
lector, GUI ni compilación mientras siga activo.

- GUI privada: 10/10 aprobadas y restauradas, informe
  `diagnosticos/resultados_v18/catalog_private_gui_20261025_205321/report.json`.
- Stage: `experimentos/fs_max_v18/release_catalog_20261025_222651/`.
- Rollback exacto aprobado:
  `experimentos/fs_max_v18/resultados/same_app_restore_20261025_222710_f9903e/report.json`.
- Prebuild, respaldo pareado y actualización transaccional aprobados.
  Respaldo previo: `respaldos/parejas/v18_antes_catalog_20261025_223234/`.
- Nueva identidad: firmware `37f049fa029ad62a10767c56dc586b2c3697f8d250a0b8a7396570ce8e0c7060`,
  relay `27da0bc4860401df27eef50429f2ec881bfd3b51b1893d1fe3bacb9e922f56ae`.
- Ya incorporados los 32 perfiles y `rate_catalog.json`; 148 rutas Scan
  históricas verificadas sin cambios. Máximos y métodos anteriores conservados.
- Regresión posterior: 237 pruebas aprobadas. Adicionales de catálogo/updater:
  30 aprobadas. V17: 175 archivos protegidos verificados intactos.
- Primer intento de matriz instalada (223700) no midió casos: arnés omitía
  marca dual al formar wire. Restauró correctamente. Corregido usando
  Configuration(bits,rate) y comprobación de geometría; informe fallido conservado.

Pendiente: terminar los 32 casos instalados de 15 s; si pasan y restauran,
GUI pública con `/private/tmp/catalog_installed_gui.py` (10 casos, hold30,
usa `tools/probe_catalog_gui_v18.py`, sin inyección de perfiles), verificación
final Preparar Q, respaldo pareado final y documentación. Si algún ensayo
falla, detener y diagnosticar antes de seguir. Ver plan del catálogo en docs.

## 25/10 · ACTIVO: GUI privada del catálogo

Root únicoQexec23013,log `/private/tmp/v18_catalog_private_gui.log`.
Campaña `diagnosticos/resultados_v18/catalog_private_gui_20261025_204734/report.json`.
10recorridos:8/3628y104,10/3628y141,12/3628y171,14/3628y190,16/1667y1166.
Hold30RADIO/A0,Scan normal enaudio bajo/16yUSen8–14bridgealto,WAVySynth
recorren40kcomoharnesshabitual,ventanavisibleexposición90%ycierre/restauración.
Duración65sparaescaneosbajos. Si fallaPARAR/analizar,nopromoverciegamente.
Evidencia física:audio17×60s194759PASS(restaurado);bridges15×60s201421PASS(restaurado);
audio17×15integrados203801PASS(restaurado). Colas1salvo8bridgealto2,todosconholgura.
Reciborelaycachecatalogcreado;mismaidentidadbridges/integración. Producción540c/eccc
arduinosincambios;V17intacta. UIlocalapp+y rate_catalog.pypreparadossinJSONpúblico:
RATESallreceiver;_destination_changedfiltrarecomendadaspero dejaseleccionada;context
Mostrar todas las tasas,~nominalaudioactualtooltip;WAVcabeceraactualconfig.rate.
4GUItestsPASScatálogo/recordWAV,12offlineintegraciónPASS. Scannerexcluye32nuevos
catalog_profilecomoauxviejos;newusaanchorprevio porbits/canales. Máximosintactos.
Próximos:stage_catalog_release.py --gui-reportcampaigncuando10/10PASS;
rollbackrecipecatalog(preparado),prebuildexacto,backupantes,recibo/backendpermitir
catalog,updateQ;hostappend32metadata purposeaudio/intermediatevalidation60y
integration_evidence;rate_catalog.json17/15opciones. Verificar145Scansprevios,
fulltests,matrizinstalada32perfiles15syGUIrepresentativa,finalprepareybackuppareado.
MantenerREADMElandingimágenes,maximosactuales;docCATALOGO_TASASplanconlímites
16no192y96CH1.Userconfirmó44,1. Sinsegundolector/compileencampaña.

## 25/10 · ACTIVO: catálogo; física integrada7/15 cerradasPASS

Root únicoQ exec8521,log `/private/tmp/v18_catalog_bridges_screen.log`;
reporte201421. Audio17/17sesentaPASS/restaurado194759. Catalogintegrado32privados:
7bridges60cerradosPASS(8todos,10todos,12/265),restoen curso. NOlector/compilar.
UIlocalappmodificadaparacatálogo(defaultsinJSONtodavíasiguelistascompletas),
rate_catalog.pyrecomendados+menúcontextualmostrarhistóricas;etiquetas~nominal+realtooltip,
WAVallowedpurposeaudio60paratodosbits,headerconfig.rateentero,no nominalfake.
4GUItestsPASScatalogo+WAVcapcanales+frames+rate.12offlinepropuestaPASS.
NoJSONpúbliconuevoni q_supportnuevoaún;arduinoV18base540c/ecccsincambios.
QactualejecutaScopeV18RateProbeCataloghastaouterrestore. V17intacta.
Siguientes:restaurar201421,recibo relaycache,17audiointegrados15sconrecipecatalog
--target-ticks3628/3333/1667/833. Luego GUIprivada porbitsaudio bajo+bridgealto
(8:3628/104,10:3628/141,12:3628/171,14:3628/190,16:1667/1166),frecuencia10/50kHz,
ScanUSsolo8–14 (16CH1nofaltan2aux,sinesUS). Propósito60s/GUIrecorridono420smaxima.
Despuésstagecatálogo32,rollbackrecipecatalog,prebuild,backuppareado,update,
hostappend32profilespurposeaudio/intermediatevalidation60+catalog_profileTrue,
rate_catalog.jsondesdeaudio_catalog/catalog.proposed.json. Scanneractualyareconoce
catalog_profile:nuevosheredanauxiliaresdeanchorprevio;métodosviejosno usannewaux.
VerificarScantodasantes/después;fulltests;físicoinstalado15s32+GUIrepresentativa;
finalprepare ybackupfinal docs/landingcifrasmaximasintactas.
Planes ytests enexperimentos/fs_max_v18/{prepare_audio_catalog,prepare_catalog_bridges,
prepare_catalog,catalog_selection,test_*catalog*}.py.Continuarautónomamente.

## 25/10 · ACTIVO: puntos intermedios del catálogo integrado

Audio17/17perfiles60sPASS conholgura,cola1todos,yrestauraciónexacta:
`experimentos/fs_max_v18/resultados/20261025_194759/report.json`true.
RootúnicoQ exec8521,log `/private/tmp/v18_catalog_bridges_screen.log`,reporte
`experimentos/fs_max_v18/resultados/20261025_201421/report.json`.
RecipecatalogScopeV18RateProbeCatalogintegra32privados:17audio+15bridges.
Se miden15bridges60s:8/170,128,104;10/220,171,141;12/265,208,171;
14/306,235,190;16/1458,1296,1166. Soloheaderslistas/políticasextendidos;
misma geometríaymétodos,CPU8SPI40cola8compact;10/12/14fastcola4;16OSx16normal.
Nolector/compilar simultáneo. Alcerrarrestauración,regresiónde17audiointegrados
15s(usarlos--target-ticks3628/3333/1667/833),GUItransicionesaudioybridges;calidadanalógica
noaceptadaportransporte. Catálogo17opciones8–14/15opciones16propuesto en
`audio_catalog/catalog.proposed.json`,construidoporcatalog_selection.py.
UIpendiente:separarrecomendadasdehistóricas;no borraridentidades;mostrar~nominal
conrealentooltip;no192en16,96soloCH1. Userconfirmó44,1yrespetarlímites.
Astrarevisó;planesdocs/CATALOGO_TASAS_V18_PLAN_20261025.md.12testsPASS.
Producción540c/eccc máximosactualesintactos;V17intacta. No nuevospúblicosaún.
Luegoaceptación:rollback/prebuild/respaldo/updaterecibos/host32profiles+
rate_catalog.json/UI+tests,regresióninstalada,finalprepareybackuppareado.

## 25/10 · ACTIVO: reorganización de catálogo y audio con Astra

Usuario confirmó44,1kHz(no44literal),respetar límites. Catálogo dual paraaudio
común;CH1extiendesobremáximodual. Configurationactualidentificabits+tasa:
NOduplicarmismosbits/ticksconCH1/dual. Nombreaudionominal+realexplícitos.
RootúnicoQ,campañaaudioexec26159,log `/private/tmp/v18_audio_catalog_screen.log`.
Reporte `experimentos/fs_max_v18/resultados/20261025_194759/report.json`.
17perfilesaudio privados60scadauno:8/10/12/14dual44.1/48/96/192,16CH196.
16dual44.1/48yaexisten;192en16NOposible,maxsimple150943/dual76226.
Recipeaudio_catalogScopeV18RateProbeAudioCatalog modificaSOLOnativeheaders.
14testsPASSsincolisiónyroundtrip;prod540c/ecccyV17intactos. Nootrolector/compile.
Planner `plan_rate_catalog.py` borradorselecciónexistentes;faltanhuecosCH1:
preparado(noejecutado)prepare_catalog_bridges.py15candidatosquartiles sobre
maxdual->maxsingle. Revisaryprobar;no habilitar sin evidencia. Asignarmétodos
rápidosidénticosalosmáximos(8SPI40cola8compact,10/12/14fastcola4,16normal).
Astrarecomienda catálogovisible separado deperfileshistóricos;conservarACK,
restauraciónyaccesoanteriores;nomodificarUARTni simularaudionominalexacto.
Luegocampañaaudio:restauraciónexacta,bridgeprep/tests/screen60,GUItransiciones,
publicaciónpareada/prebuild/rollback/backup/update. FaltaimplementarcatálogoUI.
No pedirok,rutinaautorizada;usuarioesperatrabajoytesteosconAstra.

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

---

Historial de continuidad (estados activos siguientes ya cerrados):

## 25/10 · CIERRE EN CURSO: segunda tanda instalada

Regresiónrestante9/9PASS:new10/1355932,new12/1103448,new14/1000000,control8/1860465
120s cadauno y5viejos20incluyendo16simple/dual. Informe191207true.
8/1882352RECHAZADOporUNDERRUNinstalado190204,retiradodeJSONypermisoA0.
Parejaactual540c/eccc.PrepararQfinalverificado enrateonly2_final_prepare_20261025.json.
Testsfullsession81929log `/private/tmp/v18_rateonly2_final_tests.log` en curso.
Faltaesperartests,corregirfallossilos hay,backupfinalscript`/private/tmp/backup_rateonly2_final.py`
(Qlibretrasprepare,usarboardowner),docs/continuidadconresultadosybackupruta.
HostJSONsolo3nuevos10/118,12/145,14/160;métodosactualesyV17conservados.
README/guíaactualizados;docSONDEOencabezaresultadosegundatanda,guardarhistórico.

## 25/10 · ACTIVO: restante rateonly2 tras fallo INSTALADO de8/85

IMPORTANTE:8/85(1882352)pasóprivado+largasperoFALLÓinstaladoUNDERRUNa~21s.
No reintentarhastaque pase ni incorporarlo. Retirado8/85delJSONpúblicoypermisoA0;
se conserva8/86(1860465). Informe fallido190204permanecefalse. Losotros3todavíapendientes.
Qpareja540c/ecccactualizada correctamente;Cviejaspolíticasiguales;noasumircausa.
ÚltimodiagnósticoPCteníaaudioenbuffer;nocausalidadconfirmadametadata/SPI/host.
Controller ACTIVO exec90108,log `/private/tmp/v18_rateonly2_remainder.log`:
controlnormal8/1860465con120s, luego10/1355932,12/1103448,14/1000000con120s,
luego5viejos20s(10/12/14/16simple/dual). Si controlviejo falla parar/restaurarpareja
anterior545c/3c66porupdaterconbundle/headersdelbackup185347,noforzarmétodos.
NativosJSONactual:prefijoprevio+solo3nuevos10/118,12/145,14/160;8/85NOpublicado.
Testsrateonly2releaseadaptadosarechazo8/85. RootúnicoQ,nosegundolector/compilación.
Trasrestante:demotarfaltantes si falla cualquiera;finalprepareQ,offlinefull,docs+
backupfinalsi aceptación. Stage184722.Propuestas4originales sonhistóricas.
V17y6archivoscentralesintactos,métodosactualesconservados;145Scanseleccionesiguales.

## 25/10 · ACTIVO: actualización transaccional rateonly2

RootúnicoQ.Log `/private/tmp/v18_rateonly2_production_update.log`,reporte
`diagnosticos/resultados_v18/rateonly2_production_update_20261025.json`.
16/16aisladas y4/4GUI120PASS,rollback184745_0b4426PASS,prebuildexactoPASS.
Stage `experimentos/fs_max_v18/release_rateonly2_20261025_184722`.
Backupantes `respaldos/parejas/v18_antes_rateonly2_20261025_185347/manifest.json`.
LocalarduinoV18y acceptedbundle nuevos540c1674/ecccdbcd;QupdateEN CURSO.
Hostnative_profiles.jsontodavíaconservapúblicos86/120/146/170. Trasupdateok:
append4propuestos85/118/145/160,installedevidence,compararScanantes/después,
testpreflight,GUIinstalada4nuevos120y6anteriores20,offlinefullfinal,PrepararQ10s,
backupfinalyREADMEcifrasconimágenes. MétodoScanmapyacontienelos4anchorsnuevos
conexclusióncomoauxiliaresviejos;guardasA0exactas85y160. Appscentrales/DSPintactos.
Powerguard88938liberado,ningúnlector/compilaciónsimultáneos.V17intacta.

## 25/10 · ACTIVO: incorporación rateonly2 tras calificación completa

16/16largas60+3×120 y4/4GUI120 conUS/RADIO/A0/WAV/Synth20PASS;restauraciones
verificadas. Objetivos8/85=1882352,10/118=1355932,12/145=1103448,14/160=1000000.
Mínimosmárgenes17,46/13,63/12,08/15,97%,colas3/2/2/2. Consolidadorateonly2/
qualified_candidates.json.33testsdeexperimentosPASScuandofinalizóQ.
Stage:experimentos/fs_max_v18/release_rateonly2_20261025_184722.
Rollbackprivado--recipe rateonly2 ACTIVO,log `/private/tmp/v18_rateonly2_rollback.log`.
Nolector/compilaciónsimultánea.RootúnicoQ.Powerguard88938liberado.
Siguientes:rollbackPASS,prebuildexactoStageScopeV18,backuppareadoantes,recibos,
updateScopeV18transaccional,hostappend4profiles(escannerexcluye4nuevoscomoaux
viejosyheredacadenaactual),tests,GUIinstalada4nuevos120+6viejos20,finalprepare10s,
backupfinal/docs/landingconimágenes. V17intacta,métodosactualesconservados.
Prodactual545c/3c66conmax86/120/146/170aúnsincambiar. No tasas nuevaspúblicas.

## 25/10 · ACTIVO: calificación sostenida rateonly2

Root únicoQ;exec83182,log `/private/tmp/v18_rateonly2_qualify.log`.
Reporte `experimentos/fs_max_v18/resultados/20261025_181349/report.json`.
--qualify --recipe rateonly2 --bits8/10/12/14 --target-ticks85/118/145/160.
16corridas60+3×120conreiniciosindependientes;restauraciónexactafinal.
4/4GUI120USScan/RADIO/A0/WAV/Synth20/visible/cierre/restauraciónPASS:
`diagnosticos/resultados_v18/rateonly2_gui_20261025_175917/report.json`true.
Fuentesprivadas ScopeV18RateProbeRateOnly2;actualproducción545c/3c66intacta.
Nuevosobjetivos1.882.352,941(8),1.355.932,203(10),1.103.448,276(12),1.000.000(14).
Si60+3×120yrestauraciónpasan,continuarincorporaciónpareada (usuarioquiere
avanzarsinOK):rollback/prebuild/respaldo/recibos/update/host4profiles/GUIinstalada.
Mantenermétodosactuales;capturarScanantes,heredarmismosauxiliares yexcluir
nuevoscomoauxiliaresparalosviejos. V17intacta. Nolector/compilaciónsimultánea.
Powerguardexec88938 caffeinate-i2400,liberaralterminarqual;sinpreferenciascambiadas.

## 25/10 · ACTIVO: GUI del segundo sondeo rateonly2

Root únicoQ, controller exec38861, log `/private/tmp/v18_rateonly2_gui.log`.
9/9sondeos15sPASS yrestauraciónexacta en174849;colapico2todos,márgenes:
8/85=17,48%;10/119=14,51%,118=13,78%;12/145=12,03%;14/160=16,19%.
GUIprivada120RADIO/A0+USScan+WAV+Synth20,exposiciónydibujo:8/85,10/118,
12/145,14/160. Fallback10/119y14/164->168sierrorfuncional,siemprerestaurando.
No lectorni compilar mientrascorre. No nuevosperfilespúblicos;producción545c/3c66
conmáximos86/120/146/170yV17intactos. Métodosanterioresconservados.
TrasGUIrevisarcandidatosviables;sondeos15syGUI120noequivalena60+3×120.
NuevaappScopeV18RateProbeRateOnly2;fuentesexperimentalesbajofs_max_v18/rateonly2.
15testsharnessPASSincluyendoequivalenciaCdepolíticasexistentesynodosnuevos.

## 25/10 · ACTIVO: segundo sondeo rateonly2

Root únicoQ. exec19275,log `/private/tmp/v18_rateonly2_screen.log`.
Reporte `experimentos/fs_max_v18/resultados/20261025_174849/report.json`.
App nueva Scope V18 Rate Probe RateOnly2;copiadeproducción545c/3c66.
Nuevos candidatos8/85;10/119y118;12/145;14/168,166,164,162,160(hasta1MS/s).
9casos15s,restauración exacta final;no lectorni compilaciónsimultáneos.
15testsPASS:políticasCviejasigualesynuevageometría,fuentesalteradas solo5headers.
DespuésGUIprivada120con--recipe rateonly2 --us --keep-display-awake,hereda
auxiliaresdelos máximos actuales86/120/146/170. No cambiarmétodosactuales.
8/84,10/116,12/144fallaronconaudioenlatandaanterior:mantenerrechazos.
No tasas públicas nuevaseneste sondeo. V17yproducciónintactas.

## 25/10 · CERRADO: tasas incorporadas en Monitor V18 + Scope V18

Máximos CH1: 8 bits 1.860.465,116 S/s; 10 bits 1.333.333,333 S/s;
12 bits 1.095.890,411 S/s (sin cambio); 14 bits 941.176,471 S/s;
16 bits 150.943,396 S/s (sin cambio). Dual y tasas previas conservados.
Pareja aceptada: MCU 545c2404… / relay 3c663944…; Preparar Q actualizado.

Calificación física y GUI/audio aceptadas. Rollback y prebuild exactos antes
de actualización transaccional. Regresión instalada 9/9, incluidos perfiles
anteriores y 16 bits simple/dual; 334 tests offline PASS. Las 142 configuraciones
previas conservan auxiliares de Scan US. Métodos centrales sin modificar.
Preparar Q final verificó fuentes, identidad y 10 s de adquisición.
Respaldo final: `respaldos/parejas/v18_tasas_rateonly_20261025_173359/manifest.json`.
V17: 175 hashes intactos. Landing: 16 imágenes/badges preservados.
Q libre, sin campañas activas. Usuario puede probar la app normal de V18.

Informe: `docs/SONDEO_TASAS_V18_20261025.md`.
Regresión: `diagnosticos/resultados_v18/rateonly_installed_20261025_171653/report.json`.
Verificación: `diagnosticos/resultados_v18/rateonly_final_prepare_20261025.json`.
La tanda mayor 8/84, 10/116 y 12/144 se descartó para audio; no habilitar.

---

Historial (los estados activos siguientes ya concluyeron):

## 25/10 · ACTIVO: regresión instalada rateonly

Pareja Scope V18 actualizada y verificada: MCU545c2404 / relay3c663944.
Update`diagnosticos/resultados_v18/rateonly_production_update_20261025.json`ok.
Host nuevos perfiles8/86(1860465),10/120(1333333),14/170(941176)ya incorporados.
142configuracionesprevias conservan auxiliaresScanexactos;28testsPASS.
Regresión física controller exec53230, log `/private/tmp/v18_rateonly_installed_campaign.log`:
3nuevosGUI120US/RADIO/A0/WAV/Synth20, luego6viejosGUI20 (8/10/12/14+16simple/dual).
No lectorni compilaciónsimultánea;controllerse detieneal primerfallo;guarddisplay scoped.
Tras finalizar: revisartodosasertos/exposición; metadatosinstalled_gui_evidence,
docs/READMEcifrasmanteniendoimágenes;offlinechecks;PrepararQverify10s ybackupfinal.
Respaldoantes171017;rollback170343_9be146y prebuild170513PASS. V17intacta.
Métodos anterioresconservados; nuevosScanheredan100/114,128/140,188/192respectivamente.

## 25/10 · ACTIVO: incorporación transaccional rateonly

Root únicoQ. exec deupdate en curso, log `/private/tmp/v18_rateonly_production_update.log`.
Reporte `diagnosticos/resultados_v18/rateonly_production_update_20261025.json`.
Stage:experimentos/fs_max_v18/release_rateonly_20261025_170513.
Rollback same-app170343_9be146PASS,prebuildexacto/restauraciónPASS.
Respaldoantes:respaldos/parejas/v18_antes_rateonly_20261025_171017/manifest.json.
FuentesarduinoV18solo5headerslistas/condicionesextendidos;bundleq_support545c/3c66.
GuardasradioA0admitennuevasgeometríasexactasconcombined_qualified;ScanUShereda
mismosauxiliares,sinusanuevosobjetivoscomoauxiliaresdelosperfilesviejos.
PERFILESPÚBLICOSaúnSINMODIFICAR. Trasupdateok+restauración:mergepropuestade
3perfiles(8/86,10/120,14/170),verificartodaslasScanseleccionesantes/después,
tests,GUIinstalada120porcadauno+regresióntasasviejas,PrepararQyrespaldo final.
V17congelada. No abrirsegundolector ni compilar mientras updatecorre.

## 25/10 · CERRADO: candidatos con métodos constantes

Q restaurado y libre. Candidatos privados con 60 + 3×120 s y GUI de 120 s:
- 8 bits / 86 ticks: 1.860.465,116 S/s; margen mínimo 18,38 %, cola pico 3.
- 10 bits / 120 ticks: 1.333.333,333 S/s; margen mínimo 15,39 %, cola pico 2.
- 14 bits / 170 ticks: 941.176,471 S/s; margen mínimo 20,92 %, cola pico 2.

Prueba combinada: RADIO/A0 a 40 kHz, Scan US, WAV, Synth de 20 voces,
GUI visible, cierre y restauración. 42 pruebas offline del arnés aprobadas.
8/84, 10/116 y 12/144 pasaron aislado pero fallaron con audio: no incorporar.
12 bits mantiene 1.095.890,411 S/s; 16 bits sin cambios. V17 y producción intactas.
Informe: `docs/SONDEO_TASAS_V18_20261025.md`.
Consolidado: `experimentos/fs_max_v18/rateonly/qualified_candidates.json`.

Próxima etapa para habilitar los tres candidatos: prebuild, rollback same-app,
respaldo pareado, recibos, despliegue transaccional y regresión instalada.
No basta exponer tasas: el Q de producción aún no habilita esos períodos.

---

Historial (los estados activos siguientes ya concluyeron):

## 25/10 · ACTIVO: calificación aislada de escalones menores yaGUIaceptados

Root únicoQ; exec96352, log `/private/tmp/v18_rateonly_fallback_qualify.log`.
Reporte `experimentos/fs_max_v18/resultados/20261025_153648/report.json`.
--qualify --recipe rateonly --bits8/10 --target-ticks86/120:60+3×120cadauno,
reinicios independientes yrestauraciónexactafinal. Nolector/compilaciónsimultáneos.
GUI8/86(1,860MS/s)y10/120(1,333MS/s)PASS120RADIO/A0+USScan+WAV+Synth20,
ventana visible+cierre+restauración:campaña
`diagnosticos/resultados_v18/rateonly_gui_fallback_20261025_152933/report.json`true.
14/170(941,176kS/s)yaaislado60+3×120yGUI120PASS,completocandidato privado.
8/84,10/116,12/144aisladosPASSperofallaronconaudio;noaceptadoscombinados.
12conservarmáximoactual1095890.411S/s. Producción/V17y métodos intactos.
Alcerrar153648:validartodasheadroom_ok+restauración;documentar3candidatos
8/86,10/120,14/170si pasa;Qlibre. No tasas públicasincorporadas aún.

## 25/10 · ACTIVO: GUI escalones menores rateonly

Controller exec35224, log `/private/tmp/v18_rateonly_gui_fallback.log`, campaña
`diagnosticos/resultados_v18/rateonly_gui_fallback_20261025_152933/report.json`.
Root únicoQ. GUI8/86iniciada en`gui_private_20261025_152933`, luego10/120.
No abrir otrolector; cadaGUI restaura producción. Estosperíodos aúnno tienen
60+3×120: verificarGUIprimero trasfalloscombinados deperíodosmayores.
122824:16/16aisladasPASS yrestauraciónexacta. GUIprimera ronda completada:
8/84y12/144UNDERRUN;10/116Qcerróflujo. Las3noaceptadascombinadas,restauradas.
14/170pasó120sRADIO/A0,USScan,WAV,Synth20,visibleGUI,cierre yrestauración;
`gui_private_20261025_130902/report.json`true. Candidato14listo, aúnprivado.
Producción yV17sin cambios. Métodos actuales conservados. Si8/86y10/120
pasanGUI, calificaraislado60+3×120yrestaurar; noforzar cambiandoalgoritmos.

## 25/10 · ACTIVO: GUI privada rateonly tras16/16 sostenidasPASS

Root únicoQ. Controller exec63944, log `/private/tmp/v18_rateonly_gui_campaign.log`.
Campaña `diagnosticos/resultados_v18/rateonly_gui_campaign_20261025_130208/report.json`.
PrimeraGUI8/84 `gui_private_20261025_130208`. Secuencia8/84,10/116,12/144,14/170;
120sRADIO/A0+USScan+WAV+Synth20+cierre, restauración exacta tras cadaformato.
Ventana visible y scopedcaffeinate; no abrir lector ni compilar simultáneamente.
Calificaciónaislada16/16PASS conholgura en122824 yrestauraciónexacta verificada.
8margen15,13–15,21%colas3/2/3/3;10margen11,94–12,05%cola2;
12margen11,32–11,41%cola2;14margen20,92–21,02%cola2. Cero dropped/fatal.
Toolsbootstrap GUI rateonly extiende objetivo privado yheredaauxiliaresrápidos
existentes. Se exigeexposición>=90%ypaint_events>=hold*20,además de asserts.
6testsharnessPASS. Producción/V17intactas. No tasaspúblicas todavía.

## 25/10 · ACTIVO: calificación sostenida rateonly

Root único Q. exec57973, log `/private/tmp/v18_rateonly_qualify.log`.
Reporte `experimentos/fs_max_v18/resultados/20261025_122824/report.json`.
--qualify --recipe rateonly --bits8/10/12/14 --target-ticks84/116/144/170.
60+3×120s por candidato, reinicios independientes, restauración exacta alfinal.
Noabrir otrolector ni compilar mientras corre. Producción yV17 sin cambios.
Después GUI privada120 con --us --keep-display-awake por candidato aceptado.
Tools/probe_gui_live_v18 ygui_experimental admitenrateonly;bootstrap extiende
solo el objetivo privado para heredar los mismosauxiliaresrápidos deproducción.
Ninguna tasa pública por sondeos. Usuarioautorizó avanzar.

## 25/10 · CERRADO: sondeo rateonly

Q restaurado y libre. Doce perfiles15s, integridad PASS, cola2 todos.
Candidatos:8/84ticks=1.904.761,90S/s margen15,25%;10/116=1.379.310,34
margen11,96%;12/144=1.111.111,11 margen11,37%;14/170=941.176,47 margen20,96%.
12/142y140 sin holgura(<10%) aunque integridad pasó. No promover.
Tres restauraciones exactas PASS121157,121731,122126. Producción/fuentes yV17
sin cambios. Informe docs/SONDEO_TASAS_V18_20261025.md;resultado consolidado
experimentos/fs_max_v18/rateonly/screen_summary.json. No quedan procesos activos.
Siguiente:calificar60+3×120 yGUI candidatos; nohabilitar públicos por sondeos.
Usuario pidió preservar métodos actuales: nueva receta soloamplía listas y
condiciones explícitas privadas; no cambios de relojes, packing, colas niDMA.

## 25/10 · ACTIVO: rateonly ronda2

Root único Q, exec36048, log `/private/tmp/v18_rateonly_round2.log`.
Runner --recipe rateonly --bits8/10/12/14 --target-ticks86/84/118/116/142/140/172/170,
15s cadauno, detención al primer fallo y restauración exacta. No abrir otrolector.
Primeratanda completa y restaurada:121157(8/87),121731(10/120,12/144,14/174).
Todos integridad/holgura15s PASS; aún privados. Relay buildreceipt verifica
manifest+SHA para no recompilar; app fuente exacta adoptada, no sobrescritura.
Producción y V17 intactas; no métodos nuevos ni tasas públicas.

## 25/10 · ACTIVO: tanda privada rateonly, sin cambiar métodos actuales

Root único Q. exec61235; log `/private/tmp/v18_rateonly_other.log`.
No abrir monitor ni segundo lector hasta restauración. Runner privado:
`run_probe --recipe rateonly --bits 10 12 14 --target-ticks 120 144 174 --seconds 15`.
Copia Scope V18 Rate Probe RateOnly. Producción monitor/arduino sin cambios.
Se extienden listas privadas de perfiles y política CPU; métodos/colas/SPI/ADC
actuales intactos. Ver `experimentos/fs_max_v18/rateonly/PLAN.md`.
8/87ticks=1.839.080,46 S/s pasó15s: dropped=fatal0, cola2, margen19,255%,
slack88798. Informe121157 completo ok=true y restauración exacta verificada.
Aún no es tasa pública ni aceptación sostenida/GUI. Siguiente8:86/84ticks;
primero completar sondeo10/12/14 y restauración. CPU heredada explícita para
10/12/14;8 hereda scope_spi40 y metadato compact_adc8_ipc=true para futura GUI.
Pruebas rateonly/runner13pass. V17 congelada. No incorporar sin60+3×120,
GUI combinada y restauración. Usuario autoriza continuar autónomamente.

## 25/10 · Revisión global y correcciones V18

Scan US exige muestras nuevas para confirmar restauración antes de reanudar
RADIO. Timeout/desconexión mantiene pausa. Pruebas GUI base e integrada
actualizadas al canal PCM y cierre actual. Regresión: 282 + 1 casos aprobados.
Cierre durante carga WAV y rechazo tardío comprobados offline. Sin operar Q.
V17: 175 hashes congelados sin cambios. Firmware y tasas sin cambios.
Informe: `docs/REVISION_GLOBAL_V18_20261025.md`.
Pendiente identificado: optimizar grabación CSV a FS altas, con etapa propia.
Medición sintética actual consume más que el intervalo de llegada en 8–14 bits;
no basta con pasarla a un hilo ni usar una cola sin límite. CSV sin modificar.

## 25/10 · Tasas incorporadas y regresión final aprobada

| Formato CH1 | Máximo público |
|---|---:|
| 8 bits | 1.818.181,818 S/s |
| 10 bits | 1.311.475,410 S/s |
| 12 bits | 1.095.890,411 S/s |
| 14 bits | 909.090,909 S/s |
| 16 bits (sobremuestreo x16) | 150.943,396 S/s |

16 bits dual conserva 76.226,775 S/s por canal: el siguiente candidato falló.
10/12/14/16 pasaron calificación física 60 + 3×120 s y GUI combinada de
120 s; integridad y margen se documentan por separado en la campaña.
La pareja Scope V18 instalada es MCU `7f8de38c…` / relay `f43923b0…`.
Regresión instalada final 8/10/12/14: RADIO/A0, Scan US, WAV, Synth 20 voces
y cierre aprobados, sin errores. 16 pasó su GUI pública de 120 s.
Evidencia: `diagnosticos/resultados_v18/installed_rates_regression_20261025_104120/report.json`
y `diagnosticos/resultados_v18/adc16_installed_public_gui120_20261025.json`.
No se certifica ENOB analógico con estas pruebas. V17 permanece congelada.
Detalle: [campaña de tasas](docs/TASAS_ALTAS_V18_20261025.md).
No quedan procesos de campaña activos; continuar desde esta pareja aceptada.

---

Historial de continuidad (los estados activos siguientes son históricos):

## 25/10 · ACTIVO: GUI instalada10 bits/1,311MS/s conUS

Root único Q. Sesión exec53526, log `/private/tmp/adc10_installed_gui_fixed.log`;
reporte `diagnosticos/resultados_v18/gui_installed_private_20261025_100543`.
Scan US ya pasó; RADIO/A0 en hold120. No abrir otro lector ni compilar enQ.
Calificación aislada10/12/14 completa12/12 y restaurada (093116).
Fallo GUI previo095355 fue en auxiliar legado10/176/N8192 con dropped1,
no en1311. Se restringieron auxiliares rápidos10/12/14, conservando cambio8.
Se corrigió cierre pendiente trasScan, más cancelaciónenel arnés diagnóstico.
Recuperación aceptada + snapshot exacto14/31,25kHz verificados en manual_recovery.
Siguientes: GUI privada instalada12/146 y14/176 con --us --keep-display-awake,
siempre120s y restauración; luego incorporación de candidatos aceptados.
16/1060 ya pasó60+3×120 yGUI120. Su propuesta está staged, sin aplicar; falta
rollback same-app exacto --recipe adc16 y prebuild/recibo/despliegue transaccional.
V17 intacta; usuario autoriza continuar sin pedir OK.

## 25/10 · ACTIVO: calificación instalada 10/12/14

Root único dueño del Q. Proceso exec5943, log
`/private/tmp/installed_other_bits_qualification.log`, reporte
`experimentos/fs_max_v18/installed_campaign/20261025_093116/report.json`.
Comando `screen.py --qualify --bits 10 12 14`: por formato, 60+3×120 s con
reconfiguración entre corridas; sin reinicio del MCU. No abrir otro lector ni
compilar en el Q hasta cierre/restauración. Por ahora 10 bits:60+120 pasaron,
segunda120 en curso. V17 congelada. Usuario autoriza continuar sin pedir OK.

16 bits simple150943,4 S/s: aislado60+3×120 PASS (015536) y GUI combinada120
PASS con Scan/WAV/Synth20/cierre/restauración (gui_private_20261025_020837).
16 simple152672 y dual76555 fallaron antes de medir; ambas restauradas.
Dual conserva76226,8 S/s/canal. Etapa local propuesta, NO aplicada:
`experimentos/fs_max_v18/release_adc16_20261025_093436/proposal.json`.
Pendiente para incorporar16: ensayo same-app rollback exacto (herramienta ahora
acepta --recipe adc16), prebuild exacto de fuentes Scope V18, respaldo pareado,
actualización transaccional por q_support, GUI instalada y luego perfil público.
No falsificar recibos ni reutilizar los de cad37 para firmware7f8de38.

## 25/10 · ADC16 calificación activa; luego 10/12/14

Root único Q. Sesión exec18695, log `/private/tmp/adc16_qualify.log`:
`run_probe.py --run --qualify --recipe adc16 --bits 16 --target-ticks 1060`.
Reporte `experimentos/fs_max_v18/resultados/20261025_015536/report.json`.
60s y dos120s pasaron; falta última120s y restauración. No abrir otra conexión.
Dual2090ticks falló con fatal1, originalrestaurado; conserva2099ticks.
Siguiente: GUI privada16/1060 con50kHz de sintonía, hold120 y restauración;
luego calificación10/12/14 mediante `installed_campaign/screen.py --qualify
--bits 10 12 14` (reiniciaadquisición/cambiaepochentreensayos, sin reflashear).
No incorporar perfiles públicos hasta pruebas combinadas y restauración.
V17 congelada; UI actual sóloV18. Usuario autoriza continuar sin pedir OK.

## 25/10 · Campaña de tasas reanudada (Q exclusivo)

Root opera Q. Sesión exec 53582, log `/private/tmp/adc16_staircase.log`:
`run_probe.py --run --recipe adc16 --bits 16 --seconds 15`.
App privada Scope V18 Rate Probe ADC16; preserva x16/54MHz, sólo agrega
perfiles en copia experimental. Esperar y verificar restauración antes de
otra conexión. Sondeo instalado previo: 16 bits CH1 145454,5 y dual76226,8
pasaron60s con márgenes72,2%/84,4%, cola1 y sin pérdidas; restaurado e identidad
iguales. 10/12/14 superiores pasaron15s (requieren sostenidos/combinados).
Plan y datos: `docs/TASAS_ALTAS_V18_20261025.md`.

## 25/10 · Cierre visual inmediato

Al cerrar V18 se oculta la ventana y se detiene el dibujo inmediatamente;
Qt sigue activo hasta confirmar apagado/restauración y liberar el receptor.
Stop envía cancelación al hijo en ese momento y los ejecutores PCM/DSP
cancelan trabajos pendientes. La salida de Qt se solicita explícitamente
al terminar la limpieza, porque una ventana ya oculta no siempre genera
lastWindowClosed. No se interrumpe Preparar Q ni se termina a la fuerza el Q.

Medición física, ADC14/40 kS/s sin reproducción: ventana oculta en 23,84 ms,
apagado confirmado a 847,81 ms y worker liberado/cierre completo a 951,84 ms.
Antes: 940,32 ms de cierre; la mejora medida es de respuesta visual, no de
reducción sustancial del tiempo de limpieza. Evidencia:
`diagnosticos/resultados_v18/fast_close_20261025.json`.

## 25/10 · Cursores A/B en todos los análisis

Solapa Cursor e iconos Trigger/Filtro/Radio/Cursor. Encendido independiente,
colocación con mouse, clic para fijar/reseleccionar, Esc, seguimiento/libre,
edición numérica, movimiento conjunto y recuadros translúcidos. V(t): t/V;
FFT: f/ordenada; heatmap: t/f/nivel; Bode actual: f/ganancia o fase. Diferencias
con unidades y datos originales del cuadro/bin/celda. No compara dB con grados.
Guía: `docs/CURSORES_V18.md`. Implementación propia en `scope_cursors.py`.
Validación GUI sintética/offscreen; no requiere ni opera el Q. V17 intacta.

## 25/10 · RADIO 48 kHz, heatmap y cierre interactivo

- Generador Radio acepta audio RADIO/FILTER a 48 kHz y lo convierte con el
  resampler continuo existente a 40 kHz para A0. Conserva la FS de RADIO a
  48 kHz; muestra ambas tasas en el estado. No modifica firmware/relay ni
  afirma salida física directa a 48 kHz. El guard de loops sigue observando
  los códigos enviados a la tasa real del DAC.
- Heatmap mantiene un reloj e historial acotado por panel: CH1/CH2 y RF/audio
  pueden dibujarse juntos con su propia FS/Nyquist. Sigue limitando a 512
  columnas, 16 bloques por actualización y la cadencia de pintura existente;
  no interpola muestras RF para convertirlas en audio ni elimina huecos.
- Cierre del monitor: conserva apagado y lectura del estado restaurado,
  pero solicita 0,2 s de comprobación continua en vez de la espera fija de
  10 s. El receptor conserva 10 s por defecto para diagnósticos/campañas.
  No fuerza la terminación para ocultar errores de restauración.

Validación local: pruebas de ambos tonos CH1/CH2, RF+RADIO a distintas FS,
limpieza de panel, Play a 48 kHz solicitando DAC de 40 kHz, conversión por
bloques sin cambio de tono, concurrencia, UI y restauración breve/larga.
45 regresiones adicionales del receptor/Scan/PCM pasaron. Sin validación
física nueva en esta tanda: falta medir audio y tiempo total de cierre con Q.
Los 175 archivos de la pareja V17 congelada conservaron sus hashes.

## 25/10 · Scan US desde ADC8 a 1,818 MS/s

También completó tres Scan US consecutivos con RADIO y Generador Radio→A0
reproduciendo: retornos a 1.818.181 S/s a los 9,80 / 14,96 / 20,05 s,
sin errores de flujo y con reproducción reanudada entre escaneos.
`us1818_active_repeated.json` conserva `ok=false` porque ese script adicional
no recibió confirmación de apagado (`shutdown=null`); no se considera un PASS
de cierre. La verificación posterior independiente de identidad y adquisición
pasó: `us1818_final_verification.json` (servicio Preparar Q, salida exitosa).
Q liberado. Los 175 archivos congelados de V17 mantienen sus hashes.

El cierre observado dejó una trama con CRC válido y `dropped=1` en el
perfil auxiliar de 1.118.881 S/s (143 ticks). El escaneo multirrate había
seleccionado ese perfil por ser el más distante; la pérdida ocurrió en esa
adquisición auxiliar, no en la captura original a 1,818 MS/s.

V18 restringe ahora los auxiliares del grupo ADC8 rápido a sus perfiles
SPI38/40 FIFO: 1.818.181, 1.600.000 y 1.403.508 S/s. Conserva tres capturas,
la estimación de alias y la restauración de la tasa y reproducción originales.
No cambia firmware, relay, V17 ni la selección de auxiliares de otros bits.

Validación: nueve tests locales pasaron. El ensayo físico
`diagnosticos/resultados_v18/us1818_scan_fixed.json` pasó Scan US, retorno a
1,818 MS/s, RADIO/A0 durante 34,77 s, WAV y Synth20; salida apagada y worker
liberado al cerrar. Sus 24 candidatos son hipótesis RF, no emisoras confirmadas.
El log original se conserva en `us1818_relay_failure.log`, en ese directorio.

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

Respaldo pareado final de la versión instalada:
`respaldos/parejas/v18_1818_instalada_20261024_232048/manifest.json`.
Incluye monitor/ArduinoV18, exportQ, ELF/BIN/relay y hashes.
Identidad final verificada; 175 hashes V17 intactos. Q libre.

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

## 24/10 · pareja instalada; validación final del host en curso

Despliegue de producción aprobado:
`diagnosticos/resultados_v18/production_install_20261024.json`.
Scope V18 tiene firmware cad37ccd… y relay 9b8baa1… aceptados; fuentes,
CPU, snapshot y recuperación física de 10,025 s sin pérdidas comprobados.
Backup anterior completo en
`respaldos/parejas/v18_production_0537e3be8d8845d69a6988b3e5a204c1`.
El primer intento rechazó una variable de entorno extra sin uso; rollback
completo PASS y evidencia en production_install_20261024_attempt1.json.
El segundo conserva el entorno original y pasó. No se tocó Scope V17.

Monitor: perfil público único ADC8/88/N3488, 1.818.181 S/s; IPC compacto se
activa automáticamente por metadata del perfil. RADIO permite ese caso exacto.
Sin embargo la primera validación instalada cortó RADIO tras ~73 s y otra
repetición tras ~33 s, ambas con formato compacto confirmado y ACK tardíos
(314/509 ms). Conservar esos fallos; no afirmar estabilidad universal.

Cambio posterior: flush() ya no consulta por segunda vez las colas de IPC si
no corresponde publicar un lote; collect() sigue atendiendo PCM/créditos por
cada trama ADC. 47 pruebas offline PASS. Primer recorrido instalado con ese
cambio PASS completo, RADIO120,389s + Scan/WAV/Synth20/cierre:
`gui_installed_1818_poll_20261024.json`.
Root inició dos repeticiones independientes poll2/poll3; detención ante fallo,
restauración por cada cierre. NO abrir otro monitor ni operar Q mientras midan.
Si pasan, documentar alcance y preservar pareja final; si fallan, mantener
pendiente estabilidad conjunta y no declarar que se resolvió por un solo pase.
Otros bits siguen a tasas públicas previas; candidatos 10/12/14 de60s PASS
necesitan aún campaña sostenida y carga conjunta.

## 24/10 · despliegue producción EN CURSO, root único propietario Q

`python -m tools.prepare_q_v18 --run --acceptance
respaldos/parejas/v18_promocion_20261024_191003/acceptance.json
--report diagnosticos/resultados_v18/production_install_20261024.json`.
30 tests de motor/backend/rollback PASS. Build stage volvió a dar cad37... .
Backup completo verificó fuentes/caché/ELF/BIN/relay y staging exacto.
Journal llegó a start_new_app: fuentes candidatas instaladas, cachéoriginal
preservada y relayoriginalrenombrado. CLI generacachenuevaScopeV18;
procesoautónomo haráhashgateantesrelay y10sverificación, o rollback.
NOabrir monitorniotra conexión. NOinterrumpirCLI mientrasinicia/restaura.
Antespreflight relayoriginalestabaparado; logs guardadosen
`diagnosticos/resultados_v18/pre_install_relay_20261024.log` yparejareiniciada.
Aúnsin cambios perfilesmonitor, máximo8sigue1.6. Trasreportok instalarperfil
públicoúnico8/88N3488 ycompactoautoporesetagyexcepciónradioexacta.

## 24/10 · incorporación preparada, todavía NO instalada

Usuario dijo dalevamos para incorporar. Qproducciónintacto/libre, rootúnicoowner.
Build aislado appnameScopeV18 pasó con BINexacto cad37...; launcherhash08476...
CLI0.13.0; proof/receipt yfirmware/relay/ELF/sourceprior en
`respaldos/parejas/v18_promocion_20261024_191003/`. Fuenteslocalesarduino/v18
ya copiadas desdecandidatoaceptado salvo appnamepythonScopeV18; fuentesprevias
preservadas enprior_oscilloscope/prior_relay. NO tocóV17. NocambiosmonitorFS.

Sol implementa tools/prepare_q_v18_backend.py +tests+engineyarchivehelper.
Astra revisa. Receta: preservarfullcacheprodexacta backupLIVEsinmutación,
preparebuildstagehashaccepted, noimportarcacheprivadahardcodedapprutas.
Install apartacacheprod yBoard.startnormalcreanuevaScopeV18; hashgateantesrelay.
Rollbackfuentes+fullcacheprodexactos yaddedexact3headers; no removals; soportar
.cacheausente si nuevoarranquefallaantescrear. Revisaradapter/testsantesusar.
Receiptactual tiene sources/firmware/relay/evidence+rollback_rehearsal/prebuild_proof.
Prebuildremoto /tmp/v18-production-prebuild-20261024-191003/build.
Luego instalar, validar10s yGUIproducción; habilitarsólo host8ticks88N3488,
compacto default segúneseperfil yexcepciónradio_output>1.6exacta; evitar
copiar todoscandidatoshost porque hay88N3456ambiguo. Firmwaretablesaceptadas
conprivprofilesseconservanparahash, noexponer tasasnoaceptadasalusuario.

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

## 24/10 · tres pases físicos con IPC compacto

ADC8/88 (1,818181MS/s), IPC compactoON, actividaduser normal, sin flags
de timing: tres recorridos completos aprobados120,371/120,403/120,312s.
RADIO/A0, Scan, WAV, Synth20, Stops y cierrePASS; restauración físicaPASS
en los tres. Informes184553/185302/185740. Exposición registrada por separado,
tercero oculto al final: no afirmarFPS ni aceptaciónanalógica. Consolidado:
`experimentos/fs_max_v18/resultados/compact_adc8_acceptance_20261024.json`.
La ruta compacta sigueOFFpor defecto; tasa pública8bits sigue1,6MS/s.
Siguiente: rehearsalprivado rollbackparejaQ, luegoincorporacióncontrolada.

## 24/10 · IPC compacto: primer pase físico completo; repeticiones activas

`gui_private_20261024_184553/report.json` PASS y hardware_restored=true:
RADIO/A0 a ADC8/88 (1,818181MS/s) durante120,371s, Scan, WAV, Synth20,
Stop y cierre aprobados. MONITOR_V18_COMPACT_ADC8_IPC=1; actividaduser normal,
sinchildstagetiming ni critical. La ruta compacta sigue OFF por defecto.
Root inició dos repeticiones independientes, wrapper corta ante primerfallo y
restaura cada vez. No abrirotro monitor ni operarQ mientrasroot mide.

Antes, sincompacto pero eliminando retornojoin_records descartado, `183349`
y`183840` pasaron completos120,280/120,221s conrestore; `184316` fallóRADIO
tempranoACK498ms peseRPC15ms, restauró. No calificarloseriecomopass.
50testscombinadosPASS enPython_3_13_DataScience, sinprocesoshuérfanos.
Sol añadió CompactAdc8RfBatch uint8+metadatos, reconstrucciónexactaenpadre;
selector sóloADC8CH1 yenv1. Tests incluyenwrap,ownership,pickle,splits/forced.
Comparaciónspawn sintética:1.164.040→73.190bytes/lote. NocambiosMCU/buffers.
Tasas10/12/14maximas ya60sPASS/restauradascomoabajo; faltan3×120.

## 24/10 · pruebas retomadas: tasas nuevas y estabilidad pendiente

El usuario autorizó continuar sin pedir OK entre pruebas. Root es el único
propietario del Q. V17 permanece congelada: 175 hashes iguales al respaldo.
El host previo a esta campaña está respaldado en
`respaldos/parejas/v18_host_pre_fs_20261024_174953/manifest.json`.

**Tasas privadas:** los ocho candidatos de 10/12/14 bits pasaron 15 segundos
cada uno. Los máximos pasaron además 60 segundos, sin pérdidas, cola pico 2:
10 bits a 1.311.475 S/s (17,18% de margen), 12 bits a 1.095.890 S/s (12,72%)
y 14 bits a 909.091 S/s (23,52%). Informes en
`experimentos/fs_max_v18/resultados/20261024_180456/report.json` y
`20261024_181908/report.json`; ambos restauraron producción y verificaron
la recuperación física. No son tasas públicas ni aceptación analógica.

**ADC8 a 1,818 MS/s:** `gui_private_20261024_175059` aprobó el recorrido completo
con RADIO/A0 durante 120 s. `175550` completó RADIO 120 s y WAV, pero falló
Synth20. `180149` repitió el fallo de Synth tras bajar adquisición a 40 kHz.
La etapa denominada render incluye el RPC al proceso de síntesis: sus 25 ms
no equivalen a 25 ms de CPU DSP.

Después fallaron también RADIO: `181103` durante el cebado y `181450` tras
78 s; los ACK alcanzaron 197–208 ms pese a tener audio disponible en el host.
Stock a 1,6 MS/s reprodujo esa firma en
`synth20_resume_diagnostic_20261024.json`. El ensayo `182512` con actividad
critical falló visible antes de la ocultación programada: RPC máximo 12 ms,
ACK 215 ms. Astra encontró 719 ms de CPU del receptor en el último segundo;
no atribuir el problema exclusivamente al protector de pantalla ni al relay.
Todas estas campañas restauraron el Q; se conservan los fallos.

Cambios locales V18: evidencia PCM genérica al fallar Synth; actividad macOS
user en el proceso de render con Finalize y soporte off; cebado PCM con la
ventana existente y PLAY esperando todos los ACK. La validación conjunta sigue
pendiente. El decoder ahora permite no construir el retorno concatenado que
OutputReceiver ignora, conservando eventos y validaciones. 44 tests pasaron.
Benchmark offline: CPU mediana de 10,13 a 8,77 ms por 223.232 muestras
(13,4% menos); no es aceptación física.

Sol está preparando y probando IPC compacto ADC8 CH1, experimental y apagado
por defecto (`MONITOR_V18_COMPACT_ADC8_IPC=1` lo activa). Se transportan uint8
y metadatos; el padre reconstruye la misma matriz de muestras. No operar el Q
hasta que Sol congele ediciones. Próximo paso: física con copia eliminada e IPC
compacto OFF; después contrastar compacto ON si hace falta. Mantener actividad
user y evitar mezclar otras variables. El máximo público sigue en 1,6 MS/s.

La opción diagnóstica `--occlusion-test` oculta la ventana a los 45 s y vuelve a
mostrarla a los 85 s. El cierre la muestra primero para esperar restauración,
aunque un error termine la fase oculta. No afirmar FPS visibles durante ella.

## 24/10 · campañas retomadas por pedido del usuario

Autorizado retomar pruebas físicas: primero ADC8 a 1,818181 MS/s, luego
aumentar 10/12/14 bits. Revalidar host actual (AGC gradual, volumen60%, gain10×)
sin flags diagnósticos antes de promoción. V17 congelada. Cada campaña usa
propietario exclusivo y restaura la pareja Q original con verificación física.

## 24/10 · valores iniciales RADIO solicitados

V18 inicia Volumen A0 en60% (dial y etiqueta) y gainRADIO10× (spinbox/dial y
ProcessingSettings/fallback coincidentes). Test de rampa AGC fija explícitamente
2× para seguir comprobando acumulación de subpasos independientemente del
valor inicial de usuario. No Q/firmware/V17 modificados; usuario sigue pruebas.

## 24/10 · Auto gain gradual incorporado en V18; Q libre para pruebas

El usuario retomó mejoras y pidió suavizar gain, salvo clipping extremo.
Cambio local exclusivo V18: radio_autogain.target_gain limita subida a1dB/s y
bajada normal a2dB/s, con intervalo normal100ms y elapsedmáximo0,5s para evitar
salto tras pausa de GUI. Redondeo0,1× acumula tiempo desde último cambio real.
Conserva objetivo0,5–2,8V, gain1–80, banda muerta5%/0,1× y no subir en silencio.
Emergencia: muestra≤0,05V o≥3,25V permite reducción directa hacia objetivo,
redondeada hacia abajo y sin esperar el intervalo normal. Sólo datos de la
configuración/generación vigente pueden ajustar gain. Manual sigue anulandoAuto.
El clamp digital final del DAC sigue intacto; no afirmar protección eléctrica
contra cargas externas por este control de amplitud.

11 pruebas offline de AGC+RADIO GUI PASS: rampas, clipping, inválidos/silencio,
pausa larga, acumulación subpasos, generaciones y override manual.175hashesV17
iguales al respaldo. NO conexión al Q, NO firmware/relay ni FS modificados.
Usuario puede seguir probando; reiniciar V18 para cargar el cambio. No iniciar
campañas físicas sin revisar propietario/monitor abierto. Objetivo1.818privado,
rollback/promociónpendientes como abajo; el cambio AGC no los da por completados.

## 24/10 · V18 lista para prueba manual del usuario

**Sin campañas activas. Q libre, Scope V18 y relay de producción restaurados.**
El usuario pidió probar la última versión: no iniciar nuevos ensayos ni conectar
al Q mientras la esté probando. V17 permanece congelada: 175 hashes verificados.

Abrir `monitor/v18/app.py`. Máximo público de 8 bits: **1,6 MS/s**.
El candidato de 1,818181 MS/s sigue privado; falta incorporar su pareja en
Scope V18 mediante despliegue con rollback demostrado. No confundir los pases
privados con una tasa ya disponible en el selector normal.

Versión normal comprobada sin variables ni flags especiales:
`diagnosticos/resultados_v18/gui_public_stock_final_20261024.json`.
RADIO/A0 60,323 s, Scan, WAV, Synth20, Stop y cierre: todos PASS, sin errores.
Restauración en `sessions/session_20261024_160330_654354.json`: 10,020 s,
313344 muestras, dropped=0/fatal=0, actividad del receptor liberada.

La combinación final privada pasó tres GUI independientes de 120 s:
`gui_private_20261024_124706` (120,317 s), `125152` (120,223 s) y
`125636` (120,275 s); todas con Scan/WAV/Synth20/cierre y restauración PASS.
Evidencia consolidada: `experimentos/fs_max_v18/resultados/batcharena_acceptance_20261024.json`.
Se registran por separado exposición/pintura: no afirmar 60 FPS ni aceptación
analógica por estos pases. Los fallos anteriores se conservan.

Cambios del monitor V18: canal PCM dedicado; publicación de audio antes de
correlación pasiva; crédito IPC liberado al completar DSP/audio sin descartar
la copia GUI; lotes RF normales limitados a 40 ms y resto íntegro bajo el mismo
presupuesto total; dibujo omitido sólo cuando no expuesto o con lotes listos
pendientes, conservando SINGLE. Actividad macOS `user` durante adquisición en
padre y receptor, liberada al cerrar; permite reposo de pantalla y sistema.
Sin cambios de reservas DAC, tasas públicas ni firmware de producción.

Respaldo pareado para esta prueba: `respaldos/parejas/v18_prueba_20261024_130547/manifest.json`, con fuentes,
export de app Q, binarios firmware/relay y hashes comprobados. Pruebas locales:
52 casos de la batería y 16 de proxy/actividad tras ajuste final PASS.

Después de la prueba del usuario: recoger resultado; si autoriza retomar,
continuar respaldo del candidato Arena y rehearsal privado de rollback exacto
antes del despliegue del transporte en Scope V18. 10/12/14 bits después del
cierre de 8 bits. No tocar V17 ni asumir acceso exclusivo al Q durante su prueba.

## 24/10: pública1.6bounded+actividadambosPASS;3privadas120activas

`gui_public_bounded_activity_1600_20261024.json`: RADIOhold60,300s/Scan/WAVStop/Synth20Stop/shutdown/workreleasedTODOSPASS/errors[]. Ventanaocultapartes, noFPSclaim. Session_20261024_154439_960158.jsonhardware_restoredtrue,receiveractivitypid57342modeuseractive/releasedtrue;GUIactivityreleasedtrue. Sinfirmwaredeploy,públicaScopeV18base sinmodificar.

Activa loopset-e3corridasBatchArena8/88hold120conCHILD_STAGE_TIMING1+RECEIVER_ACTIVITYuser+--macos-activityuserpadre,lotesRFnormal<=40ms. Logs `/tmp/v18_bounded_both_activity_1.log`,_2.log,_3.log. Cadaunaownerexclusivoyrestauraciónantespróxima,abortafallo. SinotrasGUI/testsCPU/QIO. Revisarexposición/pinturaseparada,latenciasACKyrestauración/tokensreleased. Si3PASSconsideraractividadscopedproductivaacquisiciónconcleanup (hoyDIAGNÓSTICOdefaultOFF) yrepetirpúblico;noafirmarcausaúnica. SiFAILpermanecerprivado/registrarhonesto.

NoNSActivityglobal,permitidoreposopantalla/sistema. V17quieta,públicas1.6M,objetivo1.818requierecerrarcalificación+rollbackpareadodeployantespublicar.

## 24/10: públicahidden1.6sinactivitysiguefallando;comparaciónambasactivityactiva

Públicagui_public_bounded_1600_20261024FAILRF>1s,sinUNDERRUN,session_20261024_154202_798218.jsonrestoredtrue10,021s/drop0/fatal0. Retained4lotesPEQUEÑOS20/20/20/18ms sum.07992s+buffer.92016s,lastcreditage.99565s;noesya giantpickle, parentnohacíaconsumo1sconwindowocultapaint7. Secuencia75844abortó,privadasrepeat2/3noarrancaron.

Activa sesiónverttool `/tmp/v18_public_bounded_activity.log`:ScopeV18público8/1.6hold60+Scan/WAV/FM20,CHILD_STAGE_TIMING1+RECEIVER_ACTIVITYuser+--macos-activityuserpadre,singuarddisplay;salidagui_public_bounded_activity_1600_20261024.json. RootúnicoQ/captura+restauraciónReceiverLifecycle, noCPUtests/otrasGUI/QIO. PolíticaOSglobalnoalterada/tokensscopedreleasedregistradossessionsjson. Comparacióncombinadalotespequeños+actividad,noatribuirúnicacausa. Públicas1.6M,V17quieta. 1.818todavíaaceptacióncombinadaNOcerrada.

## 24/10: lotesIPC40msprimerpasecompletoPASS;regresión1.6+dosrepeticionesactivas

GUI123631batchArenaoriginal+lotesIPCacotados40ms: ok/gui_ok/hardware_restoredtrue;RADIO120,178s/Scan/WAVStop/Synth20Stop/shutdown/workreleasedTODOSPASS/errors[]. SinactividadmacOS,singuardpantalla,windowexposedúltimasmuestras. No decirresuelto por1pase.

Activa secuencia(set-e):públicaScopeV18actual1.6Mhold60+Scan/WAV/FM20 `/tmp/v18_public_bounded_1600.log`,salidagui_public_bounded_1600_20261024.json;despuésprivadasBatchArena8/88hold120 `/tmp/v18_bounded_rf_repeat2.log`,repeat3.log. CHILD_STAGE_TIMING1,sinactivity;rootúnicoQ,restauracióncadacaso,abortafallo. SinotrasGUI/testsCPU/QIO. Alcerrarrevisarrestauraciónysessionsjsonpara pública,reportpara privadas. V17quieta,públicas1.6M.

51testsPASSprevios. HostincluyePCMdedi,feedfirst,IPCcreditpostDSP/WAVactivos,skiphiddensalvoSINGLE,skipdrawreadyGUI>=2,gateperframeserviceEXACTOprivado8/88+ADC10existing,unforcedRFbatch<=40msconrestosretenidos/forceACKFIFOintacto. Ningúnaumento1sbudget/colasDACnifirmwareArena. QUickACKrelaydescartadopornoresolveryvariantaislada;NOusarpara promoción.

## 24/10: backlogseconvertíaenlote533ms;IPCnormalcap40msenprueba

GUI123120relayQUICKACKFAILRF>1s,sinUNDERRUN,restoretrue. Retainedprimerlote.5333152s+otros.0585s;buffer.4086s,lastcreditage424ms. NoevidenciaQUICKACKresuelve:noincorporarrelayvariant,seconservaexperimento. VarianteMCUbitidénticaArena,relayúnicocambioackTCP.

CambiohostV18medido: flushnormalemitíatodochunksacumuladoalvolvercrédito; pausas0.4–0.6screabanlotesgiantes+pickle/copias. Ahora take_rf_prefixsinconcatbacklogdivideporreferencias máximo40ms deconfigactualennormal,reteniendoTODOSrestos/ordenbajoMISMOcap1s/MAXbatchslots. FlushforceenACKconfigsiguedrenandotodoantesbarreracomoantes (noeventreorder). No buffersnuevos. Test1000rowschunkssplit40preservavalores/orden/sharesmemory ylímites.51teststiming/receiver/pump/GUI/SINGLEPASS.

Activa sesiónverttool `/tmp/v18_bounded_rf_batches.log`:GUI120recipeBATCHARENAoriginal(noQUICKACK)8/88conCHILD_STAGE_TIMING1,activityOFF/singuardpantalla. RootúnicoQ/restauraciónobligatoria;noCPUtests/otraGUI/QIO. Revisarduraciónretainedbatch<=40msennormal,RFpending/hold/ACK/WAV/FM20/restore. Forcepuedeemitirmayoresduranteconfigboundary, mantenerdistinción. SiPASSrepetir yregresión1.6antespromoción;V17quieta,públicas1.6M.

## 24/10: parent+childactivityNOresolvió;A/BrelayTCPQUICKACKactivo

GUI122353 useractividadGUI+child FAILUNDERRUN~70s,restoretrue. ACK267,74ms/16inflightoldest267,66ms;childpump59msCPU47ms,gap3,3ms. No habilitaractividadproductiva comosolución. ScopeNSActivitytemporalseterminósegúnExitStack;persisitireleasedahoraanteslifecycle.finalize. HostguardOFFdefault.

Nuevarecipeprivada batchquickack, generadorprepare_batchquickack.py: MCUoscilloscopefuentesBITIGUALESArena,mismoappprivadoScopeV18RateProbeBatchArena(NOoverwritefuentes),relaycopyúnicodiffsetTCP_QUICKACK=1despuésrecvPC>0. PruebahipótesisTCPretardadodelcomandoadbd→relay,noclaimcausa. TCP_NODELAYyaambossocketpropios. Relaydigestnuevoaislado;ScopeV18producciónsepreservarestaura.14testrunner/journalPASS+manifestisolationexact MCU/sóloCrelaydiffPASS.

Activa sesiónverttool `/tmp/v18_relay_quickack.log`:GUI120recipebatchquickack8/88conCHILD_STAGE_TIMING1,parent/childactivityOFF,singuardpantalla. RootúnicoQ/restauraciónobligatoria. NoCPUtests/otrasGUI/QIO. RevisarcompilaciónLinuxTCP_QUICKACK,hashMCUigualArena,ACKlatency/pumps/hold/WAV/FM20/restore. Si falla guardarhonesto;nohabilitarFSnueva. V17quieta/públicas1.6M.

## 24/10: childusercirculabienperoGUIbloqueacrédito;ambosprocesosactividaduserencomparación

GUI121933 childactivityuseronly FAILRF>1s,restoretrue;childmaxpump19,95ms/gap2,64ms/events17ms,sinpausachild200ms. Retained.38272s+buffer.61772s,creditage.658s;GUIstackdraw->_reduce_trace_for_display np.isfinite. Es otroproceso: padresinactividadpuedepararseaunquechildguardactivo. No declararcausaúnicaAppNapnitratamientoproductivo.

Arregloevidenciareceiver_activityseanexaresultANTESlifecycle.finalize paraqueseapersistaen sessionjson despuésstack.close;21testsPASStrasajuste. DefaultOFFnoactividadproductiva.

Activa sesiónverttool `/tmp/v18_parent_child_activity.log`: BatchArena8/88GUI120,CHILD_STAGE_TIMING1+RECEIVER_ACTIVITYuser y --macos-activity user enpadre,displayidlesleeppermitido. Activityscopescierranyregistranrelease;sinpreferenciasglobales,rootúnicoQ/restauraciónobligatoria. SinotrasGUI/testsCPU/QIO. RevisarpausasCPUwallambos/ACK/hold/WAV/FM20/restore ytokensreleased. Sólotrascomparaciónrepetida decidirproducto;V17quieta,públicas1.6M.

## 24/10: pausa191msCPU<1enchild;actividadtemporalDENTROreceptorencomparación

GUI121455drainpriorityFAILUNDERRUN~8s,restoretrue;ACK457ms/14CHUNKinflight/oldest456,9ms,RPC13,6ms. Childtickwall191,41msCPU.480ms/collect192,39msCPU.878ms/events193msCPU7,9ms;pausanoexplicadaportrabajoCPU. GUIdrainprioritynoarregló, noclaimcausalculpaGUIúnica.

Opt-inDIAGNÓSTICO MONITOR_V18_RECEIVER_ACTIVITY=off|user|critical creaMacActivityDENTROreceiver_mainExitStack antesconexión, scopeincluyerestauraciónyclose;tokenreleaseevidenceenReceiverLifecycleterminal/session(receiver_activitypid/mode/active/released). DefaultOFF/productsinactividad. NopolíticasOSglobales/displaynosleep. Parentactividadnoheredadaexplícita por spawn,segúnSDKlocalAstra.33?testsGUI/receiver/exposure/childtimingPASS rootúltimosveroutput.

Activa sesiónverttool `/tmp/v18_child_activity_user.log`:GUI120BatchArena8/88,CHILD_STAGE_TIMING1+RECEIVER_ACTIVITYuser;parentSINactivity/singuardpantalla. RootúnicoQ,restauraciónobligatoria,sinCPUtests/otraGUI/QIO. AlcerrarrevisarpausaswallCPUenring,ACKyhold/WAV/FM20/restore,tokenreleaseden sessions/. Siuserfallasóloentoncescriticalcomparación(segúnplanAstra);nohabilitarproductivoporunpass. V17quieta/públicas1.6M.

## 24/10: RADIO120conservicioentreframesPASS;WAVpostStopfallaGUI;prioridadconsumoGUIenprueba

GUI120858 gateprivate8serviceentreframes: RADIO120,117sPASS,Stop/Scan/WAVplayprogressPASS;FAILWAVStop/RFpendiente>1s,restoretrue. overload121247a8/40k:retained.46645s+buffer.5346s,lastcreditage.6046s;parentpendientes0observadostarde,noprobareventinstantáneo. NocontarcompletoPASS.

CambioV18acotadoGUI: OutputWorker.ready_gui_batches=max(0,pending_batches-pending_dsp) bajolock. _render_with_diagnostics si>=2 ynoSINGLE retornaesetickparaqueQtconsumaloteslistosantescopiarhistoriasyredibujar. No descarta muestras, no cambiahistoriascréditos/presupuesto/temporizador;singleshotcapturasiempre. Skipcuandoocultoguardprevioseconserva.49testsPASSincluyendobacklog0/1/2/5ySINGLE.

Activa sesiónvertTool `/tmp/v18_gui_drain_priority.log`:GUI120privadoBatchArena8/88conCHILD_STAGE_TIMING1,sinactivity/displayguard;rootúnicoQ/restauraciónobligatoria. SinCPUtests/otrasGUI/QIO. RevisarholdyWAV/FMSynthStop/restauración,paintFPSrealymemoria, noafirmarresueltosinrepeticiones/pública1.6. V17quieta/públicas1.6M. SiUNDERRUNACKlatenciarevisartrazarelayantesinferirMCU.

## 24/10: repeticiónexpuestaUNDERRUNACK239ms;servicioentreframesprivadoenprueba

GUI120332repeat2FAILRADIOUNDERRUNcercafinal,restoretrue;repeat3ypública1.6noarrancaron. Ringmuestrapumps44–46ms(cpu30–34ms),nogap>31ms;sendACK239,56ms,15CHUNKinflightoldest239,5ms,RPC15,5ms. No atribuirsimpleAppNapchildpausa200ms: receiveractivodecodificandoframes. Hostvisibleenúltimasmuestras. Primerpase115825completoPASSseconserva,noaceptaciónporintermitencia.

CambioexperimentalV18receiver: igualqueservicioADC10/1.25M preexistente, habilitaservice_wavtrascadaprocess_decoder_events SÓLO radio_audio+ADC8+CH1+period88+node3488. Noamplía burst/tokens/créditos/colas,noeventreorder/reentrancia(segúnAstra). VentajarefillPCMaceptadodurantetickADCsinaguardarACKofindelectura64k. GateactualADC10preservado,8/1.6noparticipa.48testsPASSincluyendoscopegateexactoytiming/GUI/pump/SINGLE.

Activa sesión vertool `/tmp/v18_between_frames_audio.log`:GUI120privadoBatchArena8/88conCHILD_STAGE_TIMING1,sinactivity/displayguard. RootúnicoQ,restauraciónobligatoria;sinCPUtests/otraGUI/QIO. RevisarACKmax,hold,yCPUcostoserviceporframe~2k/s. V17quieta,públicas1.6M,estabilidadtodavíapendiente. Próximo siFAIL: separarbacklogTCP/ADB delrelayconRIDtimestampinstrumentadoprivadoconbackup, noconjeturasfirmware.

## 24/10: pasecompletoventanaexpuestaPASS;calificaciónrepetidaactiva

`gui_private_20261024_115825/report.json`:ok/gui_ok/hardware_restoredtrue;RADIOhold120,139s/Scan/WAVStop/Synth20Stop/shutdown/workreleasedTODOSPASS/errors[]. RADIOexposed28/28muestras,4217paints,PCMroundtripmax59,94ms,sendACK64,44ms. Hostexposureguardnoafectódibujovisibleenestepase. No decircausaúnicaresuelta por1pase.

Activa secuenciasesiónverttool: GUIrepeat2 `/tmp/v18_exposure_audio_repeat2.log`,repeat3 `/tmp/v18_exposure_audio_repeat3.log` (ambosBatchArena8/88hold120),luegoGUIpública1.6hold60+Scan/WAV/FM20 `/tmp/v18_public_1600_repeat.log`,outputgui_public_pcm_1600_repeat_20261024.json. TodosCHILD_STAGE_TIMING1,sinactivitymacOS/displayguard. Cadaunoownerexclusivo/restauración,set-eabortaantefallo. NootrasGUI/testsCPU/QIO. Alcerrarverificarexposición/identidad/restauraciónsinreinventaraceptación.

GuardUIV18skiprendercuandowindowHandle&&!isExposed&&!single_shot_armed;historias/DSP/handle_batchindependientes,SINGLEsiempreprocesa.47testsPASS. PrivadoADC8serviceporframenotocado,aúnADC10only. FirmwareArena sinmodificar. V17quieta/públicas1.6M. Trascalificación:backupArenaexacto+testsrehearsalrollbackprivado ypromociónScopeV18aúnpendientes.

## 24/10: receptorcircula;GUIinvisibletrabajaba;guardexposiciónenprueba

GUI113512 conchildtiming: RADIO120,227sPASS; FAILposteriorWAVRF>1s,restoretrue. overload113900durante8/40k:retained.56885s+buffer.4322s,creditage.494s;childmaxpump9,1ms/gap21,1ms/events4,2ms,CPUbajo;ningunapausachild200ms. GUIstackpreparandovistamixtaenSampleHistory.window/np.arange. NoclaimCPUcopycaro,perodibujadosehaceinclusocuandonowindowexposed.

CambioV18acotado _render_with_diagnostics retornaSIhandleexistente&&!isExposed&&!single_shot_armed. NOafectahandle_batch/historias/DSP/adquisición,alvolversevisiblevuelvedibujar,SINGLEsiempreprocesa. Testhidden/exposed/SINGLEPASS,47testsGUI/receiver/pump/timing/concurrenciaPASS. Cadenciamientrasvisibleintacta. NoafirmarFPSenoculto. GateADC8serviceporframe sigueNOimplementadohastatrazasUNDERRUN.

Activa sesión73388 `/tmp/v18_exposure_audio.log`:GUI120BatchArena8/88conCHILD_STAGE_TIMING1,sinactivitymacOS/guardpantalla. RootúnicoQ,restauraciónobligatoria;nootrasGUI/testsCPU/QIO. Revisarhold,WAV/FMSynthStop ypaint/exposiciónseparados. Públicas1.6M,V17intocable. SiFAILpreservarevidencia,siPASSrepetir yvalidarpública1.6másGUIvisibleantespromoción.

## 24/10: cronómetros completos enGUI1.818activos;regresiónpública fallórestaurada

Pública1.6 `gui_public_pcm_1600_20261024.json`: FAILRFpendiente>1s,sinUNDERRUN; session_20261024_143144_255380.json confirmahardware_restoredtrue10,019s/drops0/fatal0. overload113238:retained.48924s(4batchesuno.42066s)+buffer.51084s,lastcreditage.519s;GUIstackmainenSampleHistory.window.copy+guiretraso975ms, noconcluirCPUcopycaro(OSdeschedulingposible).

Agregadofail()copiachild_stages ringopt-in tambiénfallobudgetRF ademásUNDERRUN;noIPCextragordoennormal.21testsreceptordetailsPASSdespuéscambio. Activa sesión6606 `/tmp/v18_child_full_timing.log`:GUI120privadoBatchArena8/88conMONITOR_V18_CHILD_STAGE_TIMING=1,rootúnicoQ/restauraciónobligatoria,sinCPUtests/otraGUI/QIO. RevisarwallCPU/ring/active enpcm_underrun.transport_underrun.child_stages o gui_overload.receiver_failure_snapshot.child_stages.

No cambiógateperframeservice: sóloADC10/1.25M;Astraaprobógateequivalenteprivado8/88CH1N3488+radio_audio comoexperimentosiguientedespuéscronómetros. SlotshostDSP/audioPCMcambiosyaescritos39+7testsPASS;estabilidad1.6/1.818todavíanoresuelta. V17intocable,públicas1.6M. AstraplanearevisiónSDKNSActivityparentvschild sihuecoswallconpocaCPU.

## 24/10: regresión pública1.6 activa con cronómetros completos

Solentregóinstrumentaciónopt-inMONITOR_V18_CHILD_STAGE_TIMING=1 enOutputReceiver/receiver_main. FlagOFFsinhelper/ring/nuevasllamadasthread_time. FlagON wall/threadCPUdepump_global,pump,gap,events,tick/collect/flush,wav_callback/wav_service yread/decode/send/ack/generate,bytesread,RID/kind. Ring3s<=1024, sóloUNDERRUNadjuntaevents/active;progresonormalmáximos.46testsPASS;21subsuiteconúltimowav_servicewrapperPASS. IntérpreteGUIactualPython_3_13_DataScience3.13tienethread_time.

Activa sesión72427 `/tmp/v18_public_1600_child_timing.log`: GUIinstaladapública8/1.6Mhold60+Scan/WAV/Synth20,duración85s,archivo `diagnosticos/resultados_v18/gui_public_pcm_1600_20261024.json`. Sinfirmwaredeploy; ReceiverLifecyclecaptura/restaura10sconownerexclusivo. Nootrasconexiones/testsCPU/GUI. Alcerrarverificarsnapshotrestauradoen sessions/. PróximoGUIprivado1.818instrumentadoparalocalizarpausa215msantescambiofuncional.

Astrarevisiónsiguiente candidato: _process_decoder_events ya tiene service_wav porframe SÓLOADC10/1.25M; sepuedeextenderprivadoADC8/88CH1N3488+radio_audio,sinreentrancia/créditosnuevos. Medircosto2kllamadas/s,primeroobservarcronómetros. Noimplementadoaún. V17intacta,públicas1.6M,1.818todavíaprivada/intermitente.

## 24/10: repeticiónfallóACK215ms;Astraplansiguediagnósticoreceptorcompleto

NoQcampañasactivas. GUI111112PASScompleto120,147s/restaurado; repetir111621FAILUNDERRUN~44s/restauradotrue, terceranoarrancó. Parentaudio21728samples,RPC50,6ms,ACK215ms,15CHUNKenvuelo/oldest173ms/nextoffset1775520/accepted1767840. NoRF/DSP>1s niADCdrop. 480remainingenACKUNDERRUNNOsonaudioDMAutilizable(segúnwav::pollguard).

Astra revisión: decodecronómetroexcluye_process_decoder_events→_emit→collect/tick/flush y np.concatenate, noregistragapsentrepumps. NodoQpriorizaACK2halvesvs1cmdPCintercambio,noerrorcrecimientoobvio;TCPNODELAYambosextremosyaexiste. Noatribuirproblema aUSB/Nagle/MCU antesacotarchild.

SubagenteSol_child_timing implementainstrumentaciónopt-inMONITOR_V18_CHILD_STAGE_TIMING=1: wall/threadCPU pumpglobal/events/collect/flush,gapentrepumps,bytesread,RIDsend/ACK;ring<=1024sóloeventoslentos>5msysend/ACK,sinRFarraysnIOflood;anexarringalUNDERRUN,sinIPCextraenprogressnormal. V17intocable. RootnooperaráQhastaagenteentregueparaevitarimportscambiandodurantetest. Sinotrascampañas;39tests previosPASS. Revisiónroot+unitstestantespróximoGUI120 instrumentadoyregresiónpública1.6. Públicasa1.6M,objetivo1.818pendiente.

## 24/10: primerpasecompletohostnuevoPASS;dosrepeticionesactivas

`gui_private_20261024_111112/report.json`:ok/gui_ok/hardware_restoredtrue, RADIO/A0hold120,147s;Scan,WAVplay/progreso/Stop,Synth20play/progreso/Stop,shutdown/workreleasedTODOSPASS,errors[]. SinayudasmacOS/singuardpantalla;ventanaocultapartedeltiempo, noFPSclaim. Hostcambiado(PCMdedi/feedfirst/créditoRFpostDSPyWAV)con39testsPASS. Primeraevidenciacompletanocierrafallointermitente.

Activa secuenciasesiónvertTool: GUIrepeat2 `/tmp/v18_audio_delivery_repeat2.log`, despuésrepeat3 `/tmp/v18_audio_delivery_repeat3.log`;set-eabortafallo,cadacomandorestauraproducciónantespróximo. BatchArena8/88hold120mismaidentidad/host,sinayudas,rootúnicoQ. SinCPUtests/otraGUI/QIO. Alcerrarcontabilizar3passesoreportarfailhonesto,verificarV17hashesypública1.6regresión. Nopromoverhastacalificaciónyrollbackseguro.

## 24/10: DSPdesacoplado,quedaUNDERRUNDAC;ACKtimingactivo

GUI110257 extensiónWAV+DSPcrédito: FAIL RADIOUNDERRUN~83s,peroSINRF/DSP>1s ni faltaaudio: parentbuffer23128samples,buffer_min13945,audio_waits0,feedgap114ms;RPCmáx35,722ms. Bloquessehabíangeneradohasta3317760mientrasACKaccepted3308640: nopresumirculpaGIL;faltaestadioenvío/confirmaciónQ. Ventanaoculta,pintura774;restauracióntrue. GUI105600anteriorRADIO120passperoWAVfalló;noaceptacióncompleta.

InstrumentaciónadicionalRemotePcmSource.observe_transport capturatrazascuotadas16de read/decode/send/send_to_ack/generate sobre20ms y máximos;estabaausenteenproxy. snapshotincluyeDACinflightcount/kinds/oldestage/next_offset/accepted/played/free_blocksantesclearUNDERRUN. SinreservascréditosDACni firmwarecambiados.39testspump/spawn/receiver/PCM/proxy/concurrenciaPASS.

Activa sesión52303 `/tmp/v18_dac_ack_timing.log`:GUI120BatchArena8/88,sinmacOSactivity/guardpantalla;rootúnicoQ,restauraciónobligatoria. NootrasGUI/testsCPU/QIO. AlcerrarcompararRPC/ACK/read/decode,retornoscrédito,colaDAC;guardarcierreexactoantesfinal. V17quieta175hashesverificados,públicas1.6M. HostV18tienePCMdedi+feedfirst+créditoIPCpostDSPRADIO ypostbatchWAVBUFFERING/PLAYING;parentDeliveryBudgetintacto,copiasnodrop.

## 24/10: RADIO120PASS, problemaWAVposterior;desacopleaudioWAVenprueba

`gui_private_20261024_105600` créditoretornoDSP RADIO: RADIO/A0hold120,301s PASS,Stop/ScanPASS,PCMroundtripmáx14,853ms;WINDOWocultapintura862,noFPSclaim. EnsayocompletoFAILdespuésenWAV: DSPGUIRF>1s, WAVcomienzayavanzaperofallastop/Synth. Qrestauradotrue. Nocontarcomopasecompleto.

ExtensiónV18: _audio_delivery_active desdeWAVstatus BUFFERING/PLAYING; _emit_batch_readydevuelvecreditIPCantesGUItambiénparaWAV/Synth, trasDSPsiexiste; independent ydelivery_pressureusaneseestado, presupuestoDeliveryBudgetNOcambia. EstadoIDLE/DONE/UNDERRUN/FAULTconservacréditoGUIhabitual. Copiascompletasretenidas/retornounaúnicaveztesteadopara6estados.38teststiming/proxy/pump/spawn/receiver/concurrenciaPASS. No cambiobuffersDAC/créditosDAC/firmware/tasaspúblicas.

Activa sesión83604 `/tmp/v18_audio_delivery_credit.log`: GUIcompleta120BatchArenaADC8/88,sinmacOSactivity/singuardpantalla,rootúnicoQ. NootrasGUI/testsCPU/QIO,restauraciónobligatoria. RevisarRADIO120yWAVStop/FM20/cierreTODOSantescontarPASS. Siéxitonecesitarepeticionesindependientes yregresiónpública1.6. V17quieta,públicas1.6M.

## 24/10: desacople créditoRF/DSP versus GUI en prueba

GUI105006 publishfirst+PCMdedi todavíaFAILUNDERRUN/DSP>1s,restauradotrue. RPCmáx48,96ms,sourcefeedgap394ms/audio_waits137,ventanaoculta. Cadenaencontrada: ReceiverProcessretainedmax4 condicionaenvíodeRF,ycréditos sólo se devolvíanenbatch_consumedGUIaunqueDSPyacerrado. AsíGUIbloqueaentregaaudioindirectamente.

CambioV18adicional: _processed consettings.radio_enableddevuelveúnicocréditoIPCdeesa copiaRFdespuésfeedDSP yantesemitbatchGUI. BatchcompletoSIGUEenDeliveryBudgetycontadorpending_batcheshastaconsumoGUI;presupuestos1s/1.6Msamples/64MB/256entriesintactos,nodescartadatos. _release_ipc_creditbajobatchlockeliminaidunavez;GUIconsume no duplica. SinRADIO devolucióndespuésGUIcomoantes. ACKFIFO/DSPbarrierintactos.37testsPASSincluyendodobleliberación/retencióncompleta/normal,sourcesafety,spawnPCM. V17quieta.

Activa sesión28485 `/tmp/v18_pcm_dsp_credit.log`:GUI120BatchArenaADC8/88,sinayudasmacOS/guardpantalla,rootúnicoQ,restauraciónobligatoria. SinotrosQIO/testsCPU. Revisarhold,DSPpendiente,parentGUIbudget,PCMstageyexposición. SiPASSrepetirparaestabilidadyregresión1.6;nohabilitarFSnuevaantesaceptación. Públicas1.6M.

## 24/10: publicación de audio antes del detector en prueba

CanalPCMdedicado104403conNSActivityuser fallóUNDERRUN/DSPpendiente>1s,restauradotrue. RPCmáx23,834ms,request_to_parent11,945ms,render1,271ms: actividadtemporalNOresolvió. feedgap312,94ms/loopobserve109,61ms encolamientrasresultadoDSPyaestabapresente;audio_waits54,parentbuffer4454samples. Nopromover1.818.

CambioV18adicionalacotado: OutputWorker._feed_radio_output publica source.feed_result(result) ANTESde source.observe_input(CH1). Evitaretrasarlotedemoduladoporcorrpasiva;guardpositivomantienevaciado/corte yvalidacionesstalesessioncontinúan. Testpauseguardverificanuevoaudioaccesibleypositivoimpidebloquessiguientes.36tests timing/pump/spawn/receiver/proxy/concurrenciaPASS. No firmware/buffers/créditos/tasasmodificados.

Activa sesión49077 `/tmp/v18_pcm_publish_first.log`: GUI120BatchArenaADC8/88,sinNSActivity/singuardpantalla. RootúnicoQ, nootrasconexiones/testsCPU,restauraciónobligatoria. Revisarhold,UNDERRUN,PCMstage_max,pendingDSPyexposiciónpaint. Sólo1pase noaceptación. V17quieta/públicas1.6M.

## 24/10: PCMlatenciamejoró; sigue atrasoDSP, comparaciónactividadmacOSactiva

`gui_private_20261024_103926`:canalPCMdediFAIL UNDERRUN/DSPRF>1s,restauradotrue;ventanaocultamayoríacorrida(paint216). RPCroundtripmáx25,147ms,request_to_parent22,157ms vs302msanterior,executor11,18/render3,85/reply15,26ms. Noatribuircomparacióncausalequivalentealrender:exposicióndistinta. Audio_waits219,parentbuffer3827samples,feedgap307,76ms; fuenteagotándoseporDSP,reservassinmodificar. Campaña67586cerró.

Activa GUI120 `/tmp/v18_pcm_dedicated_activity.log` (--macos-activity user,singuarddisplay),BatchArenaADC8/88,mismochannel. ActividadsóloarnéstemporalnoajustesOS, terminaalcerrar. RootúnicoQ;nootraGUI/testsCPU. Restauraciónobligatoria. SiPASS noatribuicausaúnicapor1comparación;faltaabajoDSP/segundoplano. TodavíanoNSActivityproductivo, públicasa1.6M,V17quieta. Registrarresultados yestadoexactoantescerrarturno.

## 24/10: canal PCM dedicado en validación física

Medición `gui_private_20261024_102904` reprodujoUNDERRUN alfinal(~113s):request_to_parentmáx302,066ms,executor_wait5,793ms,render14,706ms,reply_to_child7,196ms. Parentbuffer13326samples ennotificación0,78msdespués,lockwait0,0227ms. RFpendiente>1s alfinal,paintpierdeexposiciónúltimossegundos;noatribuircausaúnicaOS/GILsinprobar. Producciónrestauradatrue.

CambioV18acotado: ReceiverProcess.pcm_requestsQueue2 separada deeventsRF/controlQueue32; PcmRequestPump enotrothread atiendesólopcm_request ysubmitPCMexecutororiginal. ACK/muestrasmantienenFIFOoriginal ycréditos; noreservas/tasas/firmwarecambiados. Pumpparado/joinantescerrarbackend/executor;metadatoslatenciadisponiblesenprogresonormalsinIPCeventosnuevos. Tests35casos:34PASS+1errorfakeWAVsinstate corregidoguard;11proxyrepetidosPASS;spawnPCMsinconsumirRF yFIFOACKpreservadoPASS. 175V17hashesiguales.

Activa sesión67586 `/tmp/v18_pcm_dedicated_channel.log`: GUI120BatchArenaADC8/88 RADIO/A0/Scan/WAV/Synth20,sinayudasmacOS/guardpantalla. RootúnicoQ, sinCPUtests/otraGUI/IOQ. Restauraciónobligatoria. Revisarstage_max_msdelrpcenradio_a0_diagnostics.pcm_transport durantehold/UNDERRUN ycomparar302msbaseline. No declararresuelto por1pase;si mejora necesitarepeticiones independientes y1.6regresión. Públicas1.6M,V17quieta.

## 24/10: diagnóstico PCM por etapas activo

Instrumentación V18: pcm_request marca parent_received_at aldesencolar, productor marca render_started/finished,childaccept conserva máximos request_to_parent/executor_wait/render/reply_to_child yúltimarespuesta(4números),expuestosensnapshotUNDERRUN. Mismo relojmonotónicoentreprocesosmacOS;metadatosopcionalesinválidosnoalteranaceptaciónPCM;respuestasstalenocontaminanmedición. Ningúncambioreservas/créditos/tasas/firmware.15timing/proxy+16receiver/concurrenciaPASS;175V17hashesiguales.

Activa GUI120 `/tmp/v18_pcm_stage_timing.log` (ver sesión tool), BatchArenaADC8/88,sinayudasmacOS/guardpantalla,rootúnicoQ,restauraciónobligatoria. NoejecutarCPUtests/otraGUI/IOQdurantecampaña. Alcerrar: diagnósticoetapasdelRPCypaint;siUNDERRUN sourceparentavailableesmedidaposteriornotexactmomentchildfailure. No declararaceptaciónporcorridaúnica. Últimofallo100913restauradoconfirmado, producciónpública1.6M,V17intocable.

## 24/10: retomado; BatchArena GUI reproduce UNDERRUN y producción restaurada

No campañas activas. Recuperación de restauración previa completada: `diagnosticos/resultados_v18/resume_restore_20261024_100801/report.json`, identidad/CPU/config/relayexactos,10,026s sinpérdidas. V17 175hashesiguales.

GUIArena `gui_private_20261024_100913/report.json`: FAIL RADIOstate4/reason2 UNDERRUN tras~68sreproducción; hardware_restoredtrue. ADCrelayvalidpairs136122016,dropped0, sinintegrityfailure. Secuencia set-e42789cerró1;GUI2/3noarrancaron. No llamaraceptado combinado ni publicar1.818. Informe `diagnosis_summary.json` acotaevidencia.

Telemetría: RPCroundtripmáx355,43ms; DSPfeedgap1118,58ms; PCMchunkgap412,09ms; loopobserve373,67ms; sourcelockwait0,0167ms. Alobservarfalloenchild, RPCpending97ms/cache0; parentnotificación~905msdespués con16380samplesdisponibles. Esareservaesposterior: NOpruebaaudioexactoeninstantefallo. Rendermax378ms/heartbeat927ms. Siguientefoco: distinguircolas/eventosPCM yretardoproceso/GIL/OS; no aumentarreservasniquitarloopguard porintuición. DatosdeltransporteADCaislado60+3×120PASS cola2/margen20,3% siguen válidos, aceptacióncombinadaArena no.

Pendientes: instrumentarrequestchild→recepciónparent→inicio/finrender→acceptchildparaubicarlatencia; repetircasoconmediciónacotada; luegoGUI3×120 yrollbackprivado/implementaciónproduction. Soldejótools/prepare_q_v18.pyenginecerradosinadapter, rehearsalmismaapp ytests; Astrarevisóyexigióroundtrippermisosantesmutar(yaescrito,noejecutado). Nada deproduccióndesplegado, públicas1.6M. V17intocable; usuarioautorizóavancessinOKrutinario.

## 24/10: producción recuperada y GUI BatchArena retomada

Restauracióninterrumpida cerrada por `diagnosticos/resultados_v18/resume_restore_20261024_100801/report.json`: hardware_restoredtrue, identidad/relay/config/CPUiguales,10,026scontinuos313344muestras,dropped0/fatal0,sinerrores. 175hashesV17iguales. Informeaislado3×120originalpermanececomoestabaparapreservartraza; surecuperaciónfinalreferenciaesteinforme.

Activa nuevaserieGUI3×120 secuencial (ver sesión tool): `/tmp/v18_batcharena_resume_gui1.log`,gui2.log,gui3.log. BatchArenaADC8/88N3488;sinayudasactividad/pantalla,rootúnicoQ. Set-eabortasi falla;cadaGUIrestauraproducciónantespróxima. Nootrasconexiones/testsCPU. Revisarexposición/paintyrestauraciónantescontarPASS. DespuéspreservarparejaArena,testsrehearsalpermisosroundtripyensayomismaappprivada;promociónproductivapendiente,nohabilitarbackendincompleto. Usuario pidióretomar yautorizóavanceautónomo. V17intocable.

## Retomado 24/10: cerrar restauración interrumpida antes de GUI final

No quedaron procesos locales de campaña activos. BatchArena aislado3×120 `resultados/20261023_231721/report.json` completó mediciones PASS (cola2/8, márgenes20,319/20,378/20,298%) pero el journal quedó en rollback_start_original_app intent, sin restauración final. No interpretar su ok provisional como aceptación completa. Aislado60 `231418` PASS/restaurado. GUIArena1/2/3 no arrancaron (logs inexistentes).

Inspección Q exclusiva: ScopeV18 y todasprivadasdetenidas; relayoriginal conservado como serialmonitor-usb-stream-v18-saved-acafac0bb8, sinlectoresTCP. Activa sesión41650 `/tmp/v18_resume_restore.log`, reconstruyeHardware.restore desdeidentidad/inspect/snapshotoriginal guardados y renombra/arranca relayoriginal trasarrancarScopeV18; exige10srecovery+hash/CPU/configexactos. No tocarV17. Tras cerrar: registrarrestauraciónrecuperaciónaparte, verificar175hashesV17, retomarGUIBatchArena3×120 sinayudas. Luego rehearsalexactomismaapp ypromociónV18seguropendientes.

## BatchArena: transiciones15/15 PASS; calificación final secuencial activa

`experimentos/fs_max_v18/resultados/transitions_20261023_230035_900025/report.json`: ok true,15etapas sinreset PASS yrestauracióntrue. Artefactos exactos ELF/map/bin guardados en artifacts/. ELF muestra acquisition::storage tamaño0x28060=163936sincrecer y output_worker prólogo36registros+52locals=88bytes, array2kstackeliminado (no cota totalcallees). StaticassertABIobjetivopasó. CLIappstart sólo--verbose,sinskipbuild, help/layoutcacheguardados.

Activa sesión3021, shell set-e: regresión9máximos15s `/tmp/v18_batcharena_regression.log`; aislado60 `/tmp/v18_batcharena_60.log`; aislado3×120 `/tmp/v18_batcharena_3x120.log`; GUI120trescorridas `/tmp/v18_batcharena_gui1.log`,gui2.log,gui3.log. CadacomandoconrootúnicoQ yrestauraciónconfirmadaantespróximo, abortaantefallo. No otrasconexiones/cputests/compilaciones fueraarnés. GUI sin ayudas deactividad/pantalla: verificarpaint/exposiciónrealeninformes. Seguirhasta cierrey revisaridentidad/restauración.

Sol prepara tools/prepare_q_v18.py engineinyectable/tests sinbackendhardwarehasta demostrarrollbackmismaappprivada: fuente+cachecompleta+ELF/BIN/metadata yverificaciónhashtrasstart quepuedecompilar. No tocarhelperscompartidosV17; no activardespliegueincompleto. Userautorizóavanzarsininput. V17intacta yselectorpúblico todavía1.6M.

## BatchArena: transiciones sin reset activas; BatchStack calificado y respaldado

BatchStack cerró aislado60 (224749) y3×120 (225051): PASS cola2/8, márgenes20,34%;20,52/20,31/20,43%, restauracionestrue. GUI3×120 sin ayudas macOS/guardpantalla PASS223316/223814/224307. Matriz9máximos15s PASS205425. Pareja binarios/host/Q/hash preservada en `respaldos/parejas/v18_batchstack_20261023`. No promover aún: Astra señaló presiónstack2k y transicionespersistentes sin cubrir.

Mejora final preferida por Astra: BatchArena copia BatchNative, agrega dosSampleFrame alFINAL de DualMemory, sin BSSglobal/stackextra. Dual135616<Single/Memory163840; offsetsADC/timestamps/muestrasintactos. Staticasserttamañoalineaciónoffsets. frame_slot dual usa storage.memory.dual.spi_scratch; placementnew/drainpreservados. Generador/testsdeSol.14testsgeometría/transición +14runner/journal +contratosownership/relay/APPLIED+data ydecodetodoskindASan sobreheadersBatchArenaPASS.

Activa sesión8684, `/tmp/v18_batcharena_transitions.log`: appprivadaseparadaScope V18 Rate Probe BatchArena,3ciclos continuos WordCH1→dual8→normal14→dual10→WordCH1,75smedidos,sinresetporstage. RootúnicoQ;sinotrasconexiones/testsCPU. Restauraciónobligatoria. Si pasa: matrizregresiónycalificación8aislado60+3×120 yGUI3×120 sobrebinarioArena (noreutilizarPASSStack), luegopreservarparejaprevia e incorporacióntransaccionaldedicadaScopeV18.

No tocar herramientascompartidasV17 prepare_q/usb_stream. tools/prepare_q_v18.py dedicado pendiente para rollbackfuentes+binario+relay (reiniciar no bastasi fuenteproductionreemplazada). PrepararQGUIseguirdeshabilitado hastaaceptación. V17intocable175hashesverificados, públicasaún1.6M. Userautorizócontinuarhastaobjetivosininput.

## BatchStack: dos GUI120 sin ayudas PASS; secuencia final activa

GUI223316 y223814 PASS, holds120,206/120,124s, Scan/resintonía/WAV/Synth20/cierre, sin errores, restauradas. Sin ayudas macOS/guardpantalla. Matriz9máximos públicos PASS15s.

Activa secuencia shell (sesión ver tool siguiente): terceraGUI120 `/tmp/v18_batchstack_gui_stock_repeat3.log`, después aislado60 `/tmp/v18_batchstack_60.log`, después aislado3×120 `/tmp/v18_batchstack_3x120.log`. `set -e`: aborta si falla cualquiera. Cada comando restaura/valida producción antes del siguiente. Root únicoQ, sin otras conexiones/testsCPU. Al cerrar revisar informes y restauraciones, preservar pareja BatchStack y consolidar aceptación antes de integración. BinarioBatchFast distinto ya respaldado; no transferir su calificación aislada sin repetir. V17 intacta, públicas sin cambios.

## BatchStack GUI120 sin ayudas PASS; segunda repetición activa

`diagnosticos/resultados_v18/gui_private_20261023_223316/report.json`: ok/gui_ok/hardware_restored true. RADIO/A0 hold120,206s, Scan/resintonía/WAV/Synth20 y cierre PASS, errors[], paint3812. Sin --macos-activity ni --keep-display-awake. Nueve máximos públicos CH1/dual15s PASS antes en regression205425.

Activa sesión23014, log `/tmp/v18_batchstack_gui_stock_repeat2.log`: segundaGUI120 independiente mismas condiciones sin ayudas. Root únicoQ, no otras conexiones/testsCPU, restauración obligatoria. Después repetir terceraGUI120 y aislado60+3×120 en BatchStack (BatchFast ya los tiene pero binario difiere), preservar pareja y considerar integración V18. V17 siempre intacta; no declarar listo selector público aún.

## BatchStack: nueve máximos públicos PASS y restauración verificada

`experimentos/fs_max_v18/resultados/regression_20261023_205425/report.json`: nueve perfiles máximos públicos nativos CH1/dual (8/10/12/14 y16dual),15s cada uno, todos PASS, restauración true. BatchStack permite pipeline dual con scratch en stack permanente4096 del trabajador; BatchNative con BSS extra no arrancó en dos intentos restaurados. BatchFast CH1 permanece intacto y respaldado.

Próximo: GUI combinada BatchStack ADC8/88 durante120s sin --macos-activity ni --keep-display-awake para aproximar aplicación normal; root único Q. No otras conexiones ni tests CPU durante campaña. V17 intacta, tasas públicas sin cambios.

## BatchStack activo: buffers duales sin aumento de BSS

BatchNative repitió timeout READY antes de adquirir (`regression_20261023_205127`), restauración true. App logs no muestran causa MCU. No atribuir aún fallo al tamaño estático, sólo hipótesis. Regresión inicial204039 mostró pérdida real dual8 con BatchFast, mientras CH1 pasó.

Nueva app separada BatchStack, fuentes `prepare_batchstack.py` y `batchstack/`: misma lógica de pipeline dual que BatchNative, pero dos frames dedicados viven en el stack permanente de output_worker (1984 bytes del stack existente4096), puntero publicado antes del bucle; sin nuevo arena BSS y sin timestamp DMA prestado. El worker nunca retorna. Validación ADC/clock/ownership trasDMA intactos. 18 tests runner/journal/batch2 PASS antes campaña.

Activa sesión48163, log `/tmp/v18_batchstack_regression.log`: máximos nativos públicos CH1/dual,15s cada uno, raíz único Q; no otras conexiones/tests CPU. Restaurar al cerrar y revisar READY, integridad y alcance. Sesión63800 finalizada y producción restaurada antes de nueva campaña. Usuario autorizó autonomía; V17 intocable.

## BatchNative: primer intento sin READY; repetición idéntica activa

`regression_20261023_204518`: compiló e importó app separada, primer arranque sin READY, timeout del relay antes de medir. Restauración producción true. `candidate_app.log` sólo informa inicio/cierre Python; no determina causa MCU ni permite atribuirlo al pipeline. No hubo datos de adquisición.

Activa sesión63800, `/tmp/v18_batchnative_regression_repeat.log`: repetición independiente con mismas fuentes/app, sin forzar adopción ni editar fuente instalada. Root único Q. Mantener exclusividad, no tests CPU; verificar restauración al cerrar. Sesión71504 ya cerró. Si vuelve a faltar READY, investigar límites/carga RAM y logs MCU antes de otros cambios. BatchFast CH1 sigue respaldado/calificado privado, públicas intactas.

## BatchFast preservado; BatchNative en regresión

Candidato CH1 1,818181 MS/s preservado con binarios firmware/relay y fuentes host/Q en `respaldos/parejas/v18_batchfast_20261023/manifest.json`; hashes exactos del candidato verificados. Evidencia consolidada: `experimentos/fs_max_v18/resultados/batchfast_acceptance_20261023.json`. Aislado 60+3×120 y GUI 3×120 PASS; pública sin cambios.

Regresión BatchFast `regression_20261023_204039`: CH1 8/1,6M PASS; dual8/632411 FAIL por dropped1 con CRC correcto, restauración confirmada. No promover todo el transporte. Ruta dual era serial: esperaba cada frame_sent y dejaba media transferencia agrupada vacía. Hipótesis requiere prueba física, no declarar causa única.

Nueva app separada BatchNative, generada por `prepare_batchnative.py`: sólo extiende pipeline a perfiles nativos duales, con dos SampleFrame propios (+1984 bytes estáticos), sin usar su timestamp DMA; no cambia validación ADC, clocks ni reglas de devolución tras DMA. BatchFast intacto. Registro explícito en runner/journal. 22 tests de transporte PASS antes campaña.

Activa sesión71504: `/tmp/v18_batchnative_regression.log`, `regress_batchfast.py --run --recipe batchnative --seconds 15`. Root único Q, sin tests CPU ni conexiones simultáneas, restauración obligatoria. Seguir hasta cerrar campaña, registrar resultado. Luego prueba combinada sin ayudas de actividad del arnés antes de incorporación. V17 congelada (175 hashes iguales).

## BatchFast: calificación privada ADC8 completa; regresión de perfiles en curso

ADC8/88 = 1,818181 MS/s: aislado 60 s + tres corridas independientes de 120 s PASS, cola pico 2/8 y margen medio 20,27–20,38 %. Tres GUI combinadas independientes con RADIO/A0 durante 120 s, Scan, resintonía, WAV, Synth20 y cierre también PASS. Informes GUI: `gui_private_20261023_201315`, `202710` y `203208`; producción restaurada y verificada en los tres. No hay campaña anterior activa.

Las GUI se midieron con actividad macOS user y guardia temporal de pantalla, CH1+RADIO y cadencia 16 ms; pintura efectiva mínima por intervalo 14,23–17,17 FPS. No es una medición de 60 FPS ni aceptación analógica. Las tasas públicas siguen sin cambios.

Activa sesión 79374: `experimentos/fs_max_v18/regress_batchfast.py --run --seconds 15`, log `/tmp/v18_batchfast_regression.log`. Recorre máximos nativos públicos CH1/dual de 8/10/12/14/16 con BatchFast antes de promover su transporte, con restauración obligatoria y root como único dueño del Q. No ejecutar tests CPU ni otras conexiones durante la campaña. 27 tests de transporte/PCM/concurrencia PASS; 175 fuentes congeladas V17 sin diferencias. Usuario ausente: continuar autónomo sin pedir OK.

## ADC8 BatchFast: aislado60+3×120 PASS con holgura; segunda GUI120 activa

`experimentos/fs_max_v18/resultados/20261023_201814/report.json`: tres120sindependientesPASS, cola2/8 enlas tres, márgenes20,2745/20,3824/20,3381%,sinpérdidas,restauraciónconfirmada. Sondeo60s194020PASS20,37%cola2. Aceptacióntransporteaislado yholguraPASS.

GUIcombinada120s201315PASSconRADIO/A0/Scan/retune/WAV/Synth20,restoretrue. Antes hubo fallosUNDERRUN ynohay que borrarlos ni confundirunalternancia concausaentendida.

Activa sesión44023, log `/tmp/gui8_batchfast_120_repeat2.log`: segunda repeticiónindependienteGUIhold120mismocandidato/host, user+guardpantalla. RootúnicoQ;sinotrasconexiones/testsCPU. Restituirproducciónyverificaralfin. Si pasa, completar3ªGUI120 paraevidenciasostenida; aceptaciónanalógicaaúnpendiente yno tasanueva pública.

Usuarioautorizó avanzar autónomo hasta lograr, V17siemprequieta. No preguntarOKrutinario. FixlockRADIO ytelemetríaPCM enV18;firmwareexperimentalBatchFast contieneCRCrápidorelay,WordPing,SPI16,batch2ydecodeúnico; ninguna reducción deventana/canales/buffers.

## BatchFast: GUI combinada 120 s PASS; calificación aislada activa

`diagnosticos/resultados_v18/gui_private_20261023_201315/report.json`: `ok=true`, RADIO/A0 120,164 s, Scan, retune, WAV, Synth20 y cierre PASS. Sin errores, worker liberado, producción restaurada. Host con fix de correlación fuera del lock y nueva instrumentación PCM; no se cambiaron reservas ni cadencia. El fallo combinado anterior sigue siendo evidencia de intermitencia: una corrida aprobada no basta para promoción.

Campaña activa: sesión77347, `/tmp/fs8_batchfast_3x120.log`, recipe batchfast, ADC8/88=1,818181 MS/s, 120 s ×3 con reinicios independientes. Root único Q; no otras conexiones, compilaciones ni pruebas CPU. Restauración obligatoria al terminar.

Instrumentación PCM y arnés: 16 tests receiver/concurrencia +13 timing/outputproxy PASS. La primera corrida200256 quedó esperando por un bug del arnés al leer un OutputWorker Qt eliminado; receptor hijo ya había salido, se capturó sample y se terminó sóloGUI para permitirrestore, confirmado. Corregido: guardar diagnóstico al notificarUNDERRUN y no leerworker trasdelete. Corrida200920 aprobó todasetapas60s pero informe invalidado por ese error deguardado;restaurada. Nuevaguardaprogresocada5s ycoordinadorwaitconlímite. No contar intentosinvalidos comoaceptacióncompleta.

Después: revisar tres resultados/cola/margen y restauración; repetir GUI120 al menos otra vez antes de considerar incorporación. V17 congelada y tasas públicas sin cambios. Continuar autónomo como pidióusuario.

## Diagnóstico PCM activo, sin cambios de reserva

Sesión44117, log `/tmp/gui8_pcm_timing.log`: batchfast ADC8/88 RADIO/A0hold60+Scan/WAV/Synth20, actividaduser+guardpantalla. RootúnicoQ;sinotrasconexiones/testsCPU;restauraciónobligatoria.

InstrumentaciónV18: RemotePcmSource marca requested_at yroundtripmáximo; snapshotenstate4incluyepending/edad/cache. Parentregistra pcm_request_to_render, reserva/source.diagnostics alnotificarUNDERRUN, conservadoenworker.last_pcm_underrun yherramientasmoke.pcm_underrun. Tiemposchildobserved yparentnotificationseparados. No cambiosdebuffers/créditos/cadencia.16testsreceiver/concurrencia y13timing/outputproxyPASS.

Batchfastaislado60sPASSmargen20,37%cola2;combinadoanteriorUNDERRUNsinrechazoADC. El objetivoes identificar siesRPCpendienteconaudioenpadre, faltaDSP oausenciacréd/commands. Noatribuircausaantesdelsnapshot. V17quieta,tasaspúblicasintactas.

## Combinación BatchFast medida; queda UNDERRUN de audio

Sin campañas activas. BatchFast transporteaislado `resultados/20261023_194020/report.json`:60sPASS aADC8/88=1,818181MS/s,cola2/8,margen20,3719%,restauraciónconfirmada. CombinaCRCrápidorelay+WordPing+SPI16+batch2+decodeúnicoportipo. No introducir variantesdescartadas sinmedida. No habilitartasapública.

GUI120 `diagnosticos/resultados_v18/gui_private_20261023_194632/report.json`:FAIL state4/reason2 UNDERRUNaudio a~9,95s; nointegrityfailure ni droppedADC enrelaylog. Producción restauradaconfirmada. RADIOA0arrancó8,138s con14400samplesDAC; a9,941s quedaban6240samples, y9,954sUNDERRUNcon480samplesguard. Hostsourcea8,138stenía25080samples: audio disponibleanteriorno pruebaestadoexactofallo. Heartbeatmáx588ms,render169ms. No declararnodoADCsolucionadoporunacorrida corta, perosí mejoramargenaislado.

Siguiente foco: entregaPCM host→hijoreceptor→comandosSPI, retardoRPC/GUI; capturartransportenRemotePcmSource yeventoUNDERRUNenpadreinmediato para sabersi hayaudioreservadoalinstante. Mantenerbatchfast comobaseexperimental ycompararsinreducirventana/canales. No aumentarbuffersporintuición. HostfixlockRADIOya pasó1,6MS/s120s.

Fuentesnuevasprepare_batchfast.py,batchfast/,test_batchfast.py.19testsPASSanteshardwareincluyendocomandos2/4/6/8/10/11/13,CRC/reservadosycadamitad. ErrorcompilaciónArduino193902antesmediciónporprototiposautogeneradoscorregidoadelantandoheaders;restaurado. V17congelada,rootúnicoQ.

## BatchFast combinado: sondeo60 PASS con margen20%; GUI120 activa

`experimentos/fs_max_v18/resultados/20261023_194020/report.json`: ADC8/88=1,818181MS/s60s PASS, dropped0/fatal0, cola pico2/8, margen20,3719%, holguraaisladaPASS, restauraciónconfirmada. Últimocheck59us vsbatch2dobledecode101us son valorespuntuales. CombinaCRCrápido+WordPing+SPI16+batch2+decodificaciónúnica por tipo ydescriptor, sinquitarCRC/camposvalidados. HostconlockfixRADIO.

Primerintento193902 canceló porprototiposautogeneradosArduino antes deadquirir;restaurado. Corregidoheaderdecomandos alprincipiodesketch antesprototipos. 19testslocalesPASSincluyendotodoscomandos2/4/6/8/10/11/13,corrupcióncada mitad/camposreservadosCRCválido yASan/UBSan. No olvidargetgenerator10.

Activa sesión89828, log `/tmp/gui8_batchfast_120.log`: recipebatchfast ADC8/88 RADIO/A0hold120+Scan/WAV/Synth20, user+guardpantallatemporales, canales/ventana/cadencia16mssinreducir. RootúnicoQ,sinotrasconexiones/testsCPU. Capturarelaylogyrestaurarobligatorio. SiGUIpasa, faltan3×120aislado yrepeticionescombinadas/analógicaantespromoción. V17congelada, tasaspúblicasintactas.

## Combinación BatchFast activa: decode único

Usuario pidió combinar mejoras. Candidato batchfast copia batch2: CRCrápidorelay +WordPing +SPI16 +2SCPporintercambio; nuevohelper batch_command.h despachaportipo ydecodificauna sola vez a descriptor tipado. Sevalidan ambasmitadesantesdeprocesar; RequestsWAV apuntanalRXquevivehastafinloop. PreservaCRC yvalidaciones originales,IDecho,ownershipDMA,metadata992. NoaplicarAlignedPing/Spin100/TXClean descartados sinbeneficiomedido. HostfixlockRADIOseguiráactivo.

19testsPASS: todos tipos2/4/6/8/10/11/13,CRCcorruptoen cadamitad,reservadosconCRCválido,ASan/UBSan;batch2contracts yrunner/journal. No cambiosV17 ni tasas públicas.

Campaña activa sesión47099, log `/tmp/fs8_batchfast_60.log`: recipebatchfast ADC8/88=1,818181MS/s60s, appindependienteScope V18 Rate Probe BatchFast. RootúnicoQ;sinotrasconexiones/pruebasCPU. Restauraciónautomáticaobligatoria. Revisarcheck_us/margen/colaantesGUIcombinada.

## Cierre: Batch2 aislado PASS, combinado pierde nodo; optimizar decode duplicado

No campañas activas. Q Scope V18 producción restaurado y verificado en `diagnosticos/resultados_v18/gui_private_20261023_193313/report.json`.

Batch2 aislado `experimentos/fs_max_v18/resultados/20261023_192349/report.json` PASS15s a ADC8/88=1,818181MS/s, cola2/8, margen16,6593%. GUI120 `gui_private_20261023_192909` falló; repetición corta193313 confirmó dropped1/fatal0, CRCcorrecto, cola7/pico8, send454285ticks (~2,839ms) frente1,918ms/nodo. Últimoestado prepare114us/check326us (no promedios). Firmwareagrupado no es solución incorporabletodavía.

Próximo cambio concreto: evitar validación/decodificación duplicada del RXbatch. `valid_batch_command()` decodifica cada mitad y `process_batch_command()` vuelve a repetir valid_ping/decode. Preparar descriptor tipado por mitad (Ping/Wav/Gen/Acq/Control) con petición ya decodificada; validar ambas primero y sólo entonces aplicar enorden. No quitar CRC ni saltarvalidaciones. Usar helper real compilablehost para tests corrupción de cada mitad/ceroaplicaciónparcial y preservaciónechoPING. Appprivada nueva para no sobrescribir fuenteinstalada; revisar tiempocheck/margen antescorridaslargas.

Reintento193200 canceló antesmedición porque descripciónapp local distinta: guardfuentesestrictas funcionó, restaurado. Root conservó descripciónexacta instalada enprepare_batch2 y agregó sólo capturahex alrelay;193313 adoptóappsinreescribir. No cambiar descripciónfuentesdurantecampañas ni forzaradopción.

HostfixlockRADIO a1,6MS/s pasó120,315s+Scan/WAV/Synth20,27tests regresión/concurrenciaPASS. Nueva tasa8sigueprivada. V17congelada. Sol agotócuota trasimplementarbatch2yprimeros4tests;rootcerró24tests yhardware. Plan en docs/PLAN_TRANSPORTE_SPI16_V18.md. No pedirOKrutinario;seguirfoco8.

## Batch2 sondeo PASS; combinado120 activo

`experimentos/fs_max_v18/resultados/20261023_192349/report.json`: batch2 privado ADC8/88=1,818181MS/s pasó15s, cola pico2/8, margen16,6593%, dropped0/fatal0 yrestauraciónconfirmada. Perfil inicial, warmup8/112,target yretorno pasaron. No aceptaciónsostenida por sondeo corto.

Campaña activa sesión65407, log `/tmp/gui8_batch2_120.log`: recipebatch2 ADC8/88 RADIO/A0hold120+Scan/WAV/Synth20. Host con fixlockRADIO validadoen1,6; actividaduser yguardpantalla temporales. MismoscanalesCH1+RADIO yventana/intervalo16ms. RootúnicoQ;nootrasconexiones/testsCPU. Capturar candidate_relay.log/restauraciónobligatoria alfinal.

Batch2 prepara2frames bajoúnicolock, mantiene2CRC/secuencias, comandoPCúltimo, ACKownershiptrasDMAéxito. SiempreSPI16 y1984físicos desdearranque, nohandshakedinámico. Plan yriesgos en docs/PLAN_TRANSPORTE_SPI16_V18.md. V17congelada,tasaspúblicasintactas.

## Batch2: primer sondeo físico activo

Activa sesión58665, log `/tmp/fs8_batch2_15.log`: recipe batch2 ADC8/88=1,818181MS/s,15s, appprivada Scope V18 Rate Probe Batch2. DosSCP992 por intercambio1984 desdearranque SPI16/TSIZE992, sinnegociación dinámica. RootúnicoQ;sinotrasconexiones ni pruebasCPU. Respaldo/restauraciónobligatorios.

Sol agotó cuota despuésdeescribir implementación yprimerbloque4testsPASS;root asumió revisiónycierre. Root corrió24testsPASS (batch2/SPI16/runner/journal/concurrenciaaudio). Helpersrealescompruebanownership,atomicidadvalidadorCRC2ªmitad,wrap yPINGPCúltimo,APPLIED→nuevosdatos. MCU prepara2mitadesbajomismolock, idle si faltaframe; sólo spi40_free se libera trascopia, frame_sent/node_sent trasDMAéxito. RelayvalidabatchcompletoantesTCP. Benchmarkfísicostandalone deshabilitadoenbase_verifier deestaapp; replaylógicoconservado. No afirmarestabilidadporpruebassintéticas.

HostV18 lockfixya validado a1,6MS/s120s+Scan/WAV/Synth20: PASS. SPI16unaSCPcompatiblefísicamenteperoGUIperdiónodo. Batch2buscareducciónmayordeloverheadsinrelojnibuffersADCmásgrandes. V17congelada, tasas públicassin cambios.

## Agrupación en desarrollo; corrección del lock validada en 1,6 MS/s

Sin campaña física activa. Sol está cerrando pruebas offline del prototipo batch2 desde SPI16. App privada constante: dos SCP1 de 992 bytes por intercambio de 1984 bytes desde el arranque, todos los perfiles; no conmutación dinámica. Astra revisó riesgos: PING interno primero, comando PC siempre segundo; no adelantar frame_sent, sólo spi40_free puede liberarse tras copia. Root hará revisión con Astra antes de operar Q. Plan en `docs/PLAN_TRANSPORTE_SPI16_V18.md`.

SPI16 de una trama: sondeo 15 s PASS/restaurado (162948), pero GUI combinada 163519 pierde nodo ADC con CRC correcto. No basta para calificar 1,818 MS/s.

Root corrigió en monitor/v18/radio_output.py la correlación bajo el lock que impedía consumir audio ya disponible. Prueba con correlación real pausada falló antes del cambio y pasó después. Tres pruebas de concurrencia y 24 regresiones PASS, sin editar V17. Se conservan burst8/base y burst16/subclase, créditos, reservas y límites. Diagnósticos separan loop_observe y source_lock_wait.

Validación pública `diagnosticos/resultados_v18/gui_radio_lockfix_1600_20261023.json`: RADIO/A0 120,315 s a 8 bits/1,6 MS/s + Scan, retune, WAV y Synth20 PASS. Sin errores, shutdown confirmado, worker liberado y snapshot restaurado por el backend. Detector max53,28ms, espera lock audio max0,156ms. Esto prueba regresión del fix, no estabilidad de 1,818.

Prioridad sigue ADC8. Esperar cierre de pruebas de Sol, revisar implementación real y sólo entonces sondeo batch2 y restauración. Tasas públicas intactas; V17 congelada.

## SPI16: primer sondeo físico PASS; carga combinada activa

`experimentos/fs_max_v18/resultados/20261023_162948/report.json`: gate1 SPI16, unaSCP992 por intercambio, ADC8/88=1,818181MS/s,15s PASS sinpérdidas. Cola pico3/8, margen15,4128%; corto, no aceptación sostenida. Perfil inicial, warmup8/112, target y retorno a perfilnormal pasaron; producción restaurada e identidad verificada. SPI16 físico conserva bytes/CRC/SCP1 lógicos.

Campaña activa sesión71525, log `/tmp/gui8_spi16_120.log`: recipe spi16, ADC8/88, RADIO/A0 hold120 + Scan + WAV + Synth20. NSActivityuser y guardpantalla temporales; ventana/canales/intervalo16mssinreducir. Root únicoQ; sin otras conexiones ni testsCPU. Capturar candidate_relay.log y restaurar al cierre.

No agrupar2tramas hasta revisar este resultado. Si SPI16solo no basta, planbatch2 revisado en `docs/PLAN_TRANSPORTE_SPI16_V18.md`; no cambiar geometríaantesAPPLIED. Tasas públicas sin cambios; V17 congelada.

## ADC8: primer sondeo SPI16 activo, sin agrupación

Plan revisado por Astra en `docs/PLAN_TRANSPORTE_SPI16_V18.md`. SPI3 no admite batch1984 con DSIZE8/TSIZE1984; alternativa DSIZE16/TSIZE992. Antes de agrupar, Sol preparó app/relay siempre SPI16 con una sola trama lógica de992bytes. MCU DSIZE/CRCSIZE15, TSIZE496, DMA normal2/high4, FIFO0/1. Relay configura y verifica bits16. No cambio lógico deSCP1/CRC/ACK, ni reloj/capacidad de colas.

Astra revisión estática sin bloqueos críticos. Sol cerró17tests locales, incluyendo C++producer→serialización16→relayCestricto→decoderPython, mismatch8/16 y geometría. No tocaronQ. Root leyó controlador `geni_spi`, kernel7.0.0-g122c2c22d838, modaliasunoq-mcu.

Campaña activa sesión4462, log `/tmp/fs8_spi16_gate1_15.log`: recipe spi16 ADC8/88=1,818181MS/s, 15s. App independiente Scope V18 Rate Probe SPI16. Este gate comprueba compatibilidad, no demuestra todavía ahorro material ni habilita tasa pública. Root único Q; sin otros procesos/compilaciones/pruebas CPU durante medición. Restauración automática obligatoria. V17 congelada.

Después del cierre: revisar arranque normal, transición aADC8, datos/CRC y restauración. Si falla, diagnosticar antes debatch2. Si pasa, ampliar compatibilidad/control y recién después implementar negociación de dos tramas. No cambiar geometría física usando simplementeelperfilADC: APPLIEDesbarreraobligatoria.

## Cierre bloque ADC8: causas separadas, AlignedPing descartado

No campañas activas. Q producción ScopeV18 restaurado y verificado; recuperación10,026s/313344samples dropped0/fatal0/continuoustrue. V17 manifiesto175archivos sin diferencias al cierre.

AlignedPing `experimentos/fs_max_v18/resultados/20261023_161220/report.json`: FAIL dropped1 a17,836s, cola8/8, último check23us (WordPing~26us). Mejora mínima, no justifica incorporación. App experimental quedó parada. Conservar evidencia, no promover ni seguir con esta variante.

Resultado del bloque: cierres Q por pérdida real ADC confirmada (CRCcorrecto) en155006/155820; no ráfagaWAV inmediata enring64. Otra corrida160652 falla por UNDERRUNaudio sinrechazoADC. Ventanas64frames mostraron ioctl~278us + READY70–121us y gaps438–482us; no medias globales. Hubo un PASScombinado60s160136, no resuelve intermitencia. TransporteWordPingaislado60+3×120PASS, sinholgura colas5/7/7.

Prioridad sigue8bits. Próximo plan: reducción estructural de overhead por intercambio (preservando CRC, ownershipDMA y barrerasACK), con comparación de tiempos aislado/conA0 y envíoPCM desacoplado deldibujo. No repetir ajustes pequeños que sólo ahorran3us. Faltan aceptaciónGUI/RADIOsostenida, holgura yanalógica; tasa pública8sigue1,6. No tocar V17 ni migrarotrosbitsantesdeeste foco.

Herramientas añadidas: trace8/trace8time (MCUWordPingidéntico, relayinstrumentado), capture candidate_relay.log antesrestore, guardpantalla temporal conpmsetbytes robustos. TestsC verificanringwrap/medias ytestspatróncomparanunaligned+cadabitconCRCválido.

## ADC8: falta audio sin rechazo ADC; medir AlignedPing

GUI trace8time hold120 `gui_private_20261023_160652` FAIL por audio UNDERRUN (state4 reason2), sin rechazoADC en relay; producción restaurada. Resúmenes son ventanas de64frames, no medias de corrida: ioctl~277–280us, READY~70–121us, gap~438–482us antes del fallo. AudioDAC estaba lleno a52,015s; a52,695s sólo108ms y a53s UNDERRUN, heartbeatmax531ms. Fuente seguía conaudio disponible en registros previos. Mantener separado del fallo dropped1 confirmado en155006/155820. No atribuir todo a una única causa ni cambiar prioridadWAV (traza no mostróráfaga).

Candidato AlignedPing: carga AliasWord may_alias sólo si dirección4-alineada y littleendianGCC; fallbackmemcpy conservado. Mismo patrón/CRC/protocolo/reloj/buffers que WordPing. Tests frentealoriginal en4alineaciones y cada bitdepayload conCRCválido PASS;14testsrunner/journalPASS;contratoC/relay/PythonPASS. Hipótesis es reducir carga MCU; no dar por probado ahorro sin medida.

Activa sesión99565, log `/tmp/fs8_alignedping_60.log`: recipe alignedping ADC8/88 60s, app independiente Scope V18 Rate Probe AlignedPing. Root únicoQ;sinotrasconexiones/pruebasCPU. Restauración obligatoria al final. Según check_us/margen decidir conservar o descartar. V17 congelada y tasa pública8sigue1,6.

## ADC8 READY/ioctl: 60 s combinado PASS; repetir120 con resumen

`gui_private_20261023_160136/report.json`: ADC8WordPing/1,818MS/s con trace8time pasó RADIO/A0 60,26s y Scan/WAV/Synth20, restauración confirmada. Sin rechazo no se imprimió el ring, por lo que esa corrida no aportó desglose temporal. No tomar un PASS por solución del fallo intermitente.

Activa sesión40651, log `/tmp/gui8_trace8time_120.log`: mismo recipe trace8time y hold120, user+pantalla despierta. Se agrega resumen de últimos64frames cada10s al log ya existente de progreso, sin cambiar firmware. Test C verifica wrap, mediasREADY/ioctl/gap y recuentos data/audio/chunks PASS. Root únicoQ; sin conexiones/cargas concurrentes, captura logs y restaura al final.

Previa traza155820 mostró déficit de servicio sostenido (~0,5–0,6ms/frame), no ráfagaWAV; no cambiar prioridades sin evidencia. TransporteaisladoWordPing60+3×120PASS, colas5/7/7 sinholgura. GUI intermitente. V17 congelada; ninguna tasa nueva pública.

## ADC8: no ráfaga WAV en la pérdida; separar READY/ioctl

Traza `gui_private_20261023_155820/candidate_relay.log`: pérdida ADC dropped1/fatal0, CRC correcto. Últimas64 tramas mayormente PING→muestras; sólo3 respuestasWAV, sin ráfaga larga. Cola aumenta5→8 durante intervalos sostenidos~0,5–0,6ms, frente a~479,6us por frame necesarios. No cambiar prioridadWAV por esa hipótesis no confirmada. Producción restaurada.

Primera corrida trace8 `gui_private_20261023_155551` canceló antesGUI por UnicodeDecodeError al leerpmset (nombre dispositivo noUTF8);restaurada. Corregido guardando bytes originales y texto errors=replace.

Activa sesión85600, log `/tmp/gui8_trace8time.log`: recipe trace8time, ADC8/88, hold60 RADIO/A0, actividad user+pantalla despierta. MismaMCUWordPing; sólo ringrelay agrega wait_us e io_us ytimestampatpostio. Test C del ring original y timing conwrapPASS;14testsrunner/journalPASS. Captura candidate_relay.log al liberarGUI antesrestore. Root únicoQ,sinotrasconexiones/pruebasCPU. No tasas nuevas/V17quieta.

Próximo leer desgloseREADY/ioctl/resto para elegir cambio con evidencia. TransporteaisladoWordPing60+3×120PASS, combinado siguefallando.

## ADC8: pérdida confirmada bajo RADIO/A0; traza acotada activa

`gui_private_20261023_155006/report.json`: FAIL y producción restaurada. candidate_relay.log conservado. Relay rechaza kind20, CRC recibido/calculado iguales, dropped1/fatal0, cola7/pico8, send_previous580365ticks=3,627ms frente a presupuesto306944ticks=1,918ms. No es protector ni corrupción CRC: el ADC perdió un nodo bajo carga.

Hipótesis a comprobar: prioridad absoluta de wav_replies y recuperación PCM burst8 retienen muestras. Todavía no hay prueba temporal que lo vincule; NO cambiar prioridades antes de la traza.

Activa sesión34377, log `/tmp/gui8_trace8.log`, recipe trace8 ADC8/88 hold60, RADIO/A0+Scan/WAV/Synth, actividad user+pantalla despierta. MCU WordPing idéntico; relay agrega sólo ring64 metadatos, dump al rechazo/host lento. Campos seq/txkind/rxkind/tiempo/index/node/cola/pico/send/dropped. Test C real de wrap70→últimos64 PASS;16 tests runner/journal/spawn PASS. Root único Q; restauración automática y capture candidate_relay.log al final. Sin pruebas CPU ni otras conexiones durante medida.

Siguiente: leer la traza, separar comando WAV vs pausa Linux/transferencia, y sólo entonces ajustar una cosa en candidato aislado. V17 intacta y ninguna tasa pública nueva.

## Comparación protector cerrada: fallo persiste con pantalla despierta

Sin campañas activas. `diagnosticos/resultados_v18/gui_private_20261023_094859/report.json`: ADC8 WordPing/1,818181 MS/s, pantalla16ms, NSActivityuser y caffeinate-du600 verificados en pmset. PreventUserIdleDisplaySleep=1 y UserIsActive=1, assertions del PID27507 con600s. GUI expuesta en todos los registros. Falló “Q cerró el flujo” a~25s; render máximo71ms, heartbeat489ms. Por tanto protector/apagado no son condición necesaria de este fallo; no afirmar que nunca afecten otros casos. Guard liberado, producción restaurada confirmada.

Prioridad vigente: ADC8. Transporte WordPing pasó60+3×120 sin pérdidas, pero carga RADIO/A0 falla. Próxima corrida debe conservar candidate_relay.log antes de restaurar (captura ya agregada al coordinador; instancia094859 aún no la tenía). Se necesita ese motivo de rechazo/cierre para separar pérdidas ADC, interrupciones DAC y relay. Evitar seguir ajustando dibujo sin esa evidencia. V17 congelada y tasas públicas sin cambios.

Comparaciones previas: gui_private093621 fallaRFbudget;094144hold30perfiladoPASS;094620pantalla50msfallaQcerróflujo. Ninguna habilita tasa nueva.

## Hipótesis protector: comparación activa

Usuario pidió comprobar protector/apagado de pantalla. `caffeinate -i` previo sólo impedía sueño del sistema, no pantalla. `pmset -g custom` indica displaysleep10min; lectura IODisplayWrangler CurrentPowerState4 al consultar. Consulta log ScreenSaverEngine/WindowServer no devolvió eventos últimos25min (no descarta causa). No preferencias cambiadas.

GUI WordPing8/88 con pantalla50ms (`gui_private_20261023_094620`) falló “Q cerró el flujo”, restauración confirmada. Render máximo60ms, heartbeat492ms: no explicar todo por dibujo.

Activa sesión22029, log `/tmp/gui8_wordping_display_awake.log`: mismo ADC8/88 y pantalla16ms, RADIO/A0 hold120 + Scan/WAV/Synth20, actividadmacOS user, `--keep-display-awake`. Este flag inicia caffeinate -du -t600 sólo durante GUI y guarda pmset assertions para verificar; lo termina antes de restaurar Q. Sin configuración persistente. Root único Q. Esperar cierre/restauración.

Coordinador ya añade captura candidate_relay.log al adquirir lock de restauración para futuras corridas; la instancia actual arrancó antes de ese agregado. Captura es best effort, nunca impide hw.restore. V17 congelada; no tasa nueva pública. ADC8 transporte aislado WordPing60+3×120 PASS; GUI sigue en diagnóstico.

## ADC8: comparar cadencia de pantalla sin cambiar adquisición

Perfilado `gui_private_20261023_094144/report.json`: hold30 con profiler 1/10 callbacks PASS completo y restaurado. Dump .render.pstats/.render.txt junto al reporte. No prueba sostenida, por ser diagnóstico. El fallo previo gui_private_093621 sigue válido.

Campaña activa sesión91708, log `/tmp/gui8_wordping_render50.log`: WordPing8/88, RADIO/A0 hold120, Scan/WAV/Synth20, actividad macOS user, pantalla diagnóstica50ms. Conserva CH1+RADIO y ventana409091, sin reducir datos. Se compara si la contención del dibujo contribuye; producto sigue a16ms. Restauración automática al final; root único Q, no cargas concurrentes.

Transporte WordPing ya pasó60+3×120, sin holgura por colas5/7/7. No tasas públicas nuevas, V17 intacta. Próximo según comparación: perfilar por componentes con tiempos explícitos si falla; si pasa repetir antes de decidir cadencia adaptativa/producto. No atribuir causa a AppNap ni aceptar GUI por transporte aislado.

## ADC8: transporte aprobado, GUI combinada falla; perfilado activo

WordPing 60+3×120 s transporte aislado PASS, restaurado (`resultados/20261023_092727`). GUI combinada `diagnosticos/resultados_v18/gui_private_20261023_093621/report.json` FALLÓ RF pendiente >1 s y audio faltante; producción restaurada verificada. CH1+RADIO, temporal, sin trigger, ventana 409091 muestras (~225 ms), detalle50, trazoRápido. Render crece 34→71 ms, pico318ms; heartbeat697ms. Snapshot exacto hijo: retenido0,7568s+buffer0,2436s, último crédito hace252ms. No pausa de varios segundos como caso anterior; no culpar AppNap.

Sesión activa78751, log `/tmp/gui8_wordping_profile.log`: mismo ADC8/88, hold30, actividad user, `--profile-render` diagnostica 1 de cada10 callbacks y guarda .render.pstats/.render.txt junto al gui.json. Sin cambios de producto ni reducción de ventana/canales. Root únicoQ, restauración automática obligatoria.

Próximo: revisar perfil, optimizar costo demostrado del dibujo y repetir GUI120 sin profiler. No promover tasa nueva por transporte solo. V17 congelada.

## ADC8 WordPing: 60+3×120 PASS; GUI combinada activa

`experimentos/fs_max_v18/resultados/20261023_092727/report.json`: tres corridas 120 s PASS sin pérdidas, restauración confirmada. Colas 5/7/7 sobre 8, márgenes 15,273/15,118/15,497%. Integridad sostenida PASS, holgura NO. Previo 60 s PASS/restaurado 092057.

Campaña GUI activa sesión 47423, log `/tmp/gui8_wordping_120.log`: ADC8/88=1,818181 MS/s, RADIO/A0 120 s + Scan + WAV + Synth20, actividad macOS `user`. App WordPing independiente y sólo perfil privado exacto en proceso diagnóstico. Tests identidad/spawn/token 8 PASS y bootstrap real WordPing 8/88/N3488 PASS. Root único Q; sin cargas ni conexiones concurrentes. Restauración producción al terminar obligatoria.

No integrar ni publicar por integridad sola. V17 quieta. Primero foco en 8 bits; siguientes acciones según GUI, después margen de cola y aceptación analógica.

## ADC8 WordPing mejora medida; calificación larga activa

WordPing 60 s PASS: `experimentos/fs_max_v18/resultados/20261023_092057/report.json`, restauración confirmada. ADC8/88=1,818181 MS/s, cola pico 6/8, margen medio 15,7146% frente a CRC8 13,0630%. Check PING último estado 26 us frente a 49 us; preparación 10 us en ambos. No holgura por cola.

Campaña activa sesión 59276, log `/tmp/fs8_wordping_3x120.log`: recipe wordping, 120 s, repeats 3, reinicio independiente entre casos; restauración de Scope V18 al final. No otras conexiones, compilaciones ni tests CPU mientras mide. Root único dueño Q. V17 congelada; tasas públicas intactas.

Objetivo primero ADC8; 10/12/14 quedan pendientes. No declarar 1,818 estable hasta cerrar corridas largas y carga GUI/RADIO; aceptación analógica y holgura siguen separadas.

## Foco ADC8: WordPing activo

CRC relay 60 s pasó y restauró (`resultados/20261023_091613/report.json`), pero margen 13,06% y cola 6/8: sin mejora decisiva frente a Full8, no holgura.

Nueva campaña activa sesión 8400, log `/tmp/fs8_wordping_60.log`, recipe `wordping`, ADC8/88 60 s. MCU independiente `Scope V18 Rate Probe WordPing`, sin cambiar protocolo, reloj ni buffers. Cambia verificación completa del patrón PING de cuatro comparaciones byte a una palabra de 32 bits (tabla constante de máscaras; carga memcpy sin alias/unaligned UB). Conserva CRC8 del relay del sondeo anterior. No cambia estado de producción; restauración automática obligatoria.

Validación previa: comparación contra implementación original para extremos de secuencia y cuatro alineaciones; cada bit del payload se altera y se recalcula CRC para probar rechazo por patrón. Todo PASS. Contrato C/relay/Python PASS; 14 tests runner/journal PASS. Benchmark host de valid_ping completo 0,683→0,427 us, no extrapolar a STM32. Evidencia local persistida `resultados/offline_crc_wordping_20261023/`.

Root único Q, no conexiones concurrentes ni pruebas CPU durante medición. V17 congelada, tasas públicas sin cambios.

## Foco ADC8: CRC del relay, campaña activa

Usuario priorizó 8 bits. Sesión 15180, log `/tmp/fs8_crc8_60.log`: recipe `crc8`, 8/88 (1,818181 MS/s), 60 s, root único Q. No otras conexiones ni pruebas CPU. Cierre debe restaurar Scope V18 y verificar identidad/política CPU.

`prepare_crc8.py` copia Full8 y cambia únicamente CRC software por slicing-by-eight portable. MCU idéntico y misma app experimental Full8; relay independiente por hash. Mismo reloj, buffers, protocolo y validaciones. Test diferencial zlib: longitudes 0..4096 con 8 alineaciones y cada bit de trama 988 bytes PASS. Contrato packer C / relay C / decoder Python PASS; 14 tests runner/journal PASS. Benchmark local 4,37× sólo en CRC; no representa aceleración total ni medida en Q. Resultado en `/tmp/crc8_benchmark.json`.

Baseline Full8 anterior: dos 120 s PASS y tercera pierde nodo a 28,3 s con CRC correcto y cola 8/8. No tasa pública nueva, no tocar V17. Según el resultado CRC, decidir repetición larga o descartar; no promover sólo por sondeo de 60 s.

## Cierre del bloque: GUI ADC12 PASS, ADC10 falla y Q restaurado

No hay campaña activa. ADC12/148 con actividad macOS `user` pasó RADIO/A0 120 s, Scan, WAV, Synth20 y cierre; restauración confirmada en `diagnosticos/resultados_v18/gui_private_20261023_090239/report.json`. Se suma al PASS de 60 s anterior.

ADC10/122 falló con “El Q cerró el flujo” antes de completar 120 s (`gui_private_20261023_090743/report.json`). Heartbeat máximo 512 ms, render máximo 126 ms: este fallo no reproduce la pausa GUI de 6,52 s. No atribuirlo a AppNap ni declarar el perfil estable. El cierre GUI informó salida sin confirmar, pero el coordinador sí restauró y verificó producción (`hardware_restored=true`). No quedó Q experimental activo.

Próximo: inspeccionar el cierre de flujo ADC10 bajo carga RADIO/A0 (cola llena ya observada en campaña aislada); seguir calificación ADC14 y optimización estructural ADC8. Actividad macOS continúa sólo en herramientas; tasas públicas sin cambios y V17 intacta.

## 23/10: repetición GUI ADC12 con actividad macOS

ADC12/148 cerró PASS: `diagnosticos/resultados_v18/gui_private_20261023_090239/report.json`, GUI y restauración confirmadas. RADIO/A0 120 s, Scan, WAV y Synth20 con actividad macOS `user`.

Campaña activa siguiente: sesión 88027, log `/tmp/gui10_activity_120.log`, ADC10/122 con la misma matriz de 120 s. Root único dueño del Q; restauración automática al finalizar. No otras conexiones ni pruebas CPU durante la medición.

La primera GUI con actividad explícita pasó 60 s y todas las etapas, restaurada (`gui_private_20261023_025938`). Heartbeat máximo 323 ms frente a 6,52 s en el fallo previo. Es una comparación prometedora, todavía no prueba causal de AppNap. El mecanismo sigue sólo en herramientas diagnósticas.

SPI40/WORD: 10/122 y 12/148 pasaron 60 s + 3×120 s, restaurados. ADC10 llegó a cola 4/4: integridad aprobada, holgura pendiente. ADC12 sí tiene holgura aislada. Falta aceptación combinada y analógica.

Full8/88 (1,818 MS/s) pasó dos corridas de 120 s; la tercera perdió un nodo a los 28,3 s. Restaurado, no promover. ADC14/184 pasó sólo sondeo corto; Word14 preparado sin prueba física. V17 congelada; ninguna tasa nueva pública.

Siguiente: cerrar/restaurar esta repetición, probar GUI ADC10 con actividad, luego calificar ADC14 y continuar el objetivo ADC8. Mantener separados integridad, holgura y aceptación analógica.

## 23/10 02:17: calificando SPI40/WORD10/12 3×120

Campaña física ACTIVA exec7571, resultados/20261023_021652/report.json,
log/tmp/fs_max_v18_spi40_10_12_3x120_20261023.log.10/122 y12/148,120s,
repeats3, seis mediciones con reinicioindependiente;restauraV18 alfinal.
RootúnicoQ. No otras conexiones, compilaciones ni testsCPU mientrasmide.

Previo60s020515PASS ambos:10/122cola3 margen22,17%;12/148cola2 24,41%,
restaurado. TresRADIO120públicas1,6MS/sPASS antesdeexperimentales.
ADC14baseline15s184PASScola3;180PASScola4;176falló,restaurado(015831).
Word14preparado(appindependiente),SPI40/WORDframes496,targets184180176172168;
contratoC/relay/Python5perfilesPASS. Aún nohardwareWord14.

ADC8/1,818base60PASSperoprimera120falló(014040);no califica.Wide8,
Spin100 yTXClean pasaron60perono mejoran margen/cola;descartados. TXClean
020955restauracióntrue,margen11,95%,cola6/8. No cambiarproducciónporéstos.
Full8preparado:872payloadvs864,N3488,8slots,cabeenmismauniónRAM,
appFull8independiente. FALTA contrato ypruebafísica. Objetivo8sigueabierto.

Runner --recipe baseline/spi40_10_12/wide8/spin100/txclean/word14/full8,
repeats1..3;appwhitelist+sourceadoptionexacta;CPU normal/activa yconfigrelay
verificados. Snapshotrunner.py porcampaña. FrameMetrics yaenuso paraevitar
200kdicts retenidos,mismopeso portrama;14testsrunner/journalPASS antesFull8
(correractualizadosalfin). Fallosguardanúltimostatusválido+elapsed/samples.
V17 intacta175hashes. No tasasnuevaspúblicas, noQproducciónalterado.

Despuésdecierre: contratosFull8, medida60sFull8(prioridadobjetivo8), sondeos
Word14, calificaciónsostenida/GUIdeperfilesviables. No acabarconQexperimental
activo sinrestauración. Documentarfallos yholgura separados de integridad.

## 23/10 02:10: candidatos mejorados; TXClean8 en preparación

Objetivo vigente:8/1,8MS/s ysubir10/12/14; avanzar autónomo sin pedirOK.
V17quieta;175hashesúltimaverificaciónintactos. Root únicoQ.

SPI40/WORD10/12: sondeos15s014440 todosPASS/restaurado. Luego60s
020515:10/122=1,311475MS/s PASS cola3 margen22,17%;12/148=1,081081MS/s
PASS cola2 margen24,41%; restauracióntrue. Faltan3×120 yGUI/RADIO.
14baseline015831:184=869565PASS15 cola3 margen23,20%;180PASS15cola4;
176falló. Restaurado. Pendiente60s+3×120 en184.

8/88=1,818base:60PASS cola6/8 margen12,44%; primera120(014040) falló
por dropped1 cola8/8, restaurado. Wide8 (015222)60PASS peromargen4,38%
cola4/4:DESCARTADO. Spin100 (020147)60PASS cola7/8 margen12,09%:no mejora,
DESCARTADO. Ambasrestauradas. No publicar8/1,818 comoestable.

Actualcampañafísica: TXClean8, exec92657, resultado020955,
log/tmp/fs_max_v18_8_txclean_60_20261023.log. AppScopeV18RateProbeTXClean
independiente; sólo cambia TX cache de clean+invalidate a clean en WORD,
RXintacto, framesalineados,mismoRAM. CompilaciónpreviaPASS, prepara relay;
no interferir hasta reportrestorationtrue. ReferenciaST DCACHE oficial revisada.

Runnerahorasoporta --recipe baseline/spi40_10_12/wide8/spin100/txclean,
--repeats1..3, logs por repetición, snapshotrunner.py en nuevascampañas.
CPU normal/activa separados; montajes comparadossinorden. Tests13PASS antes
últimocambio. Se añadió FrameMetrics paraagregarsinretener200kdicts y test
ponderaciónportrama (PENDIENTE ejecutar alfin actualcampaña; noCPUtestsparalelos).
TXClean60actualejecuta todavía runnerprevioalFrameMetrics. Si TXClean mejora,
compararconbaselineusandonuevo agregador antesatribuircachécausalidad.

Próximos: cierreTXClean; test14runner; calificarSPI10/122+12/148 tres120s;
14/184 60+3×120. ADC8 segúncomparaciónTXClean. NooperarQ si restorefalse.
No tasas nuevas incorporadas niGUIhabilitada paraexperimentos todavía.

## 23/10: variantes medidas; comparativo spin100 ADC8 activo

User confirmó objetivo8/1,8 y subir10/12/14, pidió aplicar técnica8a10/12.
Tres RADIO120 deperfilpúblico1,6PASS/restaurado; no másOK entrebloques.

Sondeos SPI40/WORD10/12 (014440) PASS15s/restaurado:10ticks126/124/122
hasta1,311MS/s, cola2/3/3 margen23,68/23,97/21,77%.12ticks148/146
hasta1,096MS/s, colas3/4 márgenes24,15/23,16%. Preferir12/148 paraholgura.
Sondeos14 baseline015831:184 y180PASS15s colas3/4 márgenes23,20/21,85%;
176falló dropped. Restaurado. Preferir14/184=869565S/s.

ADC8/88base60sPASS peroprimera120fallódropped1 cola8/8 (014040),restaurado.
Wide8 (015222)60sPASS pero margen4,38% ycola4/4; DESCARTAR noaporta.
Conserva mismacapacidad27648muestras (4×6912vs8×3456),sinRAMadicional.
Comparativoactivo: spin100 relayesperaREADY100usvs50, mismosMCU/reloj/buffers.
Runner sesiónexec90356, log/tmp/fs_max_v18_8_spin100_60_20261023.log,
reporte experimentos/fs_max_v18/resultados/20261023_020147/report.json.
RootúnicoQ. No interferir, esperarresultado/restauración.

Runner variantes --recipe baseline/spi40_10_12/wide8/spin100; --repeats1..3.
Apps independientes baseline, SPI40 yWide8, spin100usa mismoMCUbaseline y
relay de digestdistinto. Adopciónfuentesexacta, nuncaoverwrite. GuardsCPU
normal/activa separados; montajesordenindependiente;13testsPASS. ContratoC/
relay/Python17formatosbaseline+SPI ywide8PASS. No tasaspúblicasnuevas.
Próximo: calificardatos60s+3×120 de10/122,12/148,14/184 yADC8segúnresultado.
No avanzar aotraoperaciónQ si restauraciónfalse. GUI/RADIO/analógico se
califican separadamente, V17 congelada175archivosintactos.

## 23/10: SPI40/WORD mejora ADC10/12; prueba wide8 activa

Tres RADIO120 de1,6MS/s públicas PASS y restauradas. RunnerCPU normal/activa
corregido y tests13PASS. Montajes se comparan por destino (orden irrelevante).
Recetas separadas baseline, spi40_10_12 ywide8; fuentes Q/adopción exactas.
ADC8/1,818base:60sPASS cola6/8,margen12,44%; primera120falló dropped1
cola8/8 (resultados014040), restaurado. No califica ni sepromueve.
ADC10/126 yADC12/148 base fallaron; cierreV18 verificado.
SPI40/WORD10/12: resultados014440 cinco15sPASS/restauracióntrue:
10/126 cola2 margen23,68%;10/124 cola3 23,97%;10/122 cola3 21,77%;
12/148 cola3 24,15%;12/146 cola4 23,16% (sinholgura). Contratos17formatosPASS.

Ahora Q activo bajo runner sesión exec85464; log
/tmp/fs_max_v18_wide8_60_20261023.log.
Usa appScopeV18RateProbeWide8 independiente,8/88/N6912,4slots misma capacidad
27648muestras que8×3456. Sinmásbuffers, frames en timestampslibres, contratoPASS.
RootúnicoQ; no interferir hasta cierre/restauración. Luego priorizar8segúnresultado,
y calificar10/122 y12/148 (60s+3×120),probar14 aúnpendiente. Usuario pidió
avanzar directo y aplicar técnica8también a10/12. V17 siempre congelada.

## 23/10: tres RADIO120 PASS; sondeo 10/12/14 en curso

Usuario autorizó avanzar directo al objetivo8/1,8 y subir10/12/14 después de
las dos repeticiones restantes. Run2=120,299s yRun3=120,294s PASS sinwatchdog,
Scan/RADIO/A0/WAV/Synth20 yrestauración. Ya son3x120 completas.
Runnerfix: captura normal_cpu_governor/state tras configurar14/40k, restaura
base normal antes de recuperar perfil activo, verifica ambas.10testsPASS.

Campaña física activa: experimentos/fs_max_v18/resultados/20261023_013204/report.json,
proceso exec15450; log /tmp/fs_max_v18_10_12_14_20261023.log. Root único dueño.
Escalera15s:10ticks126/124/122;12ticks148/146;14ticks184/180/176.
No ejecutar nada adicional sobreQ ni testsCPU mientras mide. Runnerrespalda,
usa app ScopeV18RateProbe yrestaura ScopeV18 con10s verificados.
Después: revisar resultados/cierre; calificar finalistas60s+3x120,8ticks88
objetivo1,818MS/s y tasas viablesotrosbits. No incorporar sólo por15s.
V17 congelada siempre.

## 23/10: RADIO120 sin watchdog PASS; Q restaurado

Última prueba: diagnosticos/resultados_v18/gui_pair_v18_radio120_plain_20261023.json.
ADC8/1,6 MS/s, RADIO/A0 40k durante120,241s; Scan, retune, Stop, WAV,
Synth20 y todas las aserciones PASS. Sin watchdog/traza/sampler, timer normal.
Heartbeat máximo483,9ms, callback render máximo38,6ms.
Sesión042136_487996: hardware_restored=true, recuperación10,023s,
313344muestras, dropped0/fatal0, continuidad e identidad ScopeV18 confirmadas.

No hay campaña activa. No se modificó firmware ni V17; hashes175 intactos.
Siguiente: completar otras dos corridas independientes120s sininstrumentación
antes de concluir aceptación sostenida. Causa de fallos intermitentes sigue
abierta; no borrar informes fallidos ni atribuir resolución al watchdog/burst.
Luego revisar baselineCPU normal/activa del runner antes de nuevas tasas.

## Continuación 23/10: dos pases ADC8/1,6 MS/s; fallo intermitente abierto

Se corrigió OutputWorker.run para preservar el failure_snapshot del terminal
que llega sólo durante close, aun con running=False. Evita recaptura idéntica.
11 tests proxy PASS, incluidas dos regresiones. Sólo V18.

Smoke --stall-trace agrega faulthandler nativo: dump de todos los hilos tras
700 ms sin heartbeat Qt, rearmado cada tick; apagado durante restauración.
No cambia prioridades, firmware, cadencia de producto ni buffers.

Dos ensayos físicos consecutivos PASS:
- diagnosticos/resultados_v18/gui_pair_v18_stall_exact_20261023.json
- diagnosticos/resultados_v18/gui_pair_v18_stall_exact_repeat_20261023.json
Ambos ADC8/1,6 MS/s, RADIO/A0 >=60 s, Scan, retune, Stop, WAV, Synth20 y
restauración confirmada; todas las aserciones. Archivos .stacks.txt vacíos:
no se reprodujo la pausa >700 ms. No atribuir causalidad al watchdog ni dar
por resuelto el fallo; mantener evidencia fallida anterior.

No hay campaña activa. V17 congelada verificada nuevamente (175 archivos).
Siguiente bloque: repetición más prolongada sin watchdog (120 s RADIO), y
si reproduce, usar captura exacta para distinguir pausa global/GIL/IPC.
No promover tasas nuevas antes de resolver estabilidad y corregir baseline
CPU normal/activa del runner experimental. Ver docs/VALIDACION_V18.md.

## Pareja V18 activa; V17 congelada · 23/10/2026

El usuario pidió conservar V17 con su pareja del Q y desarrollar todo en V18.
Los 175 archivos de `monitor/v17` y `arduino/v17` coinciden con el manifiesto
congelado. No revertir cambios históricos que ya estaban presentes.

Respaldo completo: `respaldos/parejas/v17_20261023_000325/manifest.json`, ZIP de
fuentes y app Q, firmware/relay binarios e inspecciones con SHA256. El relay V17
ya estaba detenido al descubrir el Q; no se inventó un snapshot ADC. La app V17
se conserva instalada y detenida.

La pareja de trabajo es `monitor/v18` y `arduino/v18`, app Scope V18 en
`/home/arduino/ArduinoApps/scope-v18` y relay `serialmonitor-usb-stream-v18`.
Su firmware parte de la base validada, sin incorporar el candidato de 1,8 MS/s.
Activación: `diagnosticos/resultados_v18/activation_20261023_000458/report.json`.
La GUI verifica identidades V18 y no despliega automáticamente. Launch V18
aparece primero. README conserva la presentación, badges e imágenes.

La nueva pareja presenta fallos de acumulación RF incluso a 14 bits/40 kHz;
no está calificada como estable. Informes fallidos `gui_pair_v18*_20261023.json`
conservados. Se corrigió el cierre tras sobrecarga para completar los eventos de
la lectura; las últimas pruebas confirmaron restauración. Snapshot inicial
espera transporte confirmado; progreso WAV a 20 Hz, sin omitir ACK internos.

Astra verificó que la pila GUI antigua se guardaba tras la restauración, unos
10 s después: no demuestra bloqueo en NumPy. Ahora el terminal incluye el
primer fallo exacto del receptor, antes de limpiar buffers. Ocho tests del
receptor y dos de la traza pasaron; batería offline previa: 162 pruebas PASS.

`gui_pair_v18_sampled_20261023.json`: RF pendiente >1 s; cuatro lotes retenidos
(0,1024 s), 36.106 muestras acumuladas, último crédito ~1 s antes; restauración
confirmada. `gui_pair_v18_flow_20261023.json`: UNDERRUN RADIO; traza por ID
mide hasta 213 ms entre enqueue y recepción host, DSP <9 ms. Ese intento usó
sample sobre el receptor y puede estar perturbado. Se repite sin sampler en
`gui_pair_v18_flow_only_20261023.json`: UNDERRUN también sin sampler.
La siguiente corrida `gui_pair_v18_pcm_flow_20261023.json` pasó los 50 s
completos, Scan/RADIO/A0/WAV/FM20 y restauración; fallo intermitente aún abierto.
Astra identificó que RemotePcmSource sólo permite un bloque por ronda IPC.
Sol implementa agrupación de hasta ocho bloques autorizados sólo RADIO,
sin ampliar reserva DAC ni alterar Synth/WAV. Astra aprobó revisión; 167
tests backend y 21 GUI PASS. Burst40k físico50s PASS/restaurado.
Burst1600 sin traza falló ~40,9 s: UNDERRUN, gap PCM706ms y luego RFbudget
durante cierre; restaurado. No completó hold60 ni WAV/FM posteriores.
Astra detecta presión de render16ms frente a callbacks >30ms, sin causa
demostrada. Smoke ahora mide todos los renders/CPU/heartbeat y admite
--render-interval-ms sólo diagnóstico. Comparación50ms concluida:
gui_pair_v18_burst_1600_render50_20261023.json también falló ~29,9s y
restauró. RenderCPU25–29% en ventanas5s, maxcallback88,9ms y heartbeat
1,874s: reducir cadencia no basta y NO se cambió el timer del producto.
No hay hardware ni tests activos. Próximo diagnóstico: distinguir pausa
global/proceso/GIL frente a IPC con heartbeat y pilas de todos los hilos
en instante real (faulthandler acotado), sin sampler del receptor.
La terminal posterior al cierre puede perder la incorporación del snapshot
al informe host si RADIO detuvo running antes: revisar persistencia de ese
metadato antes de nuevas corridas. No promover tasas ni afirmar bug resuelto.

Diagnóstico opcional: `MONITOR_V18_FLOW_TRACE=<directorio>` registra etapas
por ID en JSONL por proceso; desactivado normalmente. Root es único dueño del Q.
No ejecutar suites o compilaciones en paralelo con mediciones físicas.

Tasas: sondeo anterior de 15 s pasó integridad hasta 1,818 MS/s, cola pico 5 y
margen 12,46%; no incorporación ni aceptación sostenida/GUI/analógica.
Reporte: `experimentos/fs_max_v18/resultados/20261022_192111/report.json`.
Pendientes otros bits y corregir separación CPU normal/activa en el runner
antes de volver a campañas de tasas. Herramientas ya toman/restauran V18.
Documentos: `docs/PAREJAS_V17_V18.md`, `docs/VALIDACION_V18.md`,
`docs/MEMORIA_CANDIDATO_FS_V18.md`.

## V18:20voces y optimizaciónIPC; tasasnuevas preparadas ·22/10/2026

Solicitud vigente:20vocesSynth,optimizarcadena conAstra,ADC8objetivo1.8MS/s y
subirotrosbits. V17NOtocar. Astra alcanzó revisióninicial y luego límite deuso;
Sol implementó20voces y tests antesmismolímite. Rootcontinuó ejecución.

MAX_VOICES20 ytests3PASS. CPUbenchmark11vs20/20k40k enAnacondaNumba0.62.1:
diagnosticos/resultados_v18/synth20_cpu.json. .venv-v13 noNumba no sirveDX.
Dosensayosfísicos20DX fallaronUNDERRUN:gui_synth20 ygui_synth20_refill_20261022.
Reducirtimeout/servicioantesread noalcanzó. RendererSynth ahora proceso aparte
synth_process.py, parámetros inmutables porIPC, estadofases/voces persistente;
warmupantesBEGIN. gui_synth20_process_20261022.json PASS20vocesDX20k,
played256320,accepted259200,Stop yrestauración. Testcomparacódigosidénticos
renderlocal/procesocon20notasycambioacorde. Noaceptacióntodosinstrumentos120s.

IPC RFcompactoRawRfBatch uint32 ymaterializaenproxy porgeneración: byteslote
20ms1.6MS/s896465→512820(-42.8%); benchmarkrf_batch_cpu.json.
GUIrealRADIO/Scan/WAV/FM gui_raw_ipc_20261022.json PASS.159suiteIOy20GUI PASS.
111hashV17origenguimanifestintactos. Los ACK/créditos/barreras siguenigual.

Candidatosenexperimentos/fs_max_v18:8escalera98→88ticks(1.818MS/s),incrementos
10/12/14 y16CH1. Cpack→Crelay→decoderV18todos17perfilesPASSSanitizers.
compile_only.py terminóPASSsininstalar ni tocarfuentesQ:compiledtrue,installedfalse,
restoredtrue,recovery10.00577s16,005,600samples0drops/fatal.
compile_report.json y /tmp/fs_max_v18_compile.log conservanevidencia. RAMglobal
257948/262144(98%),libre4196bytes; revisarantesdesondeo, noañadirbuffersciegos. Próximofísico necesita runneraislado conbackup/rollback,
NOusarprevio queescribaV17local. No tasas nuevas publicadas ni medidas todavía.
Docs:OPTIMIZACION_Y_TASAS_V18.md,SYNTH_20_VOCES_V18.md yexperimentREADME.

## V18 funcional validada con Q; V17 preservada · 22/10/2026

Entrada: `python -m monitor.v18 --gui`, o launch VSCode Monitor V18 GUI.
Backend maduro propio dentro de un hijo; DSP y fuentes mutables en el padre.
Firmware/relay/apps Q siguen V17, sin reinstalar ni reiniciar programas.
Preparar Q bloqueado. Requiere app y relay ya activos al conectar.

Cierre de integración:
- 154 pruebas del núcleo PASS, 20 GUI PASS. Prueba de imports propia y
  111 hashes de orígenes V17 intactos al finalizar.
- Receptor físico 8 bits/1,6 MS/s y recuperación/restauración PASS.
- Matriz de 11 casos PASS: cinco resoluciones, generador y WAV20/40/50k,
  niveles, seek, Stop. No extrapolar a aceptación sostenida de cada perfil.
- GUI con RADIO/A0 durante120,007s, Scan30candidatos, resintonía, WAVreal,
  dibujo expuesto, Stop y restauración: nueve aserciones PASS, sin errores.
- GUI final con Synth/FM20k: reproducción/progreso/Stop de RADIO/WAV/FM,
  Scan y cierre: trece aserciones PASS. WarmupFM antesBEGIN asíncrono.

Evidencia y límites: docs/VALIDACION_V18.md. Informes:
receiver_20261022_184657.json, modes_20261022_185201.json,
gui_long_20261022.json, gui_fm_20261022.json en diagnosticos/resultados_v18/.
Snapshots de cada sesión conservan estado exacto e identidad antes/después.
Último cierre confirmó restauración; sin procesos de pruebas residuales.
Antes de nueva campaña comprobar propietario/estado actual, no inferirlo
por memoria. No se probó UART ni Bode analógico ni todos los instrumentos/MIDI.
Headroom y calidad de audio escuchado permanecen sin calificación global.

No seguir ampliando el prototipo asíncrono como si fuera backend GUI:
io/process_audio.py conserva alcance simulado separado. V17 ya estaba dirty
antes del trabajo; no revertir sus cambios históricos. README raíz sigue
landing con badges e imágenes; evidencia técnica va en docs.

## V18 GUI + backend integrado; validación física en curso · 22/10/2026

Usuario pidió completar V18 sin tocar V17 y sin esperar OK por bloque.
Astra revisó arquitectura y Sol implementó GUI/proxy + receptor maduro en
hijo propio V18. Prototipo asíncrono anterior separado, no backendGUI.
Arranque: `python -m monitor.v18 --gui`; VSCode tiene entradaGUIV18 adicional.
PrepararQ bloqueado; conecta app ScopeV17 y relay ya activos, sin autoload/reset.

Root creó live_connection y ReceiverLifecycle: lockcompatibleV17 dentrochild,
identidadrealMCU/relay, snapshotADC exacto y generadorOFF, restauración y10s
continuosconcantidadmuestras. Leasevivehastacierre. Se corrigió cancelación
mitaddecoder que perdíaeventosinternos; evidencia fallida preservada.

FísicoPASS: `diagnosticos/resultados_v18/receiver_20261022_184657.json`
8bits/1.6MHz10s ~15.96Msamples, restore10.0058s16,005,600samples0drops/fatal.
MatrizPASS8casos `modes_20261022_184904.json`: perfilesSPIdual, seno997Hz,
WAVmmap20/40/50k +niveles/seek/STOP; restore10.0045s0drops/fatal.
NOaceptación analógica/holgura/largaRADIO aún. GUIvisibleconScan/RadioA0/WAV
corriendo, revisar resultado `gui_live_20261022.json` antesdeconclusión.

SuiteIO151passed20.478s antesúltimoshelpers; GUI18passed7.445s (Solreporta19
trasúltimoguard). Testshelpers3liveconnection+2lifecyclelocalesPASS; parentdeath
y cancelmidreadtambiénPASS. Revisar suitefinal cuando terminen cambios.
111fuentesV17 delmanifiestoGUI hashesintactos; V17 yaestabadirtyantes, no revertir.
Firmware actual leídoreal96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9,
relay0639869d3184c10b5a0aa70ad54713da5d414069e97209c8c0485c40c77482fe.
Qserial1060031107. Antesnuevacampaña comprobar dueño/procesos, no memoria.
READMEraíz conservado landing; guíasV18/docs actualizadas sinreorganizarV17.

## V18 creada: núcleo headless propio, GUI pendiente ·21/10/2026

Paquete monitor/v18/io + receiver propios,35copias de núcleo/protocolo/tests
con importsreescritos. No imports runtime monitor.v17 ni experimentos. Tests
migrados a tests/v18/io; conservan buildersbytes de tests.v17 solamente.
3tests nuevos auditan imports/resolución/entrada. Una ejecución de
`python -m monitor.v18 --self-test` pasó122pruebas (no5rondas). Default
`python -m monitor.v18` sóloJSON diagnóstico, noGUI/Q. No existe app.pyV18aún.

monitor/v18/migration_manifest.json guarda35orígenes/hashes; migration_audit.json
registra validación observada y hashes de creación. Verificó fuentes originales
sin cambios. Añadidos launchdiagnóstico y taskselftest enVSCode; otrasentradas
intactas. monitor/README corrige guíaactual aV17 y señalaV18experimental.
READMEraíz intacto (landing). Guía deconsolidación aplicada, noarchivarV17.

SinQ/ADBreal,firmware/relay/appsQsin cambios. El trabajo siguiente del candidato
va enV18, noseguir ampliando experimento como destino final. GUI, leaseADB+
identidad/snapshot/readback/recuperación reales aún nointegrados. Próximo unir
ese ciclo antes deGUI/aceptación física. ProcessSocketAudio siguefixture de
localhost, genbaselineconsultada yADCbaselineconocida delmodelo, noQreal.

## V18: restauración generadorOFF y QUERY final integradas ·21/10/2026

GeneratorPath conserva primera referenciaOFF recibida por QUERY y admite
set_off sólo con ella. GEN_SET acepta únicamente GeneratorConfig enabled0;
APPLIED debe coincidir exacto. Padre rechaza enabled1 antesdeencolar.
Enfinally, tras STOP yADC restaurado, si cambiógen envía referencia completa;
luego QUERY independiente (RIDnuevo) y compara todoscampos/runningfalse.
Resultado generator_verified=true sólo si consulta final coincide. Si nohay
referenciaprevia quedaFalse; última lectura no esprueba suficiente. Siempre
model_only=true. Suprime eventosGENa padre muerto para permitirlimpieza.

Cinco baterías de119pruebas pasan,4nuevas:
`experimentos/radio_io_process_v17/resultados/20261021_224010/report.json`.
Pruebasrefausente/APPLIEDdistinto/enabled1rechazado ymutaciónTCPde frecuencia,
niveles,duración,duty; hijo restauraoriginal y servidorindependienteconfirma.
Sin avisos. NoQ,ADBrealnoejecutado,V17intacta,firmware/relay/appsQsin cambios.
V18aúnnocreada. Falta unir DeviceSnapshot/identidadreal/leaseADB yrecuperación
física10s; luegoGUIV18. No presentar ACKemulado como snapshotQreal.
BaselineADC siguefixture14/125k; genbaseline ahora provienedeGENQUERY realdel
protocolo al emulador, no camposleídospor memoria compartida.

## V18: lectura de generador en hijo/TCP integrada ·21/10/2026

GeneratorPath nuevo usa encoder/decoderV17 y journal compartido. GEN_QUERY en
ProcessAudio/ProcessSocketAudio publica GENERATOR_READBACK sólo APPLIED, con
GeneratorConfig completo/running. RIDajeno/duplicado/rechazo/plazo fallan;
consulta enreposo, BEGIN/CONFIGesperanGENpendiente, STOP/SHUTDOWNesperan su
trama/ACK. Si lectura conocida indica generadoractivo, BEGINrechazado.
LocalTransport responde tipo9 con duty37/freqsnivelesintermedios; confirma
valores recibidos porprotocolo, noaccesodirectoalservidor.

Cinco baterías de115pruebas pasan,6nuevas:
`experimentos/radio_io_process_v17/resultados/20261021_223519/report.json`.
Pruebasfases/RID/timeout/ocupado/lecturaenchildlocalyTCP. Semáforoslimpios.
Resultado incluye generator_readback/generator_running deúltimalectura;
NO readback final después deSTOP ni restauraciónexacta por sí solo. Nohay
SET_GENERATOR/capturaautomática deidentidadreal antes deREADY todavía.
Fixture viejopermiteBEGINsinconsulta; no esarranquefísicocompleto.

SinQ/ADBreal,V17intacta,appsfirmwarerelayQsin cambios,V18aúnnocreada.
Próximo unir consultasADC/gen+identidad a DeviceSnapshot, SET_GENERATOR y
lectura final/recuperación con leaseADB. Persistir referencia previa yprobar
físico sólocon propietarioQactualverificado. No usar baselinefixture comoQ.

## V18: snapshot exacto y contrato de restauración offline ·21/10/2026

Nuevo device_snapshot.py. DeviceIdentity obliga serial/app/SHA256firmware y
relay. DeviceSnapshot inmutable guarda bits+request_periodADC y GeneratorConfig
completo (duty incluido), JSON esquema1 con validación. Captura sóloSPI con
WAVIDLE/DONE y genOFF/noejecución; no captura fase ni reproducción activa.
restore_contract inyectado: exclusividad/identidad, STOPconfirmado, ADC+gen
exactos, readback, recuperación10s continua con cantidadmuestras compatible,
0dropped/fatal y lectura final. ADCfallido todavía intenta restituir genOFF.
Informe JSONserializable, restore_contract_ok pero hardware_restored=false
siempre: nohay backendfísico aquí.10sdeFake no sonmediciónQ.

Cinco baterías de109pruebas pasan,9nuevas delcontrato:
`experimentos/radio_io_process_v17/resultados/20261021_223053/report.json`.
CubrenJSON/perfil/duty, ocupado/UART, identidadcambiadasinescrituras,
fallosADC/gen/STOP yrecuperación (unamuestra/10snoalcanza). Sin avisos.
NoQ,ADBrealnoejecutado,V17intacta,firmware/relay/appsQsin cambios.
V18aúnnocreada. Próximo integrar lectura/ACK reales delgenerador+snapshot
con dueño y leaseADB, persistir referencia previa, prepararV18/adaptadorGUI.
No operarfísico usando baselinefixture14/125k ni datos de memoria comoestado
actual; comprobar propietario eidentidades yconservar restauraciónreal.

## V18: lease ADB/identidad preparada y probada offline ·21/10/2026

Nuevo adb_tunnel.py con dependencias inyectadas (adb/identity/exclusive/connect).
Serial+app+firmwareSHA esperados obligatorios, identidad yUSB antes del forward,
lista previa/posterior y puertoasignadoconfirmado antes de conectar. Close
compara mapping actual, no adopta preexistentes/no borra reemplazos; asignación
inválida marca nuevo mapping noatribuible sin resolver y no lo elimina.
Conexión fallida limpia puerto propio confirmado. No usa runner/probe real
por defecto ni instala/reset/configuraQ.

Take_socket transfiere socket y retiene lease de forward; close pending_owner
hasta confirm_owner_exit(True), cuyo dato debe venir del sentinel/join real.
Identidad final sólo tras liberarforward, y exigeexclusividad de nuevo.
Hardware_restored=false siempre: NOsnapshotADC/generador/relay ni restore.
No confundir identidadigual con restauración delestado. ADB/probes fueradel
bucle de adquisición, executorreal debeacotar duraciones.

Cinco baterías de100pruebas pasan,10nuevas con FakeAdb/DummySocket:
`experimentos/radio_io_process_v17/resultados/20261021_221818/report.json`.
SinADBreal,Qnocontactado,V17intacta,V18aúnnocreada. Lease aún NO conectada
al ProcessSocketAudio. Próximo snapshotexactoADC/generador+identidades y
restauración verificada, unión lease/dueño, despuésGUIV18/aceptaciónfísica.
Seguir verificando propietarioQactual antes de operar, nunca usar snapshot
histórico como evidencia actual.

## V18: TCP real dentro del hijo, Q todavía emulado ·21/10/2026

ProcessSocketAudio transfiere socketTCP conectado al spawn y cierra copia del
padre. SocketModelPeer obtiene estado de ACK/decoder/path, sin leer memoria
emulador. Perfil inicial14/125k conocido porfixture, NOsnapshotQ; siempre
model_only=true. TcpModelServer independiente con LocalTransport, relojDAC
40kHz, RF14dual40/125k, escritura619B/vuelta; comienzaRF enprimerasolicitud.
No abrirQ con esta clase antes de túnel/identidad/snapshot/restore físicos.

Cinco baterías de90pruebas pasan, fuentes/hashes:
`experimentos/radio_io_process_v17/resultados/20261021_220841/report.json`.
6nuevas TCPspawn: GILpadre250ms conplayed>6000 yRF>50bloques; CONFIGbarrera/
reset/restauración; EOFprevioREADY; desconexión; ACKsuprimido; parentdeathreal.
Servidor confirmaIDLE/perfilinicial deformaindependiente. Semáforoslimpios.
READY exigeRFconfigconocida alhabilitarRF. EOFtemprano conservaNone en
config(generator,bits,rate), restored=false, sin excepción en informe final.
Primerascorridas detectaron113B/vuelta insuficiente, supresiónACKcreaba hueco
seqfalso y peer.configNoneenfinally; corregidos servidor e informe. RESETTCP
se clasifica termination/connection_error aparte de erroresinternosservidor.
SupresiónACK no asigna seq, permite probar timeout conRFvivo sin huecoSCP1.

SinQ,V17intacta,V18aúnnocreada. Próximo apertura/cierre túnel+identidad,
snapshot/restauración reales yprepararV18/adaptadorGUI. No afirmar aceptación
1,6MS/sniantena/sonidoanalógico. Perfil/estado de referencia en fixture no
reemplaza snapshotMCU/relay/generador del Q actual. Mantener dueñoúnico.

## V18: adaptador no bloqueante probado con TCP local ·21/10/2026

Nuevo socket_transport.py: adopta un socket stream ya conectado, valida
SO_TYPE/getpeername, no bloqueante y TCP_NODELAY en TCP. Send una syscall
(sin sendall/reintento), recv≤32×992distingueEAGAIN/EOF; contadorbytes ytimeout
2s sin datos (renovado al recibir). Closeidempotente sólo socket, no restore.
No abreADB ni buscaQ/conecta/reconecta. V17Connection sin cambios.

Cinco baterías de84pruebas pasan,8nuevas socketpair/TCP127.0.0.1:
`experimentos/radio_io_process_v17/resultados/20261021_201114/report.json`.
Cubren kernelbackpressure/shortwrite, lecturafragmentada, timeout, EOFparcial,
TCPNODELAY y AudioPump enTCP con peerfragmentado. Sin avisos de recursos.
Primercorridalocal falló: TCPNODELAYdevuelve4(no0,pero no1) y LocalTransport
no retenía bien límiteentretramas del stream; corregidos test/peer. Nuevopar
con5baterías pasa. LocalTransport.send limita bytes al resto de su trama y el
harnessreentrega sobrantes. No hardware ni transporteADB probado.

Próximo: unir SocketTransport al proceso dueño (ahora sólo LocalTransport),
apertura/cierre túnelQ con identidad y snapshot/restore, despuésGUIV18. No
atribuir a socketenhijo la pruebaGILanterior: esa unión aún no está hecha.
V17intacta,Qnoabierto,V18aúnnocreada; destino sigueV18.

## V18: adquisición/configuración unidas al hijo de audio, sin Q ·21/10/2026

ProcessAudio(rf_enabled=True) integra AcquisitionPath y LocalTransport genera
RF14dual125kS/s o40kS/s. Un decoder real procesa ADC/WAV/APPLIED. CONFIG idle
solamente; RID del mismo journal delaudio, ACCEPTED no publica, APPLIED valida
solicitud/perfil/época y emite CONFIG_APPLIED con barrera+primeríndice. Tiempo
límite APPLIED. Primera trama publica bootstrap delperfilinferido en decoder.

RF contiene tuplas(timestamp,a,b,index), generation/ordinal/first/count.
RfBarrier(block_size=None) admite conteosvariables≤904 y configure(...,
first_index=0) reinicia índice sólo al drenar barrera vieja. Default864 conserva
contrato original. Distinguir generaciónRF/épocaADC/épocaaudio.
STOP/SHUTDOWN esperanCONFIGpendiente; cierre confirma STOP y APPLIEDdeperfil
originaldelmodelo. Parentdeath inhibe publicación nueva durante limpieza y
cuenta abandoned_rf_blocks; salida admitida no se inventa. RFfull falla;
si cerró transporte restored=false (no fingir recuperación).

Cinco rondasde76pruebas pasan, fuentes/hashes:
`experimentos/radio_io_process_v17/resultados/20261021_195906/report.json`.
10nuevas: barrera/resetíndice, ADC+audio GIL250ms (>6000played,>50bloquesRF),
RFfull, CONFIGactivo, perfilfueraModelo, parentdeathconRF, shutdownconCONFIG
parcial, fasesACK, ACKajeno ytimeoutAPPLIED. Sin avisos de recursos.

SinQ,V17intacta,V18aúnnocreada. ModeloRF14dual40/125k sólo, NO1,6MS/s ni
validaciónotrosbits. Próximo transporte real no bloqueante +snapshot/restore
Q, adaptadorGUI y preparaciónV18 antes deaceptaciónfísica. OriginalSimDevice
permanece pruebaindependiente. Nunca confundir model_only con restorefísico.

## V18: AudioPump ya corre en proceso separado, aún sin Q ·21/10/2026

Nuevo ProcessAudio en process_audio.py reutiliza IPC/cierre Prototype con
_target/_options internos. Hijo crea AudioPump+ConfigurationDecoder real y
LocalTransport (extraído de tests a módulo propio) con DAC simulado40kHz por
reloj monotónico. Padre manda BEGIN/STOP/SHUTDOWN y PCM; eventos de comando
son aceptación del hijo, NO ACK dispositivo. Progreso coalescido; cierre exige
STOP→IDLE del modelo, model_only=true. Si pumpcerradofalló no finge restored.

Cinco baterías de66 pruebas pasan, fuentes/hashes en
`experimentos/radio_io_process_v17/resultados/20261021_194756/report.json`.
8nuevas: GIL padre250ms (48bloques recibidos, prebuffer30sólo prueba), tramas
siguen/played>6000; escrituras parciales, STOP/época nueva con misma sesión,
offseterróneo, EOF, noPCM, underrun y muerte real del padre con sentinel de
supervisor. Underrun retorna restored=false/salida incierta. Sin avisos de
recursos. LocalTransport bounded128historial/64respuestas yCRCpedidos.

Sin Q ni cambios V17. V18 aún no creada. Camino RF original permanece aparte:
ProcessAudio no implementa CONFIG/RF (rf_blocks=0). Próximo unir adquisición/
configuración con barrerasRF y transporte no bloqueante real antes deGUIV18.
No afirmar capturaADC, restauraciónfísica ni estabilidad deaudio real.

## V18: bucle PCM/protocolo unido, transporte local simulado ·21/10/2026

Nuevo audio_pump.py une AudioControl+ProtocolIngress con transporte abstracto
no bloqueante. Un paquete parcial de salida, colaPCM≤48, lectura≤32tramas por
turno, queries periódicos/tick y servicio ACK antes de ADC posterior. Query
no queda bloqueado por PCM esperando cuando DAC está lleno. Sin inventar
créditos; queue.Full no avanza offset. Callbacks deben ser no bloqueantes.

STOP cancelaPCM con contador; completa paquete parcial antes de STOP. Si
BEGIN no se envió, STOP usa última sesión remota confirmada, no sesión nueva.
Errorenvío/cero/EOF/timeout cierran con salida incierta, sin reintento ni
restauración declarada. Cierre normal exige STOP confirmado antes de close.

Cinco rondas de58 pruebas pasan (10nuevas del bucle), sin avisos de recursos:
`experimentos/radio_io_process_v17/resultados/20261021_193728/report.json`.
LocalTransport determinista sin sockets/relojDAC. No se probó el GIL de este
bucle ni hardware. V17 intacta; destino V18 aún no creada.
Próximo: ejecutar este bucle dentro del proceso dueño y unir IPC/control de
adquisición con barrerasRF; después transporte real y GUI V18. No asumir que
SimDevice ya fue reemplazado ni que el underrun físico está resuelto.

## V18: control asíncrono WAV/RADIO probado offline ·21/10/2026

Nuevo `experimentos/radio_io_process_v17/audio_control.py`: máquina de estados
sin I/O. QUERY capacidades, BEGIN, CHUNK, PLAY, STOP; 16/30slots negociados,
tasas anunciadas, créditos sólo confirmados y ventana acotada. Controles
serializados; STOP cancela pendientes; ACK viejos no reactivan audio. Sesión
remota ocupada se informa sin tomar posesión. Timeout al tick y al recibirACK
(no se admite ACK fuera de plazo aunque tick haya demorado). Fallo persiste
hasta STOP, que aún debe confirmarse. Prebuffer960 sólo mínimo de pruebas.

Cinco rondas de48 pruebas pasan (28dueño+9protocolo+11control), sin avisos:
`experimentos/radio_io_process_v17/resultados/20261021_193415/report.json`.
Una revisión intermedia falló por distinguir TimeoutError inicial del rechazo
RuntimeError al estar ya en fallo; corregido y repetido. Informes conservados.

Sin Q, V17 intacta, destino V18 aún no creada. Próximo: bucle de transporte
que envíe paquetes una vez, llame tick, programe consultas/PCM, propagueEOF y
fallo de envío; unir al dueño. No confundir la máquina de estados con backend
real conectado ni con estabilidad física. No cambiar política pública de
búfer por el prebuffer de esta prueba.

## V18: puente inicial al decoder/encoder real, aún offline ·21/10/2026

Nuevo `experimentos/radio_io_process_v17/wire_adapter.py`: ProtocolIngress
reutiliza ConfigurationDecoder de V17, feed máximo32×992 bytes, retiene
sólo parcial<992B, eventos por trama y ACK callback antes de decodificar el
ADC posterior. Error de decoder/consumidor cierra ingreso; EOF parcial falla,
EOF completo sólo informa transporte terminado. No Qt ni conexiones.
ChunkRequests usa encoder WAV real y journal configurable. Namespace real
0x80000000..0xfffffffe; nunca emitir 0xffffffff. Modelo previo usaba RID bajos.

Cinco rondas de37 pruebas pasan (28 del dueño+9 de protocolo). Fuentes y
hashes del experimento, receiver reutilizado y fixture archivados en:
`experimentos/radio_io_process_v17/resultados/20261021_193016/report.json`.
Sin Q ni cambios a V17. Destino sigue V18 (aún no creada).
Próximo: scheduler asíncrono BEGIN/PLAY/STOP/QUERY y negociación capacidad,
créditos/timeouts y transporte real; después unir al dueño y GUI V18.
NO afirmar que el puente ya es backend ni que quedó resuelto audio real.

## Próxima incorporación en V18; fallos del modelo probados ·21/10/2026

Instrucción del usuario: «cuando incorpores, todo en una v18».
Ver `docs/PLAN_INCORPORACION_V18.md`; V17 queda como referencia. No se creó
V18 ni se cambió aplicación/firmware. Experimento conserva ruta histórica.

Añadidas inyecciones de desconexión tras un chunk pendiente y restauración
fallida. Resultado separa error original y restoration_error; no declara
restored=true si restore falla. Ambos errores juntos se conservan. Cinco
rondas de 28 pruebas pasan, sin avisos de recursos:
`experimentos/radio_io_process_v17/resultados/20261021_192758/report.json`.
Sin uso del Q. Próximo: adaptar decoder/control asíncronos reales al contrato,
luego preparar V18 y su adaptador GUI antes de aceptación física comparada.
No confundir desconexión simulada con USB real ni diccionario con restore Q.

## RADIO: EOF y muerte del padre validados offline ·21/10/2026

El proceso dueño comprueba sentinel del padre y un canal de vida separado.
EOF termina controladamente; datos inesperados fallan. Si muere el padre,
restaura SimDevice y abandona explícitamente salida RF pendiente sin esperar
un consumidor inexistente. Resultado output_policy=abandon_on_parent_loss;
NO se afirma entrega íntegra tras morir el consumidor. Padre vivo conserva
cierre con drenaje completo y resultado idempotente.

Prueba mata un padre real con audio simulado activo; supervisor recibe el
resultado y verifica salida del huérfano mediante sentinel. Limpia sólo los
semáforos del padre de prueba tras salir el hijo. Requiere socket Unix local
para transferir descriptores (sandbox normal lo bloqueó; repetición autorizada).
Cinco baterías de 25 pruebas pasan, sin avisos de recursos en repetición final:
`experimentos/radio_io_process_v17/resultados/20261021_192613/report.json`.
Primera versión pasó casos pero avisó 75 semáforos al terminar; no ocultar
ese resultado histórico. Limpieza corregida sólo en harness de prueba.

Sin Q ni cambios públicos. Próximo: fallo/desconexión del backend y fallo de
restauración; luego decoder/control asíncrono real y adaptación GUI. El EOF
probado es del canal local, no USB/Q. Restauración sólo del modelo.

## RADIO: journal RID sin época en las respuestas ·21/10/2026

RequestJournal implementado en el experimento offline. Respuestas simuladas
sin epoch: RID/sesión se resuelven mediante identidad local. STOP cancela
pendientes; ACK viejo nunca acredita sesión nueva, incluso con el mismo
número de sesión. Pendientes y retirados limitados a 256 cada uno. Sin
reutilizar RID durante el proceso; agotamiento uint32 falla. Respuestas
fuera del historial fallan explícitamente; no se adivina su pertenencia.

Cinco baterías de 22 pruebas pasan (110 casos), fuentes y hashes en
`experimentos/radio_io_process_v17/resultados/20261021_192346/report.json`.
También conserva pruebas de barreras RF, consumo simulado durante bloqueo
GIL, créditos, cancelación y cierre. No se abrió Q ni cambió producción.
Próximo: EOF/muerte del padre/fallos y cierre; luego decoder/control real
asíncrono y adaptador GUI. No confundir este contrato con integración SCP1
ni con solución física al corte de audio.

## RADIO: barreras RF probadas offline ·21/10/2026

El prototipo aislado ahora etiqueta RF con generación y ordinal global.
CONFIG confirma la barrera de bloques anteriores; RfBarrier no publica el
cambio hasta consumirlos todos. Si RF adelanta al ACK, el llamador retiene
un bloque y procesa control antes de reintentar. Sin buffers internos ocultos.
Pruebas de ambos órdenes entre colas, reconfiguración del proceso spawn,
huecos/repeticiones/generación vieja y desborde uint32 pasan.

Cinco baterías de 18 pruebas, todas pasan. Informe y fuentes congeladas:
`experimentos/radio_io_process_v17/resultados/20261021_192150/report.json`.
No se usó Q ni cambió producción. Esto sólo valida el contrato simulado.
Sigue pendiente journal RID→época sin epoch ficticio del backend, EOF/muerte
padre/fallos, integración del decoder y adaptación GUI antes de hardware.

## RADIO: proceso dueño, prototipo offline implementado ·21/10/2026

Nuevo experimento `experimentos/radio_io_process_v17/`: prototype.py con
único dueño spawn y SimDevice SIN conexionesQ/Qt/USB/ADB. IPC acotado:
control4,audio48×960B+1retenido,RF≤1024×864muestras,confirmaciones8,progreso1;
resultado terminal separado. ControlFIFO/STOP prioritario,sesiones/épocas,
offsets y créditos sólo por ACK/QUERY; ACKperdido falla a500ms. RF lleno
falla explícitamente y cierre drena muestras admitidas/restaura sóloelmodelo.

Cinco baterías de14tests pasan con procesos nuevos. Padre retieneGIL350ms
y250ms: hijo avanza/consumeaudioSIMULADO. Tests STOP conaudioesperandocréditos,
ACKviejo/duplicado/perdido,QUERYserializado,PLAYprebuffer,CONFIGactivo,offset,
sobrecargaRFycierreidempotente. Fuentes/hashes/5logs en
`experimentos/radio_io_process_v17/resultados/20261021_191723/report.json`.

NO evidenciahardware.NO se abrióQ ni tocófirmware/aplicaciónpública.
Próximo SINQ:añadir generación y barrerasRFparaCONFIG entre colas separadas;
journalRID→época(elSCP1realnotraeepoch);pruebas EOF/muertedelpadre/error.
Luegoadaptadorprotocoloreal/decoderestricto,antesdeconectarQ. No dar por
resueltounderrun por elsimulador;READMEdelexperimento explica límites.

## RADIO: GC medido; agrupador vuelve a fallar ·21/10/2026

Usuario autoriza avanzar sinOK porbloque. Nuevo gc_audit.py pasivo yflag
--gc-audit enwire_probe.37tests pasan. GCsin cambios:habilitado,umbrales
(2000,10,10)antes/después.Controloriginal120spasa;agrupadorobjetivo120sfalla
UNDERRUNa84,12saudio,ACK355,453ms,ADCsinpérdidas,cola7. No promoveragrupador
comosolución aunqueantespasara60s+tres120s conauditoríasdistintas.

ACKdelmismoRID:299,671msenvío→recvcompleto +55,782msrecv→callback.
GCgen2(48,643ms) terminó4,87sANTESdeprimerACKPLAYING.18coleccionesdurante
PLAYINGobservado,máximo10,984ms;NINGUNA coincideconACKcrítico.Historial
64/65timestamps(elperdidoantiguo),ringrecientecubreintervalofallo,sinpendingGC.
Noajustar/desactivarGC por esteevidencia; noexcluyecontribuciónindirecta.
Evidencia `experimentos/radio_ipc_compact_v17/resultados/gc_failure_review_20261021.json`.

Qrestauradoexacto8/1,6MHzgenOFF,identidad96685…;últimos10s15992640muestras
sinpérdidas.Ningúnensayoactivo,producciónintacta. Próximo contrato/prototipo
SINQ paraaislardueñotransporte/A0delprocesoGUI,IPCacotado,órdencomandos,
sesiones,créditosconfirmadosycierre/restauración.AÚNNOIMPLEMENTADO ni validado.
No tocarfirmwarenitrasladarreceiverenteroantesdepruebasoffline.ConservarúnicodueñoQ.

## RADIO: control emparejado y repetición completos ·21/10/2026

Usuarioautorizaautonomía,sinOKporbloque. Agrupador sigueaislado,producción
intacta. Nueva pareja120+120 conhashesiguales pasaaudio/ADC/FFT100%visible:
CPUcallback4,323→0,976s,pump46,431→45,304s;ACK80,36→82,88ms,cola5→6.
Retención76,385ms coincidepump78,812mscon2,610msCPUhilo:noesGILúnico.
Repeticiónindependiente120s mismasfuentes pasa,ACK68,94ms,cola4,FFT19,95Paint/s;
retención84,36ms,cero pendientes. Hay60s+tres120spasados,peroauditoríamixta:
no llamar calificaciónformal niraízunderrunresuelta.NohayholguraADCaceptada.

Evidencias `resultados/coalesce_matched_20261021.json` y
`resultados/coalesce_repeat_20261021.json` bajo experimento radio_ipc_compact_v17.
33tests pasan,diffchecklimpio.Qrestauradoexacto8/1,6MHzgenOFF,identidad96685…;
últimos10s15993504muestras sinpérdidas.Ningúnensayoactivo.
Próximo:auditoríapasivaGCdelhostycorrelaciónconpausas/ACK,sindesactivarGC
niretocarumbrales. Históricounsolo stackgc_collect_main:pista,no causa.
ConservarúnicodueñoantesdeQ;nopromoveragrupadornuevoperfilaún.

## RADIO: agrupador aislado pasa60+120s ·21/10/2026

Usuario autoriza seguir sin OK entre bloques. Implementados `sample_coalescer.py`
y `coalesce_probe.py` en experimento radio_ipc_compact_v17. SóloADC8/1,6MHz con
RADIO→A0; validación por trama intacta, memoria≤16000muestras/32partes y
plazo10msCOOPERATIVO; flush controles/contexto/cierre. Sin cambios públicos.
32tests pasan, incluyendo receptor real que rechaza gapRF antes de entrega.

Screening60+120s pasa sincortes/pérdidas.111052→8432 y222099→16980callbacks
agrupados(~92%menos),muestras conservadas,cero pendientesalcerrar. Máximo
15552muestras/18partes;retenciónmáxima34,42/162,72ms: noeslatencia garantizada.
Colas5/5,ACK93,86/118,81ms.Noincorporar: nohaycontrolnuevoemparejado ni
corrección probada delunderrun/holgura. No afirmarahorroglobalporcallbacks.

Evidencia `experimentos/radio_ipc_compact_v17/resultados/coalesce_screening_20261021.json`.
Qrestauradoexacto8/1,6MHzgenOFF,identidad96685…;últimos10s15991776muestras
sinpérdidas.Ningúnensayoactivo. Próximo:controlindependienteconigualinstrumentación
ycorrelacionarretenciónlarga,nominal10msnoeslímitetiempoduro.Conservarúnicodueño.

## RADIO: ACK por RID y pausas de callback medidas ·21/10/2026

Usuario autoriza seguir probando sin OK por bloque. Nuevo observador pasivo
`experimentos/radio_ipc_compact_v17/wire_probe.py` y `wire_ack_audit.py`.
Tres versiones:120spasa;segunda fallaUNDERRUNa9,36saudio,ADCsinpérdidas/cola3;
tercera120spasa concallbacksmedidos. RIDdel fallo2874850373:212,599ms
envío→recvcompleto +29,453msrecv→callback =242,052ms.Noescablepuro niGILúnico.
Terceracorrida entregaon_samples47,518ms de pared con0,992msCPUhilo;
227770callbacksactivos durante lifecycle.Padresincluyenmismapausa,nosumar.
No modifica créditos/orden ni producción. Parser/tiempos añaden sobrecoste.

Evidencia `experimentos/radio_ipc_compact_v17/resultados/wire_review_20261021.json`,
README del experimento yfailure_reviewdelwire_20261021_180242.Seistestsnuevos
pasan(más16previos).Qrestauradoexacto8/1,6MHzgenOFF,identidad96685…;
últimos10s15991776muestras sinpérdidas.Ningúnensayoactivo.
Próximo candidatoAÚNNOIMPLEMENTADO:coalesceracotadodecallbacksRFvalidados;
flushantesdefronterasconfig/generador/estado/cierre;testsorden/wrap/cancelación
yretenciónantesdeQ.NoagruparACK,niliberarcréditosestimados.Conservarúnicodueño.

## RADIO: etapas medidas; mejora numérica no resuelve corte ·21/10/2026

Usuario autoriza probar sin pedir OK entre pasos. Control/adaptativo con
misma instrumentación120s cadauno pasan, peroFFT1232→1196(-2,9%),CPU pipeline
15,050→14,418s yACK31,07→71,28ms,cola5→6.No incorporar adaptativo.
Detalle60s:analyze4,254sCPU,FFT1,974s;anotaciones0,524s.No sumar etapas anidadas.

Nuevo `peak_selection.py` aislado:top5 estable por partición, equivalencia
exacta y17–19%menos medianaCPUanalyze offline. Prueba física objetivo120s
fallaUNDERRUN a33,036saudio,ACK242,36ms,ADCsinpérdidas,cola3,FFT100%visible.
Noes solución delaudio ni sepromueve. `fft_numeric=0` deesa corrida ESINVÁLIDO:
copiaaislada bypassedwrapper;helpercorregido ytestnuevo, versióncorregida
sólo offline. Fuentesanteriores archivadas.16tests pasan,diffchecklimpio.

Evidencia en `experimentos/radio_ipc_compact_v17/README.md`,
`resultados/stage_comparison_20261021.json` y `render_20261021_151218/failure_review.json`.
Qrestauradoexacto8/1,6MHzgenOFF,identidad96685…y10s15991776muestras sinpérdidas.
Nada corriendo. Próximo hipótesis atención transporte/ACK; noseguirFFT a ciegas
ni liberarcréditosestimados.ColaADC3noesestabilidadA0.Producciónsin cambios.

## RADIO: política adaptativa aislada probada ·21/10/2026

Nuevo `experimentos/radio_ipc_compact_v17/adaptive_refresh.py`, opción
`render_probe.py --adaptive-refresh`. Sólo FFT live con RADIO→A0: techo 8 Hz
ante tres lotes pendientes o ACK≥40 ms reciente; recupera tras 3 s tranquilos.
STOP, SINGLE y cambio de sesión/modo retiran el límite. Sin cambios públicos,
sin codec ni firmware; créditos inalterados. Once tests pasan.

Screening 60+120 s pasa sin cortes/pérdidas, FFT 100% visible a18,77/18,88
Paint/s. Activaciones3/5, tiempo reducido9,07/17,47 s durante el lifecycle.
ACK35,75/55,75 ms, cola6/5. No es holgura ni calificación. CPU render120s:
16,83s, igual al control anterior; no hay ahorro CPU demostrado. No incorporar.
Evidencia: `experimentos/radio_ipc_compact_v17/resultados/adaptive_screening_20261021.json`.
Q restaurado exactamente a8/1,6MHz genOFF, identidad96685…; 10s15991776
muestras sin pérdidas en cada corrida. Ningún ensayo activo.
Próximo: control con igual instrumentación y medir cálculo FFT efectivo, no
sólo llamadas omitidas; no ajustar umbrales a ciegas. No pedir OK rutinario;
comprobar único dueño antes de Q.

## RADIO: repetición inversa completada ·21/10/2026

Original→8Hz,120s cadauno,sincodec: ambos pasan audio/ADC yFFT100%visible.
OriginalACKmáx86,71ms,cola6,19,58Paint/s;reducidoACK46,32ms,cola5,14,41Paint/s.
CPU acumulada del método render16,83→11,89s(~29,3%menos delmétodo,nodelmonitor).
NoescausalidadGIL nicorrecciónvalidada;originaltambiénpuedepasar120s.
Ningunopasacola<4;noincorporar nillamarcalificación.

Evidencia `experimentos/radio_ipc_compact_v17/resultados/render_reverse_comparison_20261021.json`.
Qrestauradoexacto8/1,6MHzgenOFF,identidad96685…;10s15991776muestras sinpérdidas
encadacorrida.Ningúnensayoactivo.Sin cambiosdeproducción.
Próximo candidatoaislado:disminuir análisis/dibujo sóloRADIO→A0bajopresión,
mediractivación/recuperación,conservarresolución/SINGLE/audio/créditos.
No seguircalificaciónestricta deltecho8Hz mientrascolasincumplan.No pedirOKrutinario.

## RADIO: ablación FFT; control original vuelve a fallar ·21/10/2026

Nuevo runneraislado `experimentos/radio_ipc_compact_v17/render_probe.py`.
Sincodec, sin cambiar resolución65536/audio40k/créditos. Trescorridas:
8Hzpasa120s(ACK57,58ms,cola6);techo60Hzpasa120s(ACK59,14ms,cola4),pero
omitió2156llamadas ynoescontrolabierto;controlreal0Hzsinlímite fallaUNDERRUN
a64,992saudio(ACK291,14ms,cola4). ADCsinpérdidas yFFT100%visible enlastres.
Elfallo persiste conpayloadoriginal; noinferir causalidadFFT/GIL ni solución.
No hay cambios públicos. EvidenciaenREADMEdelexperimento y
`resultados/render_comparison_20261021.json`.

Qrestauradoexacto8/1,6MHzgenOFF,identidad96685…,últimos10s15991776muestras
sinpérdidas. Ningúnensayoactivo. Próximo comparaciónindependiente enorden
inverso8Hz/abierto conigualinstrumentación,sincodec; sólosiesrepetible diseñar
medidaadaptativa. No pedirOKrutinario; comprobarúnicodueñoantesdeQ.

## RADIO: codec IPC aislado y prueba física · 21/10/2026

**Último resultado: NO ACEPTADO.** Ensayo120s con umbral64000 fallaUNDERRUN
enposición69,192s tras62compactaciones; ADCsinpérdidas,cola5,FFT100%visible,
ACKmáx305,07ms. Qrestauradoexacto8/1,6MHzgenOFF,identidad96685…,
10s15994368muestras sin dropped/fatal. Nada corriendo. No incorporar codec
ni atribuir causalidad al mismo: el fallo ya existía. Próximo revisar atención
al transporte en pausas largas del host; auditoría acotada en
`experimentos/radio_ipc_compact_v17/resultados/physical_20261021_132102/failure_review.json`.

Experimento en `experimentos/radio_ipc_compact_v17/`, no importado por
producción. Reconstrucción bit-exact de índices/tiempos y fallback conservador;
seis tests de equivalencia, wrap, gaps, generación y FILTER pasan. A/B offline
alternado incluye compactación y reconstrucción: peor con 32000 muestras,
mejor mediana con bloques grandes. No es prueba de holgura física.

Control físico 60 s: sin cortes/pérdidas, FFT 100% visible a20,08FPS, cola4.
Candidato umbral128000 durante120s: sin cortes pero **cero activaciones**,
no atribuirle mejoras. Umbral experimental64000 durante60s:39compactaciones,
sin cortes/pérdidas,20,01FPS,cola5,ACKmáx112,16ms. Todos restaurados exactamente
a8/1,6MHz genOFF,identidad96685…+10s sin pérdidas. No incorporado.
Ver README del experimento e informes enlazados en docs/RADIO_HOST_GIL_V17.md.

## RADIO: coste IPC medido offline · 21/10/2026

Se agregó `diagnosticos/medir_ipc_radio_v17.py`, sin Qt ni acceso al Q.
Dos barridos (200 y 100 repeticiones por caso) del payload real RADIO muestran
viaje mediano de 0,91–1,18 ms con 20 ms de RF y 29,16–33,61 ms con 160 ms.
Reducir a CH1 baja bytes ~60%, pero es sólo un límite de coste inválido para
DSP: no omitir continuidad. Fuentes/hash del segundo barrido archivados.
Ver `docs/RADIO_HOST_GIL_V17.md`. Producción y Q sin cambios en este bloque.

Próximo: candidato aislado de metadatos compactos con equivalencia/rechazo de
gaps/wrap/generaciones; medir distribución real de lotes y hacer A/B visible
antes de promover. Los tamaños grandes del barrido no prueban que ocurrieron
durante un corte. No pedir OK rutinario para continuar el plan autorizado.

## WAV probado; RADIO: GIL observado · 21/10/2026

El usuario cerró V17 y autorizó continuar. Se ejecutó selecciónVivaldi50k sinPlay a8/1,6MHz conRADIO: pasa, sinreproducirfallo; GUI tuvo290ms de retraso máximo. MatrizWAV50k de8/10/12/14a100k legacy diagnóstico y16/76226:60s cadauno, todos pasan audio/ADC/gráfico100%visible. ControlesVivaldi16bits pasan ochoacciones.14testsWAV pasan. No promover100k alselectorpúblico ni llamar calificación al screening.

Primeramatriz fallóglobalmente poríndice−1 enelcombo100k, no poraudio; corregido sóloelrunner, testwidgetreal yrepeticiónlimpia código0. Fuentesarchivadas yreportes en docs/CAMPANA_WAV_TODOS_BITS_V17.md.

RADIO→A0 público8/1,6MHz120s+11resintonías pasó sinpérdidas/cortes pero cola7/8. Perfilnativo eager-symbols tuvoUNDERRUN enposición55,2s; árbol sóloderecuperación, nocausalidad. Perfilposterior sinlecturaanticipada capturó receptoractivo:808/2125muestras en take_gil (~38%deobservaciones, NOCPU); corrida120s pasó con10resintonías, cola5. Ambosperfilados son diagnósticos perturbados, noaceptación. Ver docs/RADIO_HOST_GIL_V17.md y review.json.

Próximo: medircostes concretos deholdersGIL ycopiasIPC antesdediseñar optimizaciónaislada acotada. _process_separately YAenvíasólocolumnasnecesarias yprocess_owned_result YAdevuelvesóloDSP/FILTER; no redescubrir ni reimplementar eso. No liberarcréditosestimados, no repetir1ms/ReadyRead comofix.

Qrestaurado alestadooriginal ADC8/1,6MHz genOFF, identidad96685…,10s sin dropped/fatal. Ningúnproceso deensayo dejó corriendo. No pedirOK rutinarios; conservar único dueño y comprobar siusuario volvióaabrirmonitor.

## WAV: matriz preparada; Q en uso · 21/10/2026

V17 estaba abierto (PID66442); se pidió cierre mediante pregunta asíncrona y se continuó offline. No se accedió al Q. El usuario autoriza avanzar autónomamente; no pedir OK rutinarios, pero mantener un solo lector.

Runner WAV mejorado: matriz explícita, límite público100kHz conservado, parada al primer fallo, exitcode correcto, callbacks por caso, RID, auditoría Paint/exposición, selección cronometrada y Seek/EOF por duración real. Restauración10s, identidad a baja carga antes de restaurar tasa previa; no abrir conexión si worker no terminó.13tests WAV pasan, pycompile/diffcheck pasan. Estos cambios del runner todavía no tienen prueba física.

Próximo al liberar Q: selección Vivaldi50kHz sin Play a8/1600conRADIO; luego matriz60s de8/10/12/14a100kHz y16/76226, salida50kHz, con trazas y ventana visible. No omitir protección WAV ni tratar estos ensayos como nuevas tasas calificadas. [Comandos y límites](docs/CAMPANA_WAV_TODOS_BITS_V17.md).

## FFT optimizada y validada en producción · 21/10/2026

El usuario pidió avanzar autónomamente, sin esperar un OK entre bloques.

Se incorporó un workspace privado en `spectral_analysis._fft`: mismos resultados, resolución e inputs preservados, con menos temporales. Pasan15tests numéricos y40deinterfaz. Benchmark de preparaciónFFT: alrededor de10%menosCPU; comparación física de la etapaFFT13,882→13,111sCPU en120s. No confundir con reducción global ni corrección del underrun.

Producción8bits/1,6MHz RADIO→A0/40k pasó120s, FFT100%visible19,91Paint/s y sinpérdidas/cortes; cola5. QoSHigh diagnóstico pasóotro120s, cola5 yACKmáximo58,6ms; sigueexperimental. ReadyRead y1ms noincorporados. No nuevas tasas. Qrestaurado identidad96685…, ADC16/40kgenOFF,10s399360muestras sin dropped/fatal.

La instrumentaciónsocket Linux4aa0… está compilada/probada:12817comandos completos, ACKQ→socketcompleto máximo0,218ms en corrida base. Falta capturar el underrun con esa traza nueva. La corridaReadyRead103546 fue cancelada pordefecto delprototipo, corregido ytesteadocierre; no es evidencia defallohardware. GC enreproducción≤2,33ms enlamedición, no cambiarpolítica.

[Resultados y límites](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md). Próximo: estabilidad/holgura deRADIO yWAV bajo carga, sinrepetir indefinidamente candidatos que ya fallaron; validaciónvisible16bits siguependiente delplan general.

## Instrumentación socket lista para compilaciónLinux · 21/10/2026

Nuevoexperimento adc8_a0_socket_trace_v17: FIONREADhost antes/despuésread, top8/128recientes; relay marcaACKúltimobyteaceptadosocket porRID, inclusoparcial/EAGAIN/postfreeze. Tres testslocalespasan; fuenteheredada validada. Noes entregafísica, dosioctl/read agregancoste. PendientecompilaciónLinuxcompleta/hashbinario y120sfísicos conrestauración. Qnooperado, producción/créditosintactos. [Detalles](experimentos/adc8_a0_socket_trace_v17/README.md).

## Pausahost deenvío confirmada · 21/10/2026

Auditoríaoffline porRID: hostsendgap177,803ms vsQ178,221ms. Cuatroservicebloqueadosporcréditos conaudio disponible; read84,505ms antesdereanudar. ACKhost265,833ms vsQcompleto→ACK1,173ms. Problemaseacota arecepción/esperadeconfirmaciones; no liberarcréditosestimados. Próximo instrumentarbytesdisponiblessocket/progresoTCP/flushrelay para separartransporte deatenciónhilo. Qnooperadoenestebloque; restauraciónprevia intacta. [Evidencia](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## Calificación1ms falla: no incorporar · 21/10/2026

Screen60s pasa; primera120s fallaUNDERRUN (último elapsed105s), ADCsinpérdidas cola6, FFT100%visible. Campañadetenida sinreintentos. RingQcapturó178,221ms entrecomandos conúltimareserva156ms; completo→ACKrelaymáximo2,806ms, hostACK265,833ms. Hostteníaaudio.1ms noresuelve; noincorporar nitasa. Qrestauradoexacto ADC16/40kgenOFF+10s399360muestrassinpérdidas. Próximo auditarenvíohost/refill/RIDfallidoantescambiarcréditos. [Evidencia](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## Comparación host completada5/1/1/5ms · 21/10/2026

Cuatro120s RADIO→A0/FFT100%visible pasan audio/integridad. ACKmáximos83,74/26,85/73,89/291,76ms; cola4en todas.1ms mejoraACKen ambasparejas, pero noreserva ni holgura yread variable. Qrestauradoexacto+10s399360muestrassinpérdidas enambas. Candidatoaislado: noincorporar todavía; siguiente calificación60+3×120a1ms y revisarRIDlentopost-read. [Resultados y límites](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## Host Python: comparación5/1ms · 21/10/2026

Dos corridas120s ADC8/1,633MS/s privado RADIO→A0/FFT100%visible pasaron audio/integridad. Intervalo experimental1ms frente a5ms: ACKmáximo83,74→26,85ms, read44,50→23,78ms; FFT18,97→18,90FPS, cola4enambos y reserva213,53→195,88ms. Señal favorable enlatencias, sinholgura ni causalidadGIL probada. Noincorporado; falta repetir ordenalternado. Qrestauradoexacto ADC16/40kgenOFF, identidadigual y10s399360muestrassinpérdidas. [Evidencia y límites](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## TramosA0acotados3×120 · 20/10/2026

Tracetailsaislada pasó3×120s RADIO→A0/FFTvisible96/100/100%, sinUNDERRUN/drops; colas4/4/4,sinholgura.38338comandos conetapascompletas: recibido-completo→ACKenrelaymáximo1,838ms; hostACKhasta212ms. No reproducefallo ynoescorrección. Evidenciaacotademoragrandeafuera deintervalolocalrelay(SPI/ACK) enestas corridas; faltaUSB/ADB/atenciónPython. Qrestauradoexacto+10s sindrops. PróximoCPUwallread/decode+RIDACKlento/instanteread paraubicarhost/transporte. [Informe](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## A0créditos: sin doble reserva; traza120s no reproduce · 20/10

Auditoría13inflight sonexactamente13chunksPOSTaccepted, noliberarcréditosoptimistas. MCU avanzó16bloques sinaceptarmásaudioenfalloprevio. Nuevo relayaíslado conring128RID/timestamps120svisible100% pasa audio/ADC,cola6,19Paint/s; noreproduceUNDERRUN. Últimos128comandosrápidos,norepresentanmáximoscorridacompleta. Qrestauradoexacto+10s sinpérdidas. Causaaúnabierta,nifixdecréditosincorporado. Próximo: máximosacotadosporcomando/etapa ycapturafalloinstrumentado. [Evidencia](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## N8 visible falla A0 · 20/10/2026

Nueva campaña ventana100%visible:60/120/120s pasan; última120falla~41s conWAV4/2UNDERRUN. Colas7/4/6/4; ADCdropped=fatal0. Noreintentarniincorporarcandidato. Hostteníaaudio(min6450muestras), servicecreditsrepetido13inflight/free13 yACKlat267ms: siguiente investigarconfirmaciones/créditosA0/estadoenvejecido, sinatribuircausacerrada. Qrestauradoexacto producción96685…+relayoriginal ADC16/40kgenOFF y10s399360muestrassindrops. [Informe](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## N8 RADIO→A0 calificado en integridad · 20/10/2026

Relayexperimental2253…/MCUcc46a1,633MS/s pasó60s+3×120s RADIO→A040k conburst8, sinpérdidas nifaltadeaudio. Colas4/5/4/6: sinholguraestricta; margen15,28–15,45%, reserva184,5msmínima. FFTexpuesta25/15/19/0%: novalidaciónvisual nicargagráficacompleta. NOincorporarrelaynitasa. Qrestauradoexacto firmware96685…+relayoriginal yADC16/40kgenOFF;10s399360muestrassindrops. Próximo:medircomandosA0vsenvíoADC antesnuevocandidato. [Evidencia](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## Candidato accept cada8 · 20/10/2026

Astrarevisó/Solimplementó copiaaislada. Mismorelaya1,633MS/s(runtimeN1/N8):60s ambos sinpérdidas; colas6→3, acceptportrama21,008→6,541µs(~69%menos). SóloADC; unaparéjanoaseguracola niaceptaciónsostenida. recv/send/prioridades/READY/colaintactos; acceptinmediatonocliente/otrosperfiles, clienteactivocada8tramas. Qrestauradoexacto firmware96685…+relayoriginal y10s sindrops. Noincorporado. Próximo: validarRADIO/FFT yRADIO→A0 delcandidato y60+3×120s antespromover. [Evidencia](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## READY/SPI instrumentado · 20/10/2026

Relayaislado midió ADCsolo60s×2 sinpérdidas. Colas1,6/1,633=4/3 (variaciónvsA/Banterior2/4,norelacióndeterminista). READYmáximo3,13/3,06ms, SPI0,47/0,53ms; ciclo3,92/4,10ms. Histogramasacotados,sinJSONenhigh; heartbeat10sconservado. Qrestauradoexacto+10s sindrops. Nooptimizaciones aún,públicossincambios. Próximo: timestampflancoGPIO parasepararREADYtardíodeLinuxatendiendotarde,yrecv/accept/send. [Evidencia](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## RADIO/FFT A/B · 20/10/2026

60s adquisición+DSP:1,6MS/s sinpérdidas cola3;1,632653MS/s sinpérdidas cola5 (sinholgura). Mismofirmwarecc46/nodo3456/cola8/relay/entrada. Métricas únicas(epoch,produced), no censotodosnodos. FFTexpuesta71,2%/38,9%: NOvalidaciónvisual ni cargagráficaidéntica. Primera corrida conservada; sólo se completótasapendiente. ÚltimoDSPsintonía15999Hz/banda8k (pedido20k limitadoenbase40k);A0OFF. Ambasrestauracionesexactas y10s sinpérdidas. Próximo: instrumentarREADY/SPI/control relayaislado, sinatribuircausamásalládelosdatos. [Informe](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## A/B ADC8 sólo adquisición · 20/10/2026

Mismocandidato cc46,relay,node3456,cola8,SPI40WORD,CPU2FIFO10 yentradaigualada.60s a1,6MS/s pasó95944608muestras cola2;1,632653MS/s pasó97905024 cola4 (sinholgura estricta). NohuboRADIO/A0. Una pareja,noaceptaciónsostenida niatribucióncausal deorigenpausas. Promedioheredado puederemuestrear nodos:noaceptarmargenfinal. Qrestauradoexacto firmware96685… yconfigprevia,10s sinpérdidas. Próximo: deduplicarmétricas porproduced ysumarRADIO/FFT antesoptimizar. [Plan/evidencia](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md).

## Incorporada espera corta1600 · 20/10/2026

Cambio conectado a1600 espera0,5s; primeraentrada2s y guardafría5s conservadas. Candidato pasó RADIO3×120s cola3 yRADIO→A03×120s cola5 (sinholgura estricta); restauraciones verificadas. Código integrado volvió a pasar120s conRADIO sin override, restaurado exacto y10s sindrops.41tests localesOK. No subióFs. Próximo: transporte/colas A/B y arranquefrío; no atribuir pérdidas previas a esta mejora. [Informe](docs/DIAGNOSTICO_ARRANQUE_V17.md).

## Espera0,5s con RADIO · 20/10/2026

Ensayo privado live-only conRADIO20kHz yA0OFF: cambio1600 primeraentrega634,2ms,120s191950560muestras sin dropped/fatal, colaMCU3. DSPfrío inicial1,607s medido en conexiónbase (primerlote2,243s); no mezclar con cambiotasa. Pendientesmáximos GUI9/DSP3 sinerror. Qrestauradoexacto y10s6321024muestras sinpérdidas. Esperapública2s intacta. Falta3entradasindependientes120s yRADIO→A0 antesincorporar; sinPaintvisible acreditado. [Informe](docs/DIAGNOSTICO_ARRANQUE_V17.md).

## Espera ADC1600 reducida · candidato0,5s medido

Ensayo aislado en memoria (fuentes/firmware producción intactos): primer lote592,3ms frente a2064,9ms del control2s.60s96009408muestras sin dropped/fatal, cola pico4 (sin holgura estricta). Sólo stackactivo, RADIO/FILTER OFF; no probado frío ni RADIO/A0. Q restaurado exacto y10s6321888muestras sinpérdidas. Espera pública aún2s. Próximo: entradas independientes y carga RADIO antes de incorporar. [Evidencia](docs/DIAGNOSTICO_ARRANQUE_V17.md).

## Medición física de demora1600 · 20/10/2026

Stackactivo, RADIO/FILTER OFF ysinA0: control8/1403508 primeraentrega69,8ms;8/1600000=2064,9ms, deellos2000,13ms deesperaprogramada. Todasetapas10s sindropped/fatal. Restauración exactafirmware/ADC8/632411dual genOFF y10s6321024muestras sindrops. SinprimerPaint niarranquefrío acreditados. Próximo: probaresperamáscorta encandidatoaislado, después A/Btransporte. [Medición](docs/DIAGNOSTICO_ARRANQUE_V17.md). No reducirguardas deproducción todavía.

## Arranque ADC8/1600 · revisión Astra e implementación Sol

Se identificaron dos esperas existentes:5s sólo tras reinicio autoload de perfil optimizado y2s en la preparación propia de1600 también al cambiar en vivo (14/40000→8/1428571→1600). Implementada traza opt-in SPM_STARTUP_TRACE=1, cuatro solicitudes×128eventos, hitos conexión/identidad/preparaciones/APPLIED/GUI/DSP/primera entrega. No prueba Paint visible. Guardas, firmware y tasas intactos;41tests locales pasan. Falta medir físicamente frío/cambio activo y luego probar reducción aislada; no atribuir toda demora reportada sólo a las esperas conocidas. [Uso](docs/DIAGNOSTICO_ARRANQUE_V17.md) · [Plan Astra](docs/PLAN_ARRANQUE_Y_COLAS_ADC8_V17.md). Q no operado en este bloque.

## Carga prolongada FS · 20/10/2026

8/1,633MS/s perdió un nodo por cola llena8/8; último consumidor2,317ms frente a nodo2,117ms. La demora inicial aún no se atribuye a una pieza concreta.14/909kS/s pasó dos corridas120s pero perdió un nodo en la tercera (cola4/4, CRC correcto); no incorporar.16CH1/145,455kS/s pasó audio/transporte60s+3×120s, margen77,88–77,92%, cola1; una corrida parcialmente oculta impide calificación visual completa. Sin tasas públicas nuevas. Q restaurado a firmware96685… yADC8/632411SPI dual, genOFF,10s sin pérdidas. Próximo: completar validación visible de16 y controles comparables/colas de8/10/14 antes de optimizar. [Informe](docs/CARGA_CONJUNTA_FS_V17.md).

## Carga conjunta FS: screening cerrado

14/909kS/s y16CH1/145,45kS/s pasan RADIO/FILTER→A0 conFFT60s por entrada y temporal30s, con holgura.8/1,633MS/s perdió un nodo (cola8/8) y10/1,290MS/s cerró el flujo conFILTER; no aceptar aumentos para uso conjunto.12 ya falló aislado. Q restaurado a firmware96685… yADC8/632411SPI dual, genOFF. Sin tasas públicas nuevas. Falta estabilidad conjunta prolongada de14/16 y diagnóstico/control comparable de8/10. [Informe](docs/CARGA_CONJUNTA_FS_V17.md).

## Calificación FS por bits cerrada

8/1,633MS/s y10/1,290MS/s: integridad60+3×120, sin holgura estricta por cola.14/909kS/s y16CH1/145,45kS/s: ambas.12/1,096MS/s: dropped1, no aceptar. Q restaurado con firmware96685… yADC8/632411SPI dual, generadorOFF. Tasas privadas; faltaGUI/RADIO/A0 y aceptación analógica antes de incorporar. [Informe](docs/EXPLORACION_FS_MAXIMA_V17.md).

# Continuidad · 19/10/2026

La pareja activa es **V17**. Leer primero el [estado actual](docs/ESTADO_ACTUAL_V17.md) y el [plan vigente](Plan%20de%20trabajo.md).

## Última actualización · landing y estabilidad RADIO/WAV

- README raíz recuperado como presentación completa: badges, imágenes por función, módulos y arquitectura; actualizado a V17. Regla permanente en `AGENTS.md` y memoria, por pedido explícito del usuario. No volver a reemplazar la landing por un índice técnico.
- WAV incorporado: dos chunks PCM en vuelo al reproducir, capacidad anunciada hasta 30 bloques, ACK atendidos entre tramas. La combinación pasó 3×120 s ADC16/76226→50 kHz; las variantes parciales fallidas siguen descartadas. Con producción pasaron seek/Stop/replay/EOF/reinicio. ADC14/100000→50 kHz pasó 60 s; luego SIGBUS en cierre Qt/SIP de Python, ya con Q restaurado (no underrun durante captura).
- RADIO: transición de estación con rampa 5 ms a neutral y 20 ms de entrada. Se conserva explícitamente como transición la duración de audio de sintonía anterior descartado, sólo dentro de sesión/reloj iguales. Control antes/después, 120 s y 58 resintonías: reserva mínima host 0→7670 muestras; sin cortes ni dropped/fatal. No equivale a aceptación global de todos los perfiles.
- Sweep/Chirp: saltos de inicio/fin medidos físicamente, hasta 1,62/0,74 V en este caso; suavizado de firmware sigue pendiente. No se cambió firmware.
- Resultado y evidencias: [RADIO/WAV y clics](docs/ESTABILIDAD_RADIO_WAV_CLICS_V17.md). Q restaurado a ADC8/1,6 MS/s y generador OFF, mismo firmware. Reiniciar monitor para cargar cambios host; no hace falta Preparar Q.

## Trabajo anterior

Se corrigió el orden de ACK del generador: el bloque ADC acumulado se publica antes y se respeta el executor DSP. Regresión antes/después reproducida. Tonos CH2/CH2 pasó 5/5 puntos entre 20 y 1000 Hz con asentamiento 200 ms; Sweep dibuja; Pulso sigue sin detectar estímulo con 1 y 10 ms. Ver [Bode](docs/DIAGNOSTICO_BODE_SIN_CURVAS_V17.md). RADIO sin A0 demodula y dibuja en prueba local a 8 bits/1,6 MS/s; salida por parlantes PC no implementada.

Nuevo corte real RADIO/A0 a ADC8/1,6 MS/s (18:39:17): DAC UNDERRUN, fuente sin error ni hits de lazo. Se incorporó registro acotado de huecos DSP/chunks y pausas de transporte, con tasa de salida explícita. No se cambiaron reservas ni política de entrega. [Seguimiento y pruebas](docs/DIAGNOSTICO_RADIO_A0_ADC8_1600_V17.md). Causa todavía abierta.

Se ordenó documentación sin cambiar la lógica: el README anterior y los registros acumulados se conservaron en `docs/historico`. Las fuentes activas siguen en sus rutas; experimentos, capturas y respaldos se mantienen.

Q: sólo Scope V17 como app de usuario, activa. V16 y Send1400 se retiraron después de exportar/verificar ZIP y SHA256. Los ejemplos Arduino se conservan. Firmware antes/después idéntico: `96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9`. [Limpieza](diagnosticos/resultados_v17/cleanup_apps_20261019_160438.json).

## Retomar Bode

El usuario confirmó **CH1 = antena**. El par predeterminado CH1→CH2 no puede medir correctamente el estímulo de A0 en ese cableado. Última conexión confirmada de A0 era CH2/A3; reconfirmar si se cambia el montaje.

Se corrigió Pulso/Sweep para detectar el estímulo usando la referencia seleccionada. Sweep CH2/CH2 produjo curvas físicas válidas. El seguimiento posterior validó Tonos sólo a 20–1000 Hz con 200 ms de asentamiento; Pulso continúa pendiente. Los selectores se ampliaron a 150 kHz para Tonos/Sweep/Chirp y 200 kHz para Pulso, con límite final <0,45×Fs; comprobación local de límites/intermedias correcta, no validación física de Bode a esos extremos.

## Incidencias abiertas

GUI atrasada en RADIO/Scan, cortes variables WAV y aceptación global RADIO/A0 continúan abiertas. No incorporar candidatos aislados sólo porque pasaron una corrida. Ver el plan y los informes enlazados desde el estado actual.

Herramientas CLI: indicar V17 explícitamente, porque el valor predeterminado V16 se conserva por compatibilidad. La limpieza no cambió configuración ADC/DAC ni reinició V17. Comprobar propietario antes de operar Q.

[Registro anterior completo](docs/historico/CONTINUIDAD_ACUMULADA_20261019.md).

Control final del cambio de orden: RADIO/A0 ADC8/1,6 MS/s durante 60 s, Python 3.13, sin cortes, con restauración y firmware idéntico. Q libre, generador OFF. No cerrar incidencias intermitentes por este control.
