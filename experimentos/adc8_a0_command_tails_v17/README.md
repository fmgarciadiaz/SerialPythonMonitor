# Comandos WAV: colas temporales acotadas por etapa

Copia nueva de `adc8_a0_command_trace_v17`; sólo cambia `cmd_trace.h` en el
relay. No añade llamadas de reloj ni cambia recepción, SPI, aceptación, envío,
cadencias o créditos. MCU cc46 y N8 se conservan. El nuevo hash del relay queda
registrado. El runner permite hasta tres casos independientes de120s; termina
ante el primer fallo real de audio/ADC/restauración, sin repetirlo. Visualización
y holgura se reportan aparte. El rollback y captura de logs antes de borrar el
contenedor siguen el lifecycle anterior.

Para cada una de cinco etapas se acumulan count/sum/max y los ocho intervalos
mayores con una copia completa de los campos disponibles al cerrar esa etapa:
primera lectura positiva→comando completo, completo→SPI inicio, SPI final→ACK
recibido, ACK recibido→retorno de envío/encolado y completo→ACK recibido.
Los registros tempranos pueden contener ceros en hitos posteriores: son
snapshots de etapa y no se reescriben al completar otras etapas del mismo ID.
La memoria es fija: cinco conjuntos de ocho registros, además del ring128 y
su snapshot128 del primer underrun. Un bit por etapa/ID evita contar llamadas
duplicadas. Cero, intervalos invertidos y valores fuera de rango monotónico
positivo se rechazan antes de restar; no producen underflow sin signo.

`censored_overwrite` cuenta etapas aún no observadas al sobrescribir su comando;
`missing_at_freeze` es la instantánea de etapas ausentes al primer underrun.
Los intervalos rechazados se cuentan aparte. El ACK terminal puede completar
su etapa de encolado después del freeze; ese hecho no cambia el contador de
ausencias capturado en el instante del fallo. Las estadísticas no reconstruyen
etapas no observadas ni prueban que un comando perdido siga en tránsito.

No se modifica la evidencia previa. JSON sólo en baja o al salir. Todos los
timestamps pertenecen al reloj monotónico del Q: no restar absolutos con el host.
`first_byte_ns` conserva la observación de `recv`, no llegada física a la red;
`ack_enqueue_return_ns` no prueba flush físico al PC.

Pruebas offline:

```sh
.venv-v13/bin/python -m unittest experimentos.adc8_a0_command_tails_v17.test_command_tails -v
```

Ejecución física reservada al coordinador tras revisión/compilación Linux:

```sh
QT_QPA_PLATFORM=cocoa .venv-v13/bin/python experimentos/adc8_a0_command_tails_v17/run.py
```
