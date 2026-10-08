# Análisis espectral de dos entradas

[Proyecto](../README.md) · [Monitor](../monitor/historico/v14/README.md)

Los cuatro análisis utilizan muestras de A2/V_IN y A3/V_OUT. No generan señales
por sí solos: para Transfer se necesita excitar el circuito con una señal que
cubra la banda que se desea medir. Bode por tonos, pulso o sweep conserva sus
controles y referencias independientes.

Las estadísticas se presentan en el panel inferior «Medición», seleccionando
V_IN o V_OUT. Transfer muestra la relación fija OUT / IN. Los tooltips incluyen
picos y armónicos completos. Power muestra RMS de banda, potencia de banda,
piso en dB re 1 V²/Hz, SNR y las tres potencias de bandas fijas.

## Ventana, resolución y unidades

Una ventana de N muestras a Fs tiene duración N/Fs y separación de bins
Δf = Fs/N. Más muestras mejoran la resolución y aumentan la duración necesaria.
Quitar DC resta la media del bloque; no modifica el registro CSV original.

Para `X = rfft(w*x)` se aplica factor unilateral c=2 en bins interiores y c=1
en DC y Nyquist cuando N es par:

- Magnitud pico: `c*abs(X)/sum(w)`, en V pico.
- PSD: `c*abs(X)**2/(Fs*sum(w*w))`, en V²/Hz.
- Densidad cruzada: `c*conj(X)*Y/(Fs*sum(w*w))`.
- Ancho equivalente de ruido: `ENBW = Fs*sum(w*w)/sum(w)**2`.

La escala logarítmica de magnitud usa 20 log10 respecto a **1 V pico**;
no equivale a dBV RMS. La PSD usa 10 log10 respecto a 1 V²/Hz.
Los promedios de densidades se realizan en escala lineal, nunca promediando dB.

## Spectre

Muestra magnitud o fase de cada canal, máximos locales y frecuencia dominante.
La magnitud combina en RMS las amplitudes pico de los segmentos seleccionados;
la fase usa el último bloque, sin promediar ángulos.
La fase se refiere al inicio del bloque, no a un reloj externo; un seno continuo
puede cambiar de fase entre bloques. Sólo se muestra donde hay señal suficiente.
La estimación entre bins de la frecuencia dominante no mejora la capacidad de
separar dos tonos próximos; la resolución de la ventana sigue siendo relevante.

## Power

La PSD describe cómo se distribuye el valor cuadrático de tensión por frecuencia.
La potencia de una banda es `sum(PSD)*Δf`, en V², y su raíz es tensión RMS.
Se integran los bins seleccionados, incluidos DC/Nyquist cuando corresponde.
Para calcular watts o dBm sería necesario especificar una impedancia.

Se muestran la banda configurable y las bandas fijas 20–200 Hz, 200–2000 Hz
y 2000 Hz–Nyquist, limitadas por el muestreo. El piso se estima con la media
de PSD fuera de los cinco picos más fuertes y sus tres bins vecinos a cada lado.
Es una estimación del residual, no una calibración del ruido del ADC.

El piso de ruido y SNR son estimaciones bajo un modelo de tono más ruido.
SNR compara la fundamental con el residual, retirando los armónicos analizados.
Sin fundamental identificable se indica que la métrica no está disponible;
la PSD y la potencia siguen siendo útiles. La banda, ventana y ruido del propio
ADC condicionan los resultados.

## Distort

Las marcas naranjas indican f₀ y los armónicos con nivel suficiente frente
al residual del ajuste. Las etiquetas muestran dBc respecto de la fundamental
(0 dBc); los puntos representan amplitudes ajustadas, que pueden diferir del
bin FFT por la ventana. Los tooltips incluyen frecuencia y nivel. Se espacian
las etiquetas para evitar superposición. Ocultar una marca débil no cambia
el cálculo de THD/THD+N.

La FFT localiza el tono; un ajuste de seno/coseno y constante refina su frecuencia.
Las métricas usan el último bloque; los promedios del espectro no promedian
THD ni dB. El ajuste se actualiza como máximo cinco veces por segundo.
En vivo se ejecuta en un único trabajador en segundo plano, sin acumular tareas;
el espectro se dibuja hasta 30 veces por segundo usando las últimas métricas
disponibles. Los resultados anteriores se descartan al cambiar parámetros o
detectar discontinuidades. SINGLE calcula las métricas sobre el bloque capturado.
El ajuste conjunto de fundamental y armónicos permite distinguir distorsión de
la fuga producida por un tono entre bins. La selección manual de fundamental
sirve cuando un armónico es más grande que ella.

Con P1 la potencia de la fundamental, Ph la de los armónicos incluidos y Pn la
potencia residual en la banda:

```text
THD   = sqrt(sum(Ph)/P1)
THD+N = sqrt((sum(Ph)+Pn)/P1)
SNR   = 10*log10(P1/Pn)
SINAD = 10*log10(P1/(sum(Ph)+Pn))
```

THD y THD+N se presentan en porcentaje. Los armónicos fuera de la banda/Nyquist
no se pliegan a otras frecuencias. Los que quedan fuera del orden elegido pueden
permanecer en el residual: especificar banda y orden es parte de la medición.
Se requieren varios ciclos y un ajuste identificable. Una lectura sintética
cercana a cero no constituye una medida del límite físico del instrumento.

## Transfer

X es V_IN y Y es V_OUT. Se promedian espectros sincronizados:

```text
H1        = mean(Pxy)/mean(Pxx)
coherencia = abs(mean(Pxy))**2/(mean(Pxx)*mean(Pyy))
ganancia   = 20*log10(abs(H1))
fase       = angle(H1)
retardo    = -d(fase)/d(2*pi*f)
```

H1 estima Y/X suponiendo que el ruido de la referencia es despreciable frente
al de la salida. La referencia débil invalida el cociente. La coherencia compara
la parte linealmente relacionada de ambas señales: requiere más de un segmento.
Con un solo segmento la fórmula daría trivialmente uno y se indica N/A.
Los segmentos solapados no son realizaciones independientes.

El retardo se obtiene de pendientes locales de fase desenvuelta, con suficientes
bins contiguos y coherencia alta; no se interpolan huecos de señal inválida.
Un seno único permite estimar ganancia/fase cerca del tono, no una respuesta de
banda ancha. Usar ruido o una excitación que cubra la banda para explorarla.
El resumen de ganancia y coherencia corresponde al pico de la referencia;
no representa toda la banda. El retardo incluye el circuito y cualquier
desfase de la cadena ADC.
Las referencias Bode existentes no se aplican automáticamente a este método.

## SINGLE y continuidad

SINGLE conserva su bloque de muestras para inspeccionarlo. Una PSD de ese bloque
es válida; la coherencia de una sola captura no lo es. Los promedios se reinician
si cambia el perfil, la ventana, los canales o aparece una discontinuidad.
El cálculo y el dibujo tienen trabajo limitado por actualización para preservar
la respuesta del monitor. La reducción visual conserva los datos de análisis.

## Alcance de la validación

Las pruebas numéricas usan tonos, ruido y sistemas de transferencia conocidos;
las pruebas Qt comprueban selección y dibujo sin placa. No certifican ruido,
distorsión, respuesta ni calibración del hardware. V13 permanece disponible
como referencia para comparar el comportamiento con la placa.

## Versiones

Implementación: [motor numérico](../monitor/historico/v14/spectral_analysis.py) ·
[controles y gráficos](../monitor/historico/v14/spectrum.py) ·
[pruebas](../tests/v14).
