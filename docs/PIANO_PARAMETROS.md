# Parámetros publicados para calibrar el piano físico

[Motor Synth](SYNTH.md) · [Monitor](../monitor/v15/README.md)

Aplicado al preset **Piano Virtual** de V15. Es una parametrización basada en
publicaciones, no una calibración física contra un piano o el DAC del Q.

## Tablas de referencia

[Euphonics: Parameter values for piano simulations](https://euphonics.org/12-2-1-parameter-values-for-piano-simulations/)
publica dimensiones y posiciones medidas de un Broadwood, con otras magnitudes
calculadas o estimadas a partir de literatura. La masa efectiva del martillo
es una estimación, no una medición directa. Sus tablas de fieltro proceden de
Hall/Askenfelt y Chaigne/Askenfelt; los coeficientes usan unidades SI.

| Parámetro | C2 | C4 | C7 |
|---|---|---|---|
| Frecuencia nominal | 65,4 Hz | 262 Hz | 2093 Hz |
| Cuerdas por nota | 1 | 3 | 3 |
| Longitud vibrante | 925 mm | 639 mm | 96 mm |
| Diámetro del núcleo | 1,21 mm | 1,00 mm | 0,82 mm |
| Masa vibrante total | 73 g | 11,7 g | 1,15 g |
| Posición del golpe / longitud | 0,135 | 0,125 | 0,090 |
| Masa efectiva del martillo | 11 g | 9 g | 6 g |
| Coeficiente de contacto K | 4×10⁸ | 4,5×10⁹ | 1×10¹² |
| Exponente de contacto p | 2,3 | 2,5 | 3,0 |

Contacto: `F=K*x^p`, con compresión x en metros y fuerza en newtons.
K tiene unidades N/m^p diferentes cuando cambia p: no se comparan estos
coeficientes como si fueran la misma rigidez lineal.

## Magnitudes derivadas para nuestro modelo

Usando la masa por cuerda, longitud, frecuencia nominal y acero con E=210 GPa:

- μ = masa total / (cantidad de cuerdas × longitud).
- T = (2 L f)² μ, aproximación ideal para estimar tensión.
- EI = E π d⁴ / 64, flexión del núcleo circular.
- B = π² EI / (T L²), coeficiente de inarmonicidad.
- Z = sqrt(T μ), impedancia característica de cada cuerda.
- 2 N Z, impedancia inicial aproximada de N cuerdas en paralelo vistas
  desde un contacto que emite ondas en ambas direcciones.

| Derivado | C2 | C4 | C7 |
|---|---|---|---|
| B | 0,000221 | 0,000364 | 0,007740 |
| T por cuerda | 1155,3 N | 684,3 N | 644,8 N |
| Z por cuerda | 9,55 N·s/m | 2,04 N·s/m | 1,60 N·s/m |
| Impedancia inicial 2 N Z | 19,10 N·s/m | 12,26 N·s/m | 9,63 N·s/m |

Son cálculos a partir de valores redondeados, no mediciones nuevas. En graves
la flexión de la envoltura de cobre se ignora, como en la referencia. La fórmula
ideal de tensión y el modelo de extremos añaden incertidumbre.

## Aplicación en V15

[Perfil por nota](../monitor/v15/piano_profile.py) reemplaza las heurísticas
fijas de masa, contacto e impedancia. Masa y posición se interpolan linealmente
en número MIDI; B e impedancia se interpolan en logaritmo entre C1 y C8.
K se interpola en logaritmo y p linealmente entre C2, C4 y C7. Fuera de los
extremos se conserva el valor del extremo. Son decisiones del modelo.

Hay una cuerda por nota debajo de C3, dos desde C3 y tres desde C4.
B e impedancia se interpolan desde los derivados de cada ancla para evitar
saltos de estas magnitudes al cambiar la cantidad de cuerdas.

La fundamental modal conserva su afinación mediante
`f_n = n f_1 sqrt((1+B n²)/(1+B))`; los modos fuera de banda no contribuyen.
Los controles siguen editables: Posición=12 % reproduce la posición publicada
por registro y Rigidez=15 % reproduce B de referencia. Los demás valores
escalan proporcionalmente esas referencias. Brillo=78 % reproduce K de
referencia; variar brillo multiplica K por `2**(4*(brillo-0.78))`, conservando p.
La velocidad MIDI modifica la velocidad inicial del martillo. El impulso
se normaliza por integral para separar el color de la ganancia del motor.
Esta normalización no reproduce una fuerza absoluta en newtons a la salida.

No se deben copiar coeficientes de filtros allpass como valores de B.
[El piano de Snd/CLM](https://sources.debian.org/src/snd/25.3-1/piano.scm)
usó tablas por nota para posición, detune, pérdidas y pedal; su parámetro
stiffnessCoefficient pertenece al filtro de dispersión y no es B físico.
Es una referencia de arquitectura, no una calibración intercambiable.

## Decaimiento y tabla armónica

La referencia Euphonics usa Q=2000 para ilustrar la física; no afirma que sea
una calibración sonora completa. No conviene reemplazar todas nuestras caídas
por ese Q. Deben ajustarse tasas de decaimiento por parcial y nota.
[Identificación del filtro de pérdidas](https://www.dsprelated.com/freebooks/pasp/Loop_Filter_Identification.html)
explica cómo obtenerlas de grabaciones.

Las resonancias actuales de tabla/caja siguen sin una respuesta medida.
[Síntesis conmutada de piano](https://www.dsprelated.com/freebooks/pasp/Commuted_Piano_Synthesis.html)
propone respuestas impulsionales del resonador y excitaciones por velocidad.
Las tablas mecánicas anteriores no resuelven por sí solas la tabla armónica.

## Validación y próximos ajustes

1. Aplicado: perfil por nota de masa, posición, K, p e impedancia, con conversión SI.
2. Aplicado: B dependiente del registro, preservando afinación y edición relativa.
3. Pruebas locales de contacto finito y normalizado de C1 a C8, dos velocidades,
   banda, continuidad entre bloques y parciales inarmónicos. Falta comparación
   auditiva contra grabaciones de un instrumento identificado.
4. Ajustar decaimientos contra grabaciones con condiciones identificadas.
5. Incorporar una respuesta de caja medida con licencia y procedencia claras.

Las interpolaciones entre notas de referencia serán decisiones del modelo,
no nuevos datos medidos. Comparar antes/después a igual volumen es necesario
para evaluar realismo; añadir brillo no demuestra fidelidad al instrumento.
