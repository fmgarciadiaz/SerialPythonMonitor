# ADC8/CH1 1,6000 MS/s incorporado — (s/holg.)

El selector y el resumen aplicado muestran `1,60 MHz (CH1) (s/holg.)`.
Perfil exclusivo ADC8, CH1 y SPI: 100 ticks, nodos de 3456 muestras.
La preparación automática privada a 112 ticks dura 2 s y valida el flujo sin
publicar muestras transitorias. No habilita esta tasa para otros bits, dual o UART.

## Aceptación integrada

Informe: [campaña completa](../diagnosticos/resultados_v17/adc1600_integration_20261016_153557/report.json).
Firmware, relay y receptor integrados: 60 s + tres corridas independientes de
120 s, con reinicio entre corridas. Total: **671.613.984 muestras**, sin nodos
perdidos ni errores fatales, con validación de CRC, secuencia, época e índices
/ tiempos de muestras.

| Duración | Margen medio de envío | Pico de cola |
| --- | --- | --- |
| 60 s | 7,376 % | 3 / 8 |
| 120 s, corrida 1 | 7,464 % | 4 / 8 |
| 120 s, corrida 2 | 7,432 % | 4 / 8 |
| 120 s, corrida 3 | 7,461 % | 4 / 8 |

La integridad pasó. La holgura no cumple el objetivo original de margen medio
≥10 % y pico <4 desde el arranque: se conserva `(s/holg.)`. Los ocho nodos son
capacidad física real; no se reinicia ni oculta el máximo observado. Esta
aceptación integrada reemplaza la evidencia aislada anterior para publicar
el perfil. No acredita precisión analógica, WAV, RADIO simultáneo ni FPS visibles.

## Implementación y compatibilidad

- SPI solicitado a 40 MHz, tramas SPI de 8 bits, DMA de accesos de 4 bytes,
  burst 4 y CRCSIZE=7. La aceptación es empírica; no certifica eléctricamente SCK.
- Pipeline de tres buffers: cada nodo se conserva hasta terminar su último
  frame físico. Ocho nodos de 3456 muestras reutilizan la arena existente;
  las tasas normales mantienen cuatro nodos y su disposición anterior.
- Relay con FIFO10, afinidad CPU2 y governor `performance` durante este perfil
  y su preparación. Al salir restaura política y afinidad previas. El governor
  pertenece a policy0 compartida por los cuatro núcleos.
- Cola TCP acotada que conserva desplazamientos de envíos parciales y orden
  de bytes. Las pruebas locales ejercitan envío parcial, EAGAIN/EINTR y errores.
- `loop()` compilado con `Os` reduce 1264 bytes de texto frente al candidato
  que no cargaba. El núcleo estaba activo con lista LLEXT vacía; no se capturó
  el código exacto del fallo del cargador. CRC y PING conservan su código.

Pasaron los controles físicos de tasa normal antes/después, ADC8/1403508,
dual ADC14/363636 y ADC16/40000. Son controles breves de compatibilidad,
no nuevas calificaciones prolongadas de esos perfiles.

Q conserva el firmware integrado validado SHA256
`23bc0e28212ea8c44de498f58a471a480e43feaa55899924b80d304f347de8ac`.
Se restauraron ADC8/1403508 SPI y todos los campos originales del generador
apagado; recuperación de 10 s con 14.031.360 muestras y cero dropped/fatal.
Los controles de regreso verificaron también el governor original `schedutil`.

## Trazabilidad

[Registro de intentos](../diagnosticos/resultados_v17/adc1600_integration_closure.json).
Los intentos anteriores permanecen archivados con fuentes, logs y restauración:
pérdida MCU en la primera integración; envío TCP parcial en otra revisión;
nueva pérdida MCU antes de ampliar la cola; y revisiones que no llegaron a
cargar el módulo. No se cuentan como aceptación. El informe seleccionado
conserva hashes, respaldo previo, ELF/mapa, fuentes y logs de relay.

Las 15 pruebas locales pasaron tras habilitar el perfil. Cubren almacenamiento real con sanitizadores, cola TCP,
configuración/preparación y callbacks, selector y perfiles. La prueba del
selector aísla una incompatibilidad previa de la leyenda de pyqtgraph; no es
una prueba completa de dibujo.

Siguiente etapa: medir mejoras equivalentes para 10, 12, 14 y 16 bits en
experimentos separados, sin extrapolar la aceptación de ADC8.

## Revisión del gráfico y de la entrada desde una tasa alta

Tras el aviso de gráfico detenido, se guardó el log
`diagnosticos/resultados_v17/adc1600_gui_failure_relay.log`: el relay había
rechazado una trama con CRC correcto y seis nodos perdidos todavía en
ADC8/1403508, durante la transición de perfiles. El corte del relay impide
que el gráfico reciba nuevos datos. La aceptación inicial entraba desde
una tasa baja y no cubría esa entrada directa desde 1,4035 MHz.

El receptor ahora confirma una etapa privada ADC14/40000 antes de preparar
112 ticks y aplicar 100 ticks. Así los ajustes de governor/afinidad y SPI
se hacen después de drenar la época de tasa alta. Sólo se publica la
confirmación del destino final y se conservan las validaciones estrictas.
No se midió individualmente la duración de cada syscall de la transición.

Además, se reprodujo y corrigió una excepción de construcción de la leyenda
con versiones de pyqtgraph sin `ItemSample.sigClicked`: los clics usan la
misma acción de canal que la etiqueta. El test del selector ya construye la
leyenda real y comprueba el clic cuando corresponde.

Pruebas posteriores: 15 pruebas locales pasaron; corrida con receptor y GUI
Qt offscreen de 40 s, 59.710.176 muestras sin errores. Luego ventana Cocoa
visible durante 40 s, entrada desde 1,4035 MHz y dos cambios de ida/vuelta:
51.485.760 muestras, 2.003 eventos de dibujo agregados de los PlotWidget,
cola de entregas a GUI pico 4 y sin errores. Este contador no equivale a
FPS exclusivos del gráfico principal. Informes `adc1600_gui_review.json`
y `adc1600_gui_review_visible.json` en `diagnosticos/resultados_v17/`.
Estas comprobaciones breves no reemplazan la campaña prolongada ni prueban
combinaciones con FILTER/RADIO activados.

## Conservación del generador al seleccionar 1,60 MHz

Se encontró un efecto lateral en la preparación: enviaba
`GeneratorConfig(enabled=0)`, que también imponía los valores predeterminados
(frecuencia de 2,5 Hz, amplitud de 3,3 V y offset de 1,65 V). La confirmación
actualizaba las perillas del generador en la GUI. Esto explica el salto de
amplitud y el cambio de controles informado al seleccionar esa tasa; no
constituye una medición de ganancia analógica del ADC.

Se eliminó esa orden: la preparación modifica sólo la adquisición y conserva
la configuración y el estado del generador. Reaplicar una configuración ya
activa tampoco repite la preparación. Las 17 pruebas locales pasaron,
incluyendo generador con valores no predeterminados, controles verticales,
restauración de callbacks en errores y ausencia de órdenes al DAC durante
la preparación.

Comprobación física posterior de 40 s con generador apagado y parámetros
no predeterminados (seno, 1234 Hz, final 2345 Hz, niveles 0..1024, duración
2345 ms): entrada desde 1,4035 MHz y dos cambios de ida/vuelta. Sin errores,
51.535.008 muestras y controles del generador conservados. Configuración
previa de ADC/generador restaurada. Informe:
`diagnosticos/resultados_v17/adc1600_gui_generator_preserved.json`.
Qt Cocoa registró dibujo, pero la ventana no estaba expuesta al final;
esta corrida no certifica FPS visibles sostenidos. La primera versión del
comprobador incluía el apagado de cierre como si fuera parte del período
medido; se conserva ese resultado separado con sufijo
`_shutdown_included.json`. La corrida final distingue ambos períodos.

## Revisión con Astra: confirmaciones y controles

Revisión local, sin operar Q ni modificar firmware:

- Se conservan CH1, FILTER y RADIO como segundo espectro al cambiar entre
  tasas de un canal. Antes cada confirmación imponía `Ninguno`. Se conserva
  el comportamiento existente de entrada dual→CH1 y restauración al volver.
- La entrega de muestras finales se abre dentro de la confirmación APPLIED
  del destino. Una lectura puede traer esa confirmación y DATA posterior;
  antes esos DATA seguían silenciados hasta retornar `configure()`. Se
  confirma primero la configuración y luego se entregan sus primeras muestras,
  manteniendo ocultos todos los datos privados anteriores a esa frontera.
- Pruebas específicas cubren los tres canales espectrales válidos, la
  conservación del generador y el orden datos privados→APPLIED→DATA final.

Estas correcciones no aumentan el margen físico de envío. La revisión no
aporta evidencia causal para atribuir el 7,4 % de margen a `Os` ni para
promover otra tasa. El siguiente experimento de rendimiento necesita una
comparación en igualdad de condiciones y métricas separadas de MCU, relay,
procesamiento y dibujo.

## Latencia al conectar con Q ya activo

El autoinicio informa si realmente tuvo que arrancar Q/relay. La espera de
estabilización de 5 s se conserva para ese caso; se omite cuando ya estaban
activos la aplicación y el relay de identidad correcta. Se mantienen la
etapa privada de baja tasa y los 2 s de preparación a 112 ticks.

Comparación con Q real, mismo firmware y entrada ADC8/1403508, 20 s por
corrida: primeras muestras a 8,193 s con la espera anterior y 3,215 s con
la mejora. Sin errores en ambos casos, cola de entregas GUI pico 2 y ajustes
restaurados. Informes `adc1600_startup_baseline.json` y
`adc1600_startup_optimized.json` en `diagnosticos/resultados_v17/`.
Se usó Qt offscreen: mide latencia de recepción y entrega/dibujo fuera de
pantalla, no latencia visual sostenida en macOS. No se redujeron las esperas
para un arranque real de Q. Las 35 pruebas locales de configuración,
procesamiento e identidad/autoinicio pasaron, incluyendo notificación de
arranque sólo tras éxito y ausencia de notificación con Q ya activo.
