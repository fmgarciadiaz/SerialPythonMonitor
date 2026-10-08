# Sintetizador y modelos físicos

[Proyecto](../README.md#synth--fm-ondas-y-modelos-físicos) ·
[Controles](../monitor/v15/README.md#generador-synth)

## Ruta de audio

MIDI o Play → voces Python → mezcla/filtro → ajuste de volumen y offset →
códigos DAC12 → USB/ADB → relay → SPI → MCU → temporizador y DMA → A0.
La salida es mono; hasta nueve notas se sintetizan simultáneamente.
MIDI admite velocidad, pedal CC64, volumen CC7 y liberación CC120/123.
Al exceder la polifonía se reciclan voces, priorizando notas liberadas.

La tasa inicial es 20 kHz; 40 kHz es experimental. Los bloques tienen 480
muestras y se envían según créditos, con dos bloques en tránsito. La cola
mínima es cinco bloques a 20 kHz (120 ms) y dieciséis a 40 kHz (192 ms).
La cola de 20 kHz puede crecer ante falta de muestras. Son tiempos de audio
pendiente, no una medición de latencia MIDI total. Bajar la carga del motor
no elimina esa espera ni demuestra estabilidad del transporte.

## FM y ondas clásicas

Tres parejas FM editables, con mezcla, afinación y envolventes. Osc 1 ofrece
FM o seno/cuadrada/triángulo/rampa; Osc 2 puede superponer ondas o FM;
Osc 3 es una pareja FM. Feedback realimenta el modulador con el promedio
de sus dos muestras anteriores. Su escala 0–7 es propia, sin equivalencia
exacta con el DX7. ADSR tiene ataque, caída, sostenido y liberación por
oscilador. Detune produce batimientos; filtros LP/HP/BP/notch procesan la
mezcla. Cuadrada y rampa usan PolyBLEP.

DX Piano y DX Brillo toman la estructura de tres parejas y la relación
metálica 14:1 de E.PIANO 1 como referencia. Envolventes, niveles, feedback y
detune son adaptaciones, no una reproducción exacta Yamaha. El registro
bajo incluye refuerzo transitorio de ataque y cuerpo. DX Brillo aumenta
índice y mezcla metálica. DX Piano sigue como preset inicial.

## Virtual: guitarra

Dos guías de onda representan planos de vibración de una cuerda pulsada,
con un pequeño desfase de afinación. La posición del pellizco determina
la deformación triangular inicial. Los lazos incluyen retardo fraccionario,
pérdidas de agudos y ganancia disipativa. Velocidad MIDI modifica el ataque;
un transitorio filtrado representa roce de púa. La salida combina movimiento
y una aproximación de velocidad del puente, con dos tiempos de decaimiento.

Puente ajusta pérdidas y transmisión. Caja aplica modos sintéticos de tapa,
aire y recinto, con eliminación del movimiento estático y una débil simpatía
de las seis afinaciones abiertas. La caja se procesa después de sumar las
voces y conserva sus colas. Posición afecta el próximo pellizco.

## Virtual: piano

Un martillo de masa efectiva comprime fieltro no lineal contra una impedancia
de cuerda. El pulso de fuerza se calcula a 80 kHz, con pérdida dependiente
de velocidad. Brillo define dureza del próximo golpe; velocidad MIDI cambia
su forma y duración. La fuerza excita modos inicialmente en reposo.

Las frecuencias de la cuerda rígida siguen
`f_n = n f_1 sqrt((1+B n²)/(1+B))`, normalizando la fundamental. Rigidez
ajusta B entre 0 y 0,002. Hay hasta 64 parciales en banda por cuerda: una
cuerda en graves, dos en el registro intermedio y tres desde La3. Dos planos
con diferentes pérdidas dan una caída rápida y una cola lenta. Un acoplamiento
contractivo entre cuerdas aproxima intercambio de energía vía puente.

Los modos se calculan a la tasa de salida. El pulso de fuerza se integra a
esa tasa; la señal se mantiene entre muestras en la tasa interna y atraviesa
el filtro antialias compartido antes del DAC. Tabla, puente y recinto se
representan con un banco modal común. El pedal aumenta las resonancias
simpáticas y su duración; al soltarlo se amortiguan.

## Rendimiento y límites

Numba compila los bucles de feedback, envolventes, martillo, modos y caja.
La preparación ocurre al construir el panel. NumPy/SciPy atienden operaciones
vectoriales y filtros. Las fases, pérdidas, envolventes y resonadores conservan
estado entre bloques. El volumen se aplica antes de la compresión y del
limitador de extremos; no se normaliza según la cantidad de teclas.

Última revisión: 103 pruebas locales pasan. Una ejecución con nueve notas
y 3 s de audio tomó 0,311/0,462 s para guitarra y 0,204/0,529 s para piano
a 20/40 kHz. Excluye adquisición, interfaz y transporte. La estabilidad a
40 kHz y el realismo por escucha requieren validación física.

Las resonancias y parámetros mecánicos son sintéticos, sin respuesta medida
de un instrumento real. El martillo usa una impedancia efectiva; no resuelve
el contacto con toda la velocidad del banco modal. El acoplamiento es reducido,
no la admitancia matricial completa caja–puente–cuerdas. La simpatía no modela
cada cuerda de un piano completo. La púa usa un modelo de señal. Estos límites
siguen siendo importantes para el parecido sonoro.

## Fuentes y módulos

- [Motor y voces](../monitor/v15/fm_source.py).
- [Panel de controles y MIDI](../monitor/v15/fm_panel.py).
- [Feedback y ADSR compilados](../monitor/v15/fm_feedback.py).
- [Guía de onda](../monitor/v15/virtual_string.py).
- [Piano, martillo, puente y caja](../monitor/v15/virtual_instruments.py).
- [Pruebas](../tests/v15/).

Referencias: [modelado de caja](https://www.dsprelated.com/freebooks/pasp/Body_Modeling.html),
[síntesis conmutada de piano](https://www.dsprelated.com/freebooks/pasp/Commuted_Piano_Synthesis.html),
[cuerdas rígidas](https://www.dsprelated.com/freebooks/pasp/Stiff_Piano_Strings.html),
[datos de E.PIANO 1](https://github.com/itsjoesullivan/dx7-patches/blob/master/readme.md).
