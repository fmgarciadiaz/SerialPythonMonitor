# Revisión global Astra · V19 · 27/10/2026

**Seguimiento 28/10:** los hallazgos se corrigieron y verificaron en la
[tanda posterior](CORRECCIONES_REVISION_V19_20261028.md). El estado de este
informe corresponde al cierre del 27/10, salvo la corrección factual indicada.

Revisión integral de la implementación de Arduscopio Q V19: monitor, transporte,
proceso receptor, representación, RADIO/WAV/Synth, relay, preparación/restauración
del Q y calidad de las pruebas. La revisión de código no sustituye la aceptación
física sostenida. V17 y V18 quedaron intactas; esta tanda no compiló ni instaló
firmware y no cambió la pareja activa del Q.

## Resultado de Astra

No se demostró un defecto P0. Se encontraron tres riesgos prioritarios, una
regresión funcional de medición, gates insuficientes en el smoke de GUI y riesgos
que requieren evidencia adicional. La mayor parte de RADIO/WAV/Synth conserva
el diseño anterior; los defectos V19 demostrados se concentran en estado de
representación temporal, actualización de cadencia y cierre del proceso receptor.

## Corregido en esta revisión

1. **STOP en V(t):** el frame retenido podía compartir memoria con el anillo de
   historia y cambiar después de parar; además podía quedarse con una envolvente
   reducida. STOP fuerza el render completo y conserva copias independientes.
   El test verifica que reutilizar el anillo no altera la captura y que un cursor
   activado después de STOP puede leer un punto interior.
2. **Cadencia al cambiar FS:** `_acquisition_confirmed()` y la medición de FS
   actualizan ahora la cadencia de V(t) al recalcular la escala temporal. Se
   cubren las transiciones 40 kHz → 1,860 MHz → 40 kHz.
3. **Cierre del receptor:** el padre drena el pipe terminal mientras espera al
   hijo. Una respuesta terminal grande ya no bloquea al hijo ni provoca que el
   padre lo mate antes de conservar el resultado. Se prueba un mensaje de
   512 KiB y entrega de resultado de una sola vez.
4. **Frecuencia de tonos lentos:** la estimación empieza con una ventana reciente
   y amplía la búsqueda cuando faltan cruces. En ventanas largas limita el
   fallback a 524.288 puntos y conserva la escala temporal. Tests cubren 1, 2,
   5 y 50 Hz, señales cortas y silencio.
5. **Smoke de análisis:** para VT, FFT y Heatmap exige configuración aplicada,
   muestras avanzando entre observaciones, volumen y duración mínimos de datos,
   y valores finitos en el gráfico. Bode se etiqueta como una curva sintética;
   ya no se puede confundir ese demo con una medición física.

## Hallazgos pendientes al cierre del 27/10

- **Preparación del Q:** el backend de actualización compila en el Q antes de
  marcar la transacción como incierta y antes de pausar adquisición. Si el build
  perturba el relay y falla, el flujo puede omitir recuperación. **Corrección
  factual:** `ProductionBackend` sí se habilita por recibo; el preflight no
  bloquea siempre esta ruta. No se ejecutó en esta tanda. Antes de
  calificarlo hay que separar la compilación de la carga activa y diseñar una
  recuperación que cubra también el fallo durante la etapa de preparación.
- **Cierre global:** hay esperas sin límite a algunos ejecutores/renderers. Es un
  riesgo de bloqueo, no un fallo demostrado; falta un test de worker nativo que
  no responda y una política de cierre acotada.
- **Identidad de pareja:** la conexión comprueba hashes e identidad presente,
  pero no siempre los compara con un recibo aceptado. Definir el contrato antes
  de endurecerlo para no romper ensayos privados.
- **WAV repetido:** los `QThread` de preparación terminados pueden quedar
  referenciados tras muchas selecciones. Falta prueba de repetición larga y
  limpieza explícita.
- **Arranque:** la exploración/corrección de plugins Qt ocurre al importar.
  Falta medir su aporte al inicio frío.
- **Cola del relay:** con cola llena, el relay rechaza la trama antes de volver a
  intentar vaciarla. Es un límite de robustez reproducible, pero no hay evidencia
  de que causara el cierre observado. No se cambió el protocolo como arreglo
  supuesto.
- **Causa de `sent=-1`:** sigue abierta. No instalar el relay candidato ni
  atribuirle causalidad sin la captura del error y su estado de cola.

## Validación realizada

- Suite completa V19 bajo Python 3.13, permisos locales para loopback y procesos
  auxiliares: **358 tests PASS** (84,13 s). La repetición anterior en sandbox
  restringido dio falsos errores de permisos para esos mismos sockets locales.
- 44 tests focalizados de GUI/representación/receptor PASS con los asserts
  finales incluidos.
- `py_compile` aplicado a `app.py`, receptor, smoke y test de medición.
- No se ejecutó prueba física en esta tanda: la inspección de procesos necesaria
  para confirmar que el Q tuviera un único propietario fue bloqueada por el
  entorno. No se abrió conexión al Q, no se compiló y no se cambió el firmware.

## Siguiente paso seguro

1. Confirmar dueño único del Q y correr el smoke V(t) con gates estrictos en la
   pareja actualmente aceptada; registrar muestras, exposición real y restauración.
2. Antes de tocar la ruta “Preparar Q”, rediseñar la etapa de compilación para
   que no coincida con adquisición y probar fallos simulados antes/después de
   cada punto de mutación.
3. Investigar cola/errno de `sent=-1` con logs solo en la ruta de error; mantener
   las tasas públicas y la pareja física sin cambios hasta tener evidencia.
