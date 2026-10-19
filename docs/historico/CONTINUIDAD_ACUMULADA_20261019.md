> Archivo histórico conservado el 19/10/2026. Las instrucciones y estados siguientes corresponden a sus fechas; para continuar usar el [estado vigente](../ESTADO_ACTUAL_V17.md). Los enlaces relativos Markdown se ajustaron desde la raíz original.

## 16/10/2026 — objetivo1,5MS/s sondeado; integridad sostenida conarranqueescalonado

Campañaadc8_target1500_probe_v17 cerrada,Qrestaurado. RecetaB:ADC8CH1,
SPI40,WORD/READY50us/kind20/864/N3456;aplicar112 ybombear2s,después106.
106=1.509.433,962S/s. SondeosA directo3456:1/3integridad;Bescalonado3456:3/3;
Cdirecto6912:2/3;Descalonado6912:3/3. SóloB tuvo3/3holgura ypasóalargo.
B completó60+3×120 íntegros:633,597,120muestras,dropped/fatal0. Márgenes
11,62/11,72/11,41/11,87%,colapico3/4/3/3. Integridadaceptada;holgurano.
No decir target_qualified:ese campo requiereambos. Recetaexperimental guardada
en target1500_integrity_profile.json yRESULTADOS.md. Nada deproducción.
FuentesMCU/relayidénticasaSPI40sostenido;únicocambio preparacióndelhost.

Qrestaurado exactoADC8/1403508SPI,generadorOFF/otroscampos,relay/entorno,
firmwareSHA3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c,
14,031,360muestras/10s yclock33,333M.App experimentaldetenida.
No haycampañaactiva.Pendiente reducir/localizar pico4 sinbajarobjetivo1,5M.
No aceptacióneléctrica universal,analógica/GUI/DSP/dual/UART.

## 16/10/2026 — candidato para1,5MS/s: arranqueescalonado envalidación

Activa campañaexperimentos/adc8_target1500_probe_v17/run.py,run.log.
12sondeos:AdirectoN3456 pasó1/3integridad/holgura;Bescalonado112por2s→106
N3456 pasó3/3ambos;CdirectoN6912 pasó2/3integridad0/3holgura;Descalonado
N6912 pasó3/3integridad0/3holgura. SóloB elegible paraaceptación.
B ya pasó60s conintegridad+holgura;siguen tres120s independientes.
Objetivo106ticks=1.509.433,962S/s,>=1,5M;SPI40/WORD/kind20/864/READY50us
originales,sinmodificarMCU/relay,sólo preparacióndelhost2s antes desubir.
Trazaextra512frames activa sóloenpantallas,desactivada encorridaslargas.
Un dueñoQ,nonooperarhasta consultarreporte.Finallyrestauraestado/hash/
relay/clockoriginal+10s.Sinproducción niaceptacióneléctrica universal.

## 16/10/2026 — objetivo redirigido a1,5MS/s; sondeo dearranque activo

Usuario pidió:sondear cómo llegar a1500kHz,no seguir validando tasas inferiores.
Se interrumpió adc8_spi40_search_v17 conSIGINT yrestauróQ exacto,hash y10s.
108completó60+3×120 íntegros,pero sinholgura.105/106 pasaron60s pero fallaron
settle trasreiniciar para120s,dropped1/cola4/slackpositivo.104falló2arranques.
110longparcialinterrumpido,no acreditado. VerRESULTADOS de search.

Activoahora:experimentos/adc8_target1500_probe_v17/run.py,run.log.
Objetivo106ticks=1.509.433,962S/s,el punto fijo>=1,5Mcon160MHz.
FuentesMCU/relayintactosSPI40/kind20/864/WORD/READY50us/TCPporframe.
A directoN3456;B112por2s luego106N3456;CdirectoN6912;D112por2s luego106N6912.
3×10s por esquema,enordenABCDBCDACDAB. Traza primeros512frames106 sóloen
sondeos;se desactiva paraaceptación. Acontrol,nuncasepromociona ignorando
fallos previos.B/C/D sóloelegibles3/3integridad+holgura,entonces60+3×120s.
Un dueñoQ,no operarantes derevisarreport. Finallyrestauraestado/hash/relay/
clockoriginal+10s. Sinproducción niaceptacióneléctrica universal.

## 16/10/2026 — búsqueda superior SPI40 en curso

Usuario eligió buscar tasa mayor antes de incorporar. Activo runner
experimentos/adc8_spi40_search_v17/run.py,run.log;reportprobe_1400_20261016_084742.
Un dueñoQ. MCU/relayoriginalesidénticosSPI40,kind20/864,N3456,READY50us.
Referencia112ysondeos111/110/108/106 pasaron10s conholgura.104fallósettle dos
veces:dropped1,cola4,slackpositivo.105refinó ypasó10s y60s,pero fallósettle
trasreiniciopara120s.106tambiénpasó60s yfallósettle enprimer120s.
No aceptar reintentos selectivos.Los fallos dearranque también descalifican.
Sigue validación108/1,481481MS/s;consultarreportantes deoperarQ.
Porperfil60+3×120,máximo120,no600. Buscarintegridad yholgura aparte.
FinallyrestauraADC/generador/firmware/relay/entorno,hash,10s yclockoriginal.
Sinproducción,compactación niaceptacióneléctrica.

## 16/10/2026 — SPI40 sostenido cerrado: integridad y holgura aceptadas

ADC8/CH1 ticks112=1.428.571,429S/s, kind20/864,N3456,WORDDMA,READY50us,
TCP por frame. 60s +3×120s independientes: 599,656,608 muestras íntegras,
dropped/fatal0. Márgenes medios16,90/17,08/17,41/17,42%,cola pico2/2/2/3,
slackmínimo>=1083,6us. Sin600s ni reintentos. qualification_integrity_accepted
 yqualification_headroom_accepted=true. +1,786% vs1.403.508,772S/s.
40 configurados confirmados clk_src120M/DFS6/div3;noSCKeléctricomedido.
No garantiza timingeléctrico universal ni analogía/GUI/DSP/dual/UART.

Detalle:experimentos/adc8_spi40_sustained_v17/RESULTADOS.md yqualification.json.
Reporte:probe_1400_20261016_083129/report.json;sourcehashAudit cerrado.
FuentesMCU/relayidénticas alpiloto. Sincompacto ni otroscambios.
Qrestaurado exactoADC8/1403508SPI,generadorOFF/otroscampos,relay/entorno,
firmwareSHA3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c,
14,030,496muestras/10s,restore_integrity_ok=true yclockoriginal33,333M.
App experimental detenida.No incorporación productiva ni campaña activa.

## 16/10/2026 — SPI40 sostenido en curso

Usuario pidió seguir con validación sostenida40MHz (sincompacto).
Runner:experimentos/adc8_spi40_sustained_v17/run.py,run.log.
Reporte:probe_1400_20261016_083129/report.json. Un dueñoQ,consultarreport
antes de operar. MCU/relay idénticos alpiloto,kind20/864,N3456,READY50us.
Preflights33,333/40 a250k pasaron yrelojesconfirmados;60s112 pasóintegridad
ymargen16,90%,cola2. Siguen tres120s independientes112/1,428571MS/s.
Sin600s.Sinaceptacióneléctrica ni cambiosproductivos.
SnapshotADC8/1403508SPI,generadorOFF yotroscampos exactos;finallyrestaura
firmware/relay/entorno/estado,hash,10s yclockoriginal. No arrancar otro dueñoQ.

## 16/10/2026 — reloj40 ycompactación cerrados; Qrestaurado

Secuenciaautorizada completada.SPI40piloto:origen120M/DFS6/div3 confirmado,
118.479.456muestrasíntegras.114/112pasaron30s yholguracorta;110pasó10s pero
colapico4,sinholgura.Noaceptaciónsostenida/eléctrica ni promoción.
Lectorcorregido usa clk_srcNOCACHE yregistroDFS;ramaclk_rate cacheaba100M.
Detalle:experimentos/adc8_spi40_pilot_v17/RESULTADOS.md.

CompactoADC8CH1alta velocidad implementado kind21:908muestras/992B vs864,
header80,CRC/continuidad/config/epoch/timestamps/métricas conservados.
Trescampañas aisladasa33,333MHz:inicial yO2sinmejora,prepare~80us;
directaeliminamemmove,buffers992,prepare~34,8us vsA35,2.
Directa8×30sABBA:339,661,888muestrasíntegras,dropped/fatal0,peroenvío/muestra
empeoró0,695%114 y1,060%112;2/4Bsinholgura. Gatefalse,sinpruebaslargas/promoción.
6testsC/PythonASAN/UBSAN pasan;12extrasrechazados,APPLIED ylegacy640 correctos.
Detalle:experimentos/adc8_compact_direct_v17/RESULTADOS.md;fuenteshashAudit.

Qrestauradoal cierre exactoADC8/1403508SPI,generadorOFF/otroscampos originales,
relay/entorno original,firmwareSHA3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c,
14,032,224muestras/10s,restore_integrity_ok=true.App experimentaldetenida.
Sin producción/GUI ni40+compacto combinado.No haycampañaactiva.

## 16/10/2026 — compactación directa en curso tras dos versiones sin mejora

adc8_compact_v17 cerrada8×30síntegros,peroenvío/muestra empeoró3,724%114 y6,254%112.
adc8_compact_o2_v17 cerrada8×30síntegros,peroenvío/muestra empeoró4,325%114 y6,124%112.
Ambas mantienenprepareMCU~80us vs~35usA,4/4Bsinholgura;sinpromoción.
AmbasrestauraronQ exactoADC8/1403508SPI/generadorOFF/firmwarehashoriginal.

Activa ahora experimentos/adc8_compact_direct_v17/run.py,run.log.
Construyeheader80/payload908 directamente,sinmemmove;buffers992originales.
Mismo wirekind21,decoder yCRC.6testsASAN/UBSAN pasan,encoder directo byteidéntico
aloráculo para todoscounts4..908 yfallos. Sigue a33,333MHz,no40.
ABBA114/112,N3456A/3632B,30s;gateµs/muestra>=2%+holguraB,si pasa60+3×120s.
Un dueñoQ,consultarreport antes deoperar;alwaysrestore exacto+hash+10s.
Piloto40ya cerrado:118.479.456muestras íntegros,40configconfirmados,110ticks10s
cola4,noholgura,noaceptacióneléctrica ni sostenida.Detalleadc8_spi40_pilot_v17.

## 16/10/2026 — SPI40 piloto cerrado; compactación en curso

Usuario autorizó probar40MHz aun sin margen eléctrico,y luego compactar.
Piloto válido:experimentos/adc8_spi40_pilot_v17/probe_1400_20261016_005838.
40 configurados confirmados origen120M DFS6/div3 (noSCKeléctricomedido).
118.479.456 muestras íntegras:640/10s,114/30s,112/30s,110/10s en40;
controles33,333M640/114por10s. B114/112 holgura corta;B110 cola4,sinholgura.
No aceptación sostenida/eléctrica ni promoción. Qrestaurado exactoADC8/1403508,
generadorOFF,hashidéntico,14.032.224muestras/10s yreloj100M/DFS5/div3.
Intento005453 se detuvo porlectura de rama clockcacheada100M,no error de
integridad. Lectorcorregido usa clk_srcNOCACHE yregistroGCC,repitió trasrestaurar.

Compactación autorizada en ejecución:experimentos/adc8_compact_v17/run.py,
run.log. Kind21ADC8CH1ticks<=114,cabecera80,payload908,CRC992Bigual.
Preserva métricas32bits,transportfaultbit,countflags. Otrosformatos kind20.
A N3456/864,B N3632/908,ABBA114/112×30s a33,333M,no40paraaislar.
5testsC/Python conASAN/UBSAN pasan. Driver/MCU sóloexp,sinproducción.
Si gate normalizadoµs/muestra>=2% yholguraB pasa,60+3×120s112N3632.
Siempre restaurarhash/ADC/generador/relay/10s. Consultarreport actual antes
operarQ;no segundo dueño mientrasrunner activo.

## 16/10/2026 — TCP batch2 descartado

ABBA1/2framesTCP,ADC8CH1ticks114/112,N3456,8×30s:339,658,272muestras íntegras,
dropped/fatal0.B empeoró envío0,632%114 y4,517%112;4/4B margen<10%,cola2.
Gatefalse,sinprueba larga/promoción.Conservar1frame/send.READYspin50,SPI38
solicitado yMCUWORD idénticos.Buf1984B,control inmediato,timeoutobjetivo1ms.
12lectores extra rechazados;4pruebas250kS/s yAPPLIED correctos.TestCbatch pasó.
Qrestaurado snapshotADC8/1403508SPI,generadorOFF,hashoriginalidéntico,
restore_integrity_ok=true,14,031,360muestras/10s.App experimental detenida.
Detalle:experimentos/adc8_tcp_batch_v17/RESULTADOS.md.Sinproducción.
Próxima vía sugerida:formatoADC8alta velocidad compacto;no implementado.

## 16/10/2026 — READY spin0 descartado

ABBA50/0µs,ADC8CH1ticks114/112,N3456,8×30s:339,659,136muestras íntegras,
dropped/fatal0. Spin0 empeoró envío7,342%114 y9,583%112;4/4B sinholgura,
4/4A conholgura. Gatefalse,sinprueba larga/promoción.Conservar50µs.
12lectores extra rechazados,primario yAPPLIED correctos. TestCwait pasó.
Qrestaurado al snapshot vivoADC8/1403508SPI (noADC10 previo),generadorOFF,
hashoriginalidéntico,restore_integrity_ok=true,14,031,360muestras/10s.
App experimental detenida,sinproducción.Detalle:experimentos/adc8_ready_sleep_v17/RESULTADOS.md.

## 16/10/2026 — 40 MHz no respaldaldado por presupuesto MISO

Hoja oficial Qualcomm QRB2210 tabla3-26 pág67:setupMISO mínimo5ns.
ST tabla150 pág303:tvSO máximo12ns a1,8V/range1/pines aplicables.
A40M semiperíodo12,5ns <12+5ns;saldo-4,5ns antes de placa/duty.
A33,333M saldoideal-2ns:no invalida evidencia física,pero no garantiza
margen eléctrico universal.41,5M deST asume setupmaestro0.No piloto40M.
Revisión documental,sin cambiar firmware/relay/reloj. Detalle y fuentes en
experimentos/adc8_spi_clock_v17/RELOJ_SIGUIENTE.md. Vía siguiente:coste por
transacción conservandoREADY,o capturaGENI ajustada sólo si se documenta.

## 16/10/2026 — tabla efectiva DFS resuelve discrepancia de reloj

Lectura RO fija del RCG S5 0x0141f738:DFS habilitado/control0x2b/nivel5.
Tres snapshots iguales. Fuentes efectivas19,2/32/48/64/96/100/120MHz,
slot7 repite19,2. No hay75/80M de la tabla estática upstream.
ModeloGENI con tabla física reproduce38solicitados=>100/div3=33,333MHz.
38,5/39 tampoco suben; siguiente punto40MHz=120/div3. No se cambió reloj,
firmware ni relay. Sigue pendiente timing/setup Qualcomm;40 no certificado.
Evidencia:experimentos/adc8_spi_clock_v17/clock_levels_live.json,
clock_levels_decoded.json y RELOJ_SIGUIENTE.md. Lector fijo O_RDONLY/PROT_READ.

## SPI GENI: reloj y NSS medidos — campaña cerrada

Experimento adc8_spi_clock_v17.38MHz solicitados=>33,333MHz configurados:
fuente100M/div3,GENIwrapper3.0,DMA1/GSI0,lecturas fijas sóloRO sinwrites.
Kernel7.0 tiene ftrace/kprobes/dynamicdebugOFF. MCUexperimental captura
NSSconcallbackEXTI PG12 sin cambiarMODER/AF. Dos casos30s114/112 íntegros,
65.520pares NSS/ioctl alineados por secuencia,0mismatch/negativos.
NSSmedio252,7us,ioctl339–342us,residualfueraNSS86,5–88,8us estimado.
No es CPU puro kernel ni medición eléctrica SCK;IRQ y relojes independientes.
No se cambió SPIHz ni se calificó tasa.50MHz no justificado por límites
full-duplex deST. Antes de probar otro reloj:representabilidad+timingambos.
Qrestaurado exactoV17ADC10/1167883SPI,generadorapagado,hashidéntico,
restored/restore_integrity_ok=true,configuraciónSPIreleídaidéntica.
App experimental detenida,sinproducción. Dos tests locales pasan.
Detalle:experimentos/adc8_spi_clock_v17/RESULTADOS.md.

## 15/10/2026 — accept16 A/B cerrado y descartado

Experimento adc8_accept_interval_v17:ABBA,30s114/112 por bloque,N3456,
MCUreferencia idéntico,un relay con envintervalo1/16. Ocho casos íntegros,
339.660.864 muestras,dropped/fatal0. B empeoró envío2,744%114 y4,609%112,
todosB margen<10%;sinvalidación larga ni incorporación. Conservar accept1.
Pruebas físicas:12lectores adicionales rechazados,sindatos ni reemplazo del
primario;continuidad y APPLIED posteriores correctos. B cierre4,03–12,23ms
clientevisible,no bounduniversal. Prueba C política/desborde pasó.
Qrestaurado exactoV17ADC10/1167883SPI,generadorapagado,hashidéntico,
11.675.400 muestras íntegras en10s. App experimental detenida.
Detalle:experimentos/adc8_accept_interval_v17/RESULTADOS.md.

## 15/10/2026 — Perfil detallado relay cerrado

Experimento adc8_relay_profile_v17:4×30s114/112/112/114,N3456,MCUreferencia.
Todos íntegros,dropped/fatal0. accept~32us/EAGAIN100%;recv~5us/EAGAIN100%;
send67–74us,siempre992B,sinenvíos cortos ni errores en ventanas medidas.
Candidato siguiente:no consultar accept cada trama mientras haya cliente;
A/B acotado (p.ej16tramas),manteniendo admisión por vuelta sin cliente y
rechazo de lectores extra,sin reemplazar al activo. No implementado aún.
No prometer ganancia aditiva:READY/MCU/relay se solapan. Tres tests pasan.
Qrestaurado exactoV17ADC10/1167883SPI,generadorapagado,hashidéntico,
restored/restore_integrity_ok=true. App experimental detenida,sinproducción.
Detalle:experimentos/adc8_relay_profile_v17/RESULTADOS.md.

## 15/10/2026 — A/B PING por palabras cerrado

Experimento adc8_ping_word_v17:A–B–B–A,30s114/112 por bloque,arranques
independientes. Ocho casos íntegros,dropped/fatal0. B reduce RXcheck24–27%,
pero envío mejora2,583% a114 y sólo0,815% a112. No pasa gate>=2% ambas tasas;
sin60+3×120s ni incorporación productiva. Cuatro B pasaron holgura en30s,
no aceptación sostenida. Dos pruebas locales equivalencia/gate pasan.
Q restaurado exacto V17ADC10/1167883SPI,generadorapagado,hashidéntico,
restore_integrity_ok=true. App experimental detenida. Selector local A.
Evidencia:experimentos/adc8_ping_word_v17/RESULTADOS.md.
Próximo diagnóstico:separar recv/accept/send en relay hostIO,con ioctl/READY
simultáneos,antes de elegir un cambio de transporte.

## 15/10/2026 — Perfil de etapas ADC8 cerrado

Experimento aislado adc8_stage_profile_v17:controlOFF30s114 + perfilON
30s114/112/114,pasaron íntegros,dropped/fatal0. RXcheckMCU88,7–92,9us/trama,
packing33,3us,CRC TX34,8–34,9us,validación+copia229–230us/nodo.
Relayioctl338–339us,hostIO105–106us por trama. Tiempos inclusivos y solapados;
no son CPU exclusivo ni aceptación de tasa. Perturbación instrumental posible.
Próximo candidato elegido:valid_ping por palabras,conCRC y cada byte intactos;
no implementado todavía. HostIO agrupa recv/accept/send,potencial límite global.
Ambas campañasrestored/restore_integrity_ok=true,QV17ADC10/1167883SPI,
generadorapagado,hashidéntico,11.676.096 muestras íntegras en10s al cierre.
App experimental detenida. Sin cambios productivos. Tres tests locales pasan.
Detalle y evidencia:experimentos/adc8_stage_profile_v17/RESULTADOS.md.

## 15/10/2026 — WORD corregido: campaña cerrada y Q restaurado

Burst Zephyr se expresa en bytes: corregido width4/burst1 a width4/burst4,
solamente en experimento. READY resuelto. WORD ticks110 pasó10s pero falló
asentamiento de60s; ticks108 falló dos veces. Pérdida nodo,cola4,slackpositivo.
Ticks112 y114 completaron60+3×120s íntegros. Ninguno pasa holgura completa:
112 llegó a cola4;114 tuvo margen9,962% en una repetición. Sin ganancia
sostenida adicional sobre BYTE1,428571MS/s;sin incorporación productiva.
Q restaurado exacto V17ADC10/1167883SPI,generadorapagado,hashidéntico,
11.676.792 muestras íntegras en10s. App experimental detenida.
Informe: experimentos/adc8_spi_word_v17/RESULTADOS_WORD.md.
Siguiente vía: medir costes de salida/sellado/packing antes de elegir cambio.

## 15/10/2026 — ADC8: ensayo BYTE/WORD cerrado y Q restaurado

Retomado hilo01a140bd-03a4-7861-97dd-c030c38f171c. BYTE+CRCSIZE7 pasó
60s+3×120s a ticks112/N3456 =1.428.571,429 muestras/s CH1 ADC8:
599.655.744 muestras, dropped/fatal0. Integridad sí; holgura no porque
una repetición llegó a cola4, aunque márgenes medios10,179–12,179%.
WORD no recibió READY al arrancar; sin medición ni conclusión de tasa.
Sin incorporación ni cambios productivos. Q restaurado exactamente a
V17 ADC10/1167883 SPI,generadorapagado,identidad firmware igual;
11.676.792 muestras íntegras en10s,ok/restored/restore_integrity_ok=true.
App experimental detenida. Informe: experimentos/adc8_spi_word_v17/RESULTADOS.md.
Abiertos: diagnosticar WORD,buscar holgura sostenida y decidir incorporación.

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

## 14/10/2026 — Continuación del hilo 01a13897 cerrada

FILTER inicia OFF sin ejecutar filtro ni acumular historial. DSP RADIO/FILTER
separado de GUI con trabajador único, cola acotada a ocho y generaciones;
trigger audio con alineación fraccional sin modificar muestras. Remuestreo,
FFT y registros numéricos optimizados (16 bytes/muestra); FFT/dibujo siguen
en GUI. 92 pruebas locales pasan. Cadena completa offline120s pasó:
6092lotes,168431616RF,4800243audio,cola pico5,sin errores.
No aceptación física conjunta RADIO/FILTER/FFT ni FPS visibles/analógica.
Detalles: docs/AUDITORIA_EFICIENCIA_V17.md.

Barrido físico aislado CH1 ADC10/12/14 completado:60+3×120s por finalista,
sin600s según instrucción del usuario. Máximos integridad/holgura enHz:
ADC10:1167883,212/1142857,143; ADC12:981595,092/930232,558;
ADC14:851063,830/833333,333. Integridad no implica holgura; máximos de
holgura superan10% envío medio,cola<4,slack>0 en todas las etapas.
Sin promoción a producción ni aceptación analógica/dual/cargaDSP.
Resultados: experimentos/maxfreq_optimized_v17/RESULTADOS.md.
El proceso anterior quedó interrumpido en última repeticiónADC14;
resume.py verificó fuentes locales/desplegadas y completó sólo lo pendiente.
Informe final: probe_1400_20261014_084703/report.json en ese directorio;
ok/restored/restore_integrity_ok=true. QV17 restaurado ADC10/909090SPI,
generadorapagado y campos exactos,hash idéntico al snapshot;
9087712 muestras íntegras en10s. Appexperimental detenida.
Reiniciar GUIV17 para usar las mejoras del host. Próximos gates separados:
aceptación física conjunta/visual de RADIO y decisión de incorporar perfiles.

## FFT V17 ampliada hasta 65536 muestras

Agregadas opciones 16384, 32768 y 65536 a FFT y heatmap, con selectores
sincronizados; predeterminado 2048 conservado. A ADC8/1403508, 65536 muestras
cubren 46,695 ms y dan 21,416 Hz entre bins. SINGLE RF de 65536 probado con
señal sintética y pico conocido; 30 pruebas de espectro/RADIO aprobadas.
Sólo host: reiniciar V17, sin operación ni cambio de firmware Q. No ensayo
físico de carga GUI con esos tamaños. Scan mantiene su configuración propia.

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

## 2026-10-13 — Auditoría Astra y corrección RADIO V17

Usuario confirmaFS40kHz del canalRADIO y pide búsqueda NORMAL, también durante
RADIO TEST; no usar portadoras conocidas para censurar candidatos.
FS salida40kHz predeterminada, selector20/40/48 mantenido; tonoRADIO TEST0–4kHz
enpasos1kHz. No requiere nuevo firmwareQ; sólo reiniciar GUIV17.
Astra: plan válido, implementación incompleta: DSP enGUI y señalesQt sinlímite.
Historial circular/bufferresampler acotados no limitaban entregas pendientes.
DSP offline medidoantes20/40k:5,3/7,8ms porbloque20ms; trasprecálculo57/114 fases,
2,6/3,4ms. Radio40+Filter+FFT offline15s:750lotes procesados, pico5pendientes,
atrasomax77ms, procesamientomedio4,97ms, sin errores. No aceptación física.
EntregaQt ahora acotada a8lotes conack thread-safe; sobrecarga detiene adquisición
conerror explícito, sin acumulación ilimitada. DSP sigueGUI: separación aotro
hilo/proceso y ensayo físico sostenido siguen pendientes.
Scan manual siempre5–600kHz, independienteFFTvisual. Umbral ajustable6–30dB
sobre piso local (inicial12), persistencia2/3o3/3. Piso estimaentorno±10kHz
excluyendo lóbulo±100Hz; nivelesFFT estimadosdBFS, exceso sobrepiso y persistencia.
No corte relativo alpico más fuerte ni filtro porfrecuencias delgenerador.
ZOH reproduceimágenes/aliaspersistentes; no etiquetarlos falsos desdeunasolacaptura.
TestADC8 recupera portadoradébil~54dB debajo de otra con ruido/dither.
Tono4kHz recuperado aFS40 pero atenuado porfiltrosactuales (~4dB frente1k).
Reportes:radio_cost_before/after.json, radio_gui_offline_15s.json,
audio_tones_0_4k_offline.json en diagnosticos/resultados_v17.
Sin conexión, reset ni cambio de firmware delQ en este incremento.

## 2026-10-13 — V17 instalada, RADIO TEST con diales y limpieza Q

V17 MCU/app/relay activos, primera tramaSPI verificada. Portadoras/tono con
InstrumentDial64×64; tono0–2kHz y cambios durante Play coalescidos200ms.
Tabla AM ahora usa LUT seno existente y cálculo entero; pruebas de demodulación
siguen pasando. Compilación enQ:121788bytesflash/259476RAM,2668libres.
Fallos previos GPIOREADY/redDocker y arranque conservados en resultados_v17;
no atribuir el READYtimeout exclusivamente aRAM sin evidencia adicional.
RADIO TEST real verificado con amplitudcero: Play, portadoras20→21 y40→41,
tonos1/2/0kHz. No ensayo analógico A0→A2 todavía.
Q restaura ADC14/40000 SPI,generadorapagado con campos exactos del snapshot;
401408 muestras en10s tras limpieza, dropped=fatal0,ok/restored=true.
45tests locales aprobados.
Retiradas 39 apps antiguas del monitorQ y sus recursos;
quedan scope-v16 (fuentes conservadas, estadoCLIuninitialized) y scope-v17 activa.
Archivo recuperable:respaldos/unoq/apps_antiguas_antes_v17_20261013.zip.
Código histórico local sin eliminar; backupV16preinstalacion conservado.
Reportes:diagnosticos/resultados_v17/radio_test_installed.json ycleanup_old_apps.json.

## 2026-10-13 — V17 RADIO TEST preparado

RADIO TEST implementado como modo de generador V17. Dos portadoras de1–50kHz
(distintas, pasos1kHz), tono0–5kHz en pasos1kHz, AM50% compartida; tono0 deja
portadoras sin modular. TablaDAC256muestras/256kS/s, relojTIM6exacto divisor625,
DMAcíclico; no utiliza WAV50kHz ni transmisión de muestras desdePC.
AmplitudVpp es cota de la suma, offset ajustable; nunca excede niveleslow/high.
El modo usa mode3 de protocolo generador y capabilitybit4; firmware/relay/
decoder V17 actualizados. Play permanece bloqueado sin esa capacidad.
Pruebas compilan la tablaC++ real y verifican portadoras/bandas laterales,
recuperación de tono1kHz en ambas por demoduladorCH1 y contrato/UI Play/Stop.
Compilación completa Arduino/Zephyr aprobada:118584bytes flash,258728bytesRAM,
3416byteslibres informados. Binarios en/private/tmp/v17-radio-test-build.
No instalación ni ensayo físico realizados aún; RAM informada no acredita arranque
ni margen físico.
Para loopback conectar A0 a A2, seleccionar ADC8/CH1 a1,4035MHz, generar
20/40kHz con tono1kHz y usar Scan/RADIO. Preferir separación de portadoras
mayor que el anchoAM9kHz. Recepción RADIO sólo sintoniza desde5kHz.
Tono5kHz puede quedar atenuado por el filtro audio actual cercano a4kHz;
validación inicial recomendada con1kHz. La tabla a256kS/s todavía requiere
aceptación física de amplitud/imagenDAC y carga conjunta con ADCmáximo.

## 2026-10-13 — V17 Scan manual independiente

Scan bajo demanda: botón Scan realiza una búsqueda RF independiente de la
FFT visual. Captura los últimos3×65536 valores CH1 continuos y trabaja en un
hilo aparte; no vuelve a ejecutarse hasta pulsar Scan. Ventana Hann fija,
promedio de potencia, umbral10dB sobre mediana local, prominencia6dB y
persistencia en2/3 bloques. Agrupa candidatos a menos de4,5kHz por el más fuerte.
Las flechas recorren la lista guardada, sin retocar la sintonía al terminar Scan.
Cambiar/reiniciar adquisición invalida resultados, incluso búsquedas en curso.
Son candidatos RF, no estaciones AM certificadas. Ensayos sintéticos aprobados;
coste concurrente con Q y aceptación analógica siguen pendientes.

## 2026-10-13 — V17 RADIO integrada, salida20kHz

Confirmado ADC8 (9bits era typo). PanelRadio: CH1/ADC8 perfil1403508Hz,
sintonía550kHz inicial, selectorFS20/40/48kHz;20kHz por defecto.
radio_stream.py conserva estado de remuestreo sinc y timelineaudio independiente.
FILTER fuenteRADIO usa FS salida real para diseño/cortes y procesamiento.
Gráfico temporal y FFT/espectrogramas continuos toman historialaudio;
no mezclar RF/audio en eje común. FFT sintética recupera1kHz aFS20kHz.
41tests pasan: DSP/remuestreo fragmentado, alias, interfaz/tasas, Filter/Bode.
V16 hashesintactos; ningún acceso alQ. Falta prueba física de recepcion/carga.
Pendiente grabaciónaudio,THRU y trigger/SINGLE audio, selecciónpicosFFT RF.
Estado y alcance: docs/ETAPA_III_V17.md y monitor/v17/README.md.

## 2026-10-13 — V17 AM: base y DSP offline

V17 creada desde V16 actual: monitor/v17, arduino/v17 y tests/v17.
Hashes originales en docs/v17_base_manifest.json; V16 verificada sin cambios.
Herramientas, catálogo y editor permiten selección V17 explícita; defaults V16.
No se copiaron calibraciones de identidad V16 ni se operó el Q.
Motor radio_am.py: NCO continuo, filtros/diezmado multietapa, envolvente,
bloqueo DC/audio. FS salida real43859,649Hz con RF160MHz/114; sin remuestreo.
43 tests offline/UI heredada aprobados: AM conocida, fragmentación, interferente,
silencio, discontinuidad, filtro y Bode. Timing DSP medio0,47ms/bloque3456;
no acredita margen físico. No prometer rechazo60dB sin barrido de alias.
Pendiente integración RADIO con timeline audio independiente, FILTER/análisis/
grabación, conversión de tasa y THRU; después AM física conocida y antena.
Plan detallado y estado: docs/ETAPA_III_V17.md.

## 2026-10-13 — Incorporación V16 ADC8/CH1 1,4035 MHz cerrada

Continuación del hilo 01a135c8-7ed5-7413-89a6-88e013600d90.
Reporte físico integration/physical_20261013_192502/report.json: ok/restored=true.
Pasó60+3x120+600s, dropped=fatal0 y continuidad completa. En producción,
margen7,017–9,822%, cola pico4/4: acepta integridad, NO holgura.
SPI38/FIFO10/espera50us/anillo3 se activan sólo ADC8 CH1 114ticks/N3456;
retornos ADC10 y perfiles ADC14 dual/ADC16 con scheduler normal0 verificados.
GUI completada: integration/gui_20261013_195708.json ok/restored=true;
8.832.672 muestras a1,4035MHz y WAV ADC14/40kHz con233.730frames estéreo.
Qt offscreen: no aceptación visual ni FFT/trigger/SINGLE bajo carga/analógica.
WAV permanece bloqueado a tasa alta. Referencias Bode previas conservadas,
ligadas al firmware anterior; no trasladar calibración sin nueva medición.
Q restaurado ADC8/1221374 SPI,generadorapagado con campos previos;
3.664.224 muestras íntegras en3s. Firmware incorporado fa7b490d676aa267a8a797dd0a1c409e1c30740e4bd4fb3b847a02707db41a47.
Detalle: experimentos/send1400_v16/integration/README.md.

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

## Campos Bode y referencias incorporadas · 13/10/2026

Campos de Bode alineados en dos columnas iguales, altura28 px; Asentamiento,
Pulsos y Método ocupan el mismo ancho que Desde/Hasta. Se conserva geometría
tras normalización general de controles de app.py.
Incorporadas tres referencias tone crudas en monitor/v16/calibraciones:
ADC14/40000, ADC16/40000 y ADC16/76226. Promedio de los dos primeros barridos,
tercero independiente; todos accepted=true, integridad y restauración verificadas.
Identidad ligada a Q1060031107 y hash de firmware79b0bd376fe26b11b82cbef98fb1cba57ef752f7528c14434c6fef4de295092c.
Cobertura medida20Hz–5kHz; fuera de banda se conserva compensación estimada.
Tonos muestra «medido» en estos perfiles con Q identificado; otros perfiles
y métodos conservan «estimado». No se inventaron referencias para Pulso/Chirp.
Ocho tests pasan: dimensiones reales de los tres paneles, referencias instaladas,
tercer barrido corregido e incompatibilidad de firmware/método, además de
compensación y control unificado. Sin nueva operación ni cambios de firmware Q.

---

## Corrección Bode unificada · 13/10/2026

Un solo checkbox «Corregir (medido)» si hay referencia validada para el
perfil/método/par conectado, o «Corregir (estimado)» si se usa el modelo ADC.
Activo por defecto y siempre disponible en Tonos/Pulso/Sweep/Chirp.
Referencia medida tiene prioridad dentro de su banda; fuera se usa estimación,
con alcance indicado en tooltip y conteo de puntos medidos/estimados.
Desmarcar muestra datos crudos. Cambiar perfil/referencia mantiene la elección.
No se agregaron referencias ni se operó el Q en este cambio.

---

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

## Ruta de grabación y WAV76 · 12/10/2026

V16 guarda ahora CSV/WAV en capturas/v16 (antes usaba capturas/v14).
Se habilita ADC16/76226 WAV, manteniendo FS bajas de todos los bits y audio.
Grabaciones recientes no vacías conservadas en v14. El WAV76 anterior tenía
cero muestras y fue eliminado. Limpieza: 29 archivos, 7,58 MiB, imágenes
repetidas de siete ensayos V12; se mantienen informes y dos series recientes.
Registro: diagnosticos/resultados_v16/limpieza_capturas_20261012.json.
Se mantienen informes ADC16/analog y restauración, sin grabación física nueva.

---

## WAV a FS bajas y todas las resoluciones · 12/10/2026

Se amplía RECORD WAV a FS comunes 1/5/10/20/31,25/40 kHz con ADC8/10/12/14/16.
Mantiene audio ADC16 44,1/48 nominal, bloqueo Demo y altas FS no admitidas.
Salida PCM16: menos bits ADC se convierten sin agregar resolución.
Pruebas locales de cabecera, dos canales, continuidad y rechazo de salto en
las 32 combinaciones admitidas; no ensayo físico sostenido de grabación.
CSV permanece disponible en todas las FS.

---

## Grabación WAV restringida · 12/10/2026

WAV sólo ADC16 dual 44,1/48 kHz nominales; CSV en todas las FS.
Botón, filtro DC y guardia de inicio respetan FS aplicada y Demo.
Continuidad WAV nativa admite timestamps fraccionarios y comprueba dt real.
Cabecera 44101/48004 Hz sin remuestreo. Pruebas locales de archivo/continuidad;
no se operó el Q ni se acreditó grabación física sostenida.

---

## Tasas intermedias y audio incorporadas · 12/10/2026

Se agregaron dos intermedias duales por resolución entre 40 kHz y el primer
máximo: ADC8 225,670/411,311; ADC10 191,847/343,348; ADC12 163,432/286,738;
ADC14 145,191/250,391 kHz. ADC16 agrega audio nominal 44,1/48 kHz con tasas
reales 44.101,43/48.004,80 Hz, usando ticks enteros del reloj de 160 MHz.
Los diez perfiles están en additional_profiles.json/header, separados de los
14 máximos con aceptación prolongada. Se mantienen filtros por bits/SPI/Synth.

Firmware y relay instalados con respaldo osciloscopio_20261012_232758_157182.zip:
118896 bytes flash, 259292 RAM, 2852 libres. Los diez perfiles pasaron 60 s cada
uno con generador normal cuadrado de 5 kHz: CRC, secuencia, epoch, índices y
timestamps continuos; dropped=fatal=0, cola máxima de dos nodos. Se restauró y
verificó ADC16/40000 por SPI y generador apagado con todos sus campos originales.
Son ensayos de integridad de 60 s; no aceptación prolongada de margen ni analógica.
293 pruebas V16, 32 comprobaciones de tramas/GUI y dos pruebas nuevas de tasas
pasaron. El primer intento usó una tolerancia demasiado estrecha entre relojes
host/MCU; se conservó como evidencia y se repitió con caudal >=99% del nominal,
sin relajar los controles exactos de continuidad del MCU.

[Evidencia](../../diagnosticos/resultados_v16/additional_rates_60s_20261012.json) ·
[Estado previo](../../diagnosticos/resultados_v16/additional_rates_prior_20261012.json) ·
[Primer intento](../../diagnosticos/resultados_v16/additional_rates_wall_gate_failure_20261012.json).

---

## Offset como dial y lectura no editable · 12/10/2026

Offset usa dial64×64 con color Virtual Synth y lectura de voltaje QLabel.
El control numérico interno se conserva oculto para mantener protocolo,
confirmaciones y límites de amplitud/offset. Shift permite ajuste fino y
el doble clic conserva centrado1,65 V dentro de los límites actuales.
Filas de diales con cuerpos uniformes; amplitud y offset alineados, también
en seno, triángulo y rampa. Se preservan layouts Sweep/Chirp/Pulso/WAV/Synth.
88 pruebas de duty/filtros/FM pasaron; cuatro verificaciones finales de layout
pasaron tras ajustar espaciado. No se cambió firmware ni configuración del Q.

---

## Ajuste visual del duty · 12/10/2026

Dial duty de64×64, alineado en la columna de frecuencia y amplitud, con la
entrada porcentual a la derecha. Se retiró el texto Efectivo. No se modificó
el cálculo, protocolo ni firmware. Tres pruebas de duty pasaron; geometría
comprobada con Qt y los tres diales del mismo tamaño.

---

## Duty de cuadrada continua instalado · 12/10/2026

Dial y entrada1–99 %, default50 %, sólo cuadrada continua. Se conserva frecuencia
y se muestra duty efectivo según pasos DAC: 1 % a5 kHz, 5 % a50 kHz. Duty50 %
conserva2 puntos; otros usan hasta100 puntos dentro del presupuestoDAC1 MHz.
Monitor, protocoloMCU y relay incorporan extensión compatible para default50 %.
292 tests V16 pasaron, más constructor de tabla DAC y compilación MCU/relay.
Q actualizado con respaldo osciloscopio_20261012_221920_113832.zip. Compilación:
117804 bytesflash,259244RAM,2900 libres. No se modificó ADC ni whitelist de tasas.
ACKs duty1/25/50/75/99 a5 kHz y1/99 a50 kHz pasaron, sin errores de flujo.
ADC8 CH1/1221374 con duty25 % a5 kHz pasó10 s; no es aceptación analógica ni
una nueva campaña prolongada de margen. Se restauró y verificó ADC14/20000,
generador apagado con sus campos originales. Evidencia: duty_live_20261012.json
bajo diagnosticos/resultados_v16; estado anterior duty_prior_20261012.json.
Controles análogos propuestos, todavía no implementados: simetría del triángulo,
dirección de rampa; fase para seno sólo con referencia de sincronización.

---

## Escala horizontal adaptada a FS · 12/10/2026

Dial logarítmico, mínimo 8 muestras (6,55 µs en ADC8/1,22 MHz) y máximo
max(250000 muestras, ceil(4*FS real)). Todos los perfiles ofrecen al menos4 s;
FS bajas conservan períodos largos: 250 s a1 kHz, 50 s a5 kHz, 6,25 s a40 kHz.
Historial redimensionado por perfil al máximo visible +260000 muestras, con
base510000, conservando muestras recientes al redimensionar. Se conserva la
duración seleccionada al cambiar FS incluso si el eje muestra muestras; sólo
se limita cuando queda fuera del rango nuevo. Etiqueta automática µs/ms/s.
No se modifica la frecuencia de adquisición ni el protocolo del Q.
Verificación: 289 pruebas V16 pasaron en dos procesos (62 FM +227 restantes).
La ejecución conjunta sufrió un cierre nativo Qt en test_fm al procesar eventos;
la prueba aislada pasó. La prueba de historial verificó realmente los cuatro
segundos completos a la FS máxima, además de límites, dial y duración conservada.

---

## Decodificación y entrega numérica incorporadas · 12/10/2026

V16 desempaqueta kind20 con NumPy por bloques y entrega arrays a la GUI sin
crear una tupla Python por muestra. CRC, índices, timestamps, epoch y pérdidas
siguen comprobándose antes de entregar datos. Todas las muestras se conservan.
Los lectores normales mantienen filas Python; sin NumPy se usa el camino previo.
Los bloques acumulados se concatenan antes de NumericBatch; el reloj se aplica
una sola vez y se conserva el límite correcto al cambiar configuración.
284 tests V16 pasaron; tres pruebas adicionales de desempaquetado y constructor
MCU verificaron igualdad exacta de muestras/índices/timestamps en todos los perfiles,
valores extremos/aleatorios y wraps. Firmware y tasas del Q no se modificaron.
Prueba real: ADC8 CH1/1221374 recibió6112800 muestras y ADC10 CH1/909090 recibió4531568,
en ventanas cercanas a5 s, con generador5 kHz confirmado y sin errores reportados.
Ingesta mediana1,02/0,98 ms; demora de lotes p95 0,106/0,114 ms; timer62,8/62,9 Hz.
No se observaron eventos de pintado nativo: esos valores no certifican FPS de pantalla.
Q restaurado y verificado. Evidencia: diagnosticos/resultados_v16/fps_numeric_20261012.json.
Benchmark comparativo: diagnosticos/resultados_v16/decoder_numeric_20261012.json.
Pendiente verificar FPS visibles con ventana efectivamente pintada, y validación
física más prolongada de este camino de host. No se promueve una nueva tasa.

---

## Slider existente: comparación de puntos y dibujo · 12/10/2026

No se añadió otro control ni se cambió adquisición. El slider ya reduce trazos
por píxel conservando primeros/últimos/extremos y cortes NaN; 100% es completo.
Prueba host ADC8 CH1/1221374, seno 5 kHz, ventana 1 ms: slider0 pasó de2441 a625
vértices, pero rasterizado siguió cerca de5,4 ms; no se afirma mejora deFPS.
En10 ms: slider0 835 vértices/~5,4 ms frente a100% 24427/~6,9 ms.
La comparación física mantuvo1,22 MHz y generador confirmado5 kHz; el Q fue
restaurado. Qt no entregó eventos de pintado nativo en ese intento: sus valores
paint_fps=0 son inválidos y no se usan para compararFPS. Se conservó esta limitación.
Informes: diagnosticos/resultados_v16/slider_dibujo_20261012.json y slider_live_20261012.json.
La reducción visual ya existente ayuda especialmente con ventanas largas,
pero no justifica atribuirle sola la caída ni alterar Hz/muestras de adquisición.

---

## FPS físicos: 14 perfiles nativos medidos · 12/10/2026

Se completó la comparación Qt con un único lector, generador cuadrado normal a
5 kHz confirmado, ventana de 1 ms, 2 s de estabilización + 5 s medidos por caso.
Pintado real contado desde paintEvent; sin capturas periódicas durante medición.
ADC8 CH1/1221374: 21,7 FPS; ADC10 CH1/909090: 25,2 FPS;
ADC14 CH1/747663: 39,1 FPS; referencia dual ADC14/40000: 62,6 FPS.
Se registraron ingesta, decodificación, pintado y demora de lotes por separado.
15 casos sin errores de protocolo reportados; el estado previo del Q fue
restaurado y verificado. La prueba es corta y no certifica FPS sostenidos.
Tabla completa en docs/ETAPA_II_V16.md; evidencia en
diagnosticos/resultados_v16/fps_nativos_summary_20261012.json.
Los intentos preliminares con contador de pintado no observable se conservan
con su limitación explícita; no se usaron como resultados de FPS.
Siguiente trabajo: reducir coste de procesamiento y medir CPU/GIL por etapa,
sin alterar timestamps, grabación, filtros, trigger, SINGLE ni validación ADC.

---

## Segundo gráfico CH1 y diagnóstico de rendimiento · 12/10/2026

En adquisición CH1, el segundo gráfico espectral se selecciona en Ninguno.
Al volver a dual restaura su selección anterior, incluso FILTER o Ninguno.
45 tests de filtros/interfaz/FFT pasaron. No se modificó la adquisición.
Benchmarks sintéticos de 14 perfiles y dos ventanas separaron ingesta,
preparación de dibujo y decodificación. Mayor coste de decodificación estimado:
ADC10/909090 CH1 32,5% de un núcleo; ADC12/437158 dual 27,9%;
ADC14/747663 CH1 27,4%; ADC8/1221374 CH1 26,9%.
Estos valores no son FPS físicos ni prueban una cola Qt saturada. Queda medir
entregas Qt y pintado en una captura física con un único lector.
Scripts: diagnosticos/benchmark_altas_gui_v16.py y benchmark_altas_decoder_v16.py.
Informe: diagnosticos/resultados_v16/highrate_host_20261012.json.

---

## Selector simplificado: bajas comunes y altas nativas · 12/10/2026

Tasas bajas del monitor: 1/5/10/20/31,25/40 kHz. Altas: sólo los 14 perfiles
nativos validados para cada resolución, incluidos los máximos CH1 y dual.
UART conserva máximo 31,25 kHz; Synth SPI 40 kHz. Si el cambio de bits invalida
la selección, vuelve a 40 kHz. Sólo los perfiles de un canal muestran (CH1).
El período mostrado para los duales nativos usa el reloj real de 160 MHz.
Las tablas de monitor, firmware y contrato se actualizaron. El contrato de
compatibilidad de adquisición conserva perfiles anteriores para leer capturas.
El cierre ADC12/333333 con generador normal a 5 kHz permanece pendiente de
reproducción; esta simplificación del selector no demuestra su resolución.

---

## Selector de tasas y cierre informado · 12/10/2026

Se retiró la etiqueta (CH1+CH2): los perfiles duales usan el formato general
con tasa y período; sólo los perfiles de un canal aclaran (CH1).
El usuario informó cierre del flujo y cuelgue a ADC12/333333 Hz.
El relay inspeccionado después está activo; el log actual sólo registra una
conexión anterior y dropped=0, por lo que no identifica la causa del fallo.
Evidencia: diagnosticos/resultados_autoload/adc12_333k_closed_flow_20261012.log.
Pendiente precisar generador/WAV/Synth y reproducir el caso con un único lector.
No se modificó adquisición ni se reinició el Q durante esta revisión.

---

## Limpieza de grabaciones de test · 12/10/2026

Se eliminaron 194 grabaciones, muestras y trazas crudas de ensayos
(240.9 MiB). Se conservaron informes y análisis, audios de
referencia y uso normal, firmware y respaldos. Inventario de archivos retirados:
diagnosticos/limpieza_grabaciones_20261012.json. Las referencias de informes a
estas capturas son históricas; sus archivos crudos ya no están disponibles.

---

## Reparación de arranque y organización · 12/10/2026

Se preparó e instaló Scope V16 en el Q 1060031107 y su relay actualizado.
El autoload calculaba una identidad distinta del instalador porque omitía
native_profiles.h; ambos ahora usan monitor/relay_identity.py y todas las cabeceras.
Preparar Q y las herramientas usan V16 por defecto; el arranque admite hasta 600 s.
La ruta del instalador ya no depende de la ubicación del firmware archivado.

Versiones anteriores movidas a monitor/historico/v15 y
arduino/historico/v12_audio, arduino/historico/v13_pulse. Se actualizaron imports,
manifiestos, catálogo, índices, enlaces y entradas de VS Code; se conservan capturas.
Se retiraron las cachés Numba de V15 que todavía referenciaban su ruta anterior.
Verificación: 281 tests V16, 142 V15 y 123 V13 pasaron.
Conexión física: 468.992 muestras en 15,001 s sin errores de protocolo; evidencia
en diagnosticos/resultados_autoload/repair_v16_20261012.json.
El perfil observado es ADC14 dual a 31,25 kHz, generador activo a 2,5 Hz (2500 mHz en el protocolo); la configuración
anterior ADC8/333333 con generador a 50 kHz había cerrado el relay por dropped=1.

---

## Documentación actualizada · tabla de frecuencias disponibles

Manteniendo estructura y ensayos históricos, se actualizaron README general,
monitor/v16/README.md, arduino/v16/README.md y docs/CONFIGURACION_ADQUISICION.md
con tablas completas: tasas comunes SPI/UART, altas por bits, CH1 anteriores
(599250/661157/1203007) y14 perfiles nativos CH1/dual. Todas las tasas por canal;
marca✓ sólo cuando el margen nativo está confirmado también en producción.
Sintetizador: SPI≤40kHz/UART≤31,25kHz. ADC10/495356 y ADC12/410256 sin marca.
Tablas contrastadas automáticamente con Configuration/BITS/RATES/UART_RATES
y native_profiles.json: conjuntos exactos por bits/canales y marcas coinciden.
Referencias técnicas actualizadas a V16, ADC54MHz, TIM2/TIM5 a1/160MHz y nodos variables.
README apunta a entrada V16, conserva catálogo y defaults históricos explícitos.
Sólo documentación; no se alteró código ni estado del Q.

---

## Estado más reciente: integración dual TERMINADA · 12/10/2026

V16 MCU/relay/monitor incorporan nueve perfiles dual y conservan cinco CH1.
Dual por canal: ADC8 597014/632411; ADC10 495356/519480;
ADC12 410256/437158; ADC14 355555/363636; ADC16 76226 Hz.
Selector muestra(CH1+CH2), filtra por bits/salida/Synth y actualiza máximo ADC16.
279 tests V16 + storage/constructor/colector pasaron; después de reconciliar
flags,26 tests de perfiles/UI/constructor también pasaron.

Los primeros intentos con1364 bytes libres fallaron READY y restauraron CH1.
Se preservaron production_ack_failure*, second_* y failed_relay.log.
acquisition_storage.h ahora usa arenas estáticas excluyentes CH1 compacto y
Dual/legacy, cuatro slots, timestamps completos y sin heap. DMA/producer detenidos
al cambiar arena; UART scratch con guard; WAV mantiene16 bloques.
Compilación117908 bytes flash/259132 RAM/3012 libres; arranque confirmado.

production_integration.json:ok=true/restored=true,18 casos/transiciones;
120s por cada uno de14 perfiles nativos, sin pérdidas/errores, NumericBatch
ambos canales y timestamps correctos. También mide envío por nodo y cola.
Ganadores completos previos al rechazo de margen conservados con hashes de
código; no se reutilizó ensayo interrumpido de before_margin_*.
ADC10/495356 y ADC12/410256 midieron9,03%/9,39% (<10%): etiquetas de margen
RETIRADAS en producción. Conservaron integridad. Dual ADC8/597014 (11,39%),
ADC14/355555 (10,09%) y ADC16/76226 (77,66%) conservan margen; CH1 también.
Auditoría:production_acceptance.json. Informe:RESULTADOS.md, apartado integración.

Firmware nuevo INSTALADO. Relay:usb-stream-046d2c12bc108dce30a0/unoq_stream.
Respaldo CH1 previo:respaldos/unoq/osciloscopio_20261012_155653_138423.zip.
ADC8/333333 SPI y seno50kHz con campos originales restaurados.
restore_integrity_ok=false: el perfil original sigue fallando como antes.
No quedan dueño de validación ni caffeinate. No Astra. Reiniciar monitor.

No se acepta precisión analógica/ENOB por esta evidencia. Si se busca frontera
sostenida exacta dual ADC14,422..439 ticks aún no tienen aceptación larga.

---

## Integración dual: validación física pendiente en curso

Nueva distribución estática de RAM: acquisition_storage.h comparte arenas CH1
nativo y dual/legacy, con cuatro slots y timestamps completos. Compila117908 bytes
flash,259132 bytes RAM,3012 libres. La variante anterior de1364 libres falló
READY dos veces y se restauró CH1; logs production_ack_failure* y second_*.
La distribución compartida ya arrancó correctamente varias veces.
279 tests V16 y tests de storage con sanitizadores, constructor real y colector
por nodo pasan. Firmware nuevo cargado; respaldo CH1 antes de carga:
respaldos/unoq/osciloscopio_20261012_155653_138423.zip.
Relay:usb-stream-046d2c12bc108dce30a0/unoq_stream.

Los cinco perfiles CH1 pasaron120s con NumericBatch y márgenes declarados.
Dual ADC8 ambos perfiles pasaron120s; ADC10/495356 pasó integridad120s pero
margen medio9,03% (<10%). RETIRAR su etiqueta de margen en producción al cerrar.
Evidencia margin_failure_production_integration.json y código archivado.
Reanudación conserva sólo ensayos completos y verifica hashes originales del
receptor y script archivado. Pendientes6 perfiles nativos y últimas transiciones.
ÚNICO dueño Q: verify_production.py --resume, caffeinate -i -s.
Log production_integration.log; reporte production_integration.json.
No abrir monitor ni otros clientes durante validación. Restauración final debe
volver a ADC8/333333 SPI/seno50kHz; su integridad previa falla igual que antes.
No Astra. Los perfiles locales aún deben reconciliar sus flags de margen antes
sobre todo de anunciar la integración completa.

---

## Integración dual en curso · 12/10/2026

Autorizado continuar e incorporar los nueve perfiles dual validados, conservando
los cinco CH1. No Astra. integrate_production.py aplicado con gate físico a ambas
campañas y backup local production_before_dual/; whitelist tiene14 perfiles.
Empaquetado nativo dual MCU usa capacidades exactas de campaña (ADC8=432 pares);
CH1 conserva sus capacidades previas. Constructor real/relay/decoder coinciden
para14 perfiles y wrap. Suite V16:279 tests pasaron. UI distingue CH1+CH2 y ADC16
incluye76,23kHz. Compilación MCU pasó:260780 bytes RAM,1364 libres; stacks incluidos.
No se redujo WAV ni se retiró validación temporal; validar estabilidad real.

Carga Q ACTIVA: deploy_production.py, sesión52461, production_deployment.log.
Respaldo antes de carga:respaldos/unoq/osciloscopio_20261012_153240_338072.zip.
Relay nuevo:usb-stream-046d2c12bc108dce30a0/unoq_stream.
NO abrir otros clientes/resetear. Pendiente verificar producción:120s por los14
perfiles nativos, transiciones, NumericBatch ambos canales/timestamps y restaurar
ADC8/333333 SPI/seno50kHz del snapshot (integridad previa fallaba).
Runner:experimentos/maxfreq_dual_v16/verify_production.py; informe esperado
production_integration.json. No considerar terminada la integración antes del gate.

---

## Estado más reciente 12/10/2026: barrido dual cerrado y Q restaurado

CH1 sigue incorporado y verificado en producción. Campaña dual completa:
sweep.json ok=true/restored=true, 478 ensayos, nueve perfiles distintos que
pasaron 60 + 3×120 + 600s con control de host y cero dropped/fatal.
Mayor tasa aceptada / tasa con margen, POR CANAL (dos entradas por disparo):
- ADC8: 632411,067 Hz (253/N3888) /597014,925 Hz (268/N3456).
- ADC10: 519480,519 Hz (308/N4176) /495356,037 Hz (323/N4176).
- ADC12: 437158,470 Hz (366/N4032) /410256,410 Hz (390/N4032).
- ADC14: 363636,364 Hz (440/N3968) /355555,556 Hz (450/N1984).
- ADC16: 76226,775 Hz (2099/N3456), íntegro y con margen.

Gate accepted_profiles, 45 aceptaciones controladas y hashes originales
verificados: experimentos/maxfreq_dual_v16/acceptance_audit.json.
Informe y límites: experimentos/maxfreq_dual_v16/RESULTADOS.md.
Son máximos entre candidatos ensayados; no todos los ticks intermedios tienen
aceptación larga (ADC14 422..439 pendiente si se busca frontera sostenida exacta).

El dueño original desapareció durante ADC14, sin causa establecida. Evidencia
conservada en interruption_20261012T161655Z/. Restauración intermedia registrada
y reanudación con resume_finalists.py --resume (hash en reporte), sin reutilizar
aceptaciones parciales. Conservó sólo ganadores completos ADC8/10/12; repitió
ADC14/16 desde cero. Cinco tests y gate de reanudación pasaron.

Reanudación TERMINADA con exit0; NO hay dueño host ni caffeinate activos.
Q restaurado al V16 integrado nuevo, ADC8/333333 SPI, seno50kHz y campos
originales. restore_integrity_ok=false: el perfil previo volvió a cerrar el
flujo, igual que antes; campos restaurados no equivalen a integridad aprobada.
Comprobación read-only: scope-v16-main-1 activo; app experimental detenida.

DUAL NO INCORPORADO a producción. Próxima integración requiere constructor
MCU nativo para pares, whitelist fusionada con CH1, RAM y validación física de
receptor/transiciones/restauración. Analogía/ENOB no medidos. No Astra.

---

## Seguimiento anterior 12/10/2026: dual reanudado, ADC8/10/12 aceptados

Máximos dual sostenidos, tasa POR CANAL; todos 60 + 3×120 + 600s:
- ADC8: máximo íntegro ticks253/N3888 =632411,067 Hz;
  con margen ticks268/N3456 =597014,925 Hz.
- ADC10: máximo íntegro ticks308/N4176 =519480,519 Hz;
  con margen ticks323/N4176 =495356,037 Hz.
- ADC12: máximo íntegro ticks366/N4032 =437158,470 Hz;
  con margen ticks390/N4032 =410256,410 Hz.

El dueño original desapareció durante acceptance_3 ADC14 ticks420/N3968,
sin finally ni restauración registrada. Causa no establecida; NO contar el
ensayo interrumpido como aceptación ni límite ADC. Evidencia completa archivada
en experimentos/maxfreq_dual_v16/interruption_20261012T161655Z/.
Se restauró V16 integrado y ADC8/333333 SPI/seno50kHz; campos restaurados=true,
integridad del perfil previo falló igual que antes. interruption_restore.log.

Reanudación ACTIVA: caffeinate -i -s .../python
experimentos/maxfreq_dual_v16/resume_finalists.py --resume; sesión6850.
Log resume_finalists.log; reporte sweep.json. ÚNICO dueño Q: ese proceso.
Los archivos originales sweep.py/contract.py/firmware NO cambiaron y sus hashes
coinciden. Runner nuevo registra su hash y conserva sólo ganadores completos
que pasan accepted_profiles; no reutiliza aceptaciones parciales. Descarta
fallos largos previos controlados; repite desde cero los candidatos pendientes
ADC14/16. Gate de reanudación y 5 tests de aceptación/contrato/tramas pasaron.
Pendiente finalizar ADC14/16, listar ganadores y registrar restauración final.
No hay perfiles dual incorporados a producción. No Astra.
El caffeinate extra anterior también desapareció; el dueño nuevo tiene -i -s.

---

## Estado anterior 12/10/2026: CH1 incorporado, dual activo

CH1 terminó e incorporó5 perfiles. Tabla aceptada:
ADC8 máximo1.221.374 Hz (131/N6912), margen1.118.881 Hz (143/N8192);
ADC10 máximo y margen909.090 Hz (176/N8192);
ADC14 máximo747.663 Hz (214/N7936), margen701.754 Hz (228/N7936).
Todos60+3×120+600s controlados. Otros120s por perfil de producción PASARON;
9 transiciones/perfiles, sin pérdidas/errores, timestamps NumericBatch correctos,
parámetros originales restaurados. production_integration.json ok/restored=true.

Código V16 y firmware/relay Q ACTUALIZADOS. Los perfiles antiguos se conservan.
RAM inicial excedía316 bytes; paquete UART ahora usa área fuera de los dos nodos
de timestamps utilizados en UART (guard comprueba legacy dual y N2048).
Constructor UART real comparado binariamente, incluido wrap; WAV conserva16 bloques.
Compilación258484 bytes RAM,3660 libres. Respaldo preincorporación
respaldos/unoq/osciloscopio_20261012_082204_106792.zip.
Relay estable nuevo: usb-stream-80706d1ec26cf81e535b/unoq_stream.
Primer ACK fallido preservado *_ack_failure; se corrigió comparación request_period
en unoq_config_receiver.py con prueba de regresión. Ver RESULTADOS_CH1.md y README.

Primer arranque dual falló por agotamiento de redes Docker, sin casos ADC.
Se archivó sweep_network_failure.json/log. Se inspeccionó y eliminó SOLO
scope-v16-maxfreq-experimental_default, vacía; configuración conservada en
released_network.json. Se reintentó.

DUAL físico ACTIVO: caffeinate -i -s .../python
experimentos/maxfreq_dual_v16/awake.py. Sesión91108; log sweep_v2.log, reporte sweep.json.
Único dueño Q: ese proceso. No iniciar otros clientes/resets mientras esté activo.
Variantes bits8/10/12/14/16, dos valores por fila, tasa POR CANAL.
Nodos completos:8 1728/3456/3888;10 1392/2784/4176;
12 1152/2304/4032;14 992/1984/3968;16 864/1728/3456.
Arrays/validadores admiten hasta4176 pares;201856 bytes RAM,60288 libres.
16 bits: oversampling×16 existente, explorar hasta2048 ticks para detectar
disparos omitidos, sin aumentar reloj ADC54MHz. Guard de integridad/timestamps.
Refinamiento binario y vecinos enteros; margen refinado aparte.
Aceptaciones60+3×120+600s; margen descartado al primer fallo de ese criterio.
No modificar sweep.py/contract.py/firmware durante campaña: hashes impiden mezclar.
Snapshot dual proviene de restauración integrada aprobada; backup nuevo
respaldos/unoq/osciloscopio_20261012_091652_816649.zip. Restore vuelve al V16 NUEVO.
Candidate relay: usb-stream-37773d65c3a519cfa0a2/unoq_stream.
La primera campaña dual tuvo una discrepancia de capacidad ADC8 (436 frente a432);
se preservó en full_frame_geometry_failure/ y no demuestra límites ADC.
Corregido y verificado con constructores reales de tramas completas en los5 bits.
Campaña actual dual_specialized_packing_v2: grilla completa, refinamiento activo;
todavía no hay ganadores dual. Pendiente finalizar barrido, listar resultados y
registrar restauración. Si se incorporan dual, extender empaquetador MCU nativo
para pares (actual producción kind20 esCH1), fusionar whitelist y verificar RAM.

No Astra. Preferencia menos tokens: monitorear con esperas breves y datos mínimos.
Caffeinate extra12h sesión96824 sigue activo; detener al terminar TODO.
Perfil original ADC8/333333 SPI con seno50kHz ya tenía pérdidas; no confundir
restauración de campos con integridad. Analogía digital no certifica ENOB/analogía.

---

## Estado activo actualizado 12/10/2026

- Sin Astra. Alcance autorizado: cerrar CH1, listar e incorporar perfiles
  aceptados, verificar integración, después barrer DOS canales por bits.
- CH1 íntegro completo (60 +3×120 +600s con host despierto):
  ADC8 ticks131/N6912 =1.221374MHz; ADC10 ticks176/N8192 =909.091kHz;
  ADC14 ticks214/N7936 =747.664kHz.
  Margen completo: ADC8 ticks143/N8192 =1.118881MHz y ADC10 ticks176/N8192.
- ADC14 ticks224/N7936 falló margen; se detuvo esa repetición con SIGINT y
  se restauraron los campos previos (integridad del perfil previo sigue fallando).
- Único dueño actual Q: finish_margin.py --resume, caffeinate -i -s,
  sesión65779, log experimentos/maxfreq_v16/finish_margin.log.
  Reusa sólo aceptaciones completas, afina225..241 y descarta un candidato
  de margen al primer fallo de ese criterio. ADC14 ticks228/N7936 pasó60s
  y3×120s; está en endurance600s. El Q sigue experimental: no abrir otra conexión.
- Scripts preparados incorporate.py (gate físico), integrate_firmware.py
  (conserva UART/WAV y formatos antiguos, sin ejecutar todavía),
  verify_production.py (120s por perfil nativo + transiciones y restauración).
- app.py, unoq_acquisition.py y unoq_config_decoder.py tienen soporte preparatorio
  nativo; NO existe native_profiles.json aún, por tanto no habilita nuevas tasas.
  Nuevo unoq_native.py; tests de interfaz21, contrato17 y empaquetado real
  firmware/relay/decoder8/10/14 pasaron. check_integration.py actúa en temporal.
- Variante dual PREPARADA, no compilada/cargada:
  experimentos/maxfreq_dual_v16/, bits8/10/12/14/16, kind20 con dos valores
  compactos, timestamps160MHz, pruebas packing/contrato3 pasan.
  Revisar/refinar cota temporal ADC16; PLAN.md conserva fuente primaria ST.
  Guardar prior.json después de integrar CH1 antes de preparar/cargar dual.
- Caffeinate extra de12h sesión96824 sigue vigente; detener al terminar TODO.
- Restauración y aceptación analógica son controles distintos de integridad.
  Continuar hasta integración y dual; no presentar lo preparado como terminado.

---

## Seguimiento 12/10/2026

El usuario pidió continuar sin Astra, gastar menos tokens, terminar CH1, listar e
incorporar lo validado y luego barrer dos canales al máximo por resolución.

Se confirmó una contaminación por suspensiones del Mac durante las aceptaciones:
`pmset -g log` registra Sleep/DarkWake; en varios timeout el relay continuó
adquiriendo sin dropped/fatal y cerró al PC lento. No son límites demostrados ADC.
Campaña afectada preservada en `experimentos/maxfreq_v16/antes_control_suspension/`,
con sleep_events.log. Se interrumpió PID5347 con SIGINT; campos originales
restaurados, integridad del perfil original falló igual que antes.

**Campaña CH1 activa nueva:** `caffeinate -i -s .../python experimentos/maxfreq_v16/awake.py --resume`.
Sesión exec69080; log persistente `experimentos/maxfreq_v16/sweep_awake.log`.
Conserva matriz/refinamientos del mismo firmware, repite TODAS las aceptaciones,
no usa las viejas como ganadores. Cada nuevo caso registra deriva reloj pared/
monotónico y rechaza casos con deriva mayor que dos segundos.
Hay además caffeinate de 12h, sesión96824; detener esa sesión al cerrar TODO el trabajo.
No iniciar otra conexión ni otro barrido; Q actualmente experimental.

Sigue pendiente cierre CH1, publicación en V16 de perfiles realmente validados,
pruebas de integración y campaña aislada dual. No se volvió a usar Astra.

---

## Continuación actualizada 11/10/2026, 17:09 Argentina

- Se detectó el barrido original todavía vivo (PID2997). Se detuvo con SIGINT;
  restauró los campos originales, pero la prueba de integridad del perfil previo
  falló igual que al principio. Campaña original archivada completa en
  `experimentos/maxfreq_v16/instrumentado_generico/`.
- Astra revisó plan/evidencia y luego aprobó la corrección. El empaquetador original
  genérico y la quinta trama de N3584 penalizaban el ensayo. No inferir límite ADC.
- Se especializó únicamente firmware experimental: ADC8 byte directo, ADC10 4→5,
  ADC14 4→7, padding solamente. Cuatro pruebas de packing/contrato pasan.
- Se corrigió búsqueda separada de máximo íntegro y máximo con margen, refinamiento
  con pases de repetición y hashes que impiden mezclar revisiones al reanudar.
- **Referencia estable nueva aprobada:** baseline.json, 120.000157 s,
  144273048 muestras ADC8/1203007 Hz, dropped=0/fatal=0. Campos restaurados.
  Los fallos baseline anteriores siguen conservados; aún falta explicar intermitencia.
- Variante corregida preparada con backup `respaldos/unoq/osciloscopio_20261011_170619_994241.zip`.
- **Barrido NUEVO activo**, PID5347, sesión exec 30603, `sweep.py` SIN --resume.
  Revisión `specialized_packing_v2`; resultados vivos `experimentos/maxfreq_v16/sweep.json`.
  Primer N3456 pasó 5 s a ticks133 (1.203007 MHz), pero sin criterio de 10% margen.
  No hay máximos sostenidos aceptados todavía. No lanzar otra conexión ni otro barrido.
- El Q está con firmware experimental. El proceso tiene finally con restauración
  del snapshot real de prior.json: ADC8/333333 Hz, SPI, seno50kHz habilitado.
  **No confundir ese snapshot con el antiguo ADC16/71428 del primer texto.**
- Falta completar matriz/refinamientos, 60s+3x120s+600s por candidato y comprobar
  restauración final e integridad por separado. La UI estable no se modificó.

---

Retomé y completé la validación pendiente de CH1 a 1,203 MHz con ADC8:
- 62 tests aprobados, incluido el desborde del contador.
- 120 segundos y 144.273.920 muestras, con cero pérdidas y errores.
- Cambios de perfil y FFT con el Q real aprobados.
El Q quedó restaurado en ADC16 a 71,428 kHz, SPI y generador apagado. Actualicé el archivo de continuidad y el README.
Quedan pendientes las mediciones de margen de cola, precisión analógica y pruebas visuales, trigger/SINGLE y exportación.

  Edited 2 files+43-0View changesUndoView changes

/private/tmp/restore_megaboom_profile.py/private/tmp/restore_megaboom_profile.py+21-0
monitor/v16/README.mdmonitor/v16/README.md+22-0





1:10 PM







ver de mostrar las opciones validas para cada seleccion de bits, porque en 8 aparecen todas por ejemplo







1:14 PM






Worked for 1m 18s



Aplicado: el desplegable ahora oculta las tasas incompatibles con los bits seleccionados, la salida SPI/UART y el modo Synth.
En 8 bits se ocultan 599 y 661 kHz, que requieren ADC14; se mantiene 1,203 MHz.
Pasaron 21 pruebas de interfaz. Reiniciá el monitor para ver el cambio.

  Edited 2 files+17-2View changesUndoView changes

monitor/v16/app.pymonitor/v16/app.py+1-1
tests/v16/test_filter_ui.pytests/v16/test_filter_ui.py+16-1





1:15 PM







excente. hay margen para mas mhz?







1:16 PM






Puede haber margen, pero todavía no lo medimos. Los 120 segundos a 1,203 MHz sin pérdidas demuestran que funciona durante ese ensayo; no dicen cuánto sobra.
Hay dos límites a revisar:
- ADC: tiempo mínimo de adquisición y conversión a 8 bits.
- Transporte: salida de cada nodo por SPI, ocupación de cola y margen antes de que DMA reutilice su memoria.
El siguiente paso sería medir esos tiempos a 1,203 MHz. Si sobra margen sostenido, probar una tasa superior en una variante aislada y restaurar después el perfil actual.
No subiría todavía el límite del monitor: primero necesitamos esa evidencia.


1:16 PM







ok fijate con astra de pensar planes tipo el de 8 bits que anduvo para hace run modo que maximice la freq en 8 bits, 10 y 14. tmabien validar lo actual a 1.203. astra hace el plan vos ejecutas, y hagan todo el barrido completo sin mi intervencion.







1:17 PM






Worked for 31m 40s



  Edited 8 files+471-0View changesUndoView changes

experimentos/maxfreq_v16/PLAN_ASTRA.mdexperimentos/maxfreq_v16/PLAN_ASTRA.md+57-0
experimentos/maxfreq_v16/baseline.pyexperimentos/maxfreq_v16/baseline.py+45-0
experimentos/maxfreq_v16/contract.pyexperimentos/maxfreq_v16/contract.py+88-0
Show 5 more files



















You're out of Codex messages
Your rate limit resets on 6:01 PM. Upgrade or use one of your rate limit resets now.


UpgradeReset usage

Validación final offline con capacidadRF real 5874036 muestras:
750/750lotes en15s, pico5 pendientes, atrasomax78.1ms,
procesamientomedio5.09ms, pico21.16ms; sinerror.
50pruebas locales verificadas entre suite49 y testnuevo de ventanaRFfresca.
No prueba física sostenida; reiniciar V17 para aplicar estos cambios dehost.

## Último estado — pausa solicitada 17/10/2026

El usuario frenó para probar V17. Q libre y restaurada: firmware23bc0e28212ea8c44de498f58a471a480e43feaa55899924b80d304f347de8ac; ADC8/1600000 SPI, generador apagado,10s íntegros. Nada experimental incorporado al firmware ni al selector de tasas. No iniciar más pruebas hasta que pida retomar;14/16 pospuestos explícitamente. Checkpoint detallado: `experimentos/otros_bits_crc_v17/PAUSA_20261017.md`.

## Actualización17/10 — mejora RADIO A0 instalada

Usuario retomó y priorizó que Radio A0 se detiene y requiere Play. Se instaló sólo mejora de búfer30/360ms y CRC (sin tasas nuevas) mediante `experimentos/radio_dac_headroom_v17/probe_20261017_125353/report.json`: ok/installed/settings_restored=true, firmwaree8d8411bec6a9aebef0ffc58b21448c14cd8503cd8209a4f28bd6fb852c0e1a9.120s audio sin errores, cola pico4, margen17,28%; no holgura completa. RadioTest y20tests correctos;10s finales15.991.776 muestras sin pérdidas. Q libre, ADC8/1600000 SPI y generadorOFF. Registro de causas en `diagnosticos/resultados_v17/radio_a0_stops.jsonl`.14/16 siguen pospuestos y tasas nuevas10/12 no incorporadas. El checkpoint de pausa anterior describe el firmware anterior23bc y ya no es la identidad instalada.

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

## RADIO compacto —18/10/2026

Pedido de recuperar altura anterior: FS y banda RF comparten fila; dial Gain junto a lectura y botón Auto, con nombre accesible Auto gain. Panel medido offscreen:398→289px de sizeHint. Banda RF centrada para que9kHz no se recorte en ancho actual.32pruebas existentes RADIO/UI/autogain correctas y captura inspeccionada. Sólo layout enapp.py; firmware,adquisición yA0 sin cambios. ReiniciarV17 para aplicar.

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

## Máximo RADIO según FS y auditoría etapaIV —18/10

Se eliminó tope fijo600kHz de radio_tuning_max. Máximo=ceil(FSreal/2−BandaRF/2)−1Hz:1,6MS/s con9kRF→795499Hz;con4k→797999Hz. Dial/entrada,Scan,validaciónDSP yA0siguenelmismocriterio; cambiarbandaactualizarango yrecortaelecciónsólo sifuerabanda. Bandwidthdefault9kconservado.47testsregresióncorrectos; testnuevoScan750k ysintonía segúnFS/banda,picoaudio1kdesdeAM750k. Sólohost;sinQ/firme.

Plan de trabajo.md tiene ahora checklistvigentealprincipiodeETAPAIV. Pendientesexplícitos:FFT Radio/marcasScan/bandaslaterales,OSundersampling,48kA0contratoreloj,identificaciónemisora. SiguienteprioridadfuncionalFFT Radio;no declarar etapaIVcompleta por pruebasdeestabilidad.8/1,6MA0sigueabierto;10/1,25Mservicioentretramasincorporado. ManteneraltoRADIOcompacto289px.

## 18/10 — antena real y US zona2

Captura pasiva CH1 8/1.6M,10/1.25M,14/851:5s porperfil sin dropped/fatal/saturación. NPZ+Scan+WAVcortos en diagnosticos/resultados_v17/antena_am/20261018_190744. Candidato710.44k→539.56k→140.62k compatiblealias entreFS; noidentificaciónemisora. RestauradoADC12/1066666 genOFF,10s recuperación10664640muestras,firmwaref3cab6f4igual. Qlibre.

US zona2implementadohost: dialRF,aliasFS−RF,DSPalias,Scanconvertido,FFTejealias. Límitescompartidosrechazanf≤B/2. Astra recomienda mejorasruidorobusto/confianzabandas,persistenciaScan,escuchalarga yfiltradoanalógico; estimadoractualsesgadotonos,pendiente. Detalles docs/RADIO_ANTENA_US_V17.md.

## 18/10 — US dial combinado y Scan multitasa incorporado

Contrato radio_tuning ahora0..FSconguardasbanda yrechazoNyquist;USOFF1:1. MultirateScan GUIusa mismoOutputWorker tresperfilesmismosbits/canales,descartatransitorios yvalida3×65536nuevas,restauraFS/sintonía/Play. RFestimada/ambigua;matchfoldmodulartolerancia2bins+100ppm. CancelarScanrestaura;cierreespera. A0/registro/Bodebloqueaninicio.

GUI/Q `us_multiscan_20261018_193808/report.json` oktrue:8/1.6→1.403508→1.118881→1.6M,18hipótesis incl870.532k. Qrestauradaexternamente12/1066666genOFF,10662336muestras10s sindropped/fatal,hashf3cab6f4igual.Qlibre. Primer193738fallóantesinicioporauxiliaresinválidos,restauró;corregidoRATESregistry. 42regresiones+19focalizadaspasaron (solapadas). Noescucha/identidadcertificada. DocsRADIO_ANTENA_US_V17.md.

## 18/10 — cierre Scan US ADC10max

Relaylogconfirmódropped1fatal0CRCcorrecto seq16032213 aldestino10ticks176/909090. Qyacerrabaflujoantesdiagnóstico194957. Recuperado usb_streamstartv17 (AppLabrecargasketchinstalado),hashf3cab6f4igual;ajustesarranque14/31250genOFF,noafirmarrestauracióndelestadofallido.

FixOutputReceiverconfigure: entreperfilesnativos>400kconcambioCPUoptimizado,preparar14/40k150ms,sinmuestras/ACKintermedioGUI. ErrorworkerScanabortasinesperarworkerterminado;restauraciónexige100msnuevas. GUI/QADC10max2repeticiones195122/195151ok/restoredtrue,1250000→1167883→909090→1250000,sintoníapreservada;recovery10s311296sindropped/fatal,final14/31250genOFF,Qlibre. DocsSCAN_US_ADC10_ESTABILIDAD_V17.md. NoaceptaciónprolongadaniA0.

## 18/10 — contrato RADIO/UI corregido

Banda RF inicial8kHz enUI/DSP/Scan. RadioesModoFFT (Spectre/Power/Distort/Transfer/Radio), noquintomododeanálisis. MotorRadio normalizaaSpectreconoverlays,conservaselecciónCH1. PlayRADIOsóloautoseleccionaRADIOsinohayCH1enpaneles;noalteraelotrocanel. ScandirectopausaRADIOdespuésvalidarprecondicionesyrestauraPlayalresolverfuture,inclusofallo;USyamantienepausa/restauración. PruebanuevaejecutaScanconRADIOon,preservandoCH1/FILTER. SinQenestecambio.

## 18/10 — Scan con RADIO ON validado

PausainternaScanseparadadeStop/Playmanual: nofilter_changedniautoseleccióndeanálisis,conservaGain/FILTERpreset/sintonía. USconfirmacionesnoreseteanpreset. Directoscannoreactivasiadquisicióncambió;A0activorechazainicioenlugardeapagarlosilencioso. GUI/QADC10maxRADIOon:200441US19hipótesis/19marcas;200515normal36/36,ambosresumed/restoredfrequencytrue,sinerrores. Qrestaurada12/40kgenOFF,10s399360sindropped/fatal,hashf3cab6f4igual,Qlibre. DocsSCAN_US_ADC10_ESTABILIDAD_V17.md.36regresionespasaron.

## 18/10 — Scan US ADC14/851 cierre corregido

Falloaldestino599250:seq1395229kind16CRCcorrectodropped4fatal0. Preparaciónanteriorrequeríaambos_native;599eslegacyNone.Quedabaexcluido833→599y599→851. Fixremueveexigenciaymantiene>400k/cualquierextremooptimizado,preparación14/40k150ms.Testnuevoambasdirecciones,42regresionescorrectas.

Qrecuperadareiniciandosketchinstaladoconusb_streamstartv17,hashf3cab6f4igual;boot14/31250genOFF,norestauraciónestadofallidooriginal. GUI/Q14/851RADIOon2ensayos200937/201001ok/restoredtrue,851→833→599→851,11y10marcas,Play/sintoníarestauradas.Sinerroresworker. Final14/31250genOFF,recovery10s311296sindropped/fatal,hashigual,Qlibre.ReiniciarV17.DocsSCAN_US_ADC10_ESTABILIDAD_V17.md.

## 19/10 — Scan mientras reproduceA0

ReemplazadobloqueoporpausaA0automática:STOPconfirmado→Scan→fuente nuevamismaIN/rate/volumen,sólotraséxito,mismoworker/modo/IN/rate.Espe ra8s,luegoerror;sinfalsoresumeencasofallo/desconexión. `_radio_scan_a0`context/timer,USfinishydirectfinishhooks.45regresionespasadas.

GUI/Q14/851RADIO+A040k:US012259ok11marcas,normal012355ok22marcas,played1440antesyenfuentenuevadespués,FS/sintonía/Playrestauradas,Qexterna8/1.6MgenOFF,recovery10s15990912sindropped/fatal,hashf3cab6f4igual,Qlibre. Diagnósticoprimero012048noinicióporselectores40k;012330assert500kfueraNyquistincorrecto;ambosrestaurados,preservarevidencia. Documentado docs/SCAN_US_ADC10_ESTABILIDAD_V17.md.

## 19/10 — suavizar clic de pausa Scan A0

RadioDacSource fade_out20msmarcaíndicefuturo;Scanesperaplayedconfirmado≥findefadeantesdeSTOP. Señalquedaneutral2048despuésdefade. Reanudaciónconfuentenuevafade_in20ms,sincambiovolumenvisible.HeredaHighRateRadioDacSource.17testsoutput/pause/multiscanpasaron,incluyendorampas≤2códigos/sampleparaseñalconstante0.5VySTOPnoanticipado. Escucha humana pendiente.

GUI/Qfade `us_multiscan_20261019_012656/report.json` ok/restoredtrue:14/851US,A040kplayed1440antes/después,11marcas,reanudación+FS+sintoníaconservadas.Qexternarestaurada8/1.6MgenOFF,10s15990912sindropped/fatal,hashf3cab6f4igual,Qlibre. Nocertificaeliminaciónaudibledeclic;probarrampasrealizadas.

## 19/10 — auditoría completa canal RADIO con Astra

Docs/AUDITORIA_CANAL_RADIO_ASTRA_V17.md (ruta docs/minúscula). Baselinelocal10casos8/10/12/14/16FILTEROFF/ON,enradio_chain_audit/offline_20261019_013406.json. DSPaltos.584–1.077mspornodo2.16–7.02ms;noaceptaciónfísica/GUI. Quickwins:ScanUSnocapturarepetidamentefuturependiente;fallofadependienteSTOPexplícito;feed_resultsinsegundacopiaarraypropio;índicessóloconfadeyfadeinexpira.20tests focalizadospasaron. Siguientemayor:instrumentaciónfullchainlatencia/colas ydesacoplarpresiónGUIdeDSP/A0;guardlockfueraenotrosperfilesrequiereexperimento (guard_onlypreviofalló). Buffers/créditos/FSfirmwareconservados.

## 19/10 — medir desacopleGUI/DSP

Diagnósticoaislado `benchmark_radio_gui_stalls_v17.py` usaOutputWorker/DSP/Qtqueued reales,RFsimulada10/1.25M,lotes20ms,retieneGUI50/100/250/500ms. Baselinegui_stalls013712;comparación013749:500msGUI→huecoaudio510msactualvs42msvariante. Repetición013818:498vs35ms,1.750.000RFgeneradas/recibidascada10casos. Camposrf_continuitysonconteo,noCRC.

VarianteIsolatedDspPressureWorkersóloendiagnóstico,admisiónDSPindependienteGUI,límite50lotes20ms=1s,colaGUIpico25,DSP1–2. NOincorporadaaclasesproducciónnioperadoQ. Faltalímiteporbytes/muestras,drenaje/ACKgeneracionesypruebasQ;noelevarglobalpendinglimitcomoarregloproducción. DocsRADIO_GUI_DESACOPLE_V17.md,planactualizado.

## 19/10 — desacople DSP/GUI RADIO integrado

OutputWorker.pending_dspindependiente,pending_batchesGUIcompletas;DeliveryBudget1scombinadoRFcoalescido+GUI,1.6Mmuestras,64MiBpayloadestimado,256objetos.LímitenoRADIO8conservado,salvodrenajelotesRADIOprevios.Radio_entriesgestionatransiciónOFF.LiberaciónporidentidadenGUI/fallos;ACKsprocesamientoconservados.Nofirmware/créditosDAC.

Simuladointegrado093611:500msGUIhueco496→33ms,1.75MRFcuentasiguales;noCRCfísico. GUI/Q14/851093623played1440→21600durantepause500ms,GUI24DSP1,payload12.64MB;10/1.25M093728played1440→21120,GUI25DSP1,payload18.93MB.AmbosScanUS/A0resumeok,restoredtrue;Qfinal8/1.6MgenOFF,10s15990912sinpérdidas,hashf3cab6f4igual,Qlibre.31testsbudget/pipelinepasaron,51anterioresparcialsolapados.DocRADIO_GUI_DESACOPLE_V17.mdestadoactualarriba. Noaceptaciónprolongadaglobal/FPS/escucha.

## 19/10 — validación sostenida: NO aceptación global

Ver docs/VALIDACION_DESACOPLE_RADIO_V17.md yradio_chain_audit/validation_20261019.json. Campaña105104:14/851screen60yprimer120pasan~19.2%margencola2;segundo120underrunA0~91s,ADC0drops/fatalcola2margen19.36,no completar3er120. Astra:304ms sinchunksmientrasdecode208mswall/4reads;reserveDAC288→120ms,ACKmax201ms,pumpgap132ms,hostmin178sin timestamp. Causanodiscriminada;noafirmarregresiónniJSONcausa. Siguientepruebamínima120sinJSON,ringfeed/try_codesNone/service_wav/credits,ningúncambioburst/firmware.

Campaña105741restantes:10max120pasó12.28%cola3;12maxFILTERA020k60pasó13.60%cola3;16maxdual60pasó72%cola1;8/140350860continuidadpero8.43%cola4s/holgura. InputsGain/retune/volume,GUI50/100/250/500msevery10s. Qtminimal(noFPS),DSPprewarmed. Arranquefrío104852cerróTCPporlectura1.18s,restauró;offscreen104818abortoantescaptura. Preservarevidencia.

FinalQ8/1600000genOFFexactoprevio,hashf3cab6f4igual,recovery10s15991776sindropped/fatal,Qlibre.119regresioneslocalesfinalespasaron. Ningúncambioproductivoparaocultarfallocampaña;sólodiagnósticoprewarm/gui/trazafinal.


## 19/10 — controles refill completados

ADC14/851→A0 40k, GUI hasta500ms: 120s sin guardados periódicos (111057) y120s con ellos (111355) pasaron. Rings20k cubren últimos~66s; chunks máximo83.42/67.45ms, reservaDACmínima288/312ms, sintry_codesNone. Causa del fallo anterior sin identificar; no culparJSON ni declarar estable global. Comparación radio_chain_audit/refill_comparison_20261019.json y docs/VALIDACION_DESACOPLE_RADIO_V17.md. Producciónsin cambios. Restaurado8/1600000genOFF, firmwareidéntico,10s15994368sin dropped/fatal,Qlibre. Próximo: repetir con instrumentación acotada para capturar fallo correlacionado.


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


## 19/10 — selector WAV no modal, carpeta audios

Usuario pide no modal y abrir directo /audio; carpeta real audios. Implementado QFileDialogQt no nativo/modeless show, única instancia y fileSelected. Validación física Cocoa120839,8/1.6M,RADIOoff/on16s:imperial.wavaceptado,metadatoscorrectos,sinerroresGUImax130/121ms,pendientes4. NoincluyePlayA0. Qrestaurado8/597014genOFFhashidéntico,recovery5ssinerrores. Ver docs/DIAGNOSTICO_SELECTOR_WAV_V17.md.


## 19/10 — WAV variable reproducido

Ver docs/DIAGNOSTICO_CORTES_WAV_V17.md. Matriz6x18s(8/40k,14/100k xA020/40/50k)pasó.14/100k→A050k120falló59.1168s(122317),GUImax65ms. Repeticióntrazada122520pasó120s,reservamin86.4ms,huecochunks34.66msúltimos20.79s. Causanodiscriminada;nocambiosproductivos/firmware. TrazausaCPUprocessfallbackporquePythoncarecethread_time(intento122459abortóantesADCrestaurado). FinalQrestaurado16/76226genOFFhashidéntico5s382752sindrops/fatal. Siguiente repetirconringparacapturarfallo.


## ADC16/76226: variante aislada de dos créditos

Baseline `wav_playback_20261019_122909/report.json`: imperial.wav, RADIO OFF,
salida50k falla0,8448s,40k falla10,644s,20k pasa60s. GUI máxima50/37ms en
fallos. Reserva baja hasta3bloques; huecos máximos chunks46/61ms. Esto no
prueba una causa única, pero el contrato serial limita la reposición.

Experimento `--pcm-window2`: cambia sólo service_wav dentro del diagnóstico,
con una copia de función en memoria: PCM permite hasta2créditos confirmados
trasPLAY. Arranque yBEGIN/PLAY/QUERY/STOP siguen serializados; capacidadmáxima16,
chunk/tasas/firmware intactos. No incorporado a producción.

`wav_playback_20261019_123105/report.json`: salidas50/40/20k pasan60s cadauna;
reservamínima48/120/288ms. Evidencia favorable acotada;50k mantiene margen
ajustado. Faltan3×120independientes delcasocrítico yregresionesSTOP/seek/EOF
antes de incorporar. No declarar todosloscortesresueltos.
Comparación `diagnosticos/resultados_v17/wav_adc16_comparison_20261019.json`.

Q restaurado16/76226,generadorOFF,firmwareidéntico,5srecuperación382752muestras
sindropped/fatal. Sin cambios productivos en este bloque.


## Calificación larga del candidato: RECHAZADO

`wav_playback_20261019_123559/report.json`: ADC16/76226→A050k, imperial.wav,
RADIOOFF, Cocoa. Dos arranques independientes120s pasaron, tercero tuvo
UNDERRUN4/2 a4,2048s. Campaña detenida al fallar. ADCdropped/fatal0,cola1;
GUImáxima64ms en fallo. ReservamínimaPLAYING38,4ms, no reserva en instante exacto.

Traza del fallo: readmáxima53,34ms, envío socket42,28ms, hueco máximoentre
chunks86,76ms; huecoprevio79,01ms. No atribuir todo aGUI ni a latenciaACK;
lectura, envío y planificación pueden acumular pausas. El ring registra tiempos
de pared, no tiemposCPU exclusivos. Causa exacta de esas pausas sigue abierta.

Aclaración del experimento: además de ventana de2, el cambio local de `live`
reduce consulta por defecto de20 a4ms para PCM. La evidencia evalúa ambos
cambios juntos; no demuestra que sólo ventana explicase los pases previos.
No incorporado a producción. No se ejecuta aceptación de controles de un
candidato que falló continuidad. Próximo: investigar read/send bloqueantes y
reserva efectiva frente a capacidad30anunciada; no subir créditos a ciegas.

Resumen `wav_pcm_window2_qualification_20261019.json`. Firmwareidéntico,
Qrestaurado16/76226genOFF, recuperación5s sin dropped/fatal. Producciónintacta.


## Exploración posterior: capacidad negociada y procesamiento por trama

Todos experimentos aislados, sin editar producción/firmware, imperial.wav,
GUI Cocoa, RADIOOFF. Informes `wav_playback_20261019_*` bajo resultados_v17.

- 124249: sólo capacidad/objetivoPCM hasta30 (siempre min con slots anunciados),
  mantieneventana1/poll20ms.16/76226y14/100k→A050k pasan60s;reservas230,4/211,2ms.
- 124530: mismo candidato, prueba controles falla antes de ejecutar el primer
  salto:underrun a1,6704s. Noaceptar como prueba de controles. Métricareserva
  despuésdelsalto inválida porqueGUIplayedabsoluto yacceptedrelativo;señalada
  explícitamenteenreport y corregida en diagnóstico. NoesreservaDACnegativa.
- 124617: ventana2/poll4ms+capacidad30:16/76226 falla4,3872s;14/100k pasa60s.
  Durante4,36s,accepted crece205440 yplayed217440:reserva pierde12000muestras.
  Capacidadmayor no evita insuficienciaintermitente dereposición.
- 124818: agregando únicamente decoderportramas992 paraPCM al candidato anterior,
  16/76226→A050k pasa60s,reservamínima211,2ms,ADCsinpérdidas/fatal,cola1.
- 124942: mismo candidato pasóadelantar10s,retroceder5s,Stop/Play,saltohaciaEOF,
  DONEreal,reiniciotrasEOF yStopfinal, sinunderrun. Testcontrolessinaceptaciónlarga.

Hipótesisactual: el procesamientocompletodeunreadTCP antes de atenderACKpuede
retrasar reposición. El candidato procesa eventos tras cada trama comoRADIO,
conservando orden en cable. Unpase60s no prueba causalidad niestabilidadglobal;
faltanrepeticionesindependientes120s antes deincorporar. No aumentar créditos
adicionales ni extrapolar aRADIOque conserva rutaactual.

Resumen `wav_exploration_20261019.json`. Qrestaurado16/76226genOFF,
firmwareidéntico;últimarecuperación5s382536muestras,sindropped/fatal.


# Scan sin reproducción: atraso comunicado — 19/10/2026

Usuario reportó DSP/GUI atrasado al pulsar Scan, sin reproducción activa.
Bits/tasa yUS no confirmados. No atribuir aWAV.

Pruebas físicas, firmware intacto, restauración exacta posterior:
- us_multiscan_20261019_131526:16/76226Scan directo completó4candidatos sin
  errores. Ventananoexpuesta hasta captura final. ok=false por comprobación
  fijaerrónea de frecuencia en diagnóstico (esperaba500k frente a20k); nofalloScan.
- us_multiscan_20261019_131602:8/1600000ScanUS,ventanavisible,RADIO/A0OFF,
  perfiles1.6M/1.4035M/1.1189M,7hipótesis,restauración correcta. ColaGUIpico4,
  DSP0,GUImax129.7ms. Sin errores.
- us_multiscan_20261019_131647:8/1600000Scandirecto,ventanavisible,
  FFTRadio65536,8candidatos,colaGUI4,DSP0,GUImax358.4ms. Sin errores.

No reproducido elcorte,noresuelto. Hipótesisimportaciónndimage enGUI descartada:
ndimage ya está en sys.modules trasimportapp. Cambio preventivo retirado;
producciónconservada.17regresiones Scan/multiscan/fadeA0/presupuestocorrectas.
Diagnósticoahoraadmiteadc16,ventanavisible,FFT65536,midecolas yverificafrecuencia
realoriginal envezdeunvalor fijo. No modifica comportamiento deproducción.
Qrestaurado8/1600000genOFF,firmwareidéntico,10s15992640muestrassin dropped/fatal.
Siguiente: obtenerbits/tasa/US ytextoexacto delerror; distinguirlímite8lotes,
RFpendiente>1s ypresupuestodeentregaGUI. No ampliar límites paraocultarlo.


## Caso confirmado por usuario: US OFF, ADC8/1600000, sin reproducción

`us_multiscan_20261019_131839/report.json`: cincoScan directos consecutivos en
misma sesión,ventanavisible,FFTRadio65536. Todos terminaron,sin errores;
pendientesGUIpico4,DSP0,GUImax228,08ms. Candidatos14/11/13/13/9. No reproducido
elcorte. Qrestaurado8/1600000genOFF,firmwareidéntico,10s15992640sindropped/fatal.

Instrumentaciónincorporada: OutputWorker toma instantánea de presión en el
momento de la excepción de atraso, antesdeapagado/limpieza; GUI guarda una vez
el contextoScan/US/RADIO/A0/FFT/FILTER al recibir eseerror en
`diagnosticos/resultados_v17/gui_overload_*.json`. No registrocontinuo ni cambio
de límites; no se presenta como corrección de causa. ReiniciarV17paraaplicar.
Prueba local: snapshot conserva conteos tras vaciado yJSONsóloanteatraso.
RegresionesScan/multiscan/fadeA0/presupuesto/lotes:19correctas.


## Fallo real capturado: Scan → Play RADIO, sin A0

`diagnosticos/resultados_v17/gui_overload_20261019_132523_050832.json`:
ADC8/1600000,USOFF,RADIOON,A0OFF,Scanterminado,FILTEROFF,vistatemporal,
FFT2048. Error RFpendiente>1s. En instante del fallo:47lotesGUI,0DSP,
picoDSP2,1.571.616muestrasretenidas(0,98226s),28.512RFenrecogida,
45.263.136bytesestimados;GUImax1491,94ms. Esto ubica acumulación en entregaGUI;
no prueba qué callback/OS causó la pausa. No atribuir aDSP niA0.

Diagnósticoampliado --direct --scan-play: iniciaScanconRADIOOFF ydespuésPlay,
registra callbacks lentosrender_frame/_draw_display_frame/_deliver_worker_batch/
_radio_changed,60sRADIOsinA0. Intento canceladoantesdeconectarQ por monitorPID84414.
Pendientecierreavisadoparaensayoexclusivo. No se operóQ en este intento ni se
modificó producción. No confundir con repetición previa5Scan sinPlay posterior.


## Scan→Play repetido 132901

60s8/1600000USOFF,Scan28candidatos→PlayRADIOsinA0,vistatemporal:Cocoa pasó,sinfallo,colaGUIpico10,DSP2,GUImax243ms. Slowcallbacks:render_frame82msmax,draw36ms,deliver20ms;ringacotado512eventos,noCPUexclusiva. Qrestaurado8/1600000genOFFhashidéntico10s15992640sindrops/fatal. Noexplicaelcasoreal47lotes/1492ms. Instrumentaciónproductivaampliada:sóloRAMring128callbacks>=20ms(render,espectro,handle_batch),volcadoanteoverloadincluye detalle,canales,trigger,horizontal. Sinampliarlímitesnireiniciarautomáticamente. ReiniciarV17paraaplicar.


## US10/1250000 RADIO Play: fallo real 141112

Registro gui_overload_20261019_141112_707097.json:48lotesGUI,DSP0,0.9953s
retenidos,GUImax1679ms,A0OFF,USactivoenpausaRADIO,vistatemporalCH1+RADIO,
281250muestras,detalle50,triggerOFF. Callbackrendermax55ms:noexplicapausaentera.
Otroregistro140558 esdiferente:8/1.6M,DSP4,RFcoalescido1359936,GUImax126ms;
noatribuirambos al mismobloqueo sintraza.

Reproducción141246:mismoPython3.13VSCode,Cocoa,10/1.25M,CH1+RADIO281250,
RADIOPlayhasta80000muestrasantesScanUS. Pasó3perfiles,16hipótesis,restauró
RADIO/tasa/sintonía,GUImax166ms,pendientesGUI13,DSP1. Qrestaurado10/1250000
genOFF,firmwareidéntico,10s12495984sindropped/fatal. Noresuelto.

Captura productiva ampliada solamente en el fallo: worker toma pila del hilo
principal con sys._current_frames antesdequelGUIatiendaerror. Campo
`gui_thread_stack_at_failure` engui_overload*.json permite localizar bloqueo
que no aparece como callbacklento porque aún no terminó. Noamplíalímites,
nooperaQ,noregistrocontinuo. ReiniciarV17paraaplicar.


## 19/10 — generador seno150k/cuadrada200k medido

Usuario confirmóA0→CH2/A3. Candidatoaisladoexperimentos/generador_200k_v17/probe_20261019_144937:17casoscortos8dual632411,seno25–150k,cuadrada50–200kconintermedias. Comandoscorrectos,ADC0drops/fatal. Seno150medido149812.728Hzfundamental0.964Vppvs1.017a25kpara1Vppnominal. Residual82.7mVnoTHDcertificado. Intermediasincluyen73333/123456. Frecuenciarelativa relojMCU,noreferenciaexterna. reportfundamental_inicialinválidoporunidadtimestamp;usaranalog_summary.jsoncorregido. RESULTADOS.mdexplica. Qrestauradoidentidad/configexactas,recovery10síntegro. Host/UIproductivosnoampliados;faltaintegraciónporonda,prolongado/sweep/duty.


# Generador ampliado V17 — instalado 19/10/2026

Seno:0,1Hz–150kHz. Cuadrada:0,1Hz–200kHz. Resto:0,1Hz–50kHz.
Entrada numérica de frecuencias intermedias con resolución de0,001Hz en el
contrato; frecuencia efectiva redondeada por el timer. Dialeslogarítmicos y
frecuenciafinal ajustan el máximo según onda. RadioTest conserva su contrato.

## Validación

- MediciónA0→CH2/A3:17casoscortos,intermedias62500/73333/87500/112500/123456/
  137500Hzentreotras. Resultados analógicos en
  experimentos/generador_200k_v17/probe_20261019_144937/RESULTADOS.md.
- probe_20261019_145935:3arranquesporonda de120s cadauno a seno150k/cuadrada200k,
  ADC8dual632411, dropped/fatal0. Capturaanalógica alinicio de cada tramo;
  estosintervalosprueban adquisición conjunta sostenida,noTHDcontinuo.
- deployment_20261019_151624:señalCH2yestadoRUNNINGconfirmados alfinalde60s
  adicionales poronda. Sweep/Chirp62500↔150000Hz correctos enambossentidos.
-11pruebaslocales deGUI/contrato/RADIOTest/autogain/WAVcorrectas ypruebaC++
  detemporización/límites correcta.

Seno150k usa6puntos/ciclo:real~149812,7Hz,fundamental0,964Vpp frente1,017Vpp
seno25k para1Vppnominal. Mayordistorsión/residual a frecuenciasaltas;
no presentarlo como generador calibrado niTHDcertificado. Cuadrada200k
verificada en frecuencia,noflancoscalibrados. Dutyvariableaaltasfrecuencias
redondeado a pocos puntos; campaña física fue50%.

## Instalación y cierre

Firmware instalado SHA256:96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9.
Relay actualizado con límites poronda coincidentes con host yMCU.
Ajustespreviosrestaurados:True. ADC8/
1600000,generadorOFF. Recuperación10s:
15991776muestras,dropped/fatal0. Qlibre.
Respaldoprevio:/Users/fmgarciadiaz/Documents/Development/Electronica/0Fergd/SerialPythonMonitor/respaldos/unoq/osciloscopio_20261019_151625_317279.zip.

Primerintento151406seinterrumpió para corregir un contratoPythonimportadoantes
depublicarfuentes;rollbackrestaurófuentespero verificacióndealtaFS cerróflujo.
Recuperaciónposterior verificada conidentidadoriginaly10s15991776sin errores.
Segundo intento151624usa procesoPythonnuevo para comprobaciónfísica,terminó
ok/installed/restored=true. Conservar informes delintento interrumpido.

ReiniciarV17para usar nuevos límites.
