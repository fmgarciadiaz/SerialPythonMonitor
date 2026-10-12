# Referencias reales de liberación · Salamander Grand Piano V3

Autor: Alexander Holm. Piano Yamaha C5. Licencia CC BY 3.0; licencia completa
y atribución en el directorio superior. Descarga del mismo commit fijado en
las referencias de ataque; URLs, tamaños y SHA256 en `procedencia.json`.

Fuente: https://github.com/sfzinstruments/SalamanderGrandPiano

Se descargaron para Do3, Do4 y Do5 tres capas de resonancia (`harmL`, `harmS`,
`harmV3`) y el ruido mecánico separado (`rel28`, `rel40`, `rel52`).
`str_res.txt` y `hammer.txt` conservan su mapeo original. El SFZ del directorio
superior las coloca bajo `trigger=release`: son capas disparadas al soltar.

Estas grabaciones no equivalen por sí solas a la liberación completa de una
nota: el instrumento SFZ también aplica una envolvente de salida a la nota
sostenida y pondera estas capas por velocidad y tiempo de tecla presionada.
No usar `rt_decay` como duración del sample ni ajustar el apagador modal
igualando directamente su duración con la de estas capas.

Los WAV de escucha son conversiones mono/20 kHz sin normalización individual.
`mediciones.json` contiene RMS en ventanas de 20 ms y el último instante por
encima de -20/-40 dB respecto al pico RMS. Incluye ruido residual; no es T60
ajustado ni una calibración de apagador.

## Aplicación al motor V16

`python diagnosticos/identificar_liberacion_piano_v16.py` reproduce los ajustes
de resonancia y nivel. `--apply` copia los valores al JSON de V16. No usa placas.
`ajuste_modal.json` conserva las regresiones aceptadas: bandas de los primeros
dos parciales, ventana hasta 0,8 s tras el pico, por encima del ruido +8 dB,
R² > 0,55 y pendiente menor que -3 dB/s. Medianas T60 extrapoladas:
Do3 2,16 s, Do4 1,88 s, Do5 1,62 s. Son estimaciones de resonancia, con
variación considerable entre capas; no duraciones de tecla ni de apagador.

`ajuste_nivel.json` estima el nivel relativo desde harmL y harmV3 con sus
factores SFZ, MIDI 60 y 0,5 s de tecla presionada. El motor transfiere estado
existente de los dos modos simpáticos por nota al cerrar la tecla, con entrada
gradual de 10 ms y estos tiempos. No reproduce FLAC/WAV ni agrega voces de
tecla. Las colas comparten un mapa limitado a las notas del cuerpo, expiran,
y se reciclan al volver a presionar la misma tecla. El pedal difiere la
transferencia hasta levantarse. Se conserva el apagador de 550 ms.

El nivel para otras velocidades, tiempos de tecla y registros es una
aproximación interpolada; no es un ajuste completo de todas las capas SFZ.
El ruido mecánico `rel*` no se incorporó: es un componente distinto de la
resonancia tonal. A/B con el mismo gain antes/después y benchmark local en
`diagnosticos/resultados_piano/revision_cola_v16/`. Escucha y USB pendientes.
