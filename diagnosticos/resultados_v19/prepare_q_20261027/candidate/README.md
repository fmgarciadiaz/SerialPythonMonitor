# Candidato de diagnóstico del relay V19

**Actualización 28/10:** hay un [build ARM64 actualizado y sondeo físico privado](../../../../docs/RELAY_CANDIDATO_V19_20261028.md).
El artefacto nuevo está en `../../relay_candidate_build_20261028/relay-candidate.bin`;
el viejo binario dentro de `relay/` sigue obsoleto. La pareja aceptada se restaura
después de cada ensayo; el candidato no está promovido.

Este candidato aislado busca distinguir `ENOBUFS` de errores TCP como `EPIPE` y
`ECONNRESET`. La versión inicial añadía contadores y lecturas de reloj en el
camino de envío normal; Astra detectó que eso contradecía el objetivo de una
captura pasiva. El **fuente corregido** sólo registra `errno`, ruta (envío
directo o FIFO), cola y offset en el camino de error. No añade llamadas de
reloj en los envíos exitosos. La revisión del 28/10 añade una recuperación
acotada de FIFO llena: antes de rechazar la trama intenta enviar el prefijo
retenido, con un máximo compartido de dos sends no bloqueantes. Conserva orden,
bytes, capacidad, SPI, firmware y perfiles. Está separado de
`arduino/v19/relay` y no está instalado en el Q.

El build ARM64 está en `relay/unoq_stream`; hash y arquitectura figuran en
`manifest.json`. Se compiló en un contenedor temporal limitado mientras la pareja
V19 estaba activa. Durante el build el relay de producción rechazó una trama con
`dropped_nodes=2` y se detuvo. La contención es causa plausible; tratá el build
concurrente como causal hasta probar lo contrario. No repetir compilación durante
adquisición.

El binario que está en `relay/unoq_stream` se compiló antes de corregir la
instrumentación y ahora está **obsoleto**; no instalarlo. El fuente corregido
se compiló posteriormente en la carpeta nueva indicada arriba. Las pruebas en Q
se ligan al hash del build, con backup/rollback pareado y restauración física.
El recibo de producción aceptado no se debe editar para hacer pasar el candidato.

`relay/` contiene el árbol aislado; cambian `unoq_config_stream.c` y
`frame_send_queue.h`; el
manifiesto enumera los hashes de producción y candidato. El log corregido
incluye errno, ruta de envío, cola, offset y capacidad sólo al fallar. Los
contadores acumulados, pico y tiempo desde el último envío se quitaron porque
no son necesarios para separar el error de socket de la FIFO llena.

`check_frame_send_queue.c` ejercita el header de cola candidato con bytes y
resultados simulados. Cubre orden exacto, `EAGAIN`, `EINTR`, escritura parcial,
completar una trama previa y fallar en la siguiente, escritura cero (`EIO`),
FIFO llena (`ENOBUFS`), recuperación cuando el socket vuelve a estar disponible,
preservación de `EPIPE` y el presupuesto de dos sends. La salida esperada es `PASS`;
se puede correr desde la raíz con:

```sh
cc -std=c11 -Wall -Wextra -Werror diagnosticos/resultados_v19/prepare_q_20261027/candidate/check_frame_send_queue.c -o /tmp/v19-check-frame-send-queue
/tmp/v19-check-frame-send-queue
```

El harness valida la FIFO candidata y el flujo de bytes simulado, no compila
el relay de Linux ni verifica sus mensajes de error. El build ARM64 anterior se
hizo en un contenedor del Q mientras la adquisición estaba activa; en esa
ventana el relay aceptado cerró con un frame `dropped_nodes=2`. La concurrencia
es un disparador plausible, no una causalidad probada. No volver a compilar en Q
durante adquisición. La pareja aceptada ya fue recuperada y pasó una nueva
repetición V(t); ver el estado actual en el diagnóstico enlazado.
