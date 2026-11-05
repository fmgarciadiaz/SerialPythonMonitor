# V20: revisión con Astra y cambios implementados · 1/11/2026

Astra revisó por separado memoria/recuperación y audio/ACK, leyendo código, ELF y evidencia archivada. No operó el Q. Tras un primer límite de uso, la revisión pudo completarse. Sol implementó la confirmación WAV acotada; el coordinador revisó el cambio, ejecutó la regresión con el Python 3.13 habitual y realizó las pruebas físicas. V17/V18/V19 permanecen intactas.

## Memoria de Gemini y corrección de V20

El candidato original desde `0x20040000` se solapaba con el heap LLEXT hasta `0x20053890`. Se conserva su respaldo. El contrato corregido mantiene Storage en `[0x20060000, 0x20094060)`: **213.088 bytes**, alineación32. El ELF ARM nuevo conserva ese tamaño y ubicación; inicializa la arena completa con escrituras32bit antes del primer uso.

Astra confirmó el mapa y la ausencia de desplazamiento de cookie en la construcción del array compilada para ARM. Se implementaron estos endurecimientos:

- El contrato exige las **nueve rutas exactas** del BSP, además de sus hashes y límites. Sustituir un archivo por otro conservando la cantidad ya no pasa.
- La rama CH1 de cuatro slots construye explícitamente el array `SingleMemory::Samples`, igual que ya se construía la variante rápida. Se inicia explícitamente la vida de esa variante antes de publicar sus punteros. La regla de asignación a miembros de una unión no equivale a cualquier acceso posterior por puntero; véase el [borrador del estándar C++, class.union](https://eel.is/c++draft/class.union).
- `bind()` rechaza capacidades/geometrías inválidas antes de modificar el almacenamiento. El arranque propaga el rechazo. Una aserción de compilación conserva el límite de los cuatro slots y se documenta la precondición de `at()`.

Este endurecimiento no aumenta buffers, tasa ni trabajo por muestra. La mejora anterior de Gemini reubicó buffers y amplió la cola: no eliminó su consumo físico. Los 213.088 bytes siguen ocupados en SRAM3; la menor cifra global del compilador expresa holgura en el presupuesto del módulo, no que toda esa RAM haya dejado de usarse. El contrato sigue siendo exclusivo de este BSP: no es una nueva reserva formal del linker. Los hashes en disco y la configuración archivada no equivalen a leer la identidad del kernel arrancado ni los option bytes ECC; no se declara ECC medido ni soporte de otro MPU/BSP.

## ACK de cierre WAV: bug corregido

Astra reprodujo un defecto real: `reset_wav_output()` interpretaba que desapareciera `wav_pending` como confirmación, pero `service_wav()` también lo elimina al vencer el timeout. QUERY y STOP podían darse por confirmados sin recibir ningún ACK.

La implementación V20 exige un estado nuevo, RID exacto y `reason=0` para cada QUERY/STOP, dentro del plazo original de3s. STOP acepta `IDLE` o `DONE`: el firmware puede conservar DONE cuando ya liberó ownership. ACK viejo, incorrecto, con error o tardío falla. No se cambian créditos, relleno asíncrono, reservas, buffers ni timeouts. Astra revisó la corrección y los12tests de reproducción/confirmación sin encontrar bloqueantes para prueba GUI.

Esto mejora la certeza del cierre, **no demuestra arreglar el UNDERRUN de666ms** observado con raster paralelo.

## Recuperación y observación

La limpieza del sondeo ahora ejecuta pasos independientes: un fallo de logs, socket o forward no evita intentar detener recursos y restaurar. Identifica el relay por etiqueta propia y lo detiene por ID; no toca un relay ajeno. Admite stop→kill sólo del propio, tolera ausencia verificada y distingue errores de comunicación. Si no se confirma que app/relay/compilador privados estén detenidos, bloquea undo y reinicio del aceptado.

El rollback verifica archivo de respaldo, fuentes, BIN y **todo el inventario de caché**: archivos, ELF/debug/opciones, enlaces y directorios. Sólo tolera FileNotFound al retirar directorios propios ausentes; otros errores se propagan. Los tests inyectan fallos, cancelación, relay ajeno, stop→kill, app ausente, escritor no detenido y cambios de debug con BIN idéntico.

Se corrigió además el observador reutilizado: antes seleccionaba la clase del receptor V19 incluso en V20. Ahora recibe explícitamente receptor y Configuration V20; los valores por defecto V19 permanecen compatibles. La captura distingue envío completado→ACK leído del socket y ACK leído→entrada al manejo de eventos, además de etapas wall/thread-CPU V20. La segunda marca es entrada al manejo, no final de todos los callbacks. Estos tiempos incluyen planificación/lectura del host y coste de observación; no son latencia de cable pura. No altera bytes ni orden FIFO.

Astra detectó también una posible mejora del relay cuando su FIFO TCP está llena pero el socket ya permite drenar. Se deja **sin implementar**: cambia recuperación ante saturación, no explica por sí sola el fallo ni autoriza reordenar ACK respecto de RF. Es un candidato separado para medir con su propio contrato y pruebas.

## Validación física

El firmware se compiló y probó en la app V20 independiente. La prueba corta de1,86/2MS/s pasó integridad; no habilita2MS/s como tasa pública.

En la misma conexión se verificó esta secuencia, cada paso con ACK APPLIED distinto y datos válidos:

| Configuración | Canales | Cola | Muestras validadas |
|---|---:|---:|---:|
|8bits /1.860.465S/s|1|16|9.293.776|
|14bits /1.000.000S/s|1|4|4.995.712|
|14bits /363.636S/s|2|4|1.814.864|
|8bits /1.860.465S/s|1|16|9.293.776|

En dual, el contador representa pares CH1/CH2. Después, GUI Cocoa visible y raster normal:

| Ensayo | Acciones ejecutadas | ACK CHUNK leídos/observados al procesar | Máx. leído del socket | Máx. hasta eventos |
|---|---|---:|---:|---:|
|8bits /1,86MS/s|RADIO/A0 60,062s; luego WAV y Synth20voces|5740/5740|42,31ms|20,25ms|
|14bits /1MS/s|RADIO/A0 20,073s; luego WAV|2036/2036|37,35ms|8,55ms|

Los ACK abarcan todo el ensayo, incluidas las fuentes posteriores solicitadas. WAV/Synth se ejecutan después con adquisición40kHz dual; no simultáneamente con el perfil alto. No se pidió Scan/US en este bloque. Pasaron progreso, paradas, cierre y liberación del worker. Esto no prueba calidad acústica/analógica ni otras tasas de audio.

Finalmente se ensayó la restauración de fuentes y caché V20 con su propio respaldo verificado: `sources_exact`, `firmware_exact` y `cache_exact` PASS. Es una restauración controlada del mismo candidato detenido, no una simulación de todas las fallas posibles del SDK.

**53tests V20 PASS** con `/Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python`; regresiones enfocadas del observador V19 también pasaron. Las cinco campañas guardaron restauración exacta de V19, con lectura final continua sin pérdidas/fatales. Estado final: Q libre con V19 activa; V20 corregida conservada y detenida.

## Alcance de incorporación

Quedan implementados en V20 el almacenamiento explícito/guardas, el contrato BSP reforzado y la confirmación WAV fresca. Quedan implementados en herramientas el rollback completo y la captura correcta V20. El raster paralelo continúa privado y desactivado por defecto.

No es promoción general de la pareja ni de tasas nuevas. Siguen pendientes la holgura ADC10/RADIO y2MS/s, más aceptación sostenida/analógica y la causa del cierre nativo anterior. La reserva de linker formal corresponde a una eventual generalización de BSP. Los resultados y límites de Astra se conservan aquí, sin atribuirle pruebas del Q que ejecutó el coordinador.

[Resumen y hashes de evidencia](../diagnosticos/resultados_v20/astra_implementation_summary_20261101.json).
