# Punto de continuación · 5 de octubre de 2026

Pareja actual: Monitor V12 y firmware V11 P992, SCP1 V3/992, SPI 32 MHz.
Antigravity integró ADC a 50 MHz con PLL2 (HSE16/M2/N25/R4), para todos
los perfiles; ADC16 por oversampling ×16 hasta 62,5 kHz, ADC14 hasta 125 kHz.
UART hasta 31,25 kHz; validación física R4 pendiente.

Revisión posterior: diagnóstico corregido para observar el perfil real antes
de guardarlo, preservar stream.scp y comprobar restauración exacta. Prueba
sostenida final de 120 s aprobada: 7.495.906 pares sin errores. 206 pruebas locales pasan.
Firmware local prepara/verifica PLL2 antes del generador, usa esperas acotadas
y evita conmutar el reloj compartido ADC/DAC durante reconfiguración.
Cambios compilados y cargados; respaldo previo conservado. Perfil del usuario
restaurado: ADC16/62,5 kHz, seno 26 Hz (niveles 186–3909), habilitado.

Documentación actualizada en README, monitor/, arduino/ y docs/, sin mover
versiones históricas. Margen nominal ADC16 / 62.500 Hz: 14,08 µs antes de latencias,
no 12,16 µs. Calibración Bode anterior corresponde al reloj ADC a 40 MHz.
Cableado directo A0 a A2/A3 confirmado. Comparación a 2/10/20 kHz:
amplitud cambia menos de 0,23%; residuo crece a 20 kHz (1,6→3,4 mV).
Ver diagnosticos/ADC16_V12.md para evidencia y límites.
Audio WAV: grabación implementada posteriormente en V13 (ver sección abajo); reproducción pendiente.

40 etapas de transición ADC14/125k ↔ ADC16/50k/62,5k aprobadas,
con consultas concurrentes y restauración exacta.

## Organización posterior

V12 y V11 P992 quedan como únicas versiones visibles en las carpetas
principales. V10/V11 Python y V8 config/V9 Fast/V10 diagnóstico Arduino
fueron movidas a sus carpetas histórico. Herramientas por defecto: V11 P992.
Capturas de prueba pesadas eliminadas; inventario en capturas/limpieza_20261005.json.
Informes, calibraciones y respaldos conservados. No se operó la placa.

Verificación de consolidación: 206 pruebas aprobadas; configuraciones locales
resuelven sus nuevas rutas. Limpieza: 87 archivos, aproximadamente 1,75 GiB.

V12: estados uniformados y cuadro de 34 px; etiqueta MUESTREO. Escala
horizontal temporal editable en ms, convertida internamente a muestras y
con duración conservada al cambiar Fs. Posición temporal también en ms.
208 pruebas aprobadas y layout comprobado sin operar la placa.

## V13 experimental · PyQt6

Astra planificó/revisó y Sol6.1 implementó V13 independiente. Arranque:
`.venv-v13/bin/python monitor/v13/app.py`. Firmware V11 P992 sin cambios.
V12 queda disponible; no se promovió V13 como reemplazo por rendimiento.
PyQt6 6.11.0, runtimeQt 6.11.2, pyqtgraph0.13.7, NumPy1.23.3.
Receptor/assets y copia de referencias Bode dentro de V13; CSV en capturas/v13.
Dials sin marcas densas. HelpermacOS corrige únicamente UF_HIDDEN de los
plugins Qt6 cuando ese atributo impide su descubrimiento.

24 pruebas Qt6 aprobadas y 208 pruebas Qt5 pasan en procesos separados.
Comparación sintética secuencial,40 cuadrosmedidosmás10warmup:
Qt6 más lento en todos los escenarios offscreen probados. No extrapolar
FPS reales ni atrasoUSB; probar apariencia/fluidezmanualantespromoción.
Evidencia: diagnosticos/QT6_V13.md y diagnosticos/resultados_qt/20261005/.
No se operó la placa ni se modificó firmware en esta migración.

## Entorno Conda V13 · 2026-10-05

Creado `Python_3_13_DataScience`: Python 3.13.5, NumPy 2.3.1, pandas 2.3.1,
SciPy 1.16.0, Matplotlib 3.10.0, IPykernel y PyQt6 6.11.0 / Qt 6.11.2,
pyqtgraph 0.14.0, pyserial 3.5. 24 pruebas V13 aprobadas y pip check limpio.
Reproducible con monitor/v13/environment.yml; requirements-python310.txt
preserva dependencias del benchmark previo, cuyos resultados no describen
el nuevo entorno. VS Code: intérprete predeterminado y launch/tarea V13
apuntan a este Conda; launch/tarea V12 mantienen Python_3_10_DataScience.
Arranque: `conda activate Python_3_13_DataScience`, luego
`python monitor/v13/app.py`. Si VS Code conserva una selección vieja,
Python: Select Interpreter → Python_3_13_DataScience.
Registro opcional de kernel Jupyter no ejecutado: revisión automática
indisponible por capacidad del modelo; IPykernel está instalado.


## Grabación WAV V13 · 2026-10-05

Selector CSV/WAV en la fila de estado, RECORD/STOP REC existentes y CSV predeterminado.
WAV PCM16 estéreo graba A2 izquierda y A3 derecha desde muestras crudas,
Fs confirmada, centro ADC fijo, sin remuestreo/filtro/AGC. Capturas en
capturas/v13 con misma convención de nombre y contador compartido CSV/WAV.
Máximo 30 s; STOP visual continúa grabando. Cambios de configuración,
desconexión, cierre y errores finalizan WAV. Saltos de índice/timestamp
interrumpen con error sin rellenar huecos; wrap32 permitido. Demo sólo CSV.

Astra no pudo ejecutar la planificación solicitada por límite de uso;
se continuó con alcance autorizado e implementación/revisión Sol. Pruebas
locales Qt6 aprobadas; validación física WAV pendiente. No se operó la placa.
Reproducción: próxima etapa, falta decidir botón y destino de salida.

## Reproducción WAV candidata preparada

V13 agrega modo WAV L/R/Mix, 20 ksps, DC eliminado y Vpp/offset DAC12.
Firmware y relay aislados en arduino/v12_audio; 51 pruebas locales aprobadas
y sketch compilado. No cargado: falta autorización y validación A0→A2/A3.
Respaldo previo: respaldos/unoq/osciloscopio_20261005_160559_272516.zip.
Ver arduino/v12_audio/README.md para activación y restauración.

### V12 Audio cargado y ensayo físico inicial aprobado

Autorizado y cargado el 5 de octubre: firmware MCU V12 Audio y relay MPU propio
quedaron activos. WAV estéreo 44,1 kHz→20 ksps, L=997 Hz, R=2003 Hz,
Mix con ambos tonos comprobados en A2/A3; 40000 muestras por pasada,
sin underrun ni discontinuidades ADC14/31,25 kHz. Detener→IDLE y
restauración del generador confirmados. Falta ensayo sostenido y evaluación visual.
VS Code: «Monitor V13 — WAV A0 (V12 Audio)» habilita el protocolo nuevo.
Informe: diagnosticos/resultados_wav/20261005_fisico.json.

### Tasas WAV negociadas probadas · 5 de octubre de 2026

V12 Audio MCU/relay actualizados y activos; selector Salida 20/40/50 kHz en V13.
Ensayos de 120 s aprobados: WAV40/ADC14-40k, WAV50/ADC14-40k y
WAV50/ADC14-100k. WAV50/ADC125 falló dos veces con integridad ADC;
Play bloquea ADC mayor de 100 kHz. STOP y restauración confirmados.
57 pruebas locales y regresiones Qt6 adicionales aprobadas. Respaldo previo
osciloscopio_20261005_181834_429412.zip y fuentes 20 ksps conservadas.
Ver docs/WAV_TASAS.md e informes diagnosticos/resultados_wav.

### Autoinicio después de encender Q

Reproducido READY timeout de 1 s. Relay V12 Audio actualizado: primer
READY admite 10 s; arranque sólo se confirma con primera trama SPI válida.
Autoload y lector verificados (63488 pares en 2 s, ADC14/31,25 kHz).
Firmware MCU sin cambios de fuentes. Falta nuevo ciclo físico de alimentación.
Informe diagnosticos/resultados_autoload/20261005_ready_arranque.json.

### 2026-10-06 — Botón Preparar Q

V13 ahora incluye **Preparar Q** junto al autoinicio. Ejecuta
`tools/prepare_q.py --serial` sobre el Q seleccionado: compila MCU, respalda la
app existente o importa una nueva, compila relay y arranca con confirmación SPI.
El lector permanece en el host; conectar después de la preparación.
Pruebas locales: 3 de instalación/actualización/protección y 13 de autoload/Qt.
No se ejecutó una nueva carga física en esta etapa; queda pendiente probar el
botón en el Q encendido y, especialmente, en una placa nueva.

### 2026-10-06 — Fallo real de Preparar Q y Autoiniciar

El log preparar_q_20261006_091448_711424.log mostró MCU compilado/cargado y app
iniciada; falló después el relay por READY timeout. Reproducido autoinicio:
RESET=1, READY=1 después del fallo. Relay corregido para consumir un único
crédito inicial por nivel, drenar eventos antes de SPI y conservar flancos
estrictos para todos los intercambios posteriores. Compilado en el Q sin
modificar MCU. Autoinicio real completó con primera trama validada.
Pruebas locales: 11 firmware/protocolo/autoinicio. Errores de autoinicio
persisten ahora en logs. Resultado ADC en
`diagnosticos/resultados_autoload/20261006_ready_credito_inicial.json`.
No se repitió un apagado/encendido físico después de instalar esta corrección.

### 2026-10-06 — Persistencia del autoinicio y conexión V13

Autoiniciar ahora persiste inmediatamente con QSettings INI en
.local/monitor_v13.ini (ignorado por Git); por defecto marcado sin preferencia.
Verificados ambos valores al recrear ventana. Conexión real desde el propio
V13 con QThread y casilla marcada: estado Activo SPI 14 bits 40 kHz,
219.136 muestras por canal en prueba de aproximadamente 6 s, sin error mostrado.

### 2026-10-06 — Conexión unificada

Ya no existe Autoiniciar ni Desconectar independiente. Conectar abre primero
el enlace disponible y sólo si falla ejecuta ensure_scope y vuelve a abrir.
connect_scope maneja cierre también ante error. El mismo botón muestra tres
iconos plug y permite cancelar durante arranque o desconectar al estar activo.
Preparar Q pasó a la fila Conectar/Demo, en el antiguo espacio de Desconectar.
La preferencia antigua .local/monitor_v13.ini ya no se lee. 32 pruebas OK.

### 2026-10-06 — EOF del túnel ADB tras desenchufar

Causa reproducida: app/relay Exited(255) tras corte; Connection.open aceptaba
socket local ADB pero read devolvía EOF, sin ejecutar ensure_scope. connect_scope
ahora verifica bytes con MSG_PEEK; EOF/silencio inicia recuperación. Nueve
pruebas OK. Prueba física sobre Q recién vuelto a conectar: fallback inició
app/relay y entregó 992 bytes válidos. Luego se verificó adquisición desde V13.

### 2026-10-06 — Pico al iniciar Sweep/Chirp

Usuario ubicó el pico al inicio y autorizó corregir. V12 Audio generator.h:
stop(initial) usa value(wave,phase0,low,high) con salida habilitada, antes de
reutilizar RAM; antes usaba stop(0). Apagada conserva cero. Firmware compilado
y cargado; respaldo osciloscopio_20261006_114127_867106.zip. Siete pruebas
locales OK. Seis arranques físicos (3 Sweep/3 Chirp), A2 14 bits/40 kHz, seno
2 Vpp/1,65 V, medición primeros ~0,2 s: mínimo global 0,635 V, ninguno <0,5 V.
El Q quedó con salida apagada. Evidencia resultados_autoload/20261006_sweep_start.json.
No se midió con osciloscopio externo ni se modificó el comportamiento al final.

### 2026-10-06 — Chirp intermitente: fin prematuro

Reproducido antes de la corrección: el octavo Chirp de 20→2000 Hz/2 s
quedó detenido a los 0,1 s, con confirmación OK. generator::tick convertía
la diferencia de ticks directamente a uint64_t: una diferencia negativa
terminaba inmediatamente el barrido. Ahora conserva la diferencia signed
y descarta callbacks con tiempo anterior al arranque. Prueba nativa reproduce
ese caso y verifica también la finalización normal; siete pruebas locales OK.
La relación exacta entre el callback y el fallo físico es una hipótesis;
no se instrumentaron los ticks del MCU durante el fallo.

Firmware compilado y cargado, con respaldo
respaldos/unoq/osciloscopio_20261006_123319_510143.zip. Después: 24 Chirps
consecutivos, seno 2 Vpp/offset 1,65 V, ADC 14 bits/40 kHz; todos activos
a los 0,1/0,6/1,2/1,8 s y finalizados a los 2,1 s, sin errores de estado.
Salida apagada al terminar. Informes:
diagnosticos/resultados_autoload/20261006_chirp_repeticiones.json (antes) y
20261006_chirp_timer_corregido.json (después). La repetición sin fallos
no descarta otros problemas intermitentes.

### 2026-10-06 — Documentación y organización

Usuario confirmó que Chirp funcionó tras la corrección. README principal y
los índices describen el instrumento, audio y flujo MCU/MPU/relay; versiones
con enlaces al final. Guías activas apuntan a V13/V12 Audio; V12/V11 P992
continúa disponible y las herramientas de consola conservan sus defaults.
Cuatro sketches `.bak` agrupados en respaldos/historico, contenido conservado
y referencias actualizadas. Índices nuevos de diagnósticos y respaldos.

### 2026-10-06 — Presentación e imágenes del README

Portada con badges, especificaciones y capturas actuales de V(t), FFT,
heatmap y Bode; son demostraciones sintéticas, Bode ilustra filtros RC.
Secciones independientes Python, relay C/MPU y firmware C/C++ Arduino/MCU,
con enlaces a guías ampliadas de timers, DMA, IRQ, READY y propiedad de buffers.
Las versiones siguen al final. Capturas en assets/monitor_{vt,fft,heatmap,bode}.png.

### Formato del sistema y saltos Wav · 6 de octubre de 2026

Los controles, estados y ticks numéricos de los monitores V13/V12 usan
separadores del locale del sistema. CSV, protocolos y nombres de archivo
conservan formatos independientes del idioma para mantener compatibilidad.
En Wav, −10 y +10 junto a Play saltan diez segundos durante reproducción.
Se usa la posición reproducida confirmada, se limita al inicio/final y se
confirma Stop antes de comenzar una sesión DAC nueva desde el destino.
El estado muestra la posición absoluta en el archivo tras cada salto.
Hay una breve interrupción por parada y recarga de buffers; no es un salto
continuo sin pausa. Verificado con 34 pruebas locales; saltos en hardware
pendientes de probar con el Q.

### 2026-10-06 — Final de Wav en silencio

V12 Audio libera la sesión con el generador anterior deshabilitado, tanto
al finalizar como con Stop. Ya no restaura una onda continua activa.
Seis pruebas nativas verifican EOF y Stop con salida deshabilitada.
Firmware cargado con respaldo. Prueba física: generador seno habilitado antes
de Wav50/ADC14-40k; EOF confirmado y generador enabled=0/running=false después.
Evidencia: diagnosticos/resultados_wav/20261006_final_silencio.json. Salida final apagada.


### 2026-10-06 — Pulso experimental de microsegundos

Variante independiente arduino/v13_pulse, app Scope Pulse US V13 Experimental.
TIM6 one-shot devuelve DAC al nivel bajo por hardware; DMA4 no se usa durante
ese pulso. Protocolo con duración µs y capacidad anunciada; V13 ofrece 100–65535 µs
sólo si el Q confirma soporte. Ancho inicial sigue equivalente a 1 ms (1000 µs).
V12 Audio mantiene el contrato ms y sus fuentes/app como respaldo.
18 disparos físicos ADC14/100 kHz: seis de 100, 200 y 1000 µs, anchos coincidentes
con resolución de 10 µs. Wav50 completó un segundo; salida final apagada.
La variante quedó activa, ADC14/40 kHz. Falta comprobar flancos y precisión con
osciloscopio externo. Detalles y vuelta a V12 Audio: arduino/v13_pulse/README.md.
Respaldo previo: respaldos/unoq/osciloscopio_20261006_190836_603319.zip.


### 2026-10-06 — Bode con tres paneles

V13 incorpora Tonos, Pulso y Sweep/Chirp, con inicio manual e historiales
independientes. Los métodos transitorios usan FFT de ambos canales sobre
la misma captura, nivel previo y cola; rechazan discontinuidades, respuestas
incompletas y frecuencias sin referencia suficiente. El umbral relativo se
calcula dentro de la banda medida, excluyendo DC. 31 pruebas locales pasaron.
Con A0 conectado a A2/A3, Chirp y Sweep a ADC14/40 kHz cubrieron respectivamente
5117/5138 y 5128/5128 puntos entre 20 Hz y 2 kHz. Ganancia mediana próxima
a 0 dB; fase mediana cercana a 3 grados sin calibración instrumental.
El pulso de 100 µs pasó una vez a 40 kHz pero falló repeticiones por referencia
insuficiente, también a 100 kHz: no se considera validado de forma repetible.
Evidencia: diagnosticos/resultados_bode/20261006_barridos.json.
Al terminar se restaura ADC14/40 kHz y salida apagada.


### 2026-10-06 — Corrección de referencia previa en Bode Pulso

La captura rechazada contenía el pulso en ambos canales. A3 veía el flanco
una muestra antes que A2: esa muestra entraba en la estimación de ruido previo
y elevaba artificialmente el umbral FFT. Se excluye un margen de 1 ms (mínimo
dos muestras) sólo de las estadísticas de referencia; la FFT conserva toda
la captura y el desfase real entre canales. No se reduce el umbral de ruido.
32 pruebas locales pasaron, incluida regresión del flanco adelantado.
Seis pulsos físicos consecutivos de 100 µs a ADC14/100 kHz: todas las frecuencias
20–2000 Hz válidas, ganancia mediana -0,04 a +0,07 dB y fase dentro de ±0,3°.
Seis capturas a 40 kHz también completaron, con 93–97 % de puntos válidos;
la fase mediana varió hasta 9,1°, compatible con una muestra de 25 µs
a aproximadamente 1 kHz. Para fase con pulso de 100 µs se recomienda 100 kHz;
40 kHz conserva una limitación de resolución temporal. No se corrige esa fase
automáticamente ni se considera validada su precisión a 40 kHz.
Evidencia: diagnosticos/resultados_bode/20261006_pulso_corregido_100k.json
y 20261006_pulso_corregido_40k.json. Estado final ADC14/40 kHz, salida apagada.


### 2026-10-06 — Rango y atenuación de salida en Bode

Los tres paneles arrancan en 20–5000 Hz. Pulso y Sweep/Chirp ya no
descartan la ganancia por amplitud baja de V_OUT: la referencia válida
se determina con V_IN. Se conserva la ganancia estimada y sólo se omite
la fase si V_OUT no supera el umbral de ruido. Bajo ese umbral, la ganancia
puede representar el piso de ruido y no la atenuación real del circuito.
33 pruebas locales pasaron, incluyendo salida de -80 dB y salida sólo ruido.
No se realizó una nueva prueba física con filtro en este cambio.


### 2026-10-06 — Seis correcciones de revisión Bode

Se implementaron los seis hallazgos de docs/REVISION_BODE_ASTRA.md:
referencia histórica deshabilitada sin identidad instrumental verificada;
ajuste de tonos con todas las muestras, sin decimación; plazo de captura
no renovado por consultas; rechazo correlacionado mostrado con motivo;
redibujado de resultados al regresar a Bode; y bloqueo del inicio transitorio
con configuración ADC pendiente. 39 pruebas locales pasaron, incluidas
seis regresiones en tests/v13/test_bode_review.py. No se modificó firmware
ni se operó el Q. Sigue pendiente aceptación física 20–5000 Hz con filtro.


### 2026-10-06 — Nuevas referencias instrumentales Bode

A0 conectado directamente a A2 y A3. Tres capturas por método y perfil,
20–5000 Hz, ADC14/40 y 100 kHz; dos capturas para referencia y tercera
independiente para aceptación. Se aceptaron Tonos y Sweep a ambas tasas,
y Chirp a 100 kHz. Pulso 100 µs a ambas tasas y Chirp a 40 kHz no pasaron
la repetibilidad exigida para toda la banda; no se guardan como calibración.
El monitor identifica serie/app activa/hash del binario instalado por App Lab
y exige perfil/método compatible; resultados e historiales retienen identidad.
La identidad no lee flash MCU: una programación externa obliga a invalidar
la referencia. Dos nuevos barridos físicos de Tonos verificaron carga y
aplicación automática: error máximo 0,044 dB/0,40° a 40 kHz y
0,042 dB/0,16° a 100 kHz. 40 pruebas locales aprobadas.
Evidencia: diagnosticos/resultados_bode/20261006_referencias_validacion.json
y 20261006_referencia_tonos_validacion_monitor.json.
Estado final ADC14/40 kHz, salida apagada; firmware experimental sin cambios.


### 2026-10-06 — Chirp sin curva: aceptación de cola

Se reprodujo el rechazo de un Chirp de 5 s con cola de 0,5 s. El chequeo
de asentamiento tomaba el último 10 % de toda la captura, que incluía
estímulo; limitarlo a toda la cola todavía incluía el decaimiento legítimo
del circuito. Ahora se evalúa sólo el quinto final de la cola configurada
(mínimo 16 muestras), manteniendo toda la captura para la FFT y el mismo
umbral de ruido. Una salida que no termina sigue siendo rechazada.
14 pruebas locales aprobaron, incluidas cola con decaimiento RC y cola
realmente no asentada. Ensayo físico ADC14/40 kHz, Chirp 20–5000 Hz de
5 s + 0,5 s: captura completa, 27881 puntos en curva y 2948 puntos con
ganancia/fase finitas. Esa cobertura describe la salida medida, no valida
la exactitud de un filtro desconocido. Cuatro ensayos previos de 2 s
también dejaron curvas. Estado final 14 bits/40 kHz, salida apagada.
Evidencia: diagnosticos/resultados_bode/20261006_chirp_cola_5s_diagnostico.json.


### 2026-10-06 — Estados centralizados

Conexión y visualización contiene Adquisición, Generador y Análisis en
boxes de 34 px, con texto abreviado y detalles completos en tooltip.
Se retiran mensajes de generador, análisis/Bode y trigger de los laterales;
la espera de trigger/SINGLE permanece visible arriba. Leyendas de curvas y
datos del archivo Wav se conservan junto a sus controles. Las fuentes de
mensajes notifican cambios; se mantiene el comportamiento de adquisición,
Wav y Bode. Cuatro regresiones verifican actualización, aislamiento de
paneles, espera de trigger y cambios de modo Wav. No se operó el Q.


## 2026-10-06 · Promedio Bode pulso

Selector Pulsos de 1 a 64, predeterminado 8. Estimador H1 por espectros
cruzados, ventanas iguales respecto del flanco, asentamiento entre disparos,
progreso por captura y fase filtrada por coherencia. Sweep/Chirp conserva
su método. No se modifica firmware ni se reutiliza la calibración antigua
para H1. Seis regresiones nuevas; 51 pruebas locales aprobadas.
Comparación física con A0 directo a A2/A3: dos repeticiones de N=1,4,8,16
a ADC14/40 y 100 kHz. Ocho demora unos 7 s; reduce ruido de ganancia,
pero no elimina errores instrumentales de fase (especialmente a 40 kHz).
Evidencia: diagnosticos/resultados_bode/20261006_promedio_pulsos_fisico.json
y 20261006_promedio_pulsos_sintetico.json. Panel sin barra lateral verificado.
Al finalizar se restaura ADC14/40 kHz y se apaga la salida.


## 2026-10-07 · Calibración instrumental Bode

Se conserva la tanda previa de 8 bits y los perfiles completados de 10 bits
(27 referencias aceptadas). Por pedido del usuario se limita el foco final
a las opciones actuales desde 32 kHz: 14 bits a 40/50/62,5/100/125 kHz y
16 bits a 40/50/62,5 kHz. La opción anterior es 31,25 kHz y quedó fuera.
Se completaron los ocho perfiles × cuatro métodos, con tres mediciones
por método; 16 referencias nuevas aceptadas. Pulso H1 pasó en 16 bits a
40 y 50 kHz; no a 62,5 kHz. Chirp no generó referencias nuevas; se mantiene
la anterior de 14 bits / 100 kHz. Resultados y límites completos en
 docs/CALIBRACION_BODE.md y
 diagnosticos/resultados_bode/20261007_002031_calibracion_completa.json.
Herramientas reproducibles: tools/calibrate_bode.py y
 tools/calibrate_bode_matrix.py; esta última aísla conexiones por perfil.
Los intentos iniciales de 8 bits / 200 y 250 kHz (fuera de la interfaz)
fallaron por cierre/integridad del flujo. Se recuperó reiniciando la misma
app/relay; identidad de firmware verificada, sin cambios de fuentes MCU.
Finalización confirmada: ADC14/40 kHz, salida apagada.


## Monitor con cuatro análisis FFT · 2026-10-07

Nueva variante independiente en `monitor/v14/app.py`: Spectrum, Power,
Distortion y Transfer seleccionables junto a Modo. Astra diseñó/revisó y Sol6.1
implementó. V13 se conserva. No cambia firmware ni se operó el Q.
22 pruebas nuevas y 121 regresiones adaptadas pasan. SINGLE conserva su bloque
al cambiar las vistas; coherencia/retardo N/A con un solo segmento.
Inicio: `conda activate Python_3_13_DataScience`, `python monitor/v14/app.py`.
Documentación: `monitor/v14/README.md`, `docs/FFT_ANALISIS.md` y
`diagnosticos/FFT_V14.md`. Pendiente: validación manual con hardware.
