# Primer subpaso de control PC → MCU

Fecha: 2026-10-02. Corresponde a la base del **paso dos** del
[Plan de trabajo](../Plan%20de%20trabajo.md). El cambio efectivo SPI/UART y
los selectores de transmisor todavía están pendientes.

## Implementado

Python origina PING con identificador propio; Linux lo valida y lo transmite
por SPI. El MCU devuelve el mismo identificador en el siguiente DATA. Python
espera esa respuesta y obtiene la configuración y contadores presentes en ella.
No hay una confirmación sintetizada por Linux.

[Contrato, comandos de prueba y próximos subpasos](../docs/CONTROL_TRANSPORTE.md).
El firmware ADC continúa idéntico al validado en el paso uno.

## Prueba física de consultas

[Log de 1.000 consultas](resultados_usb/20261002_020646_540912_control.json):

- 1.000 identificadores confirmados por el MCU, cero consultas fallidas.
- 15.161 bloques / 796.161 pares verificados durante las consultas.
- Sin pérdidas, CRC inválidos, errores MCU ni discontinuidades temporales.
- Mayor latencia observada: 60,735 ms.
- La mitad de las solicitudes se envió dividida en cuatro fragmentos TCP,
  con pausas deliberadas de 5 ms; la latencia incluye esas pausas.
- Una solicitud con CRC incorrecto y otra abandonada a los 17 bytes fueron
  rechazadas. Tras cada rechazo se abrió una nueva sesión y se confirmó
  otra consulta con los contadores MCU limpios.

Repetición con el arranque por flanco nuevo y aislamiento de ACK pendientes:
[log final](resultados_usb/20261002_020920_399878_control.json).
**1.000/1.000 consultas**, 15.485 bloques y **813.162 pares** sin errores.
Latencia máxima 64,747 ms; ambos casos de rechazo y las consultas posteriores
volvieron a pasar. El relay final es el utilizado en esta repetición.

Las **75 pruebas locales** pasan. Incluyen comparación exacta del PING PC
con el formato que acepta el firmware, fragmentación, rechazo de ACK viejo,
CRC obligatorio y wrap del identificador sin usar el valor de arranque.

## Arranque y aislamiento de sesiones

El [primer intento](resultados_usb/20261002_arranque_control_inicial.txt)
rechazó el bloque inicial antes de ninguna consulta. No se capturaron entonces
los contadores detallados necesarios para establecer la causa. El segundo
arranque funcionó y permitió la prueba de 1.000 consultas; eso por sí solo no
explica el primer fallo. Se amplió el informe de integridad ante nuevos fallos.

El relay se inicia siempre después de reiniciar el MCU mediante la herramienta.
Por eso ahora exige un **flanco nuevo de READY incluso en la primera transferencia**.
No interpreta como autorización el nivel alto que GPIO70 tenía para el loader.
Esto elimina una ambigüedad del arranque; no se atribuye retroactivamente el
fallo sin captura a una causa demostrada. Los verificadores SPI aislados
conservan su comportamiento de reconexión a un bloque ya preparado.

Antes de aceptar un cliente nuevo se deja terminar cualquier ACK de una consulta
abandonada. Así V8 no recibe como propia la respuesta de una sesión anterior.

## Regresión de V8 después de las consultas

[Prueba final del monitor](resultados_usb/20261002_021006_543187_monitor.json):
462.954 pares procesados, frecuencia indicada 31.250 Hz, 266.380 filas CSV
sin huecos y 167.989 pares después de reconectar. Cero errores, `pass=true`.
No se reinició el Q entre las consultas y esta prueba de interfaz.

## Alcance

Este ensayo prueba consultas y transporte de ida/vuelta simultáneo con ADC.
No prueba SET_TRANSPORT, ajustes de bits/frecuencia ni controles del generador.
V8 mantiene su interfaz y el modo SPI; UART/R4 sigue siendo el siguiente subpaso.
