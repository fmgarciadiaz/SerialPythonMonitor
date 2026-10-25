# WAV: trazabilidad de comandos, diagnóstico aislado

Una única ejecución visible de 120s, RADIO+FFT65536 CH1/RADIO y A0/40k,
con fuente `RadioDacSource` ordinaria burst8. Preserva N8 y MCU cc46.
Deriva del relay aceptado `2253ee67...34b13a`, que no se modifica. La nueva
instrumentación cambia el hash del relay; el runner registra el hash nuevo
y exige que las fuentes copiadas sólo difieran en `unoq_config_stream.c` y
el nuevo `cmd_trace.h`. No hay optimización ni cambios de crédito/firmware.

`cmd_trace.h` mantiene 128 registros WAV kind11/13, sin heap ni salida por
frame. Cada registro enlaza ID, sesión, operación/offset/count y timestamps
monotónicos **del Q**: primera lectura parcial positiva observada, comando
completo validado, inicio/final de SPI, recepción de ACK validado y retorno
del camino que envía/encola el ACK, junto con profundidad de cola de salida.
`first_byte_ns` es observación tras retornar el primer `recv` positivo de un
frame, no tiempo de llegada a la interfaz de red. Una operación TCP fragmentada
conserva ese timestamp hasta que el frame se completa.

`ack_enqueue_return_ns` mide retorno de `scope_send_frame` o `send`; no prueba
flush físico al host. El contador de cola conserva contexto, sin modificar el
algoritmo certificado de envío. No restar timestamps absolutos del host y Q:
enlazar por ID y comparar duraciones calculadas dentro de cada reloj.

El primer ACK UNDERRUN congela una copia cronológica de hasta128 registros;
STOP posterior no destruye esa evidencia. Sólo se completa en la copia el
handoff de ese ACK terminal, que ocurre después de reconocer el fallo.
Contadores de comandos, sobrescrituras y comandos posteriores al freeze son
acotados escalares. Se emite JSON `SPM_COMMAND_TRACE` sólo en baja o al salir.
La instrumentación READY/SPI previa y sus limitaciones se conservan.

El runner mantiene ownership del padre, snapshot/backups, idle checks, entrada
privada y restauración exacta. El child reutiliza el helper físico existente,
preserva su reporte incluso si falla y nunca reinstala el stack. Se detiene
tras el primer fallo real y no reintenta. Antes del rollback se detiene el
relay sin borrar su contenedor, se guardan también sus logs de salida y luego
se restaura el estado original. Evidencia visual y holgura permanecen separadas
de integridad. El reporte inicial fallido original no se modifica.

Pruebas offline:

```sh
.venv-v13/bin/python -m unittest experimentos.adc8_a0_command_trace_v17.test_command_trace -v
```

Ejecución reservada al coordinador tras revisión y compilación Linux:

```sh
QT_QPA_PLATFORM=cocoa .venv-v13/bin/python experimentos/adc8_a0_command_trace_v17/run.py
```
