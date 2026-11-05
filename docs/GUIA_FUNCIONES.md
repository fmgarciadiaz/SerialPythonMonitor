# Guía de funciones

[Volver a la presentación](../README.md) · [Especificaciones y límites](CAPACIDADES.md) · [Índice técnico](README.md)

Esta guía explica los controles en términos de uso. Las imágenes de la landing
son demostraciones; consultá [validación y límites](VALIDACION_CIERRE.md) y los
informes enlazados en el índice técnico para conocer evidencia y condiciones.

<a id="vt"></a>

## V(t)

La vista temporal muestra voltaje frente a tiempo para CH1 y CH2. Ajustá la
escala y posición para encuadrar la señal; RUN actualiza la vista, STOP la
congela y SINGLE espera un evento. El trigger ayuda a que una forma repetitiva
quede estable. Las mediciones automáticas incluyen máximos, mínimos, pico a
pico, RMS, promedio y frecuencia estimada.

[Controles y adquisición](../monitor/v20/README.md) · [Cableado y entradas](UNO_Q_TECNICO.md)

<a id="fft"></a>

## FFT

La vista espectral ayuda a reconocer frecuencias presentes en una señal.
Spectrum muestra amplitud, Power presenta potencia, Distortion estima armónicos
y Transfer compara canales. Tamaño de bloque, ventana y escala cambian la
lectura; la resolución depende de la frecuencia de muestreo y del tamaño FFT.

[Modos, unidades y límites](FFT_ANALISIS.md) · [Controles del monitor](MONITOR_TECNICO.md)

<a id="heatmap"></a>

## Heatmap

El heatmap apila espectros sucesivos: frecuencia ocupa un eje, tiempo el otro y
el color representa amplitud. Sirve para reconocer barridos, tonos persistentes
y transitorios. La duración visible depende de la configuración de historia.

[Análisis y controles](MONITOR_TECNICO.md)

<a id="bode"></a>

## Bode

Bode compara una señal de referencia X con una respuesta Y. Presenta ganancia y
fase según la frecuencia. Los modos Tonos, Pulso y Sweep/Chirp permiten medir
respuesta estable, transitorio o barrido; elegí las fuentes en el panel antes
de iniciar la captura. Una curva útil requiere señales con nivel suficiente.

[Descripción técnica y límites](MONITOR_TECNICO.md) · [Cableado de dos canales](UNO_Q_TECNICO.md)

<a id="generador"></a>

## Generador

El generador entrega señales en A0. Seleccioná seno, cuadrada, triángulo o
rampa; ajustá frecuencia, amplitud y offset dentro del rango del DAC. Sweep,
Chirp y Pulso sirven para explorar la respuesta del circuito. Los máximos
configurados y sus condiciones están en [capacidades](CAPACIDADES.md).

[Controles y formatos](../monitor/v20/README.md) · [Especificaciones](CAPACIDADES.md)

<a id="wav"></a>

## WAV

El monitor puede registrar CH1 y CH2 como audio estéreo y reproducir un archivo
por A0 en mono. Para reproducirlo, elegí L, R o Mix y ajustá amplitud y offset.
La reproducción usa el DAC del Q, no los parlantes de la computadora.

[Uso del monitor](../monitor/v20/README.md) · [Tasas y ensayos](WAV_TASAS.md)

<a id="synth"></a>

## Synth

Synth genera audio por A0 y puede tocarse desde MIDI o desde Play. Los presets
incluyen síntesis FM y modelos virtuales; los controles de timbre y envolvente
permiten modificar el sonido. La continuidad física depende de la configuración
de adquisición y transporte.

[Controles](../monitor/v20/README.md) · [Motor y modelos](SYNTH.md)

<a id="radio"></a>

## Radio

Radio procesa una entrada de CH1 para sintonizar y demodular AM. El panel ofrece
búsqueda de emisoras, sintonía y ganancia manual o automática. Generador Radio
puede enviar el audio demodulado a A0; las capturas de la landing son simuladas.

[Uso y controles](../monitor/v20/README.md) · [Antena y recepción](MONITOR_TECNICO.md)

<a id="filter"></a>

## FILTER

FILTER procesa CH1, CH2 o la señal de Radio. La vista permite comparar la señal
original con la filtrada; elegí una fuente y un preset según la interferencia o
banda que quieras atenuar. En OFF el procesamiento queda desactivado.

[Controles y fuente de entrada](../monitor/v20/README.md) · [Arquitectura del monitor](MONITOR_TECNICO.md)
