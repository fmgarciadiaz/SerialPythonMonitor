# V20: búsqueda de puertos sin bloquear la ventana

Se localizó un bloqueo concreto: el constructor llamaba `refresh_ports()`
antes de mostrar la ventana; esa función ejecutaba ADB y la enumeración
serial en el hilo GUI. La misma ruta existía en V19, por lo que no demuestra
una regresión propia de V20. La consulta ADB puede esperar hasta3s; el botón
de actualizar también detenía la atención de eventos durante esa espera.

V20 ahora busca en un hilo daemon y entrega sólo datos a un slot GUI. La
ventana se puede mostrar mientras busca. Actualizar indica progreso con
`…`, la conexión queda deshabilitada durante la búsqueda y los errores
aparecen en el estado sin modal. Se conservan las selecciones y se ignoran
resultados obsoletos, posteriores al cierre o de una conexión reemplazada.
Cerrar no espera el hilo ni destruye un QThread activo. No se cambió el
procedimiento de conexión al Q, restauración, tasas ni procesamiento.

La [comparación local antes/después](../diagnosticos/resultados_v20/startup_gui_20261104/discovery_before_after.json)
ejecuta el método original del respaldo y el nuevo con la misma búsqueda
simulada de350ms, alternados dos veces. Antes: retorno354,5/354,9ms y primer
heartbeat GUI355,8/354,9ms. Después: retorno0,23/0,21ms y primer heartbeat
7,3/6,4ms. Qt offscreen, sin Q: mide atención de eventos, no FPS visibles.

El perfil de importación/constructor sin discovery real también encontró
esperas en `importlib.get_data` de V19, con dos límites de20s agotados.
Con caché temporal V19 completó importación en11,39s y constructor5,05s,
incluidos3,34s de lecturas de texto; V20 tuvo muestras de importación~1,5s
y constructor~1,2s. No se aisló causa de almacenamiento/caché ni se atribuye
al problema del usuario. Numba aportó~0,32s al constructor V20 observado.

Cuatro pruebas focalizadas pasaron: GUI sigue atendiendo heartbeat durante
búsqueda lenta, conserva selección, ignora resultados obsoletos/cierre/cambio
de conexión, muestra errores y detecta muerte temprana del receptor.
[Comando/resultados](../diagnosticos/resultados_v20/startup_gui_20261104/tests.txt).
Backup SHA: `respaldos/host/v20_before_async_ports_20261104/manifest.json`.
No quedaron procesos locales de prueba activos. No se operó Q.

El bloqueo intermitente al conectar sigue pendiente de reproducción concreta.
Un hijo vivo retenido durante importaciones no tiene un plazo de arranque
propio; cancelar puede esperar hasta60s su cierre. No se cambiaron esos plazos
sin distinguir primero si el hijo ya posee hardware. La captura EOF añadida
antes sólo lee atributos estándar del decoder al fallar y no ejecuta trabajo
en el arranque ni en el camino normal de muestras; las pruebas de EOF y
límites pasaron en el bloque anterior.

## Reintento después de una salida inicial del worker

Se reprodujo otro fallo local concreto: si `OutputWorker.run()` termina durante
el setup y emite `finished` antes de conectar, su QThread termina pero la GUI
conserva `serial_worker` y el estado «Conectando». Faltaba vincular el final
del QThread con la limpieza de la ventana. Una excepción al crear MacActivity
es una ruta real que emite ese `finished`; no se afirma que haya sido la
excepción del usuario.

V20 ahora limpia al terminar su QThread actual, usando la desconexión
asíncrona existente. Una notificación de un intento anterior no puede borrar
el nuevo. Si no existe confirmación de apagado se conserva «estado del Q sin
confirmar», sin convertir la salida del thread en éxito de restauración.
No se cambió el tiempo de espera del receptor ni la propiedad del Q.

La prueba previa falló porque la referencia al worker seguía presente después
de terminar el thread. Después pasaron3pruebas de reintento (1,898s): dos
intentos consecutivos liberan la interfaz, `finished` viejo se ignora y una
excepción real en setup sigue emitiendo `finished`. El grupo con discovery y
muerte inicial del proceso también pasó6pruebas (4,277s), antes de añadir
la última aserción de setup. [Evidencia y comandos](../diagnosticos/resultados_v20/connection_retry_20261104/tests.txt).
Backup SHA: `respaldos/host/v20_before_connection_retry_20261104/manifest.json`.
No se accedió al Q ni quedaron procesos locales de prueba activos. Este fallo
de limpieza no identifica la causa original de los cuelgues ni demuestra un
defecto de lock; un hijo vivo bloqueado durante importaciones sigue pendiente.

## Ciclo físico normal de conexión y reconexión

Con Q libre se verificó por lectura la pareja V20 exacta y el estado inicial
ADC14/32 ticks dual, SPI, generador OFF con parámetros originales y WAV IDLE.
La [prueba GUI normal](../diagnosticos/resultados_v20/normal_reconnect_20261104/report.json)
conectó ADC14/40k dual en2,952s, adquirió10,064s (401.666muestras nuevas),
desconectó y reconectó en3,475s. La segunda adquisición sostuvo10,088s con
403.456muestras nuevas. Sin RADIO, tasas privadas, override de transporte,
compilación ni despliegue. El helper sólo amplió la comprobación de
restauración a10s y guardó etapas; no activó temporizadores detallados.

Ambas sesiones restauraron exactamente el snapshot inicial:10,025s y10,022s,
313.344muestras cada una, cero pérdidas/fatales, actividad del receptor liberada
e identidad MCU/relay igual antes/después. Ventana expuesta en las etapas de
adquisición; cierre confirmado a49,068s, sin errores. Q quedó V20 restaurada
y sin monitor de prueba. Es un ciclo funcional corto: no demuestra resuelto
el cuelgue intermitente, FPS sostenidos ni estabilidad a2M.
