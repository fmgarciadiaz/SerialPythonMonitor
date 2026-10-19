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
Detalle: [eficiencia y evidencia](AUDITORIA_EFICIENCIA_V17.md). Reiniciar GUI V17.
Este estado sustituye las menciones históricas a ausencia de prueba física.

## 14/10/2026 — Incorporación a producción completada

Seis perfiles CH1 ADC10/12/14 instalados y habilitados: 60 s + tres
arranques independientes de 120 s por perfil, sin errores de integridad.
Propuesta relay autorizada e incorporada; márgenes de integridad y holgura
separados. Q restaurado a ADC10/909090 SPI y generador apagado; firmware
nuevo permanece instalado. Detalles: [incorporación CH1](INCORPORACION_CH1_V17.md).
Las secciones anteriores sobre ausencia de incorporación son históricas.

# Etapa III — RADIO AM en V17

Estado actualizado14/10: FILTER OFF inicial; DSP continuo RADIO/FILTER fuera
deGUI, trabajador único y límite ocho lotes con generaciones/ACK ordenados.
Trigger audio fraccional y remuestreo/espectro optimizados. 92pruebas locales
y120s offline de cadena completa aprobados. FFT/dibujo siguenGUI; recepción
analógica, FPS visibles y aceptación física conjunta siguen pendientes.
Detalle: [auditoría](AUDITORIA_EFICIENCIA_V17.md).
Barrido aislado CH1 ADC10/12/14 terminado con60+3×120s y restauración exacta,
sin incorporación aproducción: [resultados](../experimentos/maxfreq_optimized_v17/RESULTADOS.md).
Las notas de incrementos siguientes conservan el historial; este estado
sustituye las menciones anteriores a DSP enGUI y triggeraudio pendiente.

Alcance acordado el 13/10/2026: recepción AM convencional, canal RADIO de
audio demodulado, FILTER con fuente RADIO, análisis/grabación y salida THRU
por A0. Diseño consultado con Astra. La antena tendrá adaptación, protección,
polarización y filtrado antialias antes del ADC; la recepción analógica se
valida por separado de la continuidad digital.

## 1. Base independiente

Crear monitor/v17, arduino/v17 y tests/v17 desde el estado actual de V16,
registrando hashes y conservando V16. Auditar imports, rutas dinámicas,
identidad de versión, entrypoints, variables de entorno, herramientas,
manifiestos, catálogo Arduino, documentación y tareas del editor.
V17 se selecciona explícitamente durante desarrollo; no cambiar los defaults
estables ni cargar firmware al Q como parte de la preparación local.
No trasladar referencias Bode a otra identidad de firmware sin nueva medición.

## 2. Motor AM offline

Procesamiento vectorizado por bloques: eliminar polarización RF, NCO complejo
con fase continua, filtros y decimación multietapa, selección de estación,
envolvente abs(IQ), bloqueo DC, filtro de audio y volumen limitado.
El filtrado antialias digital precede cada reducción de tasa.
Punto inicial CH1: Fs real = 160 MHz / 114 = 1.403.508,772 Hz;
decimaciones /8 y /4 producen 43.859,649 Hz, no 44,1 ni 48 kHz exactos.
Ancho inicial de estación ±4,5 kHz; audio hasta aproximadamente 4 kHz.
Los cortes intermedios se diseñan contra alias antes de fijar coeficientes.
Conversión con estado a la tasa de reproducción explícita y medida: no basta
con cambiar la cabecera. Otras FS requieren su propio diseño válido.

Conservar estado de NCO/filtros entre bloques. Cambio de fuente, FS, sintonía
o discontinuidad reinicia de forma controlada y silencia la transición.
Pruebas con AM sintética de audio conocido, estaciones adyacentes, ruido,
distintos tamaños de bloque, saltos de índice y cambio de configuración.
Comparar audio recuperado, rechazo de interferencia, continuidad, ganancia y
frecuencia; medir coste por bloque antes de conectar adquisición real.

## 3. Panel RADIO y adquisición

Fuente CH1/CH2, frecuencia de estación, ancho, nivel y volumen; elegir un pico
en FFT RF actualiza la sintonía. Mostrar FS RF y audio por separado.
RADIO es mono y conserva su propia escala temporal y contador de muestras.
No reutilizar índices RF como índices audio. FFT y grabación usan la FS del
canal elegido; FILTER sobre RADIO corre a la FS audio.
FFT RF continúa disponible para buscar estaciones mientras se observa audio.
No crear un bucle de fuentes RADIO/FILTER.
Separar adquisición de DSP/UI mediante buffers acotados; nunca descartar
muestras silenciosamente. Falta de capacidad o continuidad silencia RADIO
y deja el error visible. Evitar callbacks Python por muestra.

Gate físico inicial: señal AM controlada con niveles seguros, continuidad
ADC y audio, demodulación y grabación. El perfil 1,4035 MHz de producción
acepta integridad, pero margen 7–9,8% y cola4/4; medir de nuevo bajo carga DSP.
Nyquist es 701,75 kHz; cobertura hasta 600 kHz es un objetivo analógico,
no una banda ya aceptada. CH2 depende de las tasas duales disponibles.

## 4. THRU hacia A0

Fuentes RADIO/FILTER/CH1/CH2 con conversión de tasa explícita, eliminación de
DC según fuente, nivel limitado y polarización DAC adecuada. Arranque
silenciado, rampa de activación, STOP accesible y exclusión con generador/WAV.
Definir primero cómo se asignan los relojes ADC y DAC y cómo se controla la
deriva, sin acumulación ilimitada de cola.
Detectar saturación persistente, crecimiento/oscilación y underrun;
advertir y apagar. No prometer detección infalible del cable A0→ADC.
Validar inicialmente con carga de prueba y salida limitada.

## 5. Antena y aceptación final

Con frontend preparado, recibir estaciones y medir respuesta, alias,
sensibilidad, interferencia y estabilidad de sintonía. Evaluar por separado
audio audible, archivos válidos y continuidad sostenida con FFT/FILTER/THRU.
Cada ensayo físico establece un único dueño del Q, respaldo, evidencia
persistente y restauración verificada del perfil/generador previos.
No promover cobertura ni holgura por una pantalla corta o por tests offline.

Estado del primer incremento: base independiente creada con manifest de hashes
`v17_base_manifest.json`; fuentes V16 verificadas sin cambios. Imports y rutas
V17 separados, selección explícita en herramientas/editor y catálogo;
defaults V16 preservados. Sin calibraciones copiadas ni operación del Q.
Motor `monitor/v17/radio_am.py`: decimación FIR polifásica /8 y /4 con
estado acotado. La primera etapa integra la mezcla en los coeficientes FIR
y calcula la rotación NCO sólo a la tasa reducida; filtros IIR de canal y
envolvente/audio posteriores. FIR diseñado para rechazo de 80 dB en cada
etapa; pruebas verifican respuesta y equivalencia con filtrado completo,
bloques irregulares y reinicio. Salida a FS real;
remuestreo con estado a 20/40/48 kHz implementado para canal audio. No se acredita rechazo de 60 dB
para todos los alias; faltan barridos exhaustivos y perfiles alternativos.
Timing local en `v17_am_offline_timing.json`; no demuestra margen físico.
Comparación polifásica local (Python 3.13, DSP + remuestreo, bloques de
20 ms): salida 40 kHz pasa de 3,47 a 2,86 ms medios (~18% menos), salida
20 kHz de 2,38 a 1,87 ms. Evidencia `radio_polyphase_cost.json` en
`diagnosticos/resultados_v17/`. Ensayo GUI offline de 15 s: 750/750 bloques,
sin errores; no acredita estabilidad física sostenida ni ejecución DSP
fuera del hilo GUI.
Segundo incremento: panel RADIO (ADC8/CH1), FS salida 20 kHz inicial,
selector 20/40/48 kHz y sintonía. FILTER usa la FS de RADIO para límites y
procesamiento. Historial audio independiente, visualización temporal continua,
FFT/espectrogramas con FS audio; mezcla RF/audio en un mismo análisis se rechaza.
Cambio de sintonía/FS/filtro reinicia historial y estado; discontinuidades RF
silencian el bloque afectado. Remuestreo sinc con estado y lookahead64 muestras.
Mediciones temporales RADIO/FILTER audio usan timestamps y FS del historial
audio (20/40/48 kHz), con interpolación de cruces para frecuencia. Trigger
RADIO y FILTER audio disponible con nivel inicial 0 V y ajuste bipolar,
flancos ascendente/descendente, Auto/Normal y SINGLE temporal/FFT. Las
capturas FFT audio preservan su propia FS; señales RF/audio mezcladas se
rechazan. Validación sintética; aceptación física todavía pendiente.
Grabación audio y THRU todavía pendientes.
Pruebas sintéticas de integración; ninguna operación ni aceptación física Q.

Verificación local: 43 tests aprobados (AM, filtros, Bode y GUI heredada),
imports/manifiestos/rutas auditados; sin validación física V17.

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


Scan espera tres bloques posteriores al ACK si cambió el generador, y descarta
resultados en curso de una configuración anterior. La búsqueda permanece
normal de5–600kHz; no se incorporó restricción por portadoras deRADIO TEST.

Validación final offline con capacidadRF real 5874036 muestras:
750/750lotes en15s, pico5 pendientes, atrasomax78.1ms,
procesamientomedio5.09ms, pico21.16ms; sinerror.
50pruebas locales verificadas entre suite49 y testnuevo de ventanaRFfresca.
No prueba física sostenida; reiniciar V17 para aplicar estos cambios dehost.

## PRUEBA RADIO con pasos de 25 Hz

Resolución elegida por el usuario: 25 Hz. Los tres diales usan Hz internamente:
portadoras distintas de 25 Hz a 50 kHz y tono de 0 a 4 kHz. Flechas: 25 Hz;
Page Up/Down: 100 Hz. El ratón también ajusta a la grilla de 25 Hz. Las lecturas
muestran Hz por debajo de 1000 Hz y kHz con hasta tres decimales desde 1000 Hz:
`750 Hz`, `1.025 kHz`, `20.525 kHz`. Tono cero conserva portadoras sin modular.
El receptor RADIO sigue sintonizando desde 5 kHz; generar una portadora menor
no amplía ese receptor.

Firmware V17 construye una tabla inmutable de 5120 muestras (40 ms), repetida
por DMA a 128 kS/s, TIM6 con divisor exacto 1250. Cada frecuencia admitida
completa ciclos enteros por tabla. Reutiliza la RAM de WAV/generador, con
propiedad exclusiva del DAC; no genera muestras en el timer ni transmite
muestras desde el PC. Los cambios reconstruyen la tabla con DMA detenido y
fuera de IRQ. Repetir la misma configuración activa conserva la tabla.
El bit de capacidad 8 anuncia el contrato nuevo. Protocolo: portadoras en mHz,
tono en Hz. La tabla usa la LUT seno de 256 fases del generador normal.
V16 no se modifica.

Pruebas locales: C++ real a 20 525/40 750 Hz con tono 750 Hz, cierre exacto
de tabla, bandas laterales, amplitud acotada, demodulación y fallo de hardware;
estado aceptado por decoder Python y relay C. También UI, ACK de entrada,
Play/Stop, snapping, límites, unidades, generador normal y contrato WAV.
La recepción analógica y estabilidad sostenida con RADIO/FILTER/FFT siguen
como gates separados de la comprobación de instalación con amplitud cero.

La variante previa con DDS/streaming no se acepta: ensayos a 256/128 kS/s
perdieron nodos al usar ADC8/1,4035 MHz. Informes de fallo conservados en
`diagnosticos/resultados_v17/radio_hz_*failure.json`; recuperación del estado
previo verificada en `radio_hz_recovery.json`. El streaming se retiró del
código actual al elegir la resolución de 25 Hz.

Instalación final verificada: 33 tests locales y compilación Q de 121940 bytes
flash y 258496 bytes RAM (3648 libres informados). RADIO TEST a amplitud cero
pasó 10 s a ADC14/40k, 60 s a ADC8/1403508 (84.170.880 muestras) y dos cambios
de 10 s a esa FS: portadoras 750/20525 Hz, tono 0; y 20525/40750 Hz, tono 4000.
Sin pérdida ni fallos. El primer intento con tabla fija falló en actualizaciones:
Stop reconstruía la tabla y Play repetía divisiones de frecuencia por muestra.
Corregidos Stop inmediato, constantes calculadas una vez y preparación
optimizada fuera de IRQ. Informe `radio_hz_installed.json`:
ok/restored/restore_integrity_ok=true. ADC8/40000 y generador apagado restaurados
exactamente, con 399360 muestras íntegras en 10 s. Identidad de fuentes, backup
y límites en `radio_25hz_deployment.json`.
La GUI necesita reinicio; MCU y relay ya actualizados. Este ensayo con amplitud
cero no acredita respuesta analógica ni holgura sostenida con DSP/FFT/Filter.

## Corrección de transporte ADC10 dual con Radio Test · 14/10/2026

Se reprodujo el cierre del flujo al pasar de CH1 a ADC10 dual 519480 Hz nominales con Radio Test activo, incluso con amplitud cero: `dropped=1`, `fatal=0`, CRC correcto y cola 4/4. El relay cambia de SPI38/FIFO10/spin en CH1 a SPI32/normal/poll en dual.

El relay ahora separa política de transporte y validación. `transport_policy.h` conserva SPI38/FIFO10/spin para el perfil dual exacto ADC10, 308 ticks, 4176 pares. `scope_high_rate` no cambia: el MCU y el relay conservan todas las comprobaciones duales. No se modifica firmware MCU ni se amplían perfiles o límites de ADC.

Reproducción, pruebas físicas y restauración: [campaña aislada](../experimentos/radio_dual_transport_v17/README.md). El perfil sigue sin acreditación de margen mínimo del 10 %. Las pruebas de protocolo/integridad no certifican calidad analógica ni FPS visibles.

Revisión posterior de los dos límites restantes: [arranque y margen](../experimentos/radio_start_v17/README.md). Cinco arranques de CH1 máximo pasaron, con cola 3/4; el fallo intermitente sigue pendiente. El dual pasó 60 s adicionales, con margen medio observado 8,57 %; no se acredita aún 10 %. Se documentaron las siguientes correcciones de firmware y sus invariantes, sin implementarlas en esta ronda. Q restaurado y firmware sin cambios.
