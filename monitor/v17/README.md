# Monitor V17 · guía de entrada

Versión activa: `python monitor/v17/app.py`. [Estado vigente y límites](../../docs/ESTADO_ACTUAL_V17.md) · [Plan](../../Plan%20de%20trabajo.md).

Generador seno hasta 150 kHz, cuadrada hasta 200 kHz; Bode según método y Fs. RADIO con gain máximo ×80. El rótulo «s/holg.» ya no se muestra, aunque los límites de holgura siguen vigentes. RADIO/Scan y WAV conservan incidencias abiertas.

Las secciones fechadas siguientes describen incorporaciones anteriores; no deben interpretarse como estado global actual.

## 16/10/2026 — ADC8/CH1 1,60 MHz incorporado (s/holg.)

Perfil SPI habilitado tras 60 s + 3×120 s integrados, con 671.613.984 muestras
sin pérdidas ni errores fatales. Preparación automática de 2 s y cola real de
8 nodos. Margen medio de envío 7,38–7,46 %; conserva `(s/holg.)`.
Firmware nuevo instalado; configuración previa y generador restaurados.
Con Q ya activo se evita la espera adicional de arranque de 5 s; se conserva
la preparación de 2 s. Si Q acaba de arrancar, mantiene ambas esperas.
La entrada pasa por una tasa baja privada; cambiar o reaplicar la tasa no
reescribe los valores ni el estado del generador.
Ver [alcance, resultados y restauración](../../docs/INCORPORACION_ADC1600_V17.md).
La precisión analógica y el funcionamiento con cargas simultáneas siguen pendientes.

## 14/10/2026 — Radio Test: F1/F2 independientes, instalado

Cada portadora tiene un interruptor circular en la esquina superior izquierda.
Verde significa activa; apagarla conserva la frecuencia seleccionada y omite
su contribución a la tabla. Ambas apagadas producen el offset constante,
sin modulación. No se redistribuye la amplitud de la portadora restante.
Cambiar interruptores durante Play actualiza la tabla; estando detenido sólo
prepara la configuración. El host exige capacidad nueva del Q antes de
habilitar estos controles; firmware/relay nuevos ya están instalados.
Los botones de Sintonía tienen esquinas cuadradas y llenan su fila, sin huecos.
Radio Test conserva la altura reservada y no agrega barra lateral.

Contrato: frecuencia cero significa portadora apagada únicamente en modo
Radio Test; portadoras activas siguen en pasos de 25 Hz y distintas.
Nueva capacidad bit 16, combinada con las anteriores, anuncia esta extensión.
CRC, padding, geometría, metadata ADC y validación de continuidad se conservan.
Tabla DMA fija de 5120 muestras a 128 kS/s; dos portadoras activas conservan
los códigos exactos de la fórmula anterior (comprobado en C).

38 pruebas locales pasaron: UI, tabla C real, espectros, contrato host/relay,
capacidad legacy y perfiles optimizados. Compilación MCU: flash 122056 bytes,
RAM 258640/262144; 3504 bytes libres informados, sin certificar holgura de pila.
Respaldo anterior: `respaldos/unoq/osciloscopio_20261014_175034_758487.zip`.
Firmware instalado: `3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.

Dos ensayos físicos con DAC de amplitud cero: cinco casos de 3 s cada uno
(ambas, F1 sola, F2 sola, ninguna, ambas), Stop y recuperación de 10 s.
Uno a ADC14/40000 y otro a ADC14/851063. Sin dropped/fatal; restauración exacta
al ADC14/851063 SPI y generador apagado con campos previos, identidad del
firmware idéntica antes/después de cada ensayo. Nuevo firmware permanece.
Informes:
`diagnosticos/resultados_v17/carriers_toggle_20261014/report.json` y
`diagnosticos/resultados_v17/carriers_toggle_20261014/load/report.json`.
Estos ensayos validan protocolo/DMA e integridad; no la amplitud/forma analógica
ni holgura sostenida de todos los perfiles después de cambiar firmware.

## 14/10/2026 — Vista temporal mixta RF y RADIO

Seleccionar CH1 junto con RADIO/FILTER audio muestra todos los trazos.
Cada canal conserva su FS y sus muestras; se dibuja en un eje temporal común,
reduciendo extremos por píxel sin remuestrear RF. El audio transporta su
primer timestamp sobre el reloj RF, también tras cambios de Gain/Offset.
La vista termina en el último instante disponible en ambos dominios.
Filtros y remuestreador conservan sus retardos naturales; no hay calibración
ni compensación de fase RF/audio en este incremento.

En vista mixta, Horizontal usa duración/posición referida a la tasa CH1.
El modo de muestras muestra posiciones equivalentes CH1 para todos los
trazos, incluidas posiciones fraccionales del audio. Trigger puede usar RF
o audio; SINGLE y ajuste de detalle conservan los trazos de ambas tasas.
Mientras se prepara RADIO, CH1 sigue visible. FFT conserva su selección
por dominio y no mezcla RF/audio con tasas distintas en un mismo análisis.

84 pruebas locales pasaron. Ensayo sintético con proceso DSP, AM 20,525 kHz,
RADIO40 y ventana mixta de 10 ms durante 15 s: 762 lotes/21067776 muestras RF,
sin errores, cola pico cuatro, preparación de vista media 3,286 ms,
p95 6,694 ms y máximo 8,486 ms. Audio empezó después de preparar el proceso
(703 lotes DSP), como en el comportamiento de arranque existente.
Informe: `diagnosticos/resultados_v17/mixed_temporal_am_offline_20261014.json`.
No valida FPS visibles ni transporte físico, y no generaliza ese coste a
ventanas largas o a todos los perfiles ADC.

La primera variante gastó 28,247 ms por frame ante muchos cruces de ruido
que no alcanzaban la histéresis, y produjo sólo ~59,6% de la tasa sintética.
Se conserva el informe original, cuyo `ok` verificaba únicamente entrega.
El runner ahora comprueba también la cadencia sintética (>=98%). Se añadió
un rechazo vectorizado exacto cuando ningún valor alcanza la histéresis:
misma aceptación de disparos, evitando explorar cruces imposibles.
Comparación derivada: `diagnosticos/resultados_v17/mixed_temporal_comparison_20261014.json`.

## 14/10/2026 — Controles de vista por modo y RADIO compacta

RADIO muestra entrada AM, CH1/bits, tasa RF, salida audio y muestras abajo,
con separadores de punto. Solapas compactas con altura fija común; cambiar a RADIO no aumenta su
altura. Botones ▶/■, <<, >> y Scan (lupa) comparten una fila abajo dentro del marco
de Sintonía. Su pantalla tiene las mismas dimensiones que FS Salida. Horizontal/Vertical reciben el espacio
disponible.

En vista temporal, Horizontal y Vertical conservan muestras/tiempo y voltios.
En FFT (Spectre/Power/Distort/Transfer), Heatmap y Bode controlan los dos
gráficos activos: escala relativa del ancho/alto y posición porcentual
respecto del rango completo. ×1 es el rango normal; ×0,5 muestra la mitad.
En ejes logarítmicos operan sobre el rango logarítmico. Cada gráfico conserva
sus unidades. Los ajustes se guardan por modo/opciones y método Bode,
se mantienen durante el redibujado y no alteran datos, FFT ni adquisición.
Auto-Set en análisis restaura ×1/posición 0 sin reiniciar adquisición.
Volver a temporal recupera sus escalas y posiciones.

88 pruebas locales de FFT/UI, RADIO/UI, límites horizontales, FILTER/UI y
Bode timing pasaron; incluyendo ajustes, cambios de modo, ejes log y retorno
a temporal. No ensayo físico adicional en este incremento.

## 14/10/2026 — RADIO en todos los perfiles CH1

RADIO y Scan aceptan los perfiles CH1 existentes de 8, 10, 12 y 14 bits.
Sintonía desde 5 kHz hasta el menor entre 600 kHz y Nyquist menos 4,5 kHz,
con margen estricto de un Hz para las bandas laterales. Al cambiar el ADC,
la sintonía se limita al nuevo máximo; la etiqueta muestra los bits reales.
Scan excluye candidatos fuera de ese rango. Durante una transición, una
sintonía todavía incompatible silencia audio sin detener la adquisición RF.
FS de salida continúa en 20/40/48 kHz; predeterminado 40 kHz y banda audio
aproximada de 4 kHz. No cambio de firmware/relay.
Pruebas sintéticas cubren demodulación con cuantización real de cada perfil
CH1, límites de sintonía, cambios de configuración y exclusión en Scan.
La compatibilidad host no constituye aceptación física RADIO en cada perfil.

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

# Monitor V17 — RADIO AM en desarrollo

Base independiente de V16. Entrada: `python monitor/v17/app.py` con Python 3.13.
RADIO AM integrada para ADC8/CH1 a 1,4035 MHz, inicialmente apagada.
Panel Radio: sintonía hasta 600 kHz y FS salida 20/40/48 kHz (40 por defecto).
Salida mono con remuestreo sinc con estado y timeline audio independiente.
FILTER inicia en OFF, sin ejecutar el filtro ni acumular su historial;
toma la FS audio al elegir RADIO. Para visualizar audio, seleccionar sólo
RADIO/FILTER audio; no mezclar RF y audio en un eje de muestras común.
FFT y espectrogramas continuos usan el reloj de RADIO.
Trigger/SINGLE audio disponibles con alineación fraccional del cruce.
THRU y grabación audio todavía pendientes.
Sin aceptación física de recepción RF ni reproducción por A0.

Firmware V17 compilado e instalado en el Q; ver los informes de instalación
al final. La aceptación analógica continúa pendiente.
Selección explícita `--firmware v17` / `--version v17`; defaults V16 preservados.
No se copiaron calibraciones ligadas al firmware V16.
Plan: [Etapa III](../../docs/ETAPA_III_V17.md).

DSP continuo RADIO/FILTER en trabajador dedicado, con ocho lotes pendientes
como máximo y reinicio por generación. FFT/dibujo continúan en GUI.
Ensayo completo offline de 120 s aprobado con FFT65536; no aceptación física
conjunta ni FPS visibles. Estado actual y evidencia en
[auditoría de eficiencia](../../docs/AUDITORIA_EFICIENCIA_V17.md).
Las secciones fechadas siguientes conservan el historial de incrementos.

Controles RADIO actualizados: FS salida sólo desplegable; botón Play/Stop;
dial de sintonía con texto no editable y flechas a picos FFT RF de CH1.
Las flechas ordenan por frecuencia los picos significativos del detector FFT
(ventana/tamaño del análisis actual), con retorno al extremo opuesto.
No dependen del espectro audio ni borran RF al resintonizar.
31 pruebas de RADIO/Filter UI aprobadas; sin operación física del Q.

Scan bajo demanda: botón Scan realiza una búsqueda RF independiente de la
FFT visual. Captura los últimos3×65536 valores CH1 continuos y trabaja en un
hilo aparte; no vuelve a ejecutarse hasta pulsar Scan. Ventana Hann fija,
promedio de potencia, umbral10dB sobre mediana local, prominencia6dB y
persistencia en2/3 bloques. Agrupa candidatos a menos de4,5kHz por el más fuerte.
Las flechas recorren la lista guardada, sin retocar la sintonía al terminar Scan.
Cambiar/reiniciar adquisición invalida resultados, incluso búsquedas en curso.
Son candidatos RF, no estaciones AM certificadas. Ensayos sintéticos aprobados;
coste concurrente con Q y aceptación analógica siguen pendientes.

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
V17 instalada posteriormente; ver estado de carga y verificación al final.
RAM informada por sí sola no acredita margen físico.
Para loopback conectar A0 a A2, seleccionar ADC8/CH1 a1,4035MHz, generar
20/40kHz con tono1kHz y usar Scan/RADIO. Preferir separación de portadoras
mayor que el anchoAM9kHz. Recepción RADIO sólo sintoniza desde5kHz.
Tono5kHz puede quedar atenuado por el filtro audio actual cercano a4kHz;
validación inicial recomendada con1kHz. La tabla a256kS/s todavía requiere
aceptación física de amplitud/imagenDAC y carga conjunta con ADCmáximo.

RADIO TEST actualizado: portadoras y tono con tres InstrumentDial64×64;
lecturas no editables, tono de0–2kHz. Cambios durante Play aplicados con
coalescencia200ms y sin sobrescribir la selección al recibir ACK anteriores.
Salida deshabilitada al arrancar V17. PrepararQ corregido para liberar relay/
GPIO READY antes de Board.stop; primer intento quedó registrado en el log.
Respaldo preinstalación:respaldos/unoq/osciloscopio_20261013_212918_841366.zip.
Estado previo:ADC14/40000 SPI,generadorapagado; snapshot en
 diagnosticos/resultados_v17/radio_test_prior.json.

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


Validación final offline con capacidadRF real 5874036 muestras:
750/750lotes en15s, pico5 pendientes, atrasomax78.1ms,
procesamientomedio5.09ms, pico21.16ms; sinerror.
50pruebas locales verificadas entre suite49 y testnuevo de ventanaRFfresca.
No prueba física sostenida; reiniciar V17 para aplicar estos cambios dehost.

PRUEBA RADIO permite pasos de **25 Hz** en portadoras (25 Hz–50 kHz) y tono
(0–4 kHz). Lecturas: `750 Hz`, `1.025 kHz`, `20.525 kHz`. Usar las flechas
para 25 Hz y Page Up/Down para 100 Hz; el ratón también ajusta a esa grilla.
Requiere firmware V17 con capacidad RADIO TEST Hz. Una tabla fija de 5120
muestras se repite por DMA a 128 kS/s, sin generación continua por CPU.
La recepción RADIO continúa sintonizando desde 5 kHz.

## Optimización host · segunda revisión Astra, 14/10/2026

Trigger mixto vectorizado, ventanas circulares limitadas al intervalo visible y reloj compartido por dominio; perfiles wire cacheados manteniendo comprobaciones por frame; distorsión Power en trabajador acotado con descarte por contexto. 107 pruebas distintas aprobadas y ensayos offline a tasa completa. Mejora comprobada en ruido con outlier: render controlado 4,58→1,23 ms; AM normal similar. [Evidencia y límites](../../docs/OPTIMIZACIONES_ASTRA_V17.md). No implica nueva aceptación física ni FPS visibles.

## Radio Test y ADC10 dual · 14/10/2026

El relay conserva SPI38/FIFO10 al cambiar a ADC10 dual 519480 Hz (308 ticks, 4176 pares), con validación dual completa. Tres transiciones de 20 s y una corrida de 120 s pasaron sin pérdidas; cola dual pico 2/4. Firmware MCU sin cambios. Se conserva `headroom=false`; el arranque directo de Radio Test en CH1 ADC10/1142857 sigue pendiente. [Reproducción, límites y restauración](../../experimentos/radio_dual_transport_v17/README.md).

## Motor Synth

V17 utiliza únicamente `fm_source.py` y los modelos actuales. Se retiraron la copia `legacy_v15` y su selector de comparación; `SYNTH_ENGINE` ya no selecciona un motor alternativo en V17.

## Inicio de Bode con FILTER OFF

Corregida una excepción `KeyError: OFF` que impedía iniciar Bode con el filtro apagado. El retardo de CH1/CH2 ya no consulta el origen de FILTER cuando ese canal no participa. Si se elige FILTER con origen OFF o RADIO, el panel informa que requiere CH1 o CH2 como fuente, antes de enviar comandos o activar el barrido. Verificado mediante los botones de Tonos, Pulso y Sweep/Chirp en pruebas locales; no implica una nueva validación física.
