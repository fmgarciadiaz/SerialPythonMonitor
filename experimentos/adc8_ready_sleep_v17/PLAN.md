# READY: espera activa 50 µs frente a dormir inmediatamente

A: lectura no bloqueante y spin acotado50µs antes de poll.
B: misma lectura, dormir en poll al primer EAGAIN (spin0).
Un mismo binario con SCOPE_READY_SPIN_US=50/0 validado al arranque.
Sin alterar timestamp, secuencia, flanco fresco por trama, crédito inicial,
timeouts, CRC, validación completa, accept/recv/send, ACK ni backpressure.
MCU WORD de referencia idéntico; reloj solicitado38MHz sin cambios.

Hipótesis: evitar relecturas de GPIO durante espera READY puede reducir
trabajo y contención con tareas Linux. No presupone mejora en latencia;
poll puede empeorarla. READY es espera, no tiempo recuperable garantizado.

ABBA: dos tasas114/112ticks,ADC8CH1,N3456,30s cada caso, reinicios
independientes. Pruebas de admisión/rechazo extra y APPLIED fuera de ventanas.
Gate heredado: todos íntegros, B con holgura, envío>=2% mejor en ambas tasas
y medias sin solaparse. Sólo si pasa:60+3×120s en112. Sin promoción automática.
Ante fallo, detener y restaurar; no seleccionar repeticiones favorables.

Snapshot/backup previos, un dueñoQ, finally restaura firmware/relay/estado
ADC y todos los campos del generador, identidad y10s de continuidad.
Nada productivo modificado; no aceptación eléctrica,analógica,GUI,dual/UART.
