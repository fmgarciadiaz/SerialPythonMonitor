# Monitor V16

V16 implementa el paso 1 de la Etapa II: dos señales **CH1 (A2)** y
**CH2 (A3)**, con firmware, relay y monitor V16 coordinados mediante
**protocolo 4**. Cada bloque transporta un timestamp base y un período;
el receptor reconstruye los tiempos de cada muestra y conserva su índice.
V16 incorpora cinco perfiles nativos CH1 y nueve duales, con validación física
y firmware/relay coordinados. Las secciones fechadas conservan los ensayos
previos; las opciones vigentes se resumen en la tabla siguiente.

La interfaz conserva trigger, SINGLE, medidas, FFT, heatmap, Bode, generador
A0, WAV y el motor Synth con sus instrumentos, MIDI y controles.
El panel [Filtro digital](../../docs/FILTROS_V16.md) reemplaza la selección de canales. FILTER se puede mostrar en V(t), FFT y heatmap; Bode/Transfer permiten elegir referencia y respuesta entre CH1, CH2 y FILTER.

## Inicio

```sh
conda activate Python_3_13_DataScience
python monitor/v16/app.py
```

Para otro entorno: `conda env create -f monitor/v16/environment.yml`.
Se requiere PyQt6; las versiones Qt5 históricas deben ejecutarse por separado.

Conectar comprueba la app V16. La pareja V16 está instalada actualmente en el Q. **Preparar Q** ejecuta la preparación con
`--firmware v16`, instala app/MCU/relay y guarda un respaldo de la app existente.
La preparación modifica el Q y requiere su confirmación en la interfaz.
No hace falta cargar V16 para usar Demo o las pruebas locales.

### Frecuencias de adquisición disponibles · 12/10/2026

Todas las tasas son **por canal**, en **kHz**. En dual se capturan CH1 y CH2
por disparo; en CH1 sólo A2. Se muestran tres decimales cuando hace falta para
identificar la tasa en Hz enteros; la tasa efectiva depende del período aplicado.

| Salida / resolución | Tasas dual comunes (kHz) |
| --- | --- |
| SPI y UART · 8/10/12/14/16 bits | 1; 2; 4; 5; 8; 10; 12,500; 15,625; 20; 25; 31,250 |
| Sólo SPI · 8/10/12/14/16 bits | 40; 50; 62,500; 66,666; 71,428 |
| Sólo SPI · 8/10/12/14 bits | 100; 125; 200; 250; 333,333 |

| Bits | CH1 · sólo SPI (kHz) | Dual adicional · sólo SPI (kHz) |
| --- | --- | --- |
| 8 | 1118,881 ✓; 1203,007; 1221,374 | 597,014 ✓; 632,411 |
| 10 | 909,090 ✓ | 495,356; 519,480 |
| 12 | — | 410,256; 437,158 |
| 14 | 599,250; 661,157; 701,754 ✓; 747,663 | 355,555 ✓; 363,636 |
| 16 | — | 76,226 ✓ |

**✓**: perfil nativo con margen de envío ≥10%, cola máxima menor de cuatro y
margen positivo antes de sobrescritura, confirmado también en producción.
ADC10/495,356 y ADC12/410,256 kHz conservan integridad pero midieron 9,03% y
9,39% de margen integrado; no llevan esta marca.

UART conserva dos canales y un máximo de 31,250 kHz. En **Synth**, SPI limita
la adquisición a **40 kHz** y UART a **31,250 kHz**; los perfiles CH1 y dual
nativos altos no se ofrecen en ese modo. El selector filtra por resolución,
salida y Synth. Los perfiles heredados conservan la evidencia y límites de sus
ensayos; disponibilidad en el selector no equivale a certificación analógica.

[Contrato y tabla de referencia](../../docs/CONFIGURACION_ADQUISICION.md#perfiles-de-adquisición) ·
[Resultados físicos](../../experimentos/maxfreq_dual_v16/RESULTADOS.md#incorporación-a-producción-completada).

## Datos y análisis

CH1 y CH2 se expresan en voltios. Los códigos ADC dejan de ser canales de
historial, selección, medición y exportación. Índice y tiempo permanecen como
metadatos para trigger, continuidad, análisis y CSV. CSV contiene las columnas
`Muestra,Tiempo_us,CH1,CH2,FILTER`; WAV convierte ambas señales a PCM y detiene la
grabación si detecta discontinuidades de índice o tiempo.

Bode y Transfer usan la relación **respuesta Y / referencia X**, seleccionable entre CH1, CH2 y FILTER. La calibración sólo se ofrece para CH2/CH1. V16 no incluye referencias
Bode históricas: las mediciones se muestran sin corrección hasta obtener una
referencia propia que coincida con instrumento, método y perfil de adquisición.
La calibración instrumental copiada del Synth no constituye una calibración Bode.

El Piano Virtual refuerza el golpe inicial en graves y medios durante los
primeros 120 ms; conserva la subida y las pérdidas modales calibradas, y no
modifica Do5 ni registros superiores. Es un ajuste de sonoridad, pendiente de
validación auditiva, no una nueva calibración física. Comparaciones locales:
`diagnosticos/resultados_piano/revision_ataque_v16/*_aplicado.wav`.

Synth: Config contiene el volumen máximo en Vpp con perilla de color variable.
Cada Osc tiene su mezcla independiente de 0 a 100 %, previa al volumen máximo;
los presets conservan su balance anterior. Piano Virtual suma 6 % de ganancia y
un refuerzo adicional leve del ataque grave/medio. Hasta 11 voces: al cambiar
un acorde, el motor reserva todos sus lugares reciclando primero voces que ya
no están solicitadas; MIDI descarta las notas más antiguas sostenidas sólo por
pedal antes que las teclas presionadas. Las voces disponibles no dependen de
la cantidad de osciladores. Ensayo local de 11 voces (100 bloques por tasa):
máximos de 5,1 ms a 20 kHz y 6,4 ms a 40 kHz, sin saturación de códigos DAC.
Esto no reemplaza la validación física por USB; 40 kHz sigue experimental.

Piano Virtual: liberación del preset de 220 a 550 ms para conservar una cola
audible al levantar la tecla. La caída de cuerda permanece en 4 s; los
parciales superiores reciben hasta 12 % más amplitud y 6 % más duración,
gradualmente desde el tercer parcial. Se conservan el martillo y la subida.
Es un ajuste de sonoridad: las referencias locales no incluyen una liberación
aislada comparable. Audios antes/después y mediciones en
`diagnosticos/resultados_piano/revision_cola_v16/`; escucha pendiente.

La resonancia de liberación se identificó después con las capas separadas
Salamander: T60 aproximado de 2,16/1,88/1,62 s en Do3/Do4/Do5. El cuerpo
compartido conserva una cola débil al cerrar la tecla sin ocupar nuevas voces,
con transferencia gradual y nivel relativo ajustado a las capas reales.
El ataque y la nota sostenida quedan iguales. El pedal difiere esa cola hasta
levantarse; repetir una tecla recicla su cola. No se reproducen samples en el
motor. Es un modelo reducido, no la reproducción íntegra del instrumento SFZ.
Método y límites: `diagnosticos/referencias_piano/liberacion/README.md`.

Eficiencia Synth: MIDI se entrega por señal de llegada y publica una sola
actualización por tanda. La caída normal de 5 a 4 bloques de audio ya no
infla la cola a 7; se mantiene protección ante atraso real. El ataque usa
convolución exponencial recurrente equivalente a la FFT previa, y las colas
compartidas fusionan resonancia/fade en un kernel compilado. Cache de bancos
ampliada para evitar reconstruir filtros al alternar notas.
Benchmark A/B local: mediana de ataque 1,71 → 0,65 ms a 20 kHz;
53 colas 0,80 → 0,22 ms. Diferencias de audio del ataque inferiores a
4e-16; continuidad y sonido conservados. Reproducir con
`diagnosticos/benchmark_synth_v16.py`; resultados en
`diagnosticos/resultados_piano/eficiencia_v16/`.
La cola mínima continúa en 120 ms a 20 kHz y 192 ms a 40 kHz:
estas optimizaciones no prueban una latencia física total nueva.

Virtual compacto: ancho local de 249 a 212 px, Sala/Cola en dos columnas.
El cuerpo resonante compartido y la sala se preparan antes de BEGIN,
sin avanzar notas ni muestras; la generación conserva el audio exacto.
Ensayo físico headless de 30 s, 11 voces/pedal simulado a 20 kHz/ADC100:
sin cortes, pero target5 creció a7; generación máxima32,4 ms, ACK38,7 ms,
gap56,8 ms. Aún no habilita reducir cola. Q restaurado a ADC14/40 kHz,
salidas apagadas. Evidencia `20261010_044206_cola_fisica.json` en la carpeta
de eficiencia; no incluye interfaz ni latencia acústica.
Reposición Synth: llena hasta dos créditos disponibles por llamada, antes
de otra lectura de red. Durante Synth, los eventos se atienden trama por
trama para reponer al recibir ACK sin esperar la decodificación del lote ADC.
Se preservan orden, validaciones y todos los ACK de control del lote.
Fuera de Synth se conserva la decodificación de lote completo.
La reposición respeta target, capacidad y serialización de WAV
de archivo/BEGIN/PLAY/STOP. Diagnósticos agregan `max_chunk_generation_ms`,
`max_socket_send_ms` y `max_send_to_ack_ms` (ACK incluye transporte y Q).
El mínimo de cola sigue en 5/16 bloques a 20/40 kHz, pendiente de ensayo
físico para reducirlo. No se amplió la ventana de dos bloques en vuelo.
Filtro de deformación longitudinal del piano: recurrencia compilada en lugar
de preparar lfilter por voz/bloque. Los filtros SOS del ruido de ataque
también usan un kernel compilado equivalente a SciPy (tolerancia1e-12),
con coeficientes y firma preparados al arrancar. A/B local ataque completo
20kHz: mediana0,67 → 0,26ms, p952,70 → 0,77ms. Evidencia adicional:
`diagnosticos/resultados_piano/eficiencia_v16/attack_filter_ab.json`.
A/B local filtro longitudinal 480 muestras: 16,1 → 2,3 µs;
equivalencia con SciPy y continuidad verificadas a 1e-12. Resultado en
`diagnosticos/resultados_piano/eficiencia_v16/strain_ab.json`.
Sólo sus seis diales recorren verde → azul → violeta; los demás conservan
su esquema previo. El eje temporal actualiza su etiqueta sólo si cambia:
A/B Qt offscreen con 250 mil muestras, mediana 16–17 → 7–9 ms/frame.
Con revisión Astra: parseo MIDI por tandas sin copiar repetidamente el backlog,
decodificación ADC con continuidad en fronteras y comprobación de todas las
muestras, y niveles DAC constantes sin crear rampas innecesarias.
Diagnósticos FM incluyen tiempos host MIDI→Qt y control→inicio de render;
excluyen cola DAC y latencia acústica. Evidencia y benchmarks en
`diagnosticos/resultados_piano/eficiencia_v16/latencia_host.json` y
`qt_eje_ab.json`; script `diagnosticos/benchmark_latencia_host_v16.py`.

Los perfiles heredados son opciones candidatas, no evidencia de rendimiento.
La aceptación requiere pruebas con placas, continuidad de datos y restauración
del perfil anterior. V15 permanece independiente como referencia previa.

Ensayo físico inicial completado: 120 s por perfil ADC14/40 y 125 kHz, ADC16/62,5 kHz, sin pérdidas ni errores; WAV20/40 con ADC14/100 kHz completo. V16 quedó activa en el Q a ADC14/40 kHz y salida apagada. Ver límites y evidencia en el informe Etapa II.

Perfiles ADC14 de **200 y 250 kHz** disponibles como experimentales en V16, con captura temporal conservada. Ambos pasaron 120 s de integridad; WAV concurrente a ADC250 falló. Ese ensayo inicial limitaba el audio a ADC100 y ADC16 a 62,5 kHz;
los límites actuales de Synth y las tasas disponibles figuran en la tabla superior. [Evidencia y límites](../../docs/ETAPA_II_V16.md#tasas-altas-con-dma-temporal--9-de-octubre-de-2026).

Optimización adicional del synth: rampas y fase usan funciones compartidas
en lugar de crear dos funciones con cierres por voz y bloque. El cálculo y
las transiciones se conservan. `diagnosticos/benchmark_alloc_synth_v16.py`
compara con una copia previa de fm_source.py (argumento obligatorio), con
11 voces, cambios de acorde y pedal, piano/FM y20/40kHz; exige códigos DAC
idénticos. El benchmark es de host, no mide latencia acústica o transporte.

En modo Synth, la adquisición ADC queda limitada a40kHz. Al entrar desde
una tasa mayor se selecciona40kHz y se aplica por el flujo normal de
configuración; Play espera la confirmación del Q. Las tasas menores siguen
permitidas. Al salir se recupera la tasa anterior si había sido reducida,
y su aplicación espera que termine el audio. Los límites UART/ADC16 siguen
vigentes. La tasa DAC de Synth se elige por separado y no cambia por este
límite ADC. `tests/v16/test_synth_adc_limit.py` cubre selección/restauración
y bloqueo de Play mientras el cambio de adquisición está pendiente.

Optimización de piano (10/10/2026): la normalización constante de las reflexiones se calcula una vez por bloque. Salida, buffer, posición y códigos DAC conservados exactamente; benchmark calentado ABBA del kernel 0,108→0,033 ms. Cola experimental de cuatro bloques validada cinco minutos en owner separado; no cambia la cola de la GUI.

Optimización común de instrumentos: cachés acotadas e inmutables para curvas del limitador y del filtro; evitar transiciones y rampas constantes repetidas. Los 13 presets conservan exactamente 2.246.400 códigos DAC en pruebas a20/40kHz. 72 tests pasan. La cola GUI no se reduce: target4 exigió crecer a8 en guitarra/Brass y produjo UNDERRUN en DX Brillo.

Guitarra/Brass: coeficientes de cuerda con caché acotada y PolyBLEP de sierra/cuadrada en kernel Numba sin fastmath. DAC exacto; benchmark calentado ABBA a20kHz: guitarra -5,8% y Brass -52,7% en mediana de generación. 93 tests pasan. Ensayos de120s por instrumento sin cortes, pero requirieron cola adaptativa mayor; no cambia la cola de la GUI.

Segunda mejora guitarra/Brass: interpolación de cuerda precalculada por delay, filtros SOS directos y eliminación de arrays de fase que no se usan, preservando estado final. ABBA adicional a20kHz: guitarra -24,5%, Brass -19,2% en cálculo. Muestras/estados exactos y warmup previo a BEGIN. La política de lectura y la cola GUI permanecen iguales: los ensayos detectan pausas de lectura/reactivación independientes del cálculo.

### Transferencia ADC14 integrada (10/10/2026)

ADC14 usa ahora empaquetado sin pérdida: cuatro valores de 14 bits en siete bytes,
258 pares por trama y ocho tramas por nodo de 2048 pares. El receptor acepta también
las tramas anteriores de 226 pares; ADC8/10/12/16 conservan ese formato. MCU y relay
se actualizan juntos mediante `tools/prepare_q.py --firmware v16`.

Se integra CRC slicing-by-8 y preparación que limpia sólo el padding, sin retirar
CRC, secuencias, épocas ni validación DMA temporal. No se incluye la telemetría TDG2
del experimento. La interfaz ofrece **333,3 kHz** (período entero de
3 µs); 16 bits conserva el límite de 62,5 kHz y synth conserva ADC ≤40 kHz.
La evidencia de transporte no certifica precisión analógica ni la respuesta de una
fuente de alta impedancia. Ensayo reproducible de compatibilidad de codecs:
`python diagnosticos/verificar_adc_integrado_v16.py`.

Validación de la versión integrada en el Q: ADC14/250 kHz y ADC14/333,3 kHz,
120 s cada uno, 29.982.962 y 39.976.718 pares respectivamente, cero pérdidas y
cero errores. ADC8/10/12/16 a 62,5 kHz y ADC14 a 31,25 kHz también pasaron.
Con ADC40, WAV20 y WAV40 completaron 100.000 y 200.000 puntos sin underrun.
Se restauró ADC14/250 kHz y el generador previo apagado; firmware integrado activo.
[Evidencia](../../diagnosticos/resultados_v16/20261010_235156_tasas_altas.json).

### CH1 rápido integrado (11/10/2026)

Elegir **599,25 kHz (CH1)** o **661,16 kHz (CH1)** en TASA, con **SPI** y **14 bits**.
Captura sólo A2 / CH1. CH2 se deshabilita en gráficas y selectores, y vuelve a estar
 disponible al regresar al modo de dos canales. ADC12/16 y UART no admiten este
perfil; synth conserva su límite ADC40.

TIM2/TIM5 usan ticks de 160 MHz, con períodos de 267 ticks (599250,936 Hz reales) o 242 ticks (661157,025 Hz reales).
Tipo 16 transporta cuatro muestras ADC14 en siete bytes, hasta 516 muestras por
trama; tipo 3 y tipo 15 siguen disponibles. El receptor verifica continuidad en
ticks antes de convertir a microsegundos. La GUI mantiene tiempo continuo en CH1
rápido, incluido el desbordamiento de TIM5 cada 26,84 s. CSV de este modo contiene
CH1/FILTER y tiempo en microsegundos; WAV se graba mono. CH2 ausente no se presenta
como una entrada medida a cero voltios. Mediciones y espectro conservan la escala
temporal. El modo sigue experimental hasta validar precisión/impedancia analógica.

`diagnosticos/verificar_ch1_integrado_v16.py` verifica cambios entre modos, captura
sostenida, conversión temporal y restauración del perfil previo.

La integración pasó cambios entre uno/dos canales, ADC12 y ADC16; CH1 rápido sostuvo
120 s con 71.866.884 muestras sin pérdidas ni errores. El worker real y Qt procesaron
5,7 millones de muestras en cada prueba de conexión y reconexión, sin errores.
[Resultados](../../diagnosticos/resultados_v16/ch1_integrado.json).

Después de los cambios de modo, WAV20/WAV40 con ADC40 completaron 100.000/200.000
puntos sin underrun. Se conservó ADC14/333333 y generador previo apagado.

FFT en CH1 rápido (11/10/2026): los modos FFT podían restaurar una selección CH2
antigua y rechazar también el análisis válido de CH1, porque CH2 no se adquiere.
Los controles espectrales vuelven a comprobar qué canales están disponibles y
el análisis omite canales sin muestras finitas. Spectre/Power/Distort conservan
CH1; el selector de estadísticas tampoco repone CH2 al cambiar de modo.
Prueba con señal de 20 kHz y wrap de timestamps, 23 pruebas FFT y prueba Qt/Q real
con 5.712.388 muestras, 351 lotes y espectro CH1 válido sin errores.

La integración de 661,16 kHz pasó 120 s con 79.290.884 muestras, cero pérdidas y
cero errores; también pasaron los cambios a 599,25 kHz, dual ADC12 y dual ADC16.
La GUI con worker real procesó 6.296.068 muestras y produjo FFT de CH1 sin errores.
Se restauró ADC14/599,25 kHz con el generador apagado; firmware integrado activo.
[Adquisición](../../diagnosticos/resultados_v16/ch1_661_integrado.json) y
[GUI/FFT](../../diagnosticos/resultados_v16/ch1_661_gui_fft.json).

### ADC16 a 66,67 kHz (11/10/2026)

El selector omite «experimental» y muestra las tasas de un canal como «(CH1)».
ADC16 con ambos canales admite 66,67 kHz por SPI (15 µs entre pares), manteniendo
oversampling ×16 y desplazamiento de dos bits. UART conserva 31,25 kHz y synth ADC40.
A 50 MHz, las 32 subconversiones de ambos canales requieren al menos 14,08 µs
con ventana de cinco ciclos y conversión ADC14 de 17 ciclos; no se habilita 100 kHz.
Fuente: [STM32U585, tabla ADC1](https://www.st.com/resource/en/datasheet/stm32u585ri.pdf).

Pasó 120 s con 7.993.570 pares, cero pérdidas y errores, cambios de modo y FFT con
worker real. Se restauró el perfil previo ADC16/62,5 kHz y generador apagado.
La prueba valida continuidad digital; no certifica precisión analógica.
[Adquisición](../../diagnosticos/resultados_v16/adc16_66667_integrado.json) y
[GUI/FFT](../../diagnosticos/resultados_v16/adc16_66667_gui_fft.json).

### ADC16 a 71,43 kHz con ambos canales (11/10/2026)

El reloj compartido ADC/DAC se configura una vez al arranque a 54 MHz
(PLL2 HSE/2 ×27 /4), dentro del máximo ADC1 de 55 MHz especificado por ST.
No se cambia el PLL durante la reproducción. TIM2/TIM5 mantienen sus relojes y
las tasas de captura previas. La ventana ADC se muestra usando el reloj de 54 MHz.
ADC16 incorpora 71,43 kHz por SPI (14 µs entre pares), conservando dos canales y
oversampling ×16. UART sigue limitado a 31,25 kHz; synth mantiene ADC40.
En 16 bits, el desplegable oculta todas las tasas incompatibles con la resolución,
la salida y el modo synth. Al salir de 16 bits reaparecen las opciones anteriores.

Pasaron 120 s con 8.564.736 pares, cero pérdidas/errores, cambios de modo y FFT real.
ADC14/200, 250, 333,33, 599,25 y 661,16 kHz pasaron ensayos de 10 s con el nuevo PLL.
WAV20/WAV40 con ADC40 completaron 100.000/200.000 puntos sin underrun.
Se restauró el perfil previo ADC16/66,67 kHz y generador apagado.
La validación es de integridad digital; no acredita precisión analógica.
[ADC16](../../diagnosticos/resultados_v16/adc16_71428_integrado.json),
[GUI/FFT](../../diagnosticos/resultados_v16/adc16_71428_gui_fft.json),
[tasas y audio](../../diagnosticos/resultados_v16/20261011_113725_tasas_altas.json).
Fuente de límites: [STM32U585, tabla 105](https://www.st.com/resource/en/datasheet/stm32u585ri.pdf).

### CH1 ADC8 a 1,203 MHz (11/10/2026)

Integrado por SPI como «1203,0 kHz (CH1)»: ADC8 nativo, período de 133 ticks
a 160 MHz y nodos de 3.584 muestras en cuatro tramas (904/904/904/872).
Los perfiles anteriores conservan nodos de 2.048 muestras. Se mantienen CRC,
continuidad de índice/timestamp, época y rechazo de dropped/fatal. El cálculo
de posición dentro del nodo admite el desborde de índice de 32 bits; probado
en el decoder Python y el validador C.

Pasaron 62 tests locales. La integración cargada en el Q sostuvo 120 segundos
con 144.273.920 muestras, dropped=0 y fatal=0; también pasaron transiciones
ADC14/333333 → ADC8/1203007 → ADC14/661157 → ADC8/1203007 → ADC16/71428
→ ADC14/250000. La GUI en modo offscreen con worker real procesó 11.480.456
muestras en 257 lotes y produjo FFT CH1 sin errores.
Se restauró ADC16/71428 por SPI y el generador apagado con su configuración guardada.
[Adquisición](../../diagnosticos/resultados_v16/megaboom_integrado.json) y
[GUI/FFT](../../diagnosticos/resultados_v16/megaboom_gui_fft.json).

Estos ensayos validan integridad digital y funcionamiento de FFT. Quedan pendientes
ocupación de cola y margen por nodo, precisión analógica y aceptación visual,
trigger, SINGLE y exportación con este perfil. No certifican estabilidad indefinida.

## Perfiles dual incorporados, 12/10/2026

TASA muestra los perfiles nuevos como **(CH1+CH2)** y los filtra por bits y
SPI/UART/Synth. Tasas por canal:

| Bits | Tasas dual nuevas (kHz) |
| --- | --- |
| 8 | 597,01 y 632,41 |
| 10 | 495,36 y 519,48 |
| 12 | 410,26 y 437,16 |
| 14 | 355,56 y 363,64 |
| 16 | 76,23 |

Los nueve perfiles pasaron aceptación aislada 60 + 3×120 + 600s y otros120s por
perfil en producción, con ambos canales, tiempos NumericBatch y transiciones
correctos. Se conservaron los cinco perfiles CH1. Margen integrado ≥10% sólo
validado en dual ADC8/597,01, ADC14/355,56 y ADC16/76,23; los tooltips de los
otros perfiles indican que no tienen margen validado. ADC10/495,36 y
ADC12/410,26 conservan integridad pero midieron9,03% y9,39% de margen integrado.
[Evidencia, RAM y restauración](../../experimentos/maxfreq_dual_v16/RESULTADOS.md#incorporación-a-producción-completada).
Reiniciar el monitor para cargar la whitelist actualizada.

## Perfiles CH1 máximos validados, 12/10/2026

Se incorporaron ADC8 a 1,221 MHz y 1,119 MHz, ADC10 a 909 kHz y ADC14 a
748 kHz y 702 kHz. Los perfiles de 1,119 MHz, 909 kHz y 702 kHz también
aprobaron el criterio de margen de envío y cola. Los formatos anteriores siguen
disponibles; WAV conserva sus 16 bloques.

Cada perfil pasó 60 s + tres arranques de 120 s + 600 s en la variante de
medición, y otros 120 s con firmware, relay y receptor de producción,
incluida la conversión de timestamps. No se detectaron pérdidas ni errores.
Precisión analógica, asentamiento y FPS GUI no están certificados por esas pruebas.

[Tabla, parámetros y evidencia](../../experimentos/maxfreq_v16/RESULTADOS_CH1.md).
