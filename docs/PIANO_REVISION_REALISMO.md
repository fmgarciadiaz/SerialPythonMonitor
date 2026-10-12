# Revisión del Piano Virtual: realismo y latencia

Última etapa: [ajuste contra grabaciones Yamaha C5 y comparación A/B](PIANO_IDENTIFICACION.md).

Ver [comparación con Pianoteq e investigación reciente](PIANO_ESTADO_DEL_ARTE.md)
para los límites actuales y el plan de identificación acústica. El experimento
posterior añade relajación de tensión y una aproximación longitudinal; aún
no tiene validación perceptual. La tabla siguiente incluye ese experimento
y la optimización posterior de actualización de tensión.

Revisión con Astra del 8 de octubre de 2026. Se inspeccionaron el motor V15,
el modelo físico, los presets y el transporte; se hicieron pruebas numéricas
sin modificar el motor ni operar el Q. Las mejoras siguientes son propuestas.

## Implementación posterior a la revisión

El prototipo ya aplica contacto con dos retornos fraccionarios, hasta 128
parciales en banda, coeficientes separados de excitación y observación en
puente, pérdidas según frecuencia/registro y dos colas de polarización.
Se desactivó la sincronización forzada entre unísonos para conservar batimientos.
Ahora una pérdida común pasiva por parcial/polarización representa de forma
reducida el puente: atenúa el movimiento común, preservando el diferencial.
La contracción se aplica cada 16 muestras sobre el reloj absoluto. No es la
impedancia completa de una tabla armónica ni acopla teclas distintas.

El ataque incorpora tres resonancias estructurales breves, excitadas por la
misma fuerza de contacto calculada a 80 kHz. Su transferencia y ganancia son
valores de diseño, no datos medidos; se precalcula y conserva en caché. Esto
separa el impacto mecánico de los modos sostenidos sin usar ruido blanco.
La relajación de tensión actualiza la rotación modal cada 16 muestras,
conservando estado entre bloques; reduce trabajo por modo y por muestra.
La radiación por parcial mantiene un peso empírico `n**(-0.25)`; no se presenta
como respuesta medida de una tabla armónica real.

La caja del piano tiene T60 dependiente de frecuencia (0,16–0,9 s), y las
resonancias simpáticas con pedal, 1,2–9 s. Son valores de diseño ajustables,
no mediciones de un instrumento identificado. Al soltar pedal se aplican
pérdidas cortas a las simpáticas. En piano puro, el release actúa sobre las
pérdidas modales; el estado ADSR conserva el retiro de voces. Las mezclas con
otros osciladores conservan la envolvente común anterior.

La ruta del piano puro mezcla directamente a 20/40 kHz. Mantiene el reloj
de envolventes, evita repetir muestras/filtrar/diezmar y conserva una ruta
compatible para FM y otras mezclas. Al cambiar de ruta se prepara el estado
del filtro y se aplica una transición de 3 ms. Fuerzas de golpes repetidos
y coeficientes de caja/pedal están en caché; el warmup cubre las firmas
Numba de sólo lectura utilizadas por el render real.

**Límite de edición:** los modos disponibles se seleccionan al iniciar el
golpe. Bajar rigidez durante una nota actualiza los modos existentes; la
ampliación de parciales disponibles se aplica al siguiente golpe.

Verificación: 138 pruebas V15 aprobadas, incluyendo contacto por registro,
riqueza grave, amortiguamiento, continuidad de release con bloques irregulares
y cambio entre ruta nativa y mezclas, pasividad del puente, conservación del
movimiento diferencial, transitorio acotado y bloques de 1/7/13 muestras.
La ganancia final del impacto se verificó nuevamente con las 18 pruebas
de instrumentos físicos. Barrido offline C1–C8 con cuatro
velocidades, y warmup sin nuevas firmas de compilación al reproducir.

## Rendimiento y audio de comparación

Benchmark local de tres segundos por caso, bloques de 480 muestras, teclas
C3 y consecutivas. Comparación con el modelo anterior y la misma ganancia ×4:

| Nueve voces | Antes: render total | Nuevo: render total | P95 nuevo por bloque |
|---|---|---|---|
| 20 kHz | 244 ms | 231 ms | 1,90 ms |
| 40 kHz | 541 ms | 665 ms | 2,62 ms |

Antes de optimizar la actualización de tensión, el experimento costaba
302/859 ms a 20/40 kHz. La revisión actual recupera margen de CPU, pero
los tiempos varían entre ejecuciones y no demuestran calidad perceptual.
La tabla actual incluye el perfil acústico identificado. A 40 kHz cuesta más
que el modelo anterior conservado: el ajuste no se presenta como optimización
de esa tasa. Ver máximos y límites en el informe de identificación.

Son tiempos de CPU de una ejecución local sin transporte ni GUI, no medidas
MIDI→DAC ni aceptación física. La cola adaptativa permanece sin cambios;
no se declaró estable Synth40 a partir del benchmark.

[Resultado numérico](../diagnosticos/resultados_piano/20261008_motor.json) ·
[Script](../diagnosticos/comparar_piano_v15.py) ·
[Modelo previo conservado](../diagnosticos/resultados_piano/modelo_previo.py).

Audio mono 20 kHz, una nota C3, misma velocidad y nivel. Se guarda tanto el
resultado de DAC simulado como una comparación igualada por RMS:
[antes, volumen igualado](../diagnosticos/resultados_piano/piano_antes_igualado.wav) ·
[nuevo, volumen igualado](../diagnosticos/resultados_piano/piano_nuevo_igualado.wav).
La escucha y comparación con un piano real siguen pendientes; el modelo
mejorado no garantiza fidelidad acústica por sí mismo.

## Diagnóstico

1. **Contacto del martillo incompleto.** `_hammer` ve una impedancia resistiva
   constante, sin las ondas reflejadas por los extremos de la cuerda. Es una
   aproximación inicial que deja de ser adecuada cuando vuelve la primera
   reflexión. El contacto actual dura cerca de 4 ms incluso en agudos,
   suprimiendo demasiados parciales y suavizando el ataque.
2. **Riqueza grave limitada.** El techo de 64 parciales limita C2 a unos
   4,2 kHz y C1 a 2,1 kHz, aunque a 20 kHz haya margen hasta 8,4 kHz.
   El peso `1/n**.55` y la normalización por suma absoluta son heurísticos.
3. **Puente aproximado.** Excitación y observación modal no están separadas.
   Conviene representar la posición del golpe y la fuerza del puente con
   coeficientes distintos, en lugar de usar una pendiente empírica conjunta.
4. **Resonancias demasiado breves y débiles.** La caja usa filtros de Q bajo
   y pesos normalizados, con bastante señal directa. Q=30 a 1 kHz da un
   T60 aproximado de 66 ms. Las simpáticas Q=180 dan unos 0,40 s a 1 kHz,
   con poca contribución de cada cuerda. No producen una cola de pedal realista.
5. **Pérdidas y acoplamiento heurísticos.** Promediar estados de cuerdas
   desafinadas puede disipar sus diferencias y reducir batimientos.
   Las dos polarizaciones y la pérdida por parcial necesitan ajuste acústico.
6. **ADSR no duplica el decay de una tecla sostenida:** el preset usa sustain=1.
   El ataque de 1 ms sí altera el transitorio físico, y el release lineal de
   220 ms sustituye el comportamiento del apagador. Es una causa secundaria,
   no la explicación principal del timbre.

La ganancia ×4 agregada anteriormente aumenta volumen; no corrige estos puntos.

## Cambios propuestos, en orden

| Paso | Implementación | Impacto de rendimiento |
|---|---|---|
| 1 | Contacto no lineal con retornos de cuerda, precalculado por golpe | Hasta unas 960 iteraciones a 80 kHz por nota; medir ráfagas de acordes |
| 2 | Separar excitación y fuerza modal en puente; normalización por registro | Similar al motor actual |
| 3 | Pérdidas por frecuencia/registro, apagador modal y unísonos con colas distintas | Bajo, condicionado a cantidad de modos |
| 4 | Caja y simpáticas compartidas, con T60 por frecuencia | Bajo a moderado; una instancia para todas las voces |
| 5 | Ruta nativa para piano puro, perfiles y coeficientes precalculados | Reduce CPU y variabilidad |
| 6 | Medir MIDI→DAC y demoras del transporte antes de reducir cola | Requiere ensayo físico separado |

Para graves, evaluar 96–128 parciales sólo donde entren en banda; descartar
modos fuera de banda en lugar de actualizarlos con amplitud cero.
Una respuesta impulsional medida del resonador sería una mejora posterior,
con instrumento y licencia identificados. Reverberación de sala y resonancia
de cuerdas/caja deben mantenerse como fenómenos distintos.

## Prototipo numérico del contacto

Astra probó en memoria dos retornos ideales: retardos `x/f` y `(1-x)/f`,
reflexión negativa en extremos fijos y contacto `F=K*max(compresión,0)^p`.
Con ondas entrantes a,b e impedancia total Z=2NZ por las cuerdas en paralelo:

```text
v_cuerda = F/Z + a + b
onda_izquierda = F/Z + b
onda_derecha = F/Z + a
v_martillo -= F/(masa*Fs)
compresión += (v_martillo-v_cuerda)/Fs
```

El contacto resultó de 3,51 ms en C2, 2,13 ms en C4, 1,14 ms en C6,
0,71 ms en C7 y 0,58 ms en C8. Estos resultados muestran coherencia
estructural, **no validación acústica**. La implementación necesita retardos
fraccionarios, separación del martillo, pérdidas y estabilidad verificadas.
Usar una cuerda ideal durante contacto y modos dispersivos después seguirá
siendo una aproximación documentada.

## Latencia

La prueba física anterior de Synth20 terminó con nueve bloques de 480 muestras:
**216 ms de cola**, frente a pausas de ACK de hasta 102 ms. Reducir unos
milisegundos de CPU no elimina esa cola. Dos bloques a 20 kHz serían sólo
48 ms, menos que la pausa observada; no se propone ese recorte sin evidencia.

El Piano genera a 20/40 kHz, repite muestras a 80 kHz y luego vuelve a
filtrar/diezmar. Una ruta para piano puro puede mezclar a tasa de salida,
con envolvente/apagador y caja compartida, sin fases ni arrays FM innecesarios.
Con Osc 2/3 o transiciones de modo se conserva una ruta compatible.
Los coeficientes de caja y pedal deben prepararse fuera del render crítico.

Medir p50/p95/p99 y máximo de render y ACK, y timestamps desde recepción MIDI
hasta bloque reproducido. El polling MIDI de 4 ms es pequeño frente a la cola.
El origen de las pausas ACK todavía no está demostrado.

## Aceptación

- C1–C8 y velocidades 32/64/96/127: fuerza finita, separación, afinación y banda.
- Comparar ataque 0–30 ms, espectro 0–200 ms y pérdidas por parcial hasta 5 s.
- Pedal, note-off, repetición de tecla y robo de voces, con continuidad entre bloques.
- Nueve voces a 20/40 kHz: presupuesto de 24/12 ms por bloque y colas bajo carga.
- Guardar audio antes/después e igualar volumen para evaluar timbre.
- Ajustar pérdidas contra grabaciones identificadas, no declarar realismo sólo
  porque los tests numéricos pasan o porque se añade reverberación.

## Fuentes

[Julius O. Smith: Piano Synthesis](https://www.dsprelated.com/freebooks/pasp/Piano_Synthesis.html)
describe martillo, cuerda, puente y radiación.
[Commuted Piano Synthesis](https://www.dsprelated.com/freebooks/pasp/Commuted_Piano_Synthesis.html)
presenta una arquitectura eficiente con excitación y respuesta del resonador.
[Euphonics: el piano y sus cuerdas golpeadas](https://euphonics.org/11-2-hitting-strings-the-piano-and-its-relatives/)
explica el papel de las reflexiones durante el contacto.
[Parámetros publicados](PIANO_PARAMETROS.md) documenta las tablas que ya usa V15.
