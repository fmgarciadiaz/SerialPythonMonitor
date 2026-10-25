# Medir el arranque y los cambios de adquisición V17

La traza es opcional: iniciar el monitor con `SPM_STARTUP_TRACE=1` habilita
registros en memoria, con reloj monotónico. Por ejemplo, desde la raíz:

```sh
SPM_STARTUP_TRACE=1 .venv-v13/bin/python -m monitor.v17.app
```

En una sesión Python o depurador que tenga la ventana como `window`, consultar:

```python
snapshot = window.serial_worker.trace.snapshot()
for request in snapshot:
    print(request['generation'], request['kind'], request['bits'], request['rate'])
    began = request['events'][0]['monotonic']
    for event in request['events']:
        print(round(event['monotonic'] - began, 6), event['event'])
```

Consultar mientras el worker sigue conectado; si se necesita conservar el resultado
tras desconectar, guardar previamente una referencia a `window.serial_worker.trace`.
No se escribe un archivo automáticamente. Se retienen las últimas cuatro solicitudes,
con hasta 128 eventos cada una; `snapshot()` devuelve una copia independiente.
Sin la variable de entorno, no hay eventos ni lecturas adicionales del reloj de traza.

`connection_start` comienza cuando se ejecuta el worker; `active_change` comienza
cuando el worker consume el pedido de cambio. Estos tiempos no incluyen el debounce
del selector ni la espera previa en la cola de pedidos. `scope_restarted` queda en
`connection_ready`: un inicio del monitor puede reutilizar una app Q ya activa.

Los eventos separan conexión, identidad, preparación a baja carga y la espera de
cinco segundos (`warmup_5s_*`). Esa espera conserva la guarda existente: autoload,
SPI, perfil con `optimized_transport` y app Q reiniciada. Para ADC8/1.600.000,
la preparación del receptor conserva 14/40.000 → 8/1.428.571 → bombeo de dos
segundos (`settle_2s_*`) → pedido objetivo y `target_applied`. La ruta también se
ejecuta al cambiar una adquisición activa; reaplicar la configuración vigente
registra `configure_noop` y evita la preparación. Los tiempos, perfiles y guardas
no se modifican por habilitar la traza.

`target_configuration_confirmed` precede al aviso GUI; `gui_configuration_installed`
se entrega tras el callback que instala su configuración. `startup_gui_wait_*`
mide la espera inicial del ACK, cuyo timeout continúa siendo diez segundos.
`dsp_prewarm_*` sólo aparece cuando corresponde preparar el proceso DSP inicial.
`first_target_samples_admitted` excluye las muestras privadas y las recibidas antes
de habilitar publicación. `first_batch_reserved` mide la reserva del primer lote;
`first_batch_ready_signal` mide su emisión después del DSP que corresponda.
`first_gui_batch_accepted` indica que el callback GUI terminó con éxito, para el
worker vigente y una adquisición coincidente. Los lotes conservan la generación
de su buffer: trabajo de una solicitud anterior no se atribuye a la nueva.

Estos hitos de entrega no prueban que haya ocurrido un `paintEvent`, ni que los
píxeles fueran visibles. La medición de pantalla requiere una prueba separada.
`acquisition_error` y `worker_finished` permiten reconocer cierres y errores sin
convertir un recorrido incompleto en una medición de arranque exitosa.

## Medición física20/10/2026 · stack activo

[Informe](../diagnosticos/resultados_v17/arranque_20261020_105052.json). Firmware y relay de producción, RADIO/FILTER OFF, sin A0 ni reinicios. Ventanas10s desde primera entrega, GUI real Cocoa. No acredita primer Paint visible ni estabilidad prolongada.

| Transición | Pedido→primera entrega GUI |
|---|---:|
| Conexión base14/40k | 577,3ms |
| Base→8/1403508 | 69,8ms |
| Control→base | 88,0ms |
| Base→8/1600000 | 2064,9ms |
| Objetivo→base | 73,9ms |

En1600, el bombeo programado duró2,00013s. La configuración de preparación llevó21,35ms; el objetivo se confirmó a2,03109s desde que el worker tomó el pedido y la primera entrega GUI a2,06314s. La diferencia con el tiempo desde pedido incluye espera previa del worker. No se preparó proceso DSP porque RADIO/FILTER estabanOFF. La espera5s no se ejecutó: el stack estaba activo. Esto explica unos2s de la demora en esta condición, sin explicar todavía una demora mayor con otras cargas o arranque frío.

Todas las etapas finalizaron con dropped=fatal=0. Restauración exactaADC8/632411SPI dual y generadorOFF, identidad de firmware anterior/posterior igual; control final10s con6321024muestras y dropped=fatal=0. La espera2s permanece intacta. Próximo ensayo: variar sólo esa espera en candidato aislado, conservando las transiciones y comparando arranque/integridad antes de promover un cambio.

## Candidato aislado0,5s · 20/10/2026

[Informe físico](../diagnosticos/resultados_v17/arranque_20261020_110008.json). `medir_arranque_v17.py --candidate-settle 0.5 --target-seconds 60` clona sólo en memoria el método configure y reemplaza la constante de espera; exige una coincidencia exacta del código y guarda su SHA. No cambia el archivo de producción ni el firmware. Los nombres de eventos `settle_2s_*` identifican la fase original: la duración experimental se registra aparte.

El primer lote objetivo llegó a GUI en592,3ms frente a2064,9ms del control previo (reducción1472,6ms,71,3%). La espera medida fue500,20ms; APPLIED objetivo a541,47ms desde la toma del pedido por el worker. Completó96009408 muestras en la ventana60s desde primera entrega, dropped=fatal=0. **Cola pico4: no acredita holgura estricta ni resuelve los desbordes.** Es una sola transición, con stack activo y RADIO/FILTER OFF; no extrapolar a arranque frío, transiciones repetidas o RADIO/A0.

Restauración exacta y firmware idéntico, ADC8/632411SPI dual y generadorOFF; control10s6321888muestras, dropped=fatal=0. La espera de producción sigue en2s. Antes de incorporar: más entradas independientes con espera corta y carga RADIO, guardando fallos y restauración. La cola y las pérdidas a tasas superiores siguen siendo un problema separado.

## Candidato0,5s con RADIO · 20/10/2026

[Informe](../diagnosticos/resultados_v17/arranque_20261020_110344.json). Mismo ensayo privado, ahora `--radio --target-seconds 120`: RADIO habilitada a20kHz con banda predeterminada, FILTEROFF, A0 apagado y stack activo. El prearranque real del procesoDSP tomó1,607s durante la conexión base; esa conexión entregó su primer lote a2,243s. No confundir ese costo inicial con la espera del cambio a1600.

El cambio a1,6MS/s entregó en634,2ms; completó191950560 muestras en120s desde primera entrega, dropped=fatal=0, colaMCU pico3. El control1403508 entregó en95,1ms, cola3 y sin pérdidas. Pendientes globales máximos:9 lotesGUI y3DSP; no apareció error de entrega. La prueba no acredita margen medio de envío ni primerPaint visible. No hay evidencia aquí de escucha, Scan/US o A0.

Restauración exacta, firmware idéntico, ADC8/632411SPI dual y genOFF; control10s6321024muestras sin dropped/fatal. La espera pública continúa2s. El candidato ya tiene una entrada60s sinRADIO y otra120s conRADIO, pero **no** constituye tres entradas independientes120s ni validación deRADIO→A0. Completar esos casos antes de incorporar.

## Campaña completa e incorporación limitada · 20/10/2026

[Campaña](../diagnosticos/resultados_v17/espera_corta_20261020_111213/report.json) · [Revisión de seis corridas](../diagnosticos/resultados_v17/espera_corta_20261020_111213/review.json).

RADIO sinA0 completó tres entradas independientes120s: primeraentrega634,2/624,3/617,5ms, cola3 y sin pérdidas. RADIO→A0 a40kHz completó tres ventanas120s, sin errores ADC ni falta de audio; margen medio15,72–15,80%, cola pico5 en las tres, reserva host mínima152,275ms. La FFT estuvo expuesta100%. Todas las restauraciones y controles finales pasaron, con identidad antes/después igual. **Integridad/audio aprobados; holgura estricta no aprobada por cola5.** No es evidencia de que se resuelvan los desbordes de otros candidatos ni una ampliación deFs.

Se incorporó únicamente la espera0,5s cuando el receptor ya tenía un modo activo al entrar a configure. La primera entrada conserva2s y autoload tras reinicio mantiene su guardade5s. Continúan los perfiles intermedios, los límites y las protecciones de publicación.41tests locales verifican espera inicial/viva, no-op, muestras privadas, callbacks y pipeline. El override experimental ahora aborta para evitar volver a ejecutar campañas obsoletas; para verificar producción usar el harness sin `--candidate-settle`.

No se midió físicamente el arranque frío tras reinicio. La primera entrega GUI sigue siendo una métrica distinta del primerPaint visible.

Verificación física del código integrado sin override: [informe](../diagnosticos/resultados_v17/arranque_20261020_145523.json),120s conRADIO, primera entrega 581.5ms, cola3, sin pérdidas. Restauración exacta y10s sin dropped/fatal.
