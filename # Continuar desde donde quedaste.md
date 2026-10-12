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
El perfil observado es ADC14 dual a 31,25 kHz, generador activo a 2,5 kHz; la configuración
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
