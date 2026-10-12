# Piano físico: referencia y próximo diseño

Consulta del 8 de octubre de 2026. Este documento distingue características
publicadas, límites del prototipo V15 y propuestas; no declara equivalencia
acústica con un piano comercial.

Implementación posterior: [identificación contra notas de un Yamaha C5,
audio A/B y validación reservada](PIANO_IDENTIFICACION.md).

## Qué muestra Pianoteq

La [presentación técnica de Modartt](https://www.modartt.com/pianoteq_features)
describe interacción martillo–cuerdas, unísonos ligeramente desafinados,
inharmonicidad, resonancias simpáticas y propagación del sonido. La vibración
remanente interviene en golpes posteriores. Son características publicadas;
esa página no proporciona una implementación reproducible del motor.

Su [manual](https://www.modartt.com/user_manual?product=pianoteq) separa
dureza del martillo según dinámica, ruido de percusión y color del ataque:
impacto grave de madera y contacto agudo con la cuerda. La impedancia de la
tabla armónica afecta duración y pérdidas de los parciales. La reverberación
de sala es un componente distinto de la resonancia del instrumento.

## Comparación con V15

| Componente | Prototipo actual | Trabajo pendiente |
|---|---|---|
| Martillo | Contacto no lineal con retornos precalculados y transitorio estructural excitado por esa fuerza | Contacto con el estado vibratorio actual y transferencia de ataque medida |
| Unísonos | Desafinación, rigidez y pérdidas distintas; pérdida común pasiva por parcial | Impedancia del puente identificada y doble decaimiento calibrado |
| Evolución tonal | Relajación pequeña de tensión por golpe | Identificar evolución de frecuencia, amplitud y fase en grabaciones |
| Vibración longitudinal | Aproximación excitada por el cuadrado de la señal | Acoplamiento espacial consistente; la aproximación actual no resuelve la ecuación longitudinal |
| Tabla y radiación | Banco de resonadores con valores de diseño | Movilidad del puente y transferencia acústica dependientes del registro |
| Pedal | Resonancias y amortiguamiento aproximados | Estado persistente por tecla, resonancia cruzada y transición del apagador |

La relajación de tensión no es un vibrato periódico. Los batimientos entre
cuerdas y parciales cercanos también producen movimiento aparente; agregar
un LFO a toda la nota no sustituye esos mecanismos.

## Investigación reciente

[Physical Modeling of Piano Sound (2024)](https://arxiv.org/abs/2409.03481)
formula fieltro, martillo, cuerdas, tabla y aire con acoplamiento mecánico,
y reducción modal de grados de libertad. Es un trabajo de investigación;
su resumen no demuestra que ese modelo completo cumpla nuestro presupuesto
de tiempo real.

[Sines, Transient, Noise Neural Modeling of Piano Notes (2025)](https://arxiv.org/abs/2409.06513)
separa parciales, transitorios y ruido y estima parámetros desde grabaciones.
Sus autores aún reportan limitaciones perceptuales en el ataque. Esto apoya
usar referencias medidas y evaluar el ataque por separado; no demuestra que
una red neuronal sea necesaria en nuestro render.

## Plan recomendado

1. Elegir una referencia acústica con permiso de uso. Comparar notas graves,
   medias y agudas a varias velocidades, con y sin pedal, igualando volumen.
2. Extraer por registro espectro inicial, batimientos, inharmonicidad y
   decaimiento de cada parcial. Conservar datos y método de ajuste.
3. Mejorar primero martillo y transitorio de ataque. Separar impacto mecánico
   y fuerza de contacto; comprobar respuesta a velocidad y golpes repetidos.
4. Introducir puente/tabla compartidos con acoplamiento estable y parámetros
   identificados. Mantener radiación y reverberación como etapas distintas.
5. Ajustar pedal y pérdidas con esas referencias. Evaluar notas, acordes y
   repeticiones con escucha y espectrogramas, además de pruebas numéricas.
6. Medir tiempo máximo por bloque y latencia MIDI→DAC. Mantener kernels
   compilados y perfiles precalculados; no reducir colas por intuición.

La prioridad es fidelidad del ataque y de la evolución de la nota. Más
parciales o reverberación, por sí solos, no validan realismo. Las mejoras
experimentales de tensión y longitudinales requieren escucha comparativa;
las pruebas de continuidad únicamente verifican funcionamiento numérico.
