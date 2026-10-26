# FFT Radio · Recortar radios

En Análisis → FFT → Radio, el tick «Recortar radios» muestra únicamente las
bandas de las emisoras identificadas por el último Scan. Requiere candidatos
válidos y CH1 visible; queda deshabilitado sin ellos. El recorte es sólo visual:
no cambia adquisición, FFT, demodulación, Scan ni salida A0.

Cada emisora ocupa una columna, ordenada por su frecuencia RF real. El ancho
es el sugerido por Scan cuando existe; si no, se usa la banda RADIO seleccionada.
Los intervalos entre emisoras se omiten y los trazos no se conectan a través de
ellos. El centro identifica la portadora en kHz; los extremos indican el offset
de sus bandas laterales. La escala horizontal comprimida usa columnas iguales,
por lo que su posición no representa un eje continuo de frecuencia.

En US se toma el espectro del alias y se invierte su orientación cuando la RF
está por encima de Nyquist. Esto conserva el orden de las laterales respecto
a la RF mostrada. No elimina ambigüedades ni interferencias propias del alias.
Los candidatos cuyo canal cruza DC/Nyquist no se incluyen.

Un clic dentro de una columna sintoniza su frecuencia RF correspondiente; el
espacio entre columnas no sintoniza. La vista recortada tiene un juego separado
de cursores A/B; sus lecturas expresan frecuencia RF real. En esta vista el
arrastre habitual de sintonía se desactiva para no confundir la coordenada de
columna con una frecuencia; el clic y los cursores permanecen disponibles.

Al desmarcar vuelve la FFT completa, con sus unidades, escala logarítmica
preferida y cursores normales. Estando pausado se reutiliza el último espectro
compatible; no se requieren muestras nuevas. Borrar el Scan desmarca el tick.
RADIO, CH2 y FILTER conservan su representación normal.

Validación offline: ventanas/bandas exactas y orden, huecos NaN, inversión US,
cliqueo y exclusión de huecos, desactivación sin Scan, recuperación normal y
logarítmica, espectro pausado y cursores con unidades RF. Revisión visual con
señales sintéticas. No se operó el Q para esta modificación.
