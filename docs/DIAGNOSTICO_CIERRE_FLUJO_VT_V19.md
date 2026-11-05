# Diagnóstico: cierre de flujo durante V(t) en V19

## Estado del incidente

Una corrida de V(t) a ADC8/1,860 MS/s terminó con `RuntimeError: El Q cerró el
flujo` a los 18,9 s. El host dejó de recibir TCP; el relay registró
`PC disconnected or too slow; close session (sent=-1)`. La adquisición del Q
continuó, y la recuperación posterior y una repetición de V(t) de 24 s pasaron.
Es intermitente y no se atribuye todavía a un defecto específico.

| Evidencia | Resultado |
|---|---|
| Corrida con cierre | [gui_vt_smoke.json](../diagnosticos/resultados_v19/prepare_q_20261027/gui_vt_smoke.json): 18,9 s, 28,1 millones de muestras, sin A0, sin RADIO, error de flujo y cierre sin confirmación de apagado |
| Señal de carga en host | Retardo máximo de entrega GUI 604 ms, heartbeat máximo 755 ms y cola GUI pico 4; son indicios de pausa, no prueba causal |
| Relay | El log confirma cierre de la sesión TCP y luego siguen aumentando `valid` y `pairs`, con `dropped=0`; la adquisición MCU/SPI no se detuvo |
| Repetición V(t) | [gui_vt_repeat_smoke.json](../diagnosticos/resultados_v19/prepare_q_20261027/gui_vt_repeat_smoke.json): 24,1 s, unos 59 Paint fps, error vacío y salida apagada confirmada |
| Recuperación | [post_vt_smoke_recovery.json](../diagnosticos/resultados_v19/prepare_q_20261027/post_vt_smoke_recovery.json): 10,004 s y 18,6 millones de muestras, sin pérdidas/fatales y con perfil restaurado |

## Qué significa `sent=-1`

En este perfil, el relay activa la ruta de cola `scope_send_frame()`. Su FIFO
acepta hasta 64 tramas SCP1. El log actual pierde `errno` y no imprime el nivel
de cola, por lo que `sent=-1` no distingue entre:

- FIFO llena, que devuelve `ENOBUFS`;
- error TCP persistente, por ejemplo `EPIPE` o `ECONNRESET`;
- envío de cero bytes, convertido a `EIO`.

Los bloqueos recuperables `EAGAIN`, `EWOULDBLOCK` e `EINTR` mantienen la trama
pendiente y no deberían cerrar la sesión mientras haya espacio en la FIFO. La
demora GUI registrada hace plausible una pausa del consumo, pero el receptor de
muestras corre en un proceso hijo y el log disponible no demuestra que la GUI
haya llenado la FIFO. Tampoco permite descartar que ADB/TCP cerrara el extremo.

La hora se correlacionó leyendo el log del relay con timestamps: la corrida
empezó a las 22:49:56.704 UTC y el cierre aparece a las 22:50:16.721 UTC
(20,017 s después, próximo al punto en que la GUI notificó el fallo). A las
22:50:08.538 el relay reportaba `dropped=0`; a las 22:50:18.539 seguía contando
pares con `dropped=0`. Extracto guardado en
[relay_correlation.log](../diagnosticos/resultados_v19/prepare_q_20261027/relay_correlation.log).

## Siguiente captura para identificar la causa

Se preparó el árbol aislado
[candidate](../diagnosticos/resultados_v19/prepare_q_20261027/candidate/README.md).
Sólo cambia el registro del camino de error: guarda `errno` y su nombre, bytes de
tramas completas, `send_queue.count`, `send_queue.offset`, máximo de cola y tiempo
desde el último envío completo. No cambia límites, reintentos, perfiles ADC, SPI
ni política de prioridad. El harness local pasa al comprobar `EAGAIN`, escritura
parcial, cola llena y error fatal.

El build ARM64 y la corrida física siguen pendientes: el compilador actual vive
en un contenedor del Q y la compilación pareada requiere detener apps. Antes de
cargar el candidato hay que compilarlo en una ventana de mantenimiento, registrar
una identidad experimental separada, respaldar y ensayar rollback, capturar el
incidente y restaurar/verificar hashes e identidad. El recibo aceptado de
producción no se modifica. Si aparece
`ENOBUFS`, correlacionar el máximo de cola con los créditos RF y las pausas del
receptor; si aparece `EPIPE`/`ECONNRESET`, inspeccionar el túnel ADB y el dueño
del socket. No aumentar buffers ni cerrar automáticamente el diagnóstico con
una modificación de comportamiento antes de esa distinción.

## Estado actual del Q

Inventario de solo lectura del 27/10/2026: Scope V19 y su relay forman la única
pareja activa; V17 está detenida y V18 sin inicializar. Los SHA256 instalados
coinciden con el recibo V19. El incidente no dejó
una campaña activa. Ver [inventario](../diagnosticos/resultados_v19/prepare_q_20261027/inventory_final.json)
y [estado de versiones](VERSIONES.md).


## Candidato compilado y efecto durante recuperación

El relay diagnóstico ARM64 se compiló en el contenedor temporal descrito en
[candidate](../diagnosticos/resultados_v19/prepare_q_20261027/candidate/README.md).
Binario: `aarch64`, 74 072 bytes, SHA256
`f0ce6b21efdf6018b569d286c44a3cf7ec1f3f024d8dfc8c395ef8720c26ceb9`. No se
instaló. El harness de la FIFO volvió a pasar.

Durante esa compilación, el relay aceptado terminó con `ExitCode=1` y
`OOMKilled=false`. La trama SCP1 `kind=20` tenía CRC correcto, pero el contador
MCU en el offset 56 indicaba `dropped_nodes=2`. El build se ejecutó con límites
de 0,20 CPU y 768 MiB, pero coincidió con la pérdida; por prudencia debe
considerarse causal hasta demostrar lo contrario. No se debe compilar con
adquisición activa.

Se verificaron los SHA256 aceptados del firmware y relay. Reiniciar el relay
solo no bastó: rechazó el perfil que ya estaba corriendo. Luego se reinició
Scope V19 con el BIN aceptado; una prueba GUI corta a 8 bits/1,6 MS/s produjo
0 muestras y el relay terminó por `READY wait: Connection timed out`. El estado
final es app V19 activa, firmware aceptado y relay detenido; el candidato no
está instalado. El informe completo es
[recovery_report.json](../diagnosticos/resultados_v19/prepare_q_20261027/candidate/recovery_report.json).

No se continúa con otra captura hasta recuperar READY mediante un reset soportado
del MCU/placa y reconectar el monitor.


La trama rechazada se decodificó offline: ADC8 a 1 860 465 S/s, nodo de 3 488
muestras, cola de firmware con 7/8 slots ocupados y pico 8/8. `dropped_nodes=2`,
`fatal_errors=0`; CRC válido. `send_previous=1 872 114` ciclos equivale a
11,701 ms por nodo, frente a 1,875 ms entre nodos (6,24 intervalos). Esto ubica
el fallo en backpressure/hambruna del consumidor hasta llenar la cola MCU, no en
una corrupción CRC TCP. La compilación concurrente es un disparador plausible,
pero el scheduler exacto no quedó probado. El registro detallado está en
[recovery_report.json](../diagnosticos/resultados_v19/prepare_q_20261027/candidate/recovery_report.json).


Después, ADB `reboot` devolvió `closed`, pero el Q reapareció con los mismos
`StartedAt` del contenedor; no fue un reinicio confirmado y el relay continúa
detenido. La app y ambos hashes aceptados permanecen intactos. Hace falta un
ciclo físico de alimentación o un reset validado que restablezca READY antes de
seguir.

## Recuperación confirmada y repetición posterior

El 27/10 se ejecutó `monitor.v19.q_support.service` sobre el serial
`1060031107`. El servicio volvió a cargar Scope V19 mediante la secuencia
soportada, verificó la identidad del firmware y relay aceptados y completó una
captura de 10,023 s: 313.344 muestras, flujo continuo, cero nodos perdidos y
cero errores fatales. Informe:
[`service_recovery.json`](../diagnosticos/resultados_v19/prepare_q_20261027/candidate/service_recovery.json).

Después se repitió V(t) en ADC8/1.860.465 S/s durante 32,09 s, con RADIO/A0
apagadas y ventana visible durante la adquisición. La prueba recibió 54.005.576
muestras, dibujó 1.816 eventos Paint, tuvo retardo máximo de entrega GUI de
37,54 ms y terminó sin errores; el cierre confirmó salida apagada y liberación
del worker. No se reprodujo el corte que antes ocurrió a los 18,9 s. Evidencia:
[`gui_vt_post_recovery.json`](../diagnosticos/resultados_v19/prepare_q_20261027/gui_vt_post_recovery.json).

El inventario posterior confirma la pareja V19 coherente y activa, sin otras
apps/relays en ejecución:
[`inventory`](../diagnosticos/resultados_v19/prepare_q_20261027/inventory_post_vt.json).
La repetición corta descarta que el estado recuperado impida V(t), pero una
corrida exitosa no explica ni elimina el fallo intermitente. El candidato de
telemetría del relay sigue sin instalarse; la captura de `errno`/cola continúa
siendo el próximo paso para identificar el motivo de `sent=-1` si reaparece.


## Reproducción 29/10: US, 10 bits y detalle completo

Caso `us10_1355932_host_20261029`: firmware y relay aceptados, 1.355.932 S/s,
V(t) 0,534 s, detalle 100, RADIO encendida. Scan no completó: un pintado Qt
registró 1.049,94 ms y RF pendiente llegó a 1,00042 s. No se elevaron límites
ni descartaron muestras. Sesión cerrada con `hardware_restored: true`, sin
 errores de restauración; recuperación continua con cero pérdidas/fatales.

La cadencia adaptativa ayuda al costo acumulado pero no resuelve una pintura
individual mayor al presupuesto. Dibujar segmentos no mejoró suficientemente
el benchmark. Rasterizar todos los puntos sobre QImage en un hilo tampoco
libera la GUI en este entorno: 724.000 puntos, 388,83 ms de raster y hueco de
heartbeat de 382,47 ms. El binding retiene el GIL durante ese trabajo.

Astra propone proceso dedicado con un solo trabajo en vuelo, imagen terminada
para GUI y datos originales intactos para cursores/STOP. Aún no integrado;
falta medir IPC/copia y preservar transformaciones, estilos y generaciones.
Las escalas temporales y colores de medición sí están implementados. Las
pruebas dirigidas iniciales pasaron 32 casos; otras 21 de cursores y unidades
pasaron tras invalidar el costo de dibujo al cambiar la ventana temporal.
