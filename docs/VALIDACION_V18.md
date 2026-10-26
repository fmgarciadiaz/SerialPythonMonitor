## 26/10 · Comparación privada del relay diagnóstico

Compilación Linux y restauración aprobadas. Doce casos A/B de adquisición
pasaron: ADC8 máximo120s por relay y cinco controles30s. Dos recorridos
RADIO/A0 a ADC8 máximo120s pasaron funcionalidad/restauración. El control
aceptado cumplió GUI visible; el instrumentado quedó2393paintfrentea2400,
aunque expuesto100%, por eso su criterioGUI sigue falso.

Relay privado retirado, misma pareja aceptada y estado inicial restaurados;
Preparar Q final aprobó10s. No se modificaron fuentesQ ni V17. No se considera
resuelto el dropped1original ni se promueve el candidato. Se preserva un
intento previo fallido de arranque y su recuperación posterior.
[Resultados y límites](../experimentos/relay_telemetry_v18/RESULTADOS_20261026.md).

## 26/10 · Revisión por cierre ADC8 máximo con RADIO/A0

Se confirmó pérdida de1 nodo con cola8/8 y cierre deliberado del relay,
CRC correcto y sin error fatal del ADC. No atribuirlo a las etiquetas UI.
La pareja catálogo sí cambió binarios por tablas/predicados ampliados, aunque
los perfiles previos conservan configuración y métodos.

Regresión ampliada:32/32 tasas nuevas con RADIO/A0≥30s, y5/5 máximos previos
con RADIO/A0≥120s, todos con restauración e identidad verificadas. No se
reprodujo el fallo. Corrida mayormente en segundo plano; sólo6/37 casos
cumplen GUI visible, sin calificar visualmente ADC8 máximo. No se cambiaron
firmware ni tasas, ni se certifica holgura con esta matriz.
Informe: `diagnosticos/resultados_v18/radio_rates_review_20261026_130257/report.json`.
[Diagnóstico y límites](DIAGNOSTICO_ADC8_MAX_20261026.md).

## 25/10 · Catálogo de tasas incorporado y validado

Nueva pareja: firmware `37f049fa…`, relay `27da0bc4…`.
Los máximos anteriores y sus métodos se conservan. Se incorporan 17 perfiles
de audio y 15 intermedios CH1, con catálogo visible de 17 opciones en 8–14 bits
y 15 en 16 bits. Los perfiles históricos siguen accesibles.

Aceptación privada: audio 17×60 s, intermedios 15×60 s, audio integrado
17×15 s y GUI visible 10/10. Rollback exacto, prebuild, respaldo y update
transaccional aprobados. Regresión posterior: 237 pruebas V18 y 30 adicionales.
Regresión instalada: 32/32 perfiles, 15 s cada uno, holgura aprobada,
cola máxima 2, sin pérdidas/fatales y restauración verificada.
Informe: `experimentos/fs_max_v18/installed_campaign/20261025_223730/report.json`.
148 rutas históricas de Scan permanecen idénticas. V17: 175 archivos protegidos
verificados intactos. GUI instalada visible: 10/10 aprobadas y restauradas. Preparar Q final verificó
identidad y adquisición durante 10 s. Informe GUI:
`diagnosticos/resultados_v18/catalog_installed_gui_20261025_224618/report.json`.
[Detalle del catálogo](CATALOGO_TASAS_V18_PLAN_20261025.md).

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
Detalle y evidencia: [campaña](SONDEO_TASAS_V18_20261025.md).

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
Detalle: [campaña de tasas](TASAS_ALTAS_V18_20261025.md).
No quedan procesos de campaña activos; continuar desde esta pareja aceptada.

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
Validación GUI offscreen: 43 regresiones pasaron y, tras el ajuste de escalas,
10 pruebas de cursores pasaron, incluida la señal de Demo (CH1 cuadrada y
CH2 RC) atravesando V(t), FFT y heatmap. Bode se verificó con datos de
transferencia conocidos. No se opera el Q ni se acredita FPS físico. V17 intacta.

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

## 24/10 · reanudación FS y fallo Synth20

Sondeo BatchArena de ocho tasas (15s cada una) PASS, con restauración verificada:
`experimentos/fs_max_v18/resultados/20261024_180456/report.json`.
10bits: ticks126/124/122, máximo1.311.475S/s, margen17,30%, cola2.
12bits: ticks148/146, máximo1.095.890S/s, margen12,79%, cola2.
14bits: ticks184/180/176, máximo909.091S/s, margen23,65%, cola2.
Son sondeos privados, no aceptación sostenida ni habilitación pública.

Host actual con AGC gradual/default60%/10×: GUI8/88 `gui_private_20261024_175059`
PASS completo120s y restauración. `175550` completó RADIO120,341s y WAV,
falló Synth20 a20kHz (UNDERRUN); restauración PASS. Reproducción corta
`180149` repitió falloSynth: renderhasta25,03ms/480muestras(24ms), roundtrip
33,16ms, ACKmáx15,90ms; no atribuir todo al transporte ni considerar paseglobal.
Prueba de producción `synth20_resume_diagnostic_20261024.json` falló antes en
RADIO con ACK190–203ms, caso distinto. Evidencias conservadas.

Se agregó captura genérica del transporte PCM al fallar Synth y actividadmacOS
user en el proceso dedicado de render, con Finalize al cerrar el pool.18tests
proxy/Synth PASS; efecto físico pendiente de repetición. V17 intacta.

## Transición a pareja propia ·23/10/2026

Scope V18 y relay V18 activados desde copia independiente de la base validada.
V17 preservada en `respaldos/parejas/v17_20261023_000325` y detenida en el Q.
Los informes anteriores de esta página corresponden al monitor V18 usando
la pareja Q V17, y conservan esas identidades históricas. La nueva validación
se registra por separado en `gui_pair_v18*_20261023.json`.

La primera prueba nueva sufrió sobrecarga durante ejecución simultánea de
la batería offline. Su cierre falló por interrupción a mitad de eventos de
una lectura. Se preservó el informe y se recuperó el snapshot desde una
conexión nueva: `pair_v18_recovery_20261023.json` confirma10s y ceroerrores.
Se añadió una regresión y se difiere el error de sobrecarga hasta completar
los eventos del receptor; no se descartan fallos silenciosamente.

La prueba moderada también falló por acumulación RF. Astra verificó que la
traza de GUI se toma después de la restauración del Q: no identifica el lugar
del fallo original. El intento con ventana activa y caffeinate también falló;
no hay evidencia para atribuirlo a App Nap ni al render temporal.
Se instrumenta el instante de la sobrecarga en el proceso receptor antes de
repetir una prueba con muestreo externo de la GUI. No se aumentan buffers.
La batería offline de 162 pruebas pasó; esto no sustituye aceptación física.
El primer diagnóstico con Scan tardío clasificó su pausa automática de A0
como corte: el script ya espera Scan completado antes de iniciar la ventana
medida de audio. Ese intento no se usa para calificar estabilidad del producto.

El ensayo `gui_pair_v18_sampled_20261023.json` conserva el nuevo snapshot:
14 bits/40 kHz, cuatro lotes retenidos (0,1024 s), 36.106 muestras acumuladas
(0,90265 s) y último crédito recibido unos 1,000 s antes. La sobrecarga ocurrió
antes de Stop. `/usr/bin/sample` capturó la GUI durante ocho segundos; queda
pendiente correlacionar las esperas entre procesos. La restauración fue confirmada.

La repetición sin sampler `gui_pair_v18_flow_only_20261023.json` también sufrió
UNDERRUN RADIO. La fuente tenía audio disponible; la entrega de bloques sufrió
pausas de 263 ms y 164 ms. El problema no exige muestreo externo para aparecer.

`gui_pair_v18_pcm_flow_20261023.json` completó el recorrido de 50 s sin errores:
Scan, RADIO/A0 a 40 kHz, retune, Stop, WAV, Synth DX de 20 voces y restauración.
Es un pase puntual con traza PCM, no prueba que el fallo intermitente esté resuelto.
Astra identificó un cuello estructural: el remoto sólo acepta un bloque listo
por ronda IPC, impidiendo aprovechar la ráfaga de recuperación ya configurada.
Se trabaja en agrupación acotada sólo para RADIO, sin ampliar la cola DAC.

La agrupación RADIO pasó las pruebas locales (167 backend y 21 GUI) y el
recorrido físico moderado `gui_pair_v18_burst_40k_20261023.json`.
El intento sin traza `gui_pair_v18_burst_1600_20261023.json` falló cerca de
40,9 s con UNDERRUN y luego acumulación RF durante el cierre; restauración
confirmada. Registró gaps de alimentación DSP de 748,6 ms y de producción PCM
de 705,9 ms. No completó los 60 s de RADIO ni las etapas posteriores.

Astra detectó presión de dibujo: timer de 16 ms frente a callbacks lentos
habituales de más de 30 ms. La estadística disponible filtraba callbacks
mayores de 20 ms y no permite afirmar causalidad. El smoke admite ahora
`--render-interval-ms` y mide todos los renders (CPU del hilo y reloj), CPU del
proceso y heartbeat Qt. Comparación de 50 ms sólo experimental; no modifica
la cadencia de la aplicación ni amplía reservas.

La comparación `gui_pair_v18_burst_1600_render50_20261023.json` también
falló cerca de 29,9 s, con restauración confirmada. En ventanas de cinco
segundos, el render usó 25–29 % de CPU del hilo; el mayor callback completo
midió 88,9 ms y el heartbeat Qt alcanzó 1,874 s. Reducir la cadencia a 50 ms
no bastó. Se conserva la cadencia de producto de 16 ms; la causa de la pausa
larga sigue sin determinarse. No se calificó la tasa máxima ni se aumentó FS.

# Validación de V18 · 22 de octubre de 2026

La integración usa GUI y receptor propios de V18. V17 conserva sus archivos;
los 111 orígenes del manifiesto GUI coinciden con los hashes tomados al copiar.
El firmware MCU y el relay instalados no se cambiaron.

## Evidencia física

- [Receptor a 8 bits/1,6 MS/s](../diagnosticos/resultados_v18/receiver_20261022_184657.json):
  15.964.128 muestras en 485 lotes durante la prueba de aproximadamente diez
  segundos. Restauración confirmada y recuperación de 10,0058 s con 16.005.600
  muestras, cero pérdidas y cero errores reportados.
- [Matriz de once casos](../diagnosticos/resultados_v18/modes_20261022_185201.json):
  cambios de perfil en 8/10/12/14/16 bits, seno de 997 Hz, WAV por mmap a
  20/40/50 kHz, niveles, seek y Stop. Cierre con restauración y recuperación
  de 10,0085 s sin pérdidas ni errores. Estos cambios breves no califican cada
  perfil para uso sostenido.
- [Primera prueba visible](../diagnosticos/resultados_v18/gui_live_20261022.json):
  adquisición, RADIO, Scan, A0, resintonía y cierre sin errores del worker.
  Registró 1941 eventos de dibujo incluyendo desconexión; esa cifra no es FPS
  calculado sobre 32 segundos. RADIO/A0 mostró avance real y una resintonía.
  El inicio WAV sólo quedó solicitado en este primer informe; la campaña
  posterior incorpora aserciones de reproducción y progreso.

- [Campaña GUI prolongada](../diagnosticos/resultados_v18/gui_long_20261022.json):
  RADIO/A0 confirmó 120,007 s de reproducción a 40 kHz mientras adquiría a
  8 bits/1,6 MS/s. Sin UNDERRUN/FAULT ni errores registrados; resintonía
  conservada y reserva mínima de 15.041 muestras de audio. Scan terminó con
  30 candidatos. WAV confirmó PLAYING, avance y finalización desde la GUI.
  Las nueve aserciones de reproducción, Stop, cierre y liberación pasaron.
  La ventana estuvo expuesta en todas las muestras periódicas; durante la
  fase sostenida registró aproximadamente 33–47 eventos de dibujo por segundo.
  Esa medición corresponde a esta ventana y carga, no a todos los modos.

- [GUI final con Synth/FM](../diagnosticos/resultados_v18/gui_fm_20261022.json):
  confirmó reproducción, avance y Stop de RADIO, WAV y Synth/FM (20 kHz),
  además de Scan, cierre y restauración. Las trece aserciones pasaron sin
  errores. Incluye preparación nativa de FM antes de BEGIN, en un productor
  separado, mientras continúa la recepción RF.

Los informes de sesiones en `diagnosticos/resultados_v18/sessions/` guardan
identidad MCU/relay, perfil ADC codificado y todos los parámetros del generador
antes de operar. La restauración se confirma después de recuperar adquisición,
cerrar el socket y liberar el túnel propio. Los intentos fallidos iniciales se
conservan: detectaron cancelación a mitad de procesamiento de una lectura TCP.
Se corrigió para procesar todos sus eventos antes de interrumpir la recepción.

## Pruebas locales

La batería del núcleo aprobó 154 pruebas en 20,336 s. La suite GUI integrada final
aprobó 20 pruebas en 7,389 s, con controles, RF/DSP/GUI, fuentes RADIO/FM,
WAV, FIFO de confirmaciones, créditos y cierre. Se añadieron regresiones para
muerte del padre, cancelación durante una lectura, rechazo de audio ajeno sin
STOP y limpieza de túnel ante fallo del constructor de conexión.

## Alcance

Estas pruebas acreditan integración funcional y los casos medidos. No acreditan
calidad analógica ni audio escuchado, holgura mínima del 10 %, estabilidad
prolongada de todas las tasas, UART, Bode físico ni todos los instrumentos y
entradas MIDI. El prototipo asíncrono anterior permanece aislado: la GUI usa
el receptor maduro dentro de un proceso, con sus transacciones acotadas.

Arranque: `python -m monitor.v18 --gui`. V18 requiere Scope V17 y su relay ya
activos; su interfaz no instala, inicia ni reinicia programas del Q.


## Captura en el instante de pausa · 23/10/2026

Se preserva ahora el snapshot del hijo también cuando el terminal llega durante
el cierre, después de que RADIO haya detenido el worker. Once pruebas del proxy
aprobadas, incluidas dos regresiones de llegada tardía y captura única.
El smoke admite `--stall-trace`: watchdog nativo de faulthandler a 700 ms,
rearmado por heartbeat Qt; desactivado durante restauración. Sin cambios de
cadencia, prioridades, firmware o reservas.

`gui_pair_v18_stall_exact_20261023.json`: PASS, RADIO/A0 60,218 s a ADC8/
1,6 MS/s, Scan, retune, WAV, Synth20 y restauración. Todas las aserciones
aprobadas. Heartbeat máximo 493,5 ms; callback render máximo 54,8 ms. No se
activó captura de pausa. Este pase no anula los fallos intermitentes previos.
Repetición independiente `gui_pair_v18_stall_exact_repeat_20261023.json`: PASS,
RADIO/A0 60.334 s, todas las etapas y restauración confirmadas. Sin dump
de pausa. Dos pases consecutivos no determinan la causa de los fallos previos;
queda pendiente repetición sostenida y comparación sin watchdog.


## RADIO sostenida sin watchdog · 23/10/2026

`gui_pair_v18_radio120_plain_20261023.json`: PASS, 120,241 s de RADIO/A0
confirmada a ADC8/1,6 MS/s, salida 40 kHz. Sin traza IPC, sampler ni watchdog;
cadencia de producto sin cambios. Scan, retune, Stop, WAV, Synth20 y todas
las aserciones aprobadas. Heartbeat máximo 483,9 ms; render máximo 38,6 ms.

La sesión `sessions/session_20261023_042136_487996.json` confirma identidad
Scope V18, restauración del perfil inicial y recuperación de 10,023 s con
313.344 muestras, cero dropped/fatal y continuidad. Se conservan los fallos
anteriores: este pase no identifica su causa ni acredita nuevas tasas o
holgura del transporte. Faltan repeticiones independientes de 120 s.


## Tres corridas de 120 s completadas · 23/10/2026

Segunda y tercera corridas sin watchdog/traza/sampler:
`gui_pair_v18_radio120_plain_run2_20261023.json` y
`gui_pair_v18_radio120_plain_run3_20261023.json`. RADIO/A0 duró 120,299 y
120,294 s respectivamente. Ambas completaron Scan, retune, WAV, Synth20,
todas las aserciones y restauración. Se completa el bloque de tres corridas
independientes de 120 s; los fallos intermitentes históricos se conservan y
su causa no se atribuye a una corrección sin evidencia controlada.

El runner de tasas experimentales ahora captura política CPU normal después
del perfil bajo, separada de la política activa inicial. Restaura y verifica
esa base antes de reactivar el perfil original. Diez tests del runner/journal
aprobados, incluida regresión normal schedutil frente a activo performance.


## Continuación hacia tasas nuevas

Completadas las tres RADIO120 públicas, los primeros sondeos privados con la
receta original perdieron muestras en ADC10/126 y ADC12/148. ADC8/88 pasó60s
pero perdió muestras en la primera repetición120s. No se incorporan esas tasas.
Los reportes y la comparación SPI40/WORD se detallan en
[optimización y tasas](OPTIMIZACION_Y_TASAS_V18.md). El objetivo ADC8 sigue en
1,8MS/s; también se ensayan incrementos10/12/14 por instrucción del usuario.
No confundir sondeos de integridad con calificación GUI/RADIO/analógica.


## Transporte nuevo: calificación de datos ADC10/12

SPI40/WORD aprobó60s+3×120s en10bits/1,311475MS/s y12bits/1,081081MS/s.
Reporte `experimentos/fs_max_v18/resultados/20261023_021652/report.json` y
cierre restaurado. ADC10 tiene colas3/4/4:integridadPASS,holguraNO.
ADC12 tiene3/2/3 y márgenes24,25–24,36%:holgura aisladaPASS. FaltaGUI/RADIO
combinada y aceptación analógica antes de promover.

Se prepara arnés `tools/probe_gui_live_v18.py` para esas pruebas. Configura
app experimental bajo lock, cede el lock al hijoGUI durante adquisición y
lo recupera sólo al cerrar para restaurar producción. `gui_experimental_v18.py`
inyecta únicamente el perfil seleccionado en ese proceso y sus spawn; no
modifica listas públicas. La identidad experimental requiere nombre explícito;
la conexión normal mantiene ScopeV18. Seis tests cubren identidad estricta y
propagación real del perfil/factory al spawn. No hay adquisiciónQ en esos tests.

ADC8 Full8 (`resultados/20261023_023426`):60sPASS,cola7/8,margen12,98%,
restauracióntrue;noholgura. Se inicia3×120. Sin tasas nuevas publicadas.


## GUI experimental ADC12 reproduce la pausa

`gui_private_20261023_025054/report.json`:la GUI aADC12/1,081MS/s falló
RFbudget trasuna pausa heartbeat6,520s;maxrender45,8ms. La fuente de datos
había pasado60+3×120 sinGUI. Ventanaexpuesta en las etapas medidas. El hijoGUI
restauró su snapshot yel coordinador restauró producción,ambosconfirmados.
No promover por la sola integridad del transporte.

Se añade comparación diagnóstica `--macos-activity user`:actividadNSProcessInfo
UserInitiatedAllowingIdleSystemSleep,tokenretenido duranteensayo yliberado al
salir,sinpreferenciasglobales. Opcióncritical disponible sólo para comparación.
El encabezadoNSProcessInfo.h instalado y [la guía de Apple](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/PrioritizeWorkAtTheAppLevel.html)
documentaneste mecanismo para tareas iniciadasporelusuario;noatribuir todavía
el fallo aAppNap. Ochotests deidentidad,spawn yliberaciónrealdel tokenPASS.

## Primera GUI con actividad macOS: PASS, pendiente repetición

`gui_private_20261023_025938/report.json`: ADC12/1,081081 MS/s pasó RADIO/A0 60,33 s, Scan, resintonía, WAV y Synth20. Restauración de producción confirmada. Heartbeat máximo 323,28 ms; render máximo 35,65 ms. Token `user` liberado al terminar. Una corrida no demuestra que AppNap sea la causa; se repite a 120 s antes de incorporar el mecanismo al monitor.

Repetición ADC12 de 120 s: `gui_private_20261023_090239/report.json`, `ok=true`, GUI y restauración de producción confirmadas. Todas las aserciones de RADIO/A0, Scan, WAV, Synth20 y cierre aprobadas; sin errores. Actividad `user` liberada. Se continúa ADC10/122 con idéntica matriz.

## GUI ADC10/1,311475 MS/s: fallo combinado, restaurado

`gui_private_20261023_090743/report.json`: RADIO/A0 no completó 120 s; el Q cerró el flujo. Heartbeat máximo 511,87 ms y render máximo 126,13 ms. El ensayo no presenta la pausa GUI de varios segundos del caso anterior. WAV y Synth no llegaron a aprobarse; no promover este perfil. La GUI informó salida sin confirmar, pero la restauración externa de producción terminó verificada (`hardware_restored=true`, fase cerrada). Actividad `user` sigue siendo diagnóstica.

## ADC8 WordPing 1,818181 MS/s: integridad sostenida PASS

`experimentos/fs_max_v18/resultados/20261023_092727/report.json`: 3×120 s independientes, sin pérdidas, restauración confirmada. Colas pico 5/7/7 de 8; márgenes medios 15,273/15,118/15,497%. Sumado al sondeo previo de 60 s aprobado. Holgura NO por cola; no habilitar tasa pública. Se continúa GUI/RADIO/A0 120 s con Scan, WAV y Synth20 en app experimental.

GUI ADC8 WordPing (`gui_private_20261023_093621/report.json`): FAIL RF pendiente >1s y audio faltante, producción restaurada. CH1+RADIO, 409091 muestras, render máximo318ms y heartbeat697ms; tiempos de render crecen durante el ensayo. Se añade perfilado diagnóstico opcional de uno de cada diez callbacks, sin alterar producto, ventana ni canales.

## ADC8: comparación de inactividad de pantalla

A pedido del usuario se repitió con pantalla despierta y actividad declarada, sin preferencias persistentes: `gui_private_20261023_094859/report.json`. `pmset` confirmó las assertions PreventUserIdleDisplaySleep y UserIsActive del guard durante 600 s; NSActivityuser también activo. Ventana expuesta en todos los registros. Aun así el Q cerró el flujo a~25 s (render máximo71 ms, heartbeat489 ms). Esto demuestra que protector/apagado no son necesarios para reproducir este fallo; no excluye efectos de ocultación en otras condiciones. Guard liberado y producción restaurada confirmados.

El ensayo previo con pantalla50ms (`gui_private_20261023_094620`) también falló por cierre de flujo y restauró producción. No atribuir los cierres únicamente al costo de render. El coordinador añade captura best effort de candidate_relay.log tras liberar la GUI y adquirir el lock, antes de restaurar, para futuras corridas.

## Motivo confirmado del cierre ADC8 bajo RADIO/A0

`gui_private_20261023_155006/candidate_relay.log`: el validador estricto rechazó una trama kind20 con CRC correcto porque dropped=1 (fatal=0), cola pico8/8. send_previous580365ticks=3,627ms frente a 306944ticks=1,918ms disponibles por nodo. Producción restaurada. La pérdida está confirmada; su causa temporal todavía requiere aislarse.

Se añade recipe trace8 con MCU WordPing idéntico y ring64 de metadatos en relay, impreso sólo al rechazo o host lento. Sin cambiar SPI, buffers ADC/DAC, formato ni validaciones. Test C verifica orden y límites tras wrap. Se compara último tipo de comando/ACK y tiempos para evaluar la hipótesis de ráfagas WAV, sin darla por demostrada.

La traza del relay (`gui_private_20261023_155820/candidate_relay.log`) muestra intervalos sostenidos de ~0,5–0,6ms, con cola5→8 y sólo3 respuestas WAV entre64 tramas. No demuestra inanición por ráfaga WAV. Se conserva prioridad actual y se agrega desglose READY/ioctl al ring para aislar el costo. La corrida restauró producción. Un intento anterior canceló antes de medir por texto noUTF8 de pmset; su restauración también está confirmada.

`gui_private_20261023_160136`: trace8time combinado60s PASS/restaurado. Repetición120s `gui_private_20261023_160652` falla por UNDERRUN A0 (state4/reason2), sin rechazo de integridad ADC, restaurada. Resúmenes de ventanas64frames: ioctl277–280us, READY70–121us, gap438–482us; no extrapolar a medias globales. La colaDAC pasó de llena a sólo108ms antes de agotar; heartbeat máximo531ms. Es distinto del dropped1 de otros ensayos.

Se prepara AlignedPing como comparación mínima de cargas alineadas del patrón, conservando fallback seguro y todas las verificaciones. No se supone ganancia hasta medir el MCU.

AlignedPing (`experimentos/fs_max_v18/resultados/20261023_161220/report.json`): FAIL a17,836s, pérdidaADC ycola8/8, check23us. No mejora material sobreWordPing26us; descartado para promoción. Restauración completa y recuperación10s sinpérdidas verificadas. La evidencia apunta a necesitar reducir overhead de intercambio de forma sustancial, además de resolver UNDERRUN intermitente; no basta la microoptimización de carga alineada.

## Transporte SPI16: primer gate preparado

Astra revisó el plan y el código sin hardware. Sol implementó `prepare_spi16.py` y cerró17tests locales de geometría, orden debytes, CRC, muestras y decoder. La app privada SPI16 usa una tramaSCP1 de992bytes por intercambio; DSIZE/CRCSIZE15, TSIZE496, DMA2/4bytes. Se inicia un sondeo15s para verificar compatibilidad física, sin prometer una ganancia de rendimiento. El plan y las barreras para agrupación posterior están en `docs/PLAN_TRANSPORTE_SPI16_V18.md`.

SPI16 gate1 físico (`resultados/20261023_162948/report.json`): PASS15s a1,818181MS/s, cola3/8, margen15,4128%, sinpérdidas. Configuración inicial/warmup/target/retorno pasaron y producción restaurada. No es calificación sostenida. Se continúa carga combinadaGUI/RADIO/A0 hold120 con Scan/WAV/Synth20 antes de decidir agrupación.

## Audio RADIO: corrección del lock y validación pública

La prueba de concurrencia con correlación real pausada reprodujo que el consumidor no podía leer audio disponible. Se movió el cálculo fuera del lock, manteniendo segunda comprobación de cierre/error y la política de ráfaga. Pasaron tres pruebas de concurrencia y 24 regresiones.

`gui_radio_lockfix_1600_20261023.json`: 8 bits/1,6 MS/s, RADIO/A0 120,315 s, Scan, retune, WAV y Synth20 PASS; sin errores, salida apagada confirmada y worker liberado. Medidos detector max53,28ms y espera lock max0,156ms. La restauración del snapshot se completó por el backend. No es calificación de la tasa experimental.

## Batch2: sondeo físico inicial aprobado

`experimentos/fs_max_v18/resultados/20261023_192349/report.json`: ADC8/1,818181MS/s, dosSCP992 por intercambio SPI16,15s PASS sinpérdidas. Cola pico2/8, margen16,6593%; restauraciónconfirmada. Se continúa prueba combinada120s; sondeo corto no habilita tasas públicas.

## Batch2 combinado: pérdida ADC confirmada

`gui_private_20261023_192909` falló bajo RADIO/A0. La repetición diagnóstica `gui_private_20261023_193313` guardó la trama: CRC correcto, dropped1/fatal0, cola pico8/8, send454285ticks. Ambas restauraron producción. El sondeo aislado15s no predijo estabilidad combinada. Preparación/verificación del últimoestado114/326us son valores puntuales, no medias. Se detectó validación/decodificación duplicada del RXbatch en el prototipo; el siguiente candidato debe decodificar una vez, validar ambas mitades antes de aplicar y preservar todos los CRC y barreras.

## BatchFast: combinación con decodificación única

`resultados/20261023_194020/report.json`: ADC8/1,818181MS/s60s PASS sinpérdidas, cola2/8, margen20,3719%, restauraciónconfirmada. CombinaCRCrápido,WordPing,SPI16,2tramas ydescriptorcomando decodificadouna vez; validación deambasmitadesantesaplicar. Tests de todos tipos y corrupción/camposreservados PASS. Se continúa GUI/RADIO/A0hold120; holguraaislada no acreditaaceptacióncombinada.

BatchFast combinado (`gui_private_20261023_194632/report.json`) falló por UNDERRUN A0 (state4/reason2) alrededor9,95s. El relay no registró pérdida ni rechazo ADC en esta corrida; producción restaurada. Esto no constituye estabilidad ADC sostenida bajo carga. Margen aislado60s20,37%/cola2es mejora medida, pero la entrega de audio sigue pendiente. Siguiente diagnóstico debe registrar disponibilidad y latencia PCM al instante del UNDERRUN, sin aumentar buffers ni reducir canales/ventana.

## BatchFast: primera prueba combinada de 120 s aprobada

`gui_private_20261023_201315/report.json`: RADIO/A0 120,164 s a ADC8/1,818181 MS/s, Scan, retune, WAV y Synth20 PASS. Sin errores; cierre, liberación del worker y restauración de producción confirmados. Se mantienen buffers, canales, ventana y cadencia. Se continúa 3×120 s aislado y repetición combinada: el historial incluye fallos intermitentes, por lo que este PASS único no habilita todavía una tasa pública.

La instrumentación PCM registra tiempos de petición/respuesta y reserva al notificar UNDERRUN. Pasaron 29 tests de receiver/concurrencia/timing/outputproxy. Se corrigió también el arnés para no leer un worker Qt eliminado al guardar:200256 quedó detenido (terminación exclusivaGUI tras salida del receptor, restauración externa verificada),200920 pasó etapas60s pero tuvo error deguardado. Se preservan como intentos incompletos, sin convertirlos en PASS de campaña.

## BatchFast: calificación aislada completa

`experimentos/fs_max_v18/resultados/20261023_201814/report.json`:3×120s independientes PASS a1,818181MS/s, dropped0/fatal0, cola pico2/8 en las tres y márgenes medios20,2745/20,3824/20,3381%. Restauraciónconfirmada. Junto con60s194020, transporteaislado yholgura aprobados. Se repite GUI/RADIO/A0hold120 de formaindependiente; no habilitar tasa pública por aceptación aislada.

## BatchFast ADC8: calificación privada del 23/10

El candidato ADC8/88 alcanza 1.818.181,818 S/s. El transporte aislado pasó
60 s y tres arranques independientes de 120 s, con cola pico 2/8 y margen
medio de envío 20,27–20,38 %. Además, tres corridas GUI independientes
completaron RADIO/A0 durante 120 s, Scan, resintonía, WAV, Synth de 20 voces
y cierre, con restauración de producción verificada en cada caso.

[Evidencia consolidada con hashes](../experimentos/fs_max_v18/resultados/batchfast_acceptance_20261023.json).
Los ensayos GUI usaron actividad macOS `user` y guardia temporal de pantalla.
Con CH1+RADIO, la pintura mínima por intervalo fue 14,23–17,17 FPS; no se
atribuye 60 FPS a la cadencia del temporizador. La aceptación analógica sigue
pendiente. No se habilitó ninguna tasa pública nueva.

BatchFast combina CRC rápido en relay, WordPing, SPI16, dos tramas SCP1 por
intercambio y decodificación única con validación de ambas mitades antes de
aplicar comandos. El host V18 evita retener el lock PCM durante correlación
de realimentación y conserva telemetría de entrega. Los fallos anteriores
permanecen documentados; estos resultados no prueban una causa única.

Antes de incorporarlo: regresión de los máximos públicos CH1/dual, ensayo con
las condiciones de actividad de la aplicación normal y respaldo pareado del
candidato. V17 permanece congelada: 175 hashes verificados sin diferencias.

## Regresión BatchStack de perfiles públicos

`experimentos/fs_max_v18/resultados/regression_20261023_205425/report.json`
completó nueve máximos nativos públicos CH1/dual de8/10/12/14 y16dual,
15 s por perfil, con integridad y restauración PASS. Cola pico1–2 y margen
medio15,56–84,42 %. Es screening, no calificación sostenida de los nueve.

BatchFast falló en dual8/632411 con dropped1 y CRC correcto
(`regression_20261023_204039`), restaurado. Se separó el pipeline dual de la
selección del reloj y del validador rápido CH1: scratch dedicado en el stack
permanente de output_worker, no en timestamps DMA. Esta variante es otra app,
BatchStack; el candidato CH1 calificado BatchFast permanece intacto. La variante
intermedia BatchNative con1984bytes BSS adicionales no obtuvo READY en dos
arranques, ambos restaurados; el límite de memoria es hipótesis, no causa
confirmada por log MCU. BatchStack sí arrancó y completó los nueve perfiles.

Respaldo pareado del BatchFast validado: `respaldos/parejas/v18_batchfast_20261023/manifest.json`,
con firmware/relay binarios verificados contra las identidades medidas y fuentes
monitor/Q. Ninguna tasa pública nueva habilitada. Continúa GUI120 de BatchStack
sin actividad macOS ni guardia de pantalla del arnés.

## Revisión de promoción y BatchArena

Astra revisó propiedad DMA, stack y cambios de época. No observó uso después
de retorno en BatchStack, pero su scratch residente consumía1984 de4096bytes
del worker. Se prefirió BatchArena: dos SampleFrame al final de DualMemory,
135616bytes dentro de la unión de163840, sin crecimiento de RAM global y sin
cambiar offsets de ADC/timestamps/muestras. Asserts de ABI objetivo y tests
ASan/UBSan de canarios/rebinding PASS. ELF exacto en artifacts de transitions
230035: storage0x28060, workerprólogo36registros+52locals; esto confirma que
no conserva el array2k, no constituye cota completa del stack de callees.

BatchArena completó15etapas sin reinicio: tres ciclos WordCH1→dual8→normal14
→dual10→WordCH1; cada etapa exige APPLIED y datos del epoch actual, luego5s
sin pérdidas. Incluye dual8 con9fragmentos por nodo. Informe
`experimentos/fs_max_v18/resultados/transitions_20261023_230035_900025/report.json`,
restauracióntrue. La matriz completa y campañas sostenidas del nuevo binario
se registran aparte; no se heredan identidades de BatchStack.

BatchStack quedó como antecedente respaldado en
`respaldos/parejas/v18_batchstack_20261023`: aislado60+3×120 yGUI3×120 sin ayudas
macOS/guardpantalla PASS, cola2 y margen20,31–20,52%, restauracionestrue.
No está promovido. Scope V18 de producción y V17 siguen conservados.

## 24/10: latencia PCM, desacople de DSP y fallo residual DAC

Se instrumentó el recorrido del pedido PCM sin cambiar firmware ni reservas.
GUI102904 falló con hasta302ms antes de atender el pedido, mientras la espera
del ejecutor fue5,8ms y el render14,7ms. Se añadió canal acotado independiente
para pedidos PCM; muestras y ACK de control siguen en su FIFO. Las pruebas
spawn verifican atención PCM sin consumir previamente RF.

El callback publica ahora audio demodulado antes de la correlación pasiva del
detector de loops; la detección positiva sigue vaciando/cortando salida. Se
separó el crédito IPC de la copia RF ya procesada de su consumo GUI durante
RADIO y WAV BUFFERING/PLAYING. La GUI retiene el lote completo bajo el mismo
DeliveryBudget; no se descartan muestras ni se amplían reservas. Tests de
liberación única y estados WAV verifican ambos caminos.

Con este host, `gui_private_20261024_111112/report.json` completó RADIO/A0
120,147s, Scan, WAV, Synth20 y apagado, sin errores, restaurado. La repetición
`111621` falló por UNDERRUN a~44s: audio disponible en padre, RPCmáx50,6ms,
ACKmáx215ms y15CHUNK en vuelo. También restaurada. Por tanto NO está cerrada
la aceptación combinada, y1,818MS/s sigue privada.39tests localesPASS;
V17 conserva175hashes del respaldo.

Astra revisó el último tramo: read/decode no medían el procesamiento posterior
de eventos ni huecos entre pumps. No se atribuye aún la demora a ADB/MCU;
TCP_NODELAY ya existe en ambos extremos propios. Los480samples restantes
reportados al UNDERRUN son contabilidad de la guardia, no audio DMA utilizable.
Siguiente evidencia: wall/threadCPU del receptor completo con ring acotado,
sin cambiar arbitraje ni colas. Una actividad macOS sólo en padre no evitó
el fallo; eso tampoco descarta descheduling del proceso receptor separado.

## 24/10 · cierre para prueba manual

La combinación final pasó tres corridas privadas independientes con RADIO/A0
120 s, Scan, WAV, Synth20 y cierre. [Evidencia consolidada](../experimentos/fs_max_v18/resultados/batcharena_acceptance_20261024.json).
La exposición de la ventana varió y se registra en el informe; esos pases no
constituyen una afirmación de 60 FPS ni aceptación analógica.

El monitor normal sin flags especiales también pasó a8bits/1,6MS/s, con RADIO
60,323s y todas las etapas, restauración10s sin pérdidas. Informe:
`diagnosticos/resultados_v18/gui_public_stock_final_20261024.json`.
La actividad macOS durante adquisición se crea en padre/receptor y se libera
al cerrar; no cambia preferencias de reposo. El máximo público sigue en1,6MS/s.
1,818MS/s espera incorporación y validación de la pareja instalada.

El usuario pidió probar: Q libre/restaurado, sin campañas activas. Se preservó
la pareja actual con fuentes, app, binarios y manifiesto; V17 conserva175hashes.

## Auto gain gradual ·24/10

En V18, subida normal limitada a1dB/s y bajada a2dB/s; revisión normal cada100ms.
La cuantización0,1× acumula tiempo desde el último ajuste efectivo. Una pausa de
interfaz no genera catch-up brusco (máximo0,5s de rampa por ajuste).

Sólo ante audio próximo a los límites (≤0,05V o≥3,25V) se permite una reducción
directa, sin esperar el intervalo normal y redondeada hacia abajo. Se conserva
el objetivo0,5–2,8V, gain1–80, rechazo de generaciones anteriores, override manual
y el clamp digital final de A0. No equivale a protección eléctrica ante cargas.

11tests offline de AGC y GUI RADIO PASS. Sin intervención en Q ni cambios V17;
los175hashes congelados siguen iguales. Validación auditiva/manual pendiente.

Respaldo pareado final: `respaldos/parejas/v18_catalogo_20261025_230123/manifest.json`.
