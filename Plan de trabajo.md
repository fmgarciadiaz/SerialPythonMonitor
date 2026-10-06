# Plan de trabajo para Osciloscopio Arduino*

Este es el plan de la app completa. Pero lo tenemos que ir haciendo paso a paso. Te paso todo asi cada paso no hacemos cosas que sean incompatbles con los proximos.

1) Una vez testeado el link viable MCU MPU de UNO Q via SPI con DMA y velocidad suficiente, integraremos a nuestros codigos pero de la siguiente forma, paso a paso:
2) Paso uno, una version con todo lo mismo que la anterior, pero con conexion de Python al UNO Q sin pasar por el R4
3) Paso dos: una version con todo lo mismo que la anterior, pero pudiendo elegir port Generador/Osciloscopio (Va a ser siempre el UNO Q) y transmisor (Puede ser el R4 via UART como antes o el UNO Q mismo via SPI directo al MPU). Esa eleccion implica que el IDE de Python se comunique con la App del UNO Q y le indique el modo de operacion, UART (al R4) o SPI (al MPU->USB). Es decir el UNO Q hay que conectarlo igual, aunque este con el R4 como puente, para poder controlar todo el sistema (ahora se conecta solo el R4)
4) Paso tres: poder configurar la adquisición, con opciones que dependan de los máximos de cada transmisor: bits, frecuencia de sampleo (usar sólo válidas). Para eso Python debe controlar la App del Q, y ademas adaptar su propia lectura a los datos que van a llegar; sobre todo los bits (la frecuencia de sampleo no le cambia nada en principio)
5) Paso cuatro: Agregar sección de generador de ondas a la izquierda del aparato. Actualmente solo genera on off, quiero un panel desplegable que permita hacer las operaciones tipicas de un generador: square, triangle, ramp, sine, ajustar frecuencia, hacer un swipe, un chirp, un spike.
6) Paso cinco: modo FFT, para analizar frecuencias. Espectro en cada t o evolucion en el tiempo por heatmap. Tambien trazar la curva de ganancia/transferencia en base al chirp, o swipe o spike.
7) Paso seis: panel para grabar sonido o reproducir sonidos grabados en formato wav.



## Estado al 2 de octubre de 2026

- **Paso uno:** implementado y validado en [V8](monitor/historico/v8/README.md), Q directo por USB.
- **Paso dos:** implementado en [V9](monitor/historico/v9/README.md): selector del Q de control, destino SPI/UART y puerto R4. Cambios en vivo y CSV continuo [validados con las placas](diagnosticos/MONITOR_V9.md).
- **Paso tres:** implementado en [V10](monitor/historico/v10/README.md): panel plegable, ADC de 8/10/12/14 bits y once tasas válidas de 1 a 31,25 kHz para ambos destinos, más 40/50/62,5 kHz exclusivas de SPI ([ensayo](diagnosticos/TASAS_SPI_V10.md)). [Validación física y CSV](diagnosticos/ADQUISICION_V10.md).
- **Paso cuatro:** [salida física implementada y probada](docs/GENERADOR_PASO4.md): DAC0 en A0, entrada V_IN en A2 y entrada V_OUT en A3. Firmware cargado y cuadrada de 2,5 Hz observada en el circuito; captura continua y perfiles SPI de 14/16 bits hasta 50 kHz verificados. Motor DAC con TIM6 + DMA4 y columna permanente a la izquierda: cuadrada, seno, triángulo, rampa, sweep lineal, chirp exponencial y pulso; rango ampliado 0,1 Hz–20 kHz, dial logarítmico, selector con dibujos de onda y valores numéricos. Generador SPI validado con señales reales, CSV continuo, STOP y SINGLE; reinicio DMA corregido; timestamps capturados en TIM5 CCR1 para evitar jitter de lectura CNT, con 40 perfiles repetidos de 14/16 bits sin discontinuidades ni intercambio de canales. Captura UART/R4 pendiente de comprobar el enlace físico.
- **Paso cinco (avance al 3 de octubre):** FFT en vivo y heatmap deslizante implementados en V10, con hasta dos canales apilados y controles de tamaño, ventana, solapamiento, escala, DC e historia. [Uso y pruebas locales](docs/FFT_V10.md). Agregados ejes de frecuencia logarítmicos y Bode automático mediante barrido senoidal por pasos: ganancia y fase V_OUT/V_IN, restauración del generador al terminar. Bode [validado físicamente entre 2 y 100 Hz; recorrido ampliado hasta 1 kHz](diagnosticos/BODE_V10.md) con ADC de 16 bits, CSV sin saltos y restauración exacta del generador. Control de puntos por década, opciones con checks neutros y escalas FFT enlazables con margen e histéresis. Asentamiento y ciclos de medición independientes, con tiempo mínimo estimado del barrido. Calibración relativa de ganancia/fase y recorrido hasta 20 kHz completados con ADC de 16 bits a 50 kHz; detalles en el avance de Bode al final del plan.
- Paso seis en V13: grabación WAV y reproducción por A0 implementada en candidato; validación física de reproducción pendiente.

### Último avance de Bode

- Marcadores en cada frecuencia medida y contador de puntos válidos de ganancia y fase.
- **Agregar** conserva hasta cinco barridos con colores de la paleta de entradas; **Repetir** borra la comparación e inicia un nuevo barrido.
- Sombra translúcida tenue agregada a las curvas y corrección instrumental por referencia de ganancia/fase implementada.
- Validación física y calibración relativa entre canales completadas entre 20 Hz y 20 kHz, ADC 16 bits / 50 kHz: 31/31 puntos, CSV sin saltos y restauración exacta. Referencia anterior invalidada por cableado incorrecto; reemplazada por el ensayo 20261003_123522_633848, con 581 579 filas CSV sin saltos. La repetibilidad de la nueva referencia aún no fue medida. [Evidencia y límites](diagnosticos/BODE_V10.md). Otros perfiles ADC requieren su propia referencia.


### Ensayo de adquisición rápida · 4 de octubre de 2026

- Conjunto estable V10/V8 config respaldado y fuentes conservadas.
- Nuevos [V11](monitor/historico/v11/README.md) y [V9 Fast](arduino/historico/v9_fast/README.md): SPI a 32 MHz, CRC más rápido y sellado único; 100 kHz por canal en 8/10/12/14 bits. 16 bits sigue hasta 50 kHz, UART hasta 31,25 kHz.
- 100 kHz / 14 bits pasó 120 s, casi 12 millones de pares sin huecos, rangos inválidos, dropped ni fatal. 18 segmentos verifican resoluciones, ida/vuelta a 16 bits y generador concurrente hasta 20 kHz.
- V(t), FFT y heatmap con USB real a ~100 000 pares/s; heatmap 30 s, CSV de 734 350 filas sin saltos. V11 limita el pintado FFT/heatmap a 20 Hz a alta Fs, conservando todas las muestras y pasos del análisis.
- 125 kHz perdió nodos; 200/250 kHz no se ensayaron después del fallo. No se ofrecen en V11.
- Validación analógica de ambos canales pendiente: A2 recibe una senoide limpia, A3 una señal muy pequeña; confirmar conexión directa para medir precisión. No se alteró la calibración de Bode existente.
- [Estudio, evidencia, límites y restauración](experimentos/tasas_spi/README.md). Este ensayo no adelanta el paso seis de WAV.

- Diagnóstico posterior de 125 kHz: [mediciones con y sin PC](experimentos/tasas_spi/DIAGNOSTICO_125.md) confirman atraso sostenido del consumidor (473/465 µs por trama frente a 420 µs disponibles). Cola llena, CRC correcto y fatal=0 en ambos; pendiente separar costos MCU/driver Linux. Firmware conservado.
- Medición MCU aislada de 125 kHz: [instantáneas con/sin DAC](experimentos/tasas_spi/resultados/mcu_20261004/README.md), cola 4/4 y envío de nodo 18,17–18,36 ms frente a 16,384 ms. Armado DMA ~20 µs; copia ADC ~432–434 µs/nodo. No se cambió V9 Fast. Sigue pendiente optimizar y validar la coordinación/preparación por fragmento antes de habilitar 125 kHz.

### Optimización P992 · cierre del 4 de octubre de 2026

- [Candidato P992 aprobado](experimentos/tasas_spi/opt125/README.md) a 14 bits / 125 kHz por canal: tramas SCP1 V3 de 992 bytes, 19 fragmentos por nodo. P512 no alcanzó el margen.
- Envío medio de 14,118/14,067 ms por nodo sin/con cuadrada de 2,5 Hz: margen medio medido de 13,83/14,14 %, cola máxima 2/4.
- Dos capturas normales de 120 s, 14989425 pares cada una, sin errores ni pérdidas; 119 comandos concurrentes con DAC activo y nueve etapas de transición aprobadas.
- Monitor experimental con USB real: V(t), FFT, heatmap, trigger/SINGLE y CSV de 507551 filas sin saltos; Qt offscreen. Precisión analógica de ambos canales y disparo relacionado al generador siguen pendientes.
- V9 Fast normal restaurado a 14 bits / 100 kHz y cuadrada de 2,5 Hz; 298762 pares verificados sin pérdidas. 38 archivos originales intactos y 185 pruebas locales aprobadas. [Aceptación y restauración](experimentos/tasas_spi/opt125/resultados/aceptacion_p992.json).
- P992 queda independiente; V11 conserva su límite de 100 kHz hasta una promoción posterior. Este ciclo de optimización queda cerrado.

### Comparación analógica posterior · 4 de octubre de 2026

- [A2/A3 aprobados con señal común directa](experimentos/tasas_spi/opt125/ANALOGICO.md): ADC de 14 bits, seno ~1996,805 Hz, cinco capturas de 10 s entre V9 Fast (62,5/100 kHz) y P992 (62,5/100/125 kHz).
- Amplitud ~1,216 V pico en ambos canales, diferencia relativa observada <0,02 %, residuo RMS 6,8–7,5 mV, fase relativa ~1,53°; cero saltos, rangos inválidos, dropped o fatal.
- Esta prueba cierra la comparación pendiente para ese estímulo y resolución; no calibra tensión/reloj ni valida todas las frecuencias o resoluciones. Calibraciones Bode conservadas.
- P992 aún no se promovió a V11. Firmware, relay y perfil anterior se restauran tras la medición.

### Integración en nueva versión · 4 de octubre de 2026

- Nueva pareja [Monitor V12](monitor/v12/README.md) + [firmware V11 P992](arduino/v11_p992/README.md), independiente de los experimentos. Receptor dentro de V12 y relay propio junto al firmware, SCP1 V3/992 a 32 MHz, hasta 125 kHz por canal.
- V10/V11 y V8 config/V9 Fast se conservan en sus carpetas. Nuevas entradas de VS Code, catálogo App Lab y selección explícita `--firmware v11_p992`; defaults de herramientas conservados.
- 198 pruebas locales aprobadas y firmware/relay ARM compilados. La evidencia sostenida y analógica de P992 corresponde a ADC14/125 kHz con los estímulos documentados; UART físico y calibración absoluta siguen pendientes.
- Verificación física de integración mediante `diagnosticos/verificar_v12.py`, con seno de 2 kHz, trigger/SINGLE, V(t), FFT, heatmap y CSV, restaurando el generador al terminar.
- [Integración aprobada con USB real](capturas/validacion_v12/20261004_204139_688307/informe.json): SINGLE con seno de ~2 kHz / 2,46 Vpp, FFT, heatmap y CSV de 511082 filas continuo. Generador restaurado a 2,5 Hz; nueva pareja activa en Q a ADC14/125 kHz. Sigue el paso seis de WAV; no se hizo un nuevo Bode físico ni se validó UART/R4.

### Optimización 16 bits · 5 de octubre de 2026

- Se implementó el **Camino A**: reloj de ADC acelerado a **50 MHz vía PLL2** (HSE 16 MHz / 2 * 25 / 4 = 50.000 MHz, dentro de los 55 MHz nominales del STM32U5).
- Desbloqueado **16 bits a 62,5 kHz** por canal conservando el oversampling $\times 16$ intacto (período 16 µs, tiempo nominal de conversión 14,08 µs, antes de latencias; margen nominal 12%).
- Validado físicamente en la placa ([informe](capturas/adc16_rate/test62k5_20261005_002648/informe.json)): 311.409 pares en 5 s a 62.275 pares/s sostenidos, dropped=0, fatal=0.
- Interfaz gráfica de [Monitor V12](monitor/v12/app.py) actualizada para permitir 62,5 kHz en 16 bits; suite completa de tests aprobada (`OK`).


- Revisión posterior: [ADC16 V12](diagnosticos/ADC16_V12.md). Diagnóstico corregido para restaurar el perfil observado; 7.495.680 pares en 120 s sin discontinuidades, dropped ni fatal. Suite de 206 pruebas aprobada. El reloj ADC de 50 MHz afecta todos los perfiles y requiere comprobar las referencias Bode anteriores.

- Correcciones de reloj compiladas y cargadas: [120 s finales](capturas/adc16_rate/test_20261005_011511_251289/informe.json), 7.495.906 pares sin errores. Comparación analógica 50/62,5 kHz a 2/10/20 kHz: amplitud estable (<0,23%), residuo mayor a20 kHz; no certifica ENOB ni reemplaza calibración Bode. Perfil y generador del usuario restaurados.

### Evaluación V13 / PyQt6 · 5 de octubre de 2026

- V13 independiente conserva el receptor, assets y una copia de las referencias
Bode; requiere PyQt6 en entorno separado. Firmware V11 P992 sin cambios.
- V12 sigue disponible con PyQt5. Backend pyqtgraph seleccionado explícitamente;
pruebas Qt5 y Qt6 en procesos distintos.
- Ver [uso y evaluación](monitor/v13/README.md). No se inició WAV ni se alteró
la adquisición; la mejora de rendimiento se evalúa por escenario.

- Validación V13:24 pruebas Qt6 y208 Qt5 aprobadas. [Comparación](diagnosticos/QT6_V13.md) con40 cuadros medidos por escenario: Qt6 más lento en el ensayo offscreen; V12 se conserva como referencia. Prueba manual de pantalla pendiente.


### Paso seis: grabación WAV · 5 de octubre de 2026

- V13 incorpora selector CSV/WAV junto al estado de grabación y conserva RECORD/STOP REC. WAV estéreo PCM16: A2 izquierda, A3 derecha; Fs confirmada, todas las muestras, centro ADC fijo sin filtros ni AGC.
- Archivos en capturas/v13, numeración compartida con CSV, máximo 30 s y cabecera finalizada al detener/cerrar. Las discontinuidades detienen WAV explícitamente; no se rellenan huecos. Demo continúa disponible en CSV.
- Astra fue solicitado para planificación, pero estaba indisponible por límite de uso; se siguió el alcance concreto autorizado con implementación/revisión Sol. No se operó hardware ni se cambió firmware.
- Pruebas locales Qt6 del grabador y regresiones anteriores aprobadas. Validación WAV con entradas reales pendiente; siguiente etapa: decidir botón de reproducción y salida física.

### Paso seis: reproducción WAV candidata · 5 de octubre de 2026

- Modo WAV en V13: archivo local, L/R/Mix, Reproducir y Detener; conversión antialias a 20 ksps, eliminación de media y ajuste Vpp/offset a códigos DAC12.
- Firmware aislado V12 Audio y relay MPU propio con créditos, buffers acotados y parada neutral ante falta de datos. V11 P992 sigue predeterminado.
- 51 pruebas locales Qt6/protocolo/firmware aprobadas; sketch compilado (107000 bytes flash, 192524 RAM). Respaldo V11 conservado. Carga y ensayo A0→A2/A3 pendientes de autorización.
- Ver [activación y restauración](arduino/v12_audio/README.md) y [uso](monitor/v13/README.md).

### V12 Audio cargado y ensayo físico inicial aprobado

Autorizado y cargado el 5 de octubre: firmware MCU V12 Audio y relay MPU propio
quedaron activos. WAV estéreo 44,1 kHz→20 ksps, L=997 Hz, R=2003 Hz,
Mix con ambos tonos comprobados en A2/A3; 40000 muestras por pasada,
sin underrun ni discontinuidades ADC14/31,25 kHz. Detener→IDLE y
restauración del generador confirmados. Falta ensayo sostenido y evaluación visual.
VS Code: «Monitor V13 — WAV A0 (V12 Audio)» habilita el protocolo nuevo.
Informe: diagnosticos/resultados_wav/20261005_fisico.json.

### Evaluación de mayor tasa WAV

Iconos vectoriales por modo y etiqueta Wav en V13. Siguiente candidato:
40 ksps y luego 50 ksps con tasa negociada; 20 ksps sigue vigente.
Ver [cálculos y pruebas necesarias](docs/WAV_TASAS.md).

### Tasas WAV negociadas probadas · 5 de octubre de 2026

V12 Audio MCU/relay actualizados y activos; selector Salida 20/40/50 kHz en V13.
Ensayos de 120 s aprobados: WAV40/ADC14-40k, WAV50/ADC14-40k y
WAV50/ADC14-100k. WAV50/ADC125 falló dos veces con integridad ADC;
Play bloquea ADC mayor de 100 kHz. STOP y restauración confirmados.
57 pruebas locales y regresiones Qt6 adicionales aprobadas. Respaldo previo
osciloscopio_20261005_181834_429412.zip y fuentes 20 ksps conservadas.
Ver docs/WAV_TASAS.md e informes diagnosticos/resultados_wav.

### 2026-10-06 — Preparación completa del Q desde V13

- Agregado botón **Preparar Q** para instalar/actualizar app V12 Audio, firmware
  MCU y relay en el dispositivo USB seleccionado, con respaldo si la app existe.
- Progreso en el estado, log completo, trabajo en segundo plano y confirmación
  de la primera trama SPI antes de declarar el Q preparado.
- Verificación local: 3 pruebas de preparación y 13 de autoinicio/controles Qt.
- Pendiente: validar instalación completa en un Q nuevo y tras apagado/encendido.

### 2026-10-06 — Corregir READY inicial del relay

Reproducido fallo real tras cargar MCU: app inicia, relay espera un flanco que
puede haber ocurrido antes de la espera. Se admite un único READY inicial alto,
con drenaje de eventos y validación íntegra; siguientes tramas requieren nuevos
flancos. Relay compilado e instalado; autoinicio físico confirmado. Pruebas
locales de firmware/protocolo/autoinicio: 11 OK. Nueva prueba de apagado/encendido
pendiente; evidencia de adquisición en resultados_autoload.

### 2026-10-06 — Valores iniciales del generador

V13: Wav 50 kHz (con reducción por capacidades), amplitud compartida 2 Vpp,
salida apagada y casilla centrada. Al conectar en Continuo se aplica el estado
preparado; modos finitos esperan disparo manual. 19 pruebas Qt/Wav OK.

### 2026-10-06 — Botón único de conexión

Eliminados checkbox Autoiniciar y botón Desconectar independiente. Conectar
abre el transporte existente primero; si no está disponible, verifica/inicia
la app instalada y el relay. Mismo botón cancela o desconecta según estado,
con tres iconos plug. Preparar Q ocupa el antiguo lugar de Desconectar.
32 pruebas de conexión/autoinicio, Qt y monitor pasaron.

### 2026-10-06 — Dial de amplitud Wav durante Play

Dial Wav 0–3,3 Vpp; amplitud aplicada en bloques pendientes, con transición
suave de un bloque. Preparación a escala completa permite subir desde cero sin
remuestreo ni reinicio. Cola de niveles conserva sólo el último ajuste y se
atiende durante playback. Más espacio entre icono y texto de conexión.

### 2026-10-06 — Recuperación de A0 tras Wav

Dial Wav reducido a 64 px. Corregido cierre: Stop con ACK antes de cerrar USB,
y recuperación de sesión anterior al conectar. UNDERRUN/FAULT conserva Stop.
Validación física: seno 1 kHz/2 Vpp en A2, Wav 50 kHz y dial 2→1 Vpp;
cierre sin excepción, salida final apagada. Evidencia en
resultados_wav/20261006_recuperacion_generador_dial.json.

### 2026-10-06 — Apagar salida al desconectar

Desconectar/cerrar libera Wav y confirma generador deshabilitado a 0 V antes
de cerrar USB. Pruebas locales de shutdown, monitor e instalación: 21 OK.

### 2026-10-06 — Reconexión tras corte de alimentación

Reproducido con contenedores detenidos: el socket del túnel ADB abre aunque
el relay remoto esté cerrado y después entrega EOF. Conectar ahora exige datos
por MSG_PEEK antes de validar el enlace; EOF/silencio activa comprobación e
inicio de app/relay. Nueve pruebas de conexión/autoinicio OK.

### 2026-10-06 — Corregido paso por cero al iniciar barridos

V12 Audio generator::apply detiene DMA con el primer valor de la nueva onda
si está habilitada; salida apagada mantiene 0 V. Compilado/cargado en Q con
respaldo osciloscopio_20261006_114127_867106.zip. Siete pruebas locales OK.
Tres arranques Sweep + tres Chirp, 20→2000 Hz/2 s, seno 2 Vpp/offset 1,65 V:
ventana inicial medida A2 a 40 kHz sin caída inferior a 0,5 V. Salida final
apagada. Evidencia: resultados_autoload/20261006_sweep_start.json.

### 2026-10-06 — FFT de SINGLE anclada al trigger

SINGLE en FFT/heatmap espera ventana FFT completa y calcula sobre copia del
bloque con 10 % pretrigger. STOP mantiene la captura y RUN sigue usando las
muestras recientes. Prueba sintética con pulso ya fuera del bloque más reciente
verifica conservación del espectro y regreso a FFT en vivo. Amplitud/offset:
texto de dos decimales y resolución interna 1 mV.

### 2026-10-06 — SINGLE: bloque FFT de mayor energía

Selecciona entre bloques próximos que contienen el trigger el de mayor energía
AC ponderada por la ventana FFT, sumando canales seleccionados. Copia fija del
bloque elegido; indicador SINGLE naranja dentro de los gráficos, borrado al
volver a RUN o rearmar. Prueba de pulso verifica ventana energética y marcador.

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
