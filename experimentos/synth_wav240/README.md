# WAV240 experimental

Copia aislada de V16: sólo cambia POINTS de480 a240 y nombre de aplicación.
Frames SPI/TCP siguen siendo992 bytes; RATE20k,16slots, guardas DMA y
verificación de timestamps no cambian. Cada bloque dura12ms. No es versión
aceptada para uso normal. Monitor usa480 por defecto; --chunk-size240 sólo
se empareja explícitamente con esta aplicación. Firmware480 rechaza bloques
240 no finales; firmware240 rechaza480. No inferir compatibilidad automática.

Antes de ensayo: unittest tests.v16.test_wav240_experiment y
 tests.v16.test_synth_credit_window; compilar Board con unoq.json experimental.
probar.py guarda perfil y exporta respaldo de app V16, importa/actualiza sólo
app experimental, usa expresamente relayV16 y restaura appV16 y perfil exacto
en finally. --seconds,--targets,--presets,--credits permiten repetir casos.
Driver sigue único dueño del socket/Q; ADC compartido se valida sin descartes.
No fuerza cierre de monitor ni toma otra aplicación activa.

Compilación MCU pasó:108264bytes flash,145120bytes RAM. Test C++17 sobre
wav.h real verifica anillo, prefetched/current no sobreescritos, final parcial,
rechazo480, corte neutro ySTOP. Host verifica offsets240, créditos3/4 ySTOP.

Primer intento182549 rechazado antes de audio: usb_stream infería relayv12
por ruta experimental, incompatible con frameV16. No incluir como evidencia
de latencia. Corregido en wrapper local para elegir fuentes de relayV16 sin
modificar tools/usb_stream.py. Restauración original vio generador activado
por arranqueV16; corrigió aapagado y confirmó igualdad exacta. Reporte conserva
initial_restore_error yrestored=true con perfil final verificado.

Evidencia UTC en diagnosticos/resultados_piano/eficiencia_v16:
-20261010_213002_audio_owner.json:240p,créditos2,target8=96ms;
 Guitarra60s sin cortes ni crecimiento. target6=72ms cortó1,115s.
 Brass96ms cortó21,742s; Piano55,557s,cola8→10.
-20261010_213411_audio_owner.json: repetirGuitarra96ms, hasta120s;
 cortes96,085s (target8) y65,956s (8→10). Primer minuto no es aceptación.
-20261010_213848_audio_owner.json:240p,créditos4,target8=96ms;
 Guitarra cortó47,549s (8→10),Brass73,217s (8→12),Piano73,278s (8→10).
 Piano render worker máximo146,100ms es wall time, noCPU: no atribuir ese
 pico a coste de cálculo sin medir CPU del worker.

Nueve casos,19.761.152 muestras ADC con índices/timestamps continuos,
IPC íntegro,dropped/fatal0. Los tres ciclos de instalación/restauración
terminaronrestored=true: ADC14/100k,generadorapagado,WAVIDLE, appV16 activa.
Reportes de restauración (hora local):182933,183341,183819_wav240_restoration.
Appexperimental instalada pero detenida; V16 instalada sin modificar fuentes.
No promover240p/créditos4 ni cola96ms. Cambiar granularidad sólo no resuelve
entrega dentro del plazo; investigar tramo de tiempo real y tiempos separados
CPU/wall en trabajador, sin debilitar guardas ni validación de adquisición.
