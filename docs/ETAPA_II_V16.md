# Etapa II · V16: implementación y aceptación

La revisión de Astra propone separar la compactación del transporte de la retirada del DMA temporal. La versión anterior ya captura timestamps por TIM5 CCR1 y GPDMA0: no llama a micros() para cada conversión. El productor valida cada diferencia y copia registros de ocho bytes; esos registros también ocupan el transporte.

## Primer incremento implementado

Monitor, app/sketch y relay tienen carpetas propias V16. El protocolo SCP1 pasa a **V4 en todas las tramas**, incluidos PING, adquisición, generador, transporte y WAV. Una versión mezclada debe fallar explícitamente, no aceptar datos con interpretación distinta.

| Campo | Posición/tamaño |
|---|---|
| Trama y CRC | 992 bytes; CRC32 en 988 |
| Estado/metadata | Sin cambio hasta byte 79 |
| Timestamp inicial | uint32 LE en 80 |
| CH1 / CH2 | Dos uint16 LE por par desde 84 |
| Capacidad | 226 pares por fragmento |
| Nodo ADC | 2048 pares; 9 fragmentos de 226 y uno de 14 |

El receptor calcula `t[i] = (t0 + i × período) mod 2^32`. Comprueba CRC, secuencia, índice, período/perfil, época, APPLIED, rangos y padding, incluidos estado vacío, fragmento final y wrap temporal. El MCU conserva la verificación de timestamps originales; sólo publica un nodo después de comprobar continuidad y propiedad DMA. La cola reduce el dato de cada par a cuatro bytes, más timestamp inicial e índice del nodo.

El transporte pasa de 19 a 10 tramas por nodo: 18 848 a 9 920 bytes (47,4 % menos). No representa automáticamente 47,4 % más tasa ADC: quedan conversión, relojes, scheduling, SPI y reproducción DAC concurrente.

CH1=A2 y CH2=A3. Los canales derivados ADC_IN/ADC_OUT desaparecen del monitor. Tiempo e índice son metadata interna necesaria para continuidad, trigger, CSV y WAV. UART/R4 conserva DATA heredado mediante expansión explícita en el sketch; el ahorro de tráfico es SPI/USB. Bode exige identidad V16 y referencias nuevas, sin promover las calibraciones anteriores.

## Secuencia restante

1. Construir el relay Linux completo, instalar V16 y medir a las tasas anteriores: integridad sostenida, dropped/fatal, cola, margen de envío y comandos ADC/DAC/WAV concurrentes. Probar SPI→UART→SPI y restaurar perfil/salida anteriores. No prometer tasas nuevas antes de medir.
2. Retirar o reducir DMA temporal con una medición independiente del tiempo: timestamps reconstruidos no detectan por sí solos disparos omitidos. Diseñar anclaje inicial y comprobación por nodo antes de habilitarlo.
3. Reemplazar selección de canales por filtros digitales con fuente CH1/CH2 y salida FILTER; filtros con estado continuo, corte limitado por Nyquist y cambios sin discontinuidades artificiales.
4. Ofrecer CH1/CH2/FILTER en todos los análisis, definiendo también el par de referencia/respuesta para Bode/Transfer y el retardo de los filtros.
5. Explorar adquisición de un canal a mayor tasa con firmware y aceptación física propios.

## Verificación local

Vectores C/C++ y Python V4; CRC/padding/rangos, nodo completo, fragmentación TCP, reloj que envuelve, rechazo V3 y comandos. Regresiones V16 de UI, trigger/SINGLE, medidas, CSV/WAV, FFT, Bode y Synth/MIDI. Estas pruebas no son evidencia física de muestreo ni aceptación del sketch instalado.

Inicio: `python monitor/v16/app.py`. Preparación explícita: `python tools/prepare_q.py --serial NUMERO --firmware v16`. V15 sigue siendo la referencia anterior y las herramientas conservan su default anterior.

El sketch completo compiló localmente con Arduino Zephyr 1.0.0: 104 844 bytes de programa y 159 644 bytes de RAM estática (60 %). No se cargó en el Q. Suite V16: 135 pruebas pasan; golden C++ y validador C compilados con warnings tratados como errores.

## Ensayo físico · 9 de octubre de 2026

V16 se instaló después de respaldar la app V13 Pulse anterior. Firmware y relay ARM compilados en el Q, sin otra conexión al puerto del relay.

| Perfil | Duración | Pares recibidos | dropped / fatal |
|---|---:|---:|---:|
| 14 bits / 40 kHz | 120 s | 4 796 416 | 0 / 0 |
| 14 bits / 125 kHz | 120 s | 14 991 346 | 0 / 0 |
| 16 bits / 62,5 kHz | 120 s | 7 495 666 | 0 / 0 |

El decoder estricto no detectó CRC incorrectos, discontinuidades de trama/índice/tiempo, padding inválido ni códigos fuera de rango. El MCU siguió validando los timestamps originales. Generador senoidal activo durante 10 s con ADC14/100 kHz; WAV de cinco segundos terminó con todas sus muestras a 20 y 40 kHz, también con ADC14/100 kHz. Estos ensayos acreditan integridad del flujo en los perfiles probados; no precisión analógica, carga máxima concurrente Synth ni tasas nuevas. No se probó UART/R4, margen de cola o comparación de Bode física.

Estado final confirmado: V16 activa, ADC14/40 kHz, configuración del generador anterior restaurada y salida apagada. V15 requiere volver a su firmware/relay V3 si se quiere usarlo con la placa. El código anterior y su respaldo permanecen disponibles.

[Evidencia JSON](../diagnosticos/resultados_v16/20261009_143247_integridad.json), [estado previo](../diagnosticos/resultados_v16/estado_previo.json), [estado final](../diagnosticos/resultados_v16/estado_final.json), [herramienta reproducible](../diagnosticos/verificar_v16.py). Respaldo: `respaldos/unoq/osciloscopio_20261009_142740_338127.zip`.

## Análisis de canales derivados

Implementada selección X/Y de CH1, CH2 o FILTER en FFT Transfer y los tres
métodos Bode. La fase incluye el filtro causal, sin adelantar artificialmente
la salida. La calibración original sólo se usa en CH2/CH1; el resto se mide sin
corrección. Cambiar el par elimina resultados previos; cambiar el filtro invalida
Bode cuando usa FILTER. En transitorios CH1 sigue detectando el estímulo y debe
estar conectado a A0. [Uso y límites](FILTROS_V16.md).

La retirada de TIM5/GPDMA temporal y el modo de un canal siguen pendientes:
requieren diagnóstico independiente del reloj y aceptación física antes de
promover nuevas tasas.

## Tasas altas con DMA temporal · 9 de octubre de 2026

Sin modificar firmware ni retirar TIM5/GPDMA temporal, se ensayaron los perfiles
que ya admitían MCU, relay y receptor, pero estaban ocultos en la interfaz:

| Perfil | Duración | Pares | dropped / fatal |
|---|---:|---:|---:|
| 14 bits / 200 kHz | 120 s | 23 986 176 | 0 / 0 |
| 14 bits / 250 kHz | 120 s | 29 982 028 | 0 / 0 |

El decoder estricto no detectó errores de CRC, secuencia, índice ni continuidad
temporal. Seno de 1 kHz concurrente durante 10 s a ADC250 también pasó.
**WAV concurrente a ADC250 cerró el flujo del Q** y la restauración inicial
falló; fue necesario reiniciar app/relay V16 y restaurar el perfil por una nueva
conexión. No se considera aprobada esa combinación ni se identifica todavía
la causa del cierre. A ADC200, una segunda prueba terminó los WAV de cinco
segundos a 20 y 40 kHz con 100 000 y 200 000 muestras completas.

El monitor ofrece 200/250 kHz como **experimentales**. El límite de 16 bits
permanece en 62,5 kHz; WAV y Synth en la interfaz mantienen ADC ≤100 kHz.
No se midieron margen de cola, precisión analógica, Synth a estas tasas ni UI
sostenida con todos los análisis. El tiempo de adquisición por canal baja a
1,36 µs en 200 kHz y 0,72 µs en 250 kHz: el asentamiento depende de la fuente.
No se promovieron como perfiles estables generales. Default: 14 bits/40 kHz.

Estado final confirmado: ADC14/40 kHz, salida apagada, V16 activa.

[Evidencia sostenida y fallo concurrente](../diagnosticos/resultados_v16/20261009_161658_tasas_altas.json),
[recuperación](../diagnosticos/resultados_v16/recuperacion_tasas_altas.json),
[WAV a ADC200 y restauración final](../diagnosticos/resultados_v16/20261009_162234_tasas_altas.json).
Reproducir: `python diagnosticos/verificar_tasas_v16.py --seconds 120`;
para el ensayo concurrente a ADC200: `--rates 200000 --concurrent-rate 200000`.

## Validación temporal por nodo

El productor valida todos los timestamps contra una secuencia esperada y separa
la copia según la propiedad de la cola fuera del bucle por muestra. No se retiran
TIM5 ni GPDMA temporal. Se conservaron controles de sincronización, propiedad
y errores. [Diseño y pruebas](CAPTURA_TEMPORAL_V16.md).

Ensayo del validador optimizado: 60 s a ADC14/200 y 250 kHz sin pérdidas;
seno y WAV20/40 a ADC200 completos. Estado final: ADC14/40 kHz, salida
apagada. 154 pruebas pasan. No se mide todavía ahorro CPU.

## Monitor a tasas altas: ingesta por columnas

El lector entrega bloques numéricos NumPy (tiempo, índice, CH1 y CH2) en lugar
de crear diccionarios por cada muestra. La GUI calcula FILTER y llena el
historial con las columnas completas. CSV/Bode materializan filas sólo cuando
se necesitan; WAV conserva las entradas originales y valida continuidad.
No se descartan ni se submuestrean datos de adquisición para mejorar FPS.

Comparación sintética de 409 600 muestras, bloques de 4096, a configuración
ADC14/200 kHz: mediana de construcción + ingesta de 8,93 ms a 0,36 ms por
bloque (≈25×). Llamada de render: 2,67 ms a 2,25 ms. Son mediciones de host
sin USB ni pintado completo: no acreditan esos factores en los FPS físicos.
La latencia de la cola Qt se sigue midiendo mediante `published_at`.
[Benchmark reproducible](../diagnosticos/benchmark_ingesta_v16.py),
[resultado](../diagnosticos/resultados_v16/benchmark_ingesta.json).

Escala horizontal mínima: 8 muestras. En modo tiempo, las ventanas menores
a 1 ms usan µs; a 200 kHz el mínimo es 40 µs, a 250 kHz es 32 µs. El valor
mantiene un decimal y su conversión de vuelta a muestras respeta el período.
No cambia firmware ni configuración física del Q.

## Generador hasta 50 kHz

Monitor, protocolo MCU y validación de estados del relay aceptan 0,1 Hz–50 kHz,
incluidas frecuencias inicial/final de Sweep y Chirp. Los diales conservan escala
logarítmica y alcanzan 50 kHz. La cuadrada usa dos puntos por ciclo (100 000
actualizaciones/s a 50 kHz); seno, triángulo y rampa reducen la tabla hasta
16 puntos por ciclo (640 000 a 40 kHz; 800 000 a 50 kHz), manteniendo el límite
existente de 1 000 000 actualizaciones/s. Sweep/Chirp dimensionan la tabla por
la mayor frecuencia de sus extremos, también en barridos descendentes.

Implementación y pruebas de host: no acredita amplitud, asentamiento ni forma
analógica a estas frecuencias. Instalación del firmware/relay actualizados y
validación física pendientes. La versión de trama sigue V4; una instalación
V16 anterior aún limita el generador a 20 kHz. ADC16 permanece en 62,5 kHz.

### Instalación y ensayo físico de 50 kHz · 9 de octubre de 2026

Firmware MCU y relay actualizados compilados e instalados en la Q 1060031107.
MCU: 108 264 bytes de programa y 160 488 bytes de RAM estática (61 %).
Respaldo previo: `respaldos/unoq/osciloscopio_20261009_171752_407946.zip`.

Con ADC14/250 kHz, cuadrada, seno, triángulo y rampa pasaron 10 segundos cada
una a 40 y 50 kHz. Sweep y Chirp senoidales pasaron en ambos sentidos entre
40 y 50 kHz, con duración de 2 segundos y confirmación de fin. Los 12 casos
recibieron 22 501 122 pares en total; decoder estricto sin errores CRC,
secuencia, índice ni tiempo, dropped/fatal cero en los estados registrados.
No se ensayó WAV/Synth concurrente ni margen de cola.

CH1 mostró energía a la frecuencia solicitada (FFT aproximadamente 40 000 y
50 000 Hz con reloj compartido). Para niveles DAC 1427–2668 (~1 Vpp), el seno
observado tuvo ~1,02 Vpp a 40 kHz y ~1,00 Vpp a 50 kHz. CH2 tuvo una variación
mucho menor; el cableado no se confirmó en este ensayo. Triángulo/rampa a
50 kHz mostraron ~0,89/~0,86 Vpp muestreados: sólo cinco muestras ADC por ciclo
no permiten certificar extremos, flancos ni forma continua. No es calibración
absoluta ni validación de excitación del piezo o del sobreimpulso anterior.

Restauración exacta confirmada por respuestas MCU: ADC14/250 kHz, SPI,
generador cuadrado de 2,5 Hz con niveles 0/0 y salida apagada. V16 actualizado
permanece instalado; ahora se puede seleccionar hasta 50 kHz en el monitor.

[Informe y capturas crudas](../diagnosticos/resultados_v16/20261009_172039_generador_50khz.json),
[estado anterior](../diagnosticos/resultados_v16/estado_previo_generador_50khz.json),
[ensayo reproducible](../diagnosticos/verificar_generador_v16.py).
Para repetir: cerrar monitor, ejecutar primero `--snapshot` y luego el ensayo;
restaura ADC y configuración del generador guardados incluso ante errores.

### Ajustes de interfaz y nivel del piano

Por pedido del usuario se retiró la etiqueta «experimental» de los selectores
200/250 kHz y de la ayuda del generador. Se conservan límites ADC16, las
restricciones WAV/Synth y la información de adquisición/impedancia en los
tooltips; las limitaciones físicas documentadas de los ensayos siguen vigentes.
La ganancia de salida del piano virtual pasa de 4 a 5 (+25 %, ~1,94 dB),
conservando el limitador de salida existente.

### Integración del empaquetado ADC14 — 10 de octubre de 2026

El formato SCP1 V4/992 incorpora tipo 15 para ADC14: dos pares por siete bytes,
258 pares por trama, ocho fragmentos por nodo (último: 242). Tipo 3 permanece para
los demás perfiles y el receptor también admite firmware anterior. Se conservan
las comprobaciones estrictas de CRC, padding, índices, timestamps y épocas.
CRC slicing-by-8 y limpieza exclusiva del padding reducen trabajo del MCU; no se
integran los paquetes TDG2 usados para medir el experimento. 333333 Hz se muestra
como experimental, con período de 3 µs y ventana ADC de 0,72 µs. Synth sigue limitado
a ADC40 y ADC16 a 62,5 kHz. La validación digital no reemplaza la analógica.

Validación de la versión integrada en el Q: ADC14/250 kHz y ADC14/333,3 kHz,
120 s cada uno, 29.982.962 y 39.976.718 pares respectivamente, cero pérdidas y
cero errores. ADC8/10/12/16 a 62,5 kHz y ADC14 a 31,25 kHz también pasaron.
Con ADC40, WAV20 y WAV40 completaron 100.000 y 200.000 puntos sin underrun.
Se restauró ADC14/250 kHz y el generador previo apagado; firmware integrado activo.
[Evidencia](../diagnosticos/resultados_v16/20261010_235156_tasas_altas.json).

### CH1 rápido integrado — 11 de octubre de 2026

La interfaz admite `CH1 rápido · 599,25 kHz · experimental`, SPI y ADC14. El perfil
se identifica por período 267 y reloj TIM2/TIM5 de 160 MHz; el resto conserva su
reloj de 1 MHz. La configuración confirmada cambia la época, DMA ADC usa un
resultado por disparo y mantiene TIM5 independiente, validación de cada muestra,
CRC, secuencia y límites de cola originales. Cuatro muestras ADC14 por siete bytes,
516 por trama, tipo 16. Los modos de dos canales conservan tipo 3/tipo 15.

La conversión a microsegundos sucede después de validar los ticks crudos. CH1
rápido mantiene tiempo continuo a través del wrap; CH2 queda ausente en la GUI,
CSV y WAV mono. Los selectores restauran CH2 al volver al modo de dos canales.
Synth sigue limitado a ADC40 y UART no admite el perfil de un canal.

Validación física integrada: dos canales ADC14/333333 → CH1 rápido → ADC12/125000
→ CH1 rápido durante 120 s → ADC16/62500 → dos canales ADC14/333333. La etapa de
120 s recibió 71.866.884 muestras sin pérdidas ni errores; también se comprobó
continuidad de tiempos convertidos entre lotes. Perfil previo restaurado a
ADC14/333333 y generador apagado. [Resultado](../diagnosticos/resultados_v16/ch1_integrado.json).

Prueba con worker real y Qt sin pantalla: 5.704.196 muestras y 364 lotes sin errores.
Reconexión con CH1 rápido ya activo: 5.707.260 muestras y 357 lotes sin errores.
[GUI](../diagnosticos/resultados_v16/ch1_gui.json),
[reconexión](../diagnosticos/resultados_v16/ch1_gui_reconnect.json).
La verificación Qt no reemplaza la aceptación visual del usuario ni certifica
precisión analógica. Pasaron 50 pruebas locales de protocolo/UI y comprobaciones
adicionales focalizadas de WAV mono y límite ADC del synth.

Después de los cambios de modo, WAV20/WAV40 con ADC40 completaron 100.000/200.000
puntos sin underrun. Se conservó ADC14/333333 y generador previo apagado.

### FFT corregida y ensayo CH1/661,16 kHz — 11 de octubre de 2026

Se corrigió la restauración de CH2 no disponible al cambiar de modo FFT: los
controles vuelven a verificar los canales disponibles y el análisis omite
historiales sin muestras finitas. CH1 permanece válido en Spectre/Power/Distort.
La regresión usa una señal conocida de 20 kHz y wrap de timestamps. Pasaron 23
pruebas FFT y seis pruebas del contrato experimental. La FFT Qt con el worker
real procesó 5.712.388 muestras en 351 lotes, sin errores y con espectro CH1 válido.

El ensayo separado CH1 ADC14/661157,025 Hz (242 ticks a 160 MHz) pasó 10 y 120 s,
con 79.294.964 muestras en la prueba prolongada, dropped=0 y fatal=0. Conserva
CRC, índices, secuencia y validación DMA temporal; no aumenta cola ni reduce bits.
Se restauró V16 CH1/599250 y generador apagado, comprobado otros 10 s.
[Resultado](../experimentos/ch1_660_v16/results.json). 661,16 kHz sigue aislado;
precisión analógica y margen mínimo de cola no certificados.


### FPS reales de los perfiles nativos — 12 de octubre de 2026

Se midieron los 14 perfiles y una referencia común, con generador normal cuadrado
a 5 kHz confirmado por el Q, ventana temporal de 1 ms y pintado Qt real.
Cada caso tuvo 2 s de estabilización y aproximadamente 5 s medidos. No se
realizaron capturas de imagen periódicas dentro de las ventanas medidas.

| Bits | Canales | Tasa (Hz por canal) | FPS pintados | Demora de lotes p95 (ms) |
| --- | --- | --- | --- | --- |
| 8 | 1 | 1118881 | 31.7 | 44.1 |
| 8 | 1 | 1221374 | 21.7 | 57.6 |
| 8 | 2 | 597014 | 59.8 | 16.4 |
| 8 | 2 | 632411 | 58.7 | 15.3 |
| 10 | 1 | 909090 | 25.2 | 37.8 |
| 10 | 2 | 495356 | 52.4 | 17.6 |
| 10 | 2 | 519480 | 49.4 | 17.9 |
| 12 | 2 | 410256 | 57.0 | 16.7 |
| 12 | 2 | 437158 | 51.9 | 17.0 |
| 14 | 1 | 701754 | 46.9 | 17.4 |
| 14 | 1 | 747663 | 39.0 | 19.2 |
| 14 | 2 | 40000 | 62.6 | 7.6 |
| 14 | 2 | 355555 | 59.9 | 15.6 |
| 14 | 2 | 363636 | 59.6 | 16.6 |
| 16 | 2 | 76226 | 62.5 | 11.2 |

Los modos CH1 más rápidos redujeron claramente el pintado y aumentaron la demora
de entrega de lotes. El pintado individual se mantuvo cerca de 5 ms; la ingesta
y la decodificación comparten ejecución con la interfaz y requieren optimización.
Estas mediciones cortas no certifican FPS sostenidos ni identifican una causa
única; son sensibles a carga del host, ventana, trigger y modo de análisis.
No se alteró la adquisición de producción. Se restauraron y verificaron los
bits, tasa y generador iniciales tras cada campaña.

[Informe completo](../diagnosticos/resultados_v16/fps_nativos_summary_20261012.json) ·
[Medidor reproducible](../diagnosticos/medir_fps_nativos_v16.py).


### Comparación del slider existente — 12 de octubre de 2026

El slider ya reduce únicamente el dibujo y conserva extremos y cortes. Una
comparación host a ADC8 CH1/1,22 MHz mostró que, con ventana de 1 ms, bajar de
2441 a 625 vértices mantuvo el rasterizado cerca de 5,4 ms. Con 10 ms, pasar de
24427 a 835 vértices redujo ese coste de unos 6,9 a 5,4 ms. Estos tiempos incluyen
QWidget.grab; no equivalen a FPS físicos. La prueba confirma utilidad en ventanas
largas, pero no respalda duplicar el control ni considerarlo solución suficiente.
La repetición con Q preservó la tasa y restauró el estado inicial, pero no observó
eventos de pintado nativo; sus FPS de pantalla quedan explícitamente inválidos.
[Comparación host](../diagnosticos/resultados_v16/slider_dibujo_20261012.json) ·
[Prueba Q y límites](../diagnosticos/resultados_v16/slider_live_20261012.json).


### Camino numérico del host incorporado — 12 de octubre de 2026

El decoder vectoriza el desempaquetado nativo y la GUI recibe bloques numéricos,
sin reconstruir cada muestra como una tupla. Se conservan las comprobaciones de
CRC, secuencia, índice, timestamp, configuración y pérdidas. Grabación, filtros,
mediciones y trigger reciben todas las muestras. Los lectores de diagnóstico
mantienen su interfaz de filas; sin NumPy permanece el camino anterior.

Pasaron 284 pruebas V16 y la comparación del constructor MCU con ambos decoders
para todos los perfiles, incluidos extremos e índices con wrap. La adquisición
real ADC8 CH1/1,22 MHz y ADC10 CH1/909 kHz conservó sus tasas, con ingesta mediana
cercana a 1 ms por lote y demoras p95 de 0,106 y 0,114 ms. El timer de dibujo
rondó 63 llamadas/s. No se observaron eventos de pintado nativo en esa ejecución:
no se presentan esas llamadas como FPS de pantalla. El Q quedó restaurado.
Son ventanas cortas de alrededor de 5 s, con generador a 5 kHz confirmado.
[Prueba real y límites](../diagnosticos/resultados_v16/fps_numeric_20261012.json) ·
[Benchmark de decodificación](../diagnosticos/resultados_v16/decoder_numeric_20261012.json).


### Escala horizontal adaptativa — 12 de octubre de 2026

El dial logarítmico conserva definición para ventanas cortas. El mínimo es ocho
muestras y el máximo es max(250000 muestras, ceil(4 × FS real)), por lo que todos
los perfiles alcanzan al menos 4 s. A 1 kHz se ofrecen 250 s; a 5 kHz, 50 s;
a 40 kHz, 6,25 s. El historial se amplía hasta el máximo visible más 260000
muestras de margen, con base de 510000, y conserva los valores recientes al
redimensionarse. La lectura selecciona µs, ms o s automáticamente.
Al cambiar FS se mantiene la duración elegida —también en modo muestras— salvo
que esté fuera del rango nuevo, en cuyo caso se limita al extremo disponible.

Pasaron 289 pruebas en dos procesos: 62 de FM y 227 restantes. La ejecución
conjunta sufrió un cierre nativo Qt en una prueba FM al procesar eventos; aislada
pasó. Las pruebas nuevas verifican todos los perfiles, conservación de duración,
extremos del dial, resize circular y cuatro segundos completos de historial a
la FS máxima. No se cambió firmware, protocolo ni la tasa del Q.


### Duty de cuadrada continua — 12 de octubre de 2026

Pasaron 292 pruebas V16 y el constructor de tabla DAC.
Se incorporó y desplegó el dial1–99 %, default50 %, conservando frecuencia
y mostrando duty efectivo. A5 kHz los pasos son1 %; a50 kHz son5 %.
El 50 % mantiene el camino de dos puntos. MCU/relay anuncian capacidad de duty;
las configuraciones anteriores siguen representando50 %. Se verificaron ACKs
de siete combinaciones y continuidad ADC, incluido ADC8 CH1/1,22 MHz durante
10 s con cuadrada5 kHz/duty25 %. Se restauró el estado anterior del Q y se
conservó respaldo de la aplicación. No se certificó duty analógico ni margen
prolongado con las tablas nuevas. [Evidencia](../diagnosticos/resultados_v16/duty_live_20261012.json).


### Tasas intermedias y audio — 12 de octubre de 2026

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

[Evidencia](../diagnosticos/resultados_v16/additional_rates_60s_20261012.json) ·
[Estado previo](../diagnosticos/resultados_v16/additional_rates_prior_20261012.json) ·
[Primer intento](../diagnosticos/resultados_v16/additional_rates_wall_gate_failure_20261012.json).
