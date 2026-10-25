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
