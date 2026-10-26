# Telemetría privada del relay V18

Estado: fuente preparada y dos pruebas offline aprobadas. No compilada para
el Q, no instalada y sin aceptación física. No cambia el firmware MCU ni
las fuentes de `arduino/v18/relay`.

`prepare.py` copia el relay de producción a un directorio nuevo y exige anclas
exactas. `candidate_v2.manifest.json` conserva hashes de la base y del candidato. No ejecutar
otra vez sobre el candidato existente: sus bytes se preservan para revisión.

La única fuente existente modificada en la copia es `unoq_config_stream.c`;
se agrega `telemetry.h`. Las tablas, política de CPU/SPI, capacidades, validación
y cola de envío permanecen iguales.

Candidato vigente: `candidate_v2/`; `candidate/` conserva la primera revisión.
Mediciones acumuladas desde el arranque (mezclan startup y cambios de perfil;
no atribuir estos máximos al último perfil sin una corrida dedicada):

- Máximo de espera READY, incluida la espera normal por producción. No equivale
  por sí solo a retraso de scheduling.
- Duración de ioctl SPI y máximo intervalo entre comienzos de transferencias.
  El intervalo también incluye el servicio normal y los cambios de perfil.
- Pico de backlog incluyendo la trama recién encolada, llamadas send, EAGAIN,
  EINTR, envíos parciales, errores y rechazo por cola llena.

El wrapper conserva retorno y errno de send; la cola original conserva los
parciales y su orden. No se imprimen mensajes por trama: sólo fallo de integridad, fallo de envío y salida. El progreso periódico
original se conserva sin agregar escritura periódica de diagnóstico. Imprimir puede introducir pausa:
la medición física deberá evaluar ese coste y separar las transiciones.

Prueba offline:

```sh
python -m unittest experimentos.relay_telemetry_v18.test_telemetry
```

Valida el alcance de los cambios y compila un ensayo C con envíos parciales,
EAGAIN, cola llena, preservación de errno y orden exacto de los bytes. Esto
no comprueba rendimiento, GPIO, SPI ni tiempos Linux del Q.

Siguiente paso: revisar candidato; construir binario privado en condiciones
controladas y comparar coste con el relay aceptado. Antes de usarlo, el
controlador físico debe capturar identidad/estado, respaldar contenedor y binario,
asegurar un único propietario y restaurar exactamente la pareja aceptada. No
apuntar Preparar Q a este candidato ni cambiar los recibos de aceptación.

Revisión Astra: V2 corrige el registro periódico adicional y la omisión del
intento SPI fallido. Pendiente antes de uso físico: métricas por perfil/época,
identificar intentos frente a transferencias completadas y pruebas del bucle
correspondiente. Este candidato todavía no habilita una campaña física.

## Candidato V3

`candidate_v3/` y `candidate_v3.manifest.json` son la versión vigente.
Separa por bits, modo, período codificado (incluye geometría) y época confirmada
antes de la transferencia. El intento que recibe un ACK de cambio se contabiliza
con el perfil previo; la siguiente iteración inicia el intervalo nuevo. No hay
impresión al cambiar: guarda ocho intervalos en memoria y cuenta los descartados.
El arranque queda en su intervalo inicial. Mide intentos SPI, completadas y
fallidas, incluyendo la duración del intento fallido. Los resúmenes conservan
errno y se imprimen sólo al fallo/salida.

Las dos pruebas offline incluyen ahora cambios de configuración/época, no reset
para la misma identidad, historial acotado y duración de SPI fallida. No se ha
medido el coste en el Q ni compilado el relay completo para Linux. El cambio de
cliente TCP sin cambio de época comparte contadores del perfil: no interpretar
estos contadores como exclusivos de una sesión de cliente.

## Candidato V4 vigente

`candidate_v4/` conserva V3 y elimina el informe adicional al fallar el cliente
TCP, porque ese camino continúa adquiriendo. La revisión de Astra no encontró
otros bloqueantes en V3. V4 imprime diagnóstico nuevo únicamente al fallo de
integridad (que termina el relay) y a la salida; el log original se conserva.
Dos pruebas offline ampliadas aprobadas. Pendiente compilación Linux y medición
física del coste, con controlador de respaldo/restauración antes de instalar.
