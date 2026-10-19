# TCP: uno frente a dos frames por send

Un binario, env SCOPE_TCP_BATCH=1/2. MCU WORD y READY spin50µs idénticos;
SPI solicitado38MHz sin cambios. CRC/continuidad/ACK se validan por cada
frame antes de agrupar. A envía frame original sin copia adicional; B almacena
como máximo2×992B y envía bytes originales en orden, sin framing TCP nuevo.

Primer frame de cliente, control/noDATA, comandos pendientes/parciales y
ACK fuerzan envío. Si hay DATA anterior, sale antes del control en el mismo
send. Antigüedad objetivo1ms: deadline de espera READY se acorta para vaciar
el buffer y vuelve a esperar el flanco fresco dentro del deadline original.
No es una garantía de tiempo real:planificación y otras etapas pueden demorar.
Al cerrar/reemplazar sesión se descarta buffer;ningún byte viejo va al nuevo
cliente. Envío parcial/EAGAIN/EINTR/error desconecta,sin continuar ese stream.

ABBA114/112ticks,N3456,8×30s. Políticas admisión/rechazo yAPPLIED fuera de
ventanas. Gate:todos íntegros,B holgura>=10%,queue<4,slack positivo,
envío medio>=2% mejor sin solapamiento en ambas tasas. Sólo si pasa:
60+3×120s112. Snapshot/backup,un dueñoQ,finally restaura firmware/relay/ADC/
generador exactos,hash y10s continuidad. Sin incorporación productiva.

La métrica envío MCU abarca cadenaSPI/relay solapada,no sólo TCP. No asumir
que dividir send entre dos recupera70µs. No se cambia frecuencia ni protocolo
SPI;no aceptación eléctrica,analógica,GUI,RADIO/FILTER,dual niUART.
