# FFT y mapa de calor — V10

La columna izquierda se reparte entre GENERADOR y MODOS · ANÁLISIS. Los
controles que no entran en cada mitad se recorren con scroll. La botonera
**V / t**, **FFT** y **Heatmap** reemplaza el gráfico central; se puede volver
al osciloscopio sin desconectar ni cambiar la adquisición.

- **FFT:** espectro del último bloque completo, de 0 a Fs/2.
- **Heatmap:** frecuencia vertical y tiempo horizontal, relativo al último
  bloque; lo reciente aparece a la derecha. La historia se desplaza y recicla.
- **Canal arriba / abajo:** V_IN (A2), V_OUT (A3) o Ninguno. Las selecciones
  espectrales son independientes de las casillas del gráfico temporal.
- **Muestras:** 256–8192; resolución Δf = Fs/N y duración de ventana N/Fs,
  indicadas debajo de los controles.
- **Ventana:** Hann, Hamming, Blackman o rectangular.
- **Escala:** V pico o dBV, con referencia de 1 V pico. Es amplitud espectral,
  no densidad de potencia ni RMS. La ganancia coherente de la ventana se
  corrige; DC y Nyquist no se duplican. Los tonos entre bins pueden tener
  menor pico por fuga espectral.
- **Quitar componente DC:** resta la media del bloque antes de la ventana.
- **Solapamiento:** 0, 50 o 75 %. Para limitar carga y memoria, el mapa usa un
  paso mínimo de 1/30 s y como máximo 512 columnas; el paso efectivo se muestra.
- **Historia:** 2–60 s. La barra de color usa −100 a +10 dBV o 0–3,3 V pico.

STOP congela los gráficos. Los controles de trigger y SINGLE siguen usando
el motor temporal; SINGLE detiene también la actualización espectral. La FFT
es del último bloque de adquisición, no de la ventana centrada en el trigger.
CSV sigue grabando muestras originales. Un cambio de perfil de adquisición
limpia la historia espectral. Los saltos de timestamps invalidan los bloques;
si el procesamiento queda atrás, quedan huecos en el mapa, sin comprimir tiempo.

La simulación Demo usa tiempos de muestreo uniformes de 400 µs, independientes
del jitter del temporizador de la interfaz. La tasa física se obtiene de los
timestamps del bloque; sin timestamps se usa la tasa estimada por el monitor.

Validación local: tonos sintéticos de amplitud y frecuencia conocidas con las
cuatro ventanas; DC/Nyquist; dos canales; STOP; cambio de modo; reciclado de
historia; discontinuidades; Demo. Capturas de interfaz sintéticas:
[FFT actual con relleno](../assets/historico/monitor_v10_fft_actual.png) y
[Heatmap](../assets/historico/monitor_v10_heatmap.png).
La validación física específica de FFT/heatmap sigue pendiente. Bode cuenta
con los ensayos físicos y referencia descritos en su sección y en
[el informe de calibración](../diagnosticos/BODE_V10.md).

Referencias de implementación: [NumPy rFFT](https://numpy.org/doc/stable/reference/generated/numpy.fft.rfft.html)
y [pyqtgraph ImageItem](https://pyqtgraph.readthedocs.io/en/pyqtgraph-0.13.6/api_reference/graphicsItems/imageitem.html).

## Frecuencias logarítmicas y Bode

**Frecuencia logarítmica** transforma el eje X de la FFT y el eje Y del
heatmap. DC queda fuera de la vista logarítmica. La frecuencia mínima visible
es Fs/N; para analizar más abajo hay que aumentar N o reducir Fs. El mapa se
remuestrea sobre una grilla uniforme en log10(f), conservando la historia y
las unidades de color. Las etiquetas usan décadas y, cuando hay espacio, 2 y 5.

El generador ocupa el alto necesario para mostrar todos sus controles sin
scroll lateral; los modos usan el espacio restante y sus opciones sí pueden
recorrerse con scroll.

**Bode** inicia automáticamente un barrido senoidal por pasos logarítmicos si
el Q está conectado y RUN activo. Usa amplitud y offset del generador, y activa
su salida durante la medición. A2 debe medir la entrada del circuito; A3, la
salida. Se muestran dos gráficos: ganancia en dB y fase en grados. El cociente
es complejo: H(f) = V_OUT(f)/V_IN(f); la ganancia es 20 log10(|H|) y la fase
es arg(H). Ambos canales se ajustan simultáneamente a seno, coseno y un nivel
DC usando los timestamps del mismo bloque.

Los controles Bode permiten elegir inicio/final (0,1 Hz–20 kHz), 1–100 puntos por década
y asentamiento (0–60 000 ms), más 1–64 ciclos de medición. El extremo superior debe ser menor a 0,45 Fs.
En cada punto se espera la confirmación APPLIED del Q, después el asentamiento
fijo elegido en milisegundos; finalmente se mide la cantidad de ciclos elegida,
con un mínimo de 32 muestras. Los valores iniciales son 200 ms y tres ciclos. Para tonos lentos se reduce el conjunto usado para el
ajuste, conservando al menos 32 muestras por ciclo; se comprueba continuidad
en todas las muestras recibidas. No se usa el sweep continuo del firmware:
cada paso usa un seno estable, para dar tiempo a que se asiente el circuito.

Durante el barrido quedan bloqueados los ajustes del generador, ADC, Fs,
destino y SINGLE. STOP, cambiar de modo, cancelar, timeout, rechazo del Q,
o discontinuidad terminan el barrido. Una referencia de entrada insuficiente invalida el punto, dejando un hueco,
pero el barrido continúa hasta el final elegido. La salida atenuada no invalida
la ganancia. Con control disponible
se envía la configuración anterior del generador para restaurarla; si era un
sweep/pulso, se reinicia. Al desconectar no se puede garantizar restauración.
Los puntos válidos quedan visibles. **Agregar** conserva la comparación y mide
otra curva, hasta cinco, con los colores de la paleta de entradas. Cada color
identifica la misma medición en ganancia y fase. **Repetir** borra las curvas
anteriores e inicia un nuevo barrido. Durante la medición este botón permite
cancelar; Agregar se habilita al terminar si queda espacio.
Cada curva tiene un relleno translúcido bajo la línea, del mismo color. FFT
también rellena el área bajo el espectro. El relleno tiene opacidad tenue
y no modifica las mediciones. Cada tramo válido se cierra verticalmente;
no se rellena ni se une el área a través de huecos sin lectura.

La calibración instrumental usa un barrido de referencia con A0 conectado
directamente a A2 y A3. El ensayo `verificar_bode_qt_v10.py --calibration`
guarda la referencia en `calibraciones/bode_v10.json` sólo si todos los puntos
son válidos, el CSV es continuo y se restauró la configuración inicial.
Al abrir el monitor, **Corregir con calibración** permite quitar esa respuesta
de ganancia y fase de las curvas. Se interpola en frecuencia logarítmica,
únicamente dentro del rango calibrado y con los mismos bits y tasa ADC. El
contador indica cuántos puntos recibieron corrección. Los resultados internos
y los CSV del diagnóstico conservan la medición original sin corrección.

La amplitud debe permitir medir ambos canales sin saturación. Para circuitos
lentos puede ser necesario aumentar el asentamiento. Esta primera medición de
fase incluye el desfase instrumental del ADC y del circuito de entrada; falta
calibrarlo con A2/A3 conectadas al mismo nodo. No es una medición calibrada.

Validación local ampliada: RC simulado (ganancia/fase), rechazo por señal débil,
espera de confirmación, secuencia de tonos, restauración al terminar/cancelar,
timeout y discontinuidades, más coordenadas FFT/heatmap logarítmicas. Capturas
sintéticas: [Bode](../assets/historico/monitor_v10_bode.png) y
[Heatmap log](../assets/historico/monitor_v10_heatmap_log.png). Validación física pendiente.

Referencia para la representación de ganancia y fase:
[SciPy Bode](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.bode.html).

## Validación física de Bode

Ensayo del 3 de octubre: ocho frecuencias de 2 a 100 Hz, ADC 16 bits / 31,25 kHz,
461 470 filas CSV sin discontinuidades y restauración exacta del generador de
79 Hz y códigos DAC 310/4033. [Informe y capturas](../diagnosticos/BODE_V10.md).
La prueba no calibra el desfase instrumental y no cubre todo el rango de Bode.

## Escalas FFT y densidad del barrido

Los modos usan botones luminosos exclusivos; las opciones DC, frecuencia
logarítmica y escala compartida usan el tick neutro de los canales. **Misma escala en ambos canales** enlaza X/Y de los dos gráficos FFT
y calcula una escala de amplitud común. Desmarcado, cada canal ajusta Y por
separado. La escala automática deja un 15 % de margen (mínimo 3 dB o 5 mV),
crece si la señal se acerca al borde y sólo se contrae después de tres segundos
con un rango inferior al 60 % del actual. Cambiar los parámetros reinicia ese
ajuste.

Bode usa **Puntos / década**: 10 produce un paso de 0,1 década; se incluyen
ambos extremos y el final exacto de rangos parciales. Los comandos se redondean
a 1 mHz y se eliminan frecuencias repetidas. Antes de empezar se confirma el
texto editado en los campos. El eje X abarca siempre el rango solicitado,
aunque haya puntos inválidos. No se reemplazan por una ganancia ficticia.

Cada frecuencia medida tiene un marcador en la curva. Con 10 puntos por década
hay 10 intervalos tanto entre 20–200 Hz como entre 200–2000 Hz y 2000–20 000 Hz;
el espaciado visual es uniforme con el eje X logarítmico. El panel muestra
cuántos puntos de ganancia y fase se obtuvieron sobre el total previsto. Una
fase indeterminada puede dejar un hueco en su curva sin quitar el punto de
ganancia correspondiente.

Ensayo físico ampliado: rango 2–1000 Hz, dos puntos por década, siete tonos,
seis puntos válidos y uno inválido por ruido a 1 kHz; 528 755 filas CSV sin saltos
y restauración exacta. [Evidencia](../diagnosticos/resultados_usb/20261003_022037_325268_bode_qt_v10.json).

## Salida muy atenuada y eje de Bode

La salida cercana a cero es una medición válida: la ganancia usa la amplitud
de su componente al tono de ensayo sin un umbral mínimo fijo de salida. Una
salida constante (incluido su nivel DC) registra ganancia cero, equivalente a
−∞ dB. Para poder verla en un gráfico finito se dibuja en un piso visual de
−160 dB o menor, indicado en el título; el resultado original conserva −∞.

La fase se deja indeterminada si no hay tono de salida o su amplitud no supera
tres veces la incertidumbre estimada del ajuste. Esto no descarta la ganancia.
Con ruido, la ganancia es una estimación de la componente del tono, no una
demostración de salida exactamente cero. La entrada A2 debe seguir siendo una
referencia medible para formar el cociente.

Bode tiene su propio check **Eje X logarítmico**, activado inicialmente. Cambiarlo
sólo modifica la presentación (lineal/log); conserva resultados y barrido.

## Asentamiento separado de la medición

**Asentamiento** admite 0–60 000 ms: es la espera fija antes de medir cada tono,
sin agregar automáticamente tres períodos. **Ciclos a medir** admite 1–64,
con tres como valor inicial. Más ciclos integran durante más tiempo; circuitos
lentos o resonantes pueden requerir un asentamiento mayor. No se detecta
automáticamente el fin del transitorio en esta versión.

El tiempo mínimo por punto es `asentamiento_ms/1000 + max(ciclos/f, 32/Fs)`.
El panel suma estos tiempos para los puntos por década elegidos y aclara que
se agregan comunicación y entrega de muestras. Los cambios de perfil ADC
actualizan la estimación. Ambos controles quedan bloqueados mientras se mide,
y el timeout contempla el tiempo elegido incluso en frecuencias muy bajas.

Ejemplo: a 0,1 Hz, con 200 ms y tres ciclos, el mínimo es 30,2 s, frente a los
110 s del esquema anterior. No implica que 200 ms sea suficiente para cualquier
circuito. La validación nueva es local: independencia de asentamiento y
frecuencia, ciclos, mínimo de muestras, estimación y timeout. Los ensayos
físicos anteriores corresponden a los tiempos indicados en sus informes.
