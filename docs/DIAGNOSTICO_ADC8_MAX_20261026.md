# Cierre de flujo ADC8 máximo · 26/10/2026

Revisión conjunta con Astra, sin editar firmware ni operar adquisición.
V17 intacta. Se leyeron contenedores y logs del Q tras confirmar que no había
monitor abierto. No se reinició el relay ni se instaló ninguna pareja.

## Causa inmediata confirmada

A las 12:38:29 de Argentina, el relay rechazó una trama kind20 con
`dropped_nodes=1`, `fatal_errors=0`, ocupación de cola7 y pico8/8.
Perfil ADC8/CH1, ticks86, N3488: 1.860.465,116 S/s.
CRC recibido y calculado `4f07ac18`; secuencia62504752, anterior62504751.
El rechazo ocurre en `native_feed` por el campo dropped; el relay sale1.
El contenedor de la app sigue activo y no hay OOM del relay.

El firmware incrementa dropped cuando no puede reservar un slot libre.
El último tiempo de consumo del nodo era525777 ciclos =3,286ms, frente al
período de producción de299968 ciclos =1,875ms. Es evidencia de drenaje lento
y saturación; todavía no distingue scheduling, contrapresión o cambio temporal
de los binarios nuevos.

Evidencia preservada:
`diagnosticos/resultados_v18/adc8_flow_review_20261026_124018/`.
Sesión fallida:
`diagnosticos/resultados_v18/sessions/session_20261026_153641_530139.json`.

## Qué cambió

Desde el respaldo previo `v18_tasas_rateonly2_20261025_193958` al catálogo
`v18_catalogo_20261025_230123`, sólo cambiaron cinco headers del firmware/relay:
tablas native, predicados high_rate y cpu_profile. ADC8/86 mantiene lógicamente
SPI40, WORD, CPU policy y cola8. El código principal de adquisición y transporte
es idéntico. Los predicados ampliados pueden modificar tiempos del binario;
no hay evidencia para atribuirles por sí solos la pérdida.

Los cambios posteriores a la pareja catálogo son de etiquetas/UI, sin cambio
de la identidad ADC ni del protocolo. Los objetos de perfiles anteriores son
idénticos. Las rutas históricas de Scan se conservaron.

## Hueco de validación

La regresión instalada del catálogo probó los32 perfiles nuevos15s cada uno.
En GUI probó ADC8/104, no el máximo ADC8/86. Por tanto esos PASS no acreditaban
la estabilidad sostenida del máximo anterior con la nueva pareja recompilada.

## Prueba siguiente, sin alterar tasas ni ocultar pérdidas

1. Confirmar escenario del usuario: adquisición, Scan/US o RADIO/A0.
2. Con acceso exclusivo, capturar estado y reproducir ADC8/86/N3488 en pareja
   catálogo, con métricas de cola y stderr del relay; comparar OFF y carga real.
3. Si reproduce, repetir misma secuencia con la pareja previa completa en
   experimento aislado, verificar hashes y restaurar exactamente.
4. Sólo si catálogo falla y anterior pasa, aislar relay/firmware y medir el
   costo de predicados en camino caliente. No aumentar cola ni reducir tasa
   como supuesto arreglo sin identificar la pausa responsable.

Estado al terminar esta revisión: relay detenido por el fallo original,
Scope V18 app activa. No se ejecutó recuperación automática ni nuevas pruebas.

## Reproducción RADIO/A0 después de la aclaración del usuario

El usuario confirmó RADIO o generador A0 como escenario. Sin monitor abierto,
se recuperó la pareja aceptada con Preparar Q, preservando sus hashes.
`diagnosticos/resultados_v18/adc8_flow_review_20261026_124018/recovery.json`
registra recuperación/verificación correcta.

Se ejecutó RADIO/A0 a ADC8/86/N3488, sintonía550kHz, salida40kHz,
120s de reproducción confirmada, sin Scan/WAV/Synth. Todos los asserts de
reproducción/progreso/cierre pasaron y no hubo errores de la GUI.
Restauración10s aprobada, identidad sin cambios.

Informe `diagnosticos/resultados_v18/adc8_max_radio_20261026_124849/report.json`.
Su resultado global es FALSE y se conserva: exposición de ventana13,3%,
455 eventos paint, por debajo de la aceptación de GUI visible.
Esto verifica la corrida de audio/transporte, pero no reproduce ni descarta el
fallo bajo carga de dibujo visible. Tampoco se recogieron métricas de cola para
certificar holgura en esta corrida. No declarar resuelta la saturación original.

No se modificaron fuentes, firmware, relay ni tasas. Q recuperado y restaurado,
sin ensayo activo. Para la comparación siguiente, reproducir el escenario con
ventana visible y captura de STATUS/cola, y luego A/B con la pareja previa si
reaparece el cierre, manteniendo una única propiedad del hardware.

## Matriz ampliada autorizada

El usuario pidió comprobar todas las tasas nuevas y los cambios respecto de las
anteriores. Campaña `diagnosticos/resultados_v18/radio_rates_review_20261026_130257/`:
32 perfiles nuevos con30s de RADIO/A0 y cinco máximos anteriores con120s cada uno,
precedidos por control ADC8 máximo120s. Son barrido combinado y controles,
no una nueva certificación prolongada de todos los perfiles. GUI visible se
registra por separado. No se modifican tasas ni firmware. Parar ante fallo
funcional o restauración, preservar logs; continuar sólo tras diagnosticar.

La revisión de ELF de Astra confirmó tres comparaciones/ramas adicionales por
nodo/batch en las rutas del máximo8. `scope_high_rate` creció268→328bytes y
`scope_spi40`60→72bytes. No se ejecutan por muestra y no demuestran por sí
solas el origen de la pausa. La búsqueda native de86 conserva su posición:
las32 entradas añadidas al final no se recorren para ese perfil.

## Cierre de la matriz ampliada

El usuario indicó dejar la ventana en segundo plano. Se completaron37/37 casos
funcionales, con reproducción/progreso y apagado confirmados, sin errores y con
restauración e identidad verificadas por caso:

-32 perfiles nuevos, al menos30s de RADIO/A0 cada uno.
-5 máximos CH1 anteriores, al menos120s cada uno: ADC8/86, ADC10/118,
 ADC12/145, ADC14/160 y ADC16/1060.
-Control inicial adicional ADC8/86 de120s, también funcionalmente aprobado.

No se reprodujo la saturación ni el cierre original. Esto no lo resuelve ni
acredita estabilidad prolongada de cada tasa nueva. No se midió holgura de cola
en esta matriz. Sólo6 de37 casos cumplieron exposición/dibujo visible; ADC8
máximo no está entre los controles visuales aprobados. La aceptación funcional
y de visibilidad permanece separada en los informes, sin reescribir sus fallos
por ocultación. Se mantuvieron firmware y relay de la pareja catálogo.

Informe `diagnosticos/resultados_v18/radio_rates_review_20261026_130257/report.json`;
auditoría `audit.json` del mismo directorio:175 archivos V17 intactos,
47 archivos arduino/v18 idénticos al respaldo final del catálogo, todas las
pruebas sobre la misma identidad37f049fa…/27da0bc4….

Sigue pendiente reproducir ADC8 máximo con dibujo visible bajo la carga del
usuario. Si reaparece, comparar parejas completas en la misma condición antes
de atribuir el episodio al coste adicional de los predicados o modificar código.

Preparar Q final aprobado: misma pareja y10s de adquisición verificados.
Informe `final_prepare.json` de la campaña. Q libre, sin pruebas activas.

## Nuevo cierre a 10 bits máximo

Registro local detectado al investigar el aviso «runtime error» tras la FFT
recortada. El usuario aún no confirmó el texto completo ni la acción exacta.
Relay aceptado terminó a las15:47:28 Argentina, perfil10 bits/118ticks/N5568,
1.355.932S/s, dropped1,fatal0,colaactual3,pico4/4,CRCcorrecto,secuenciacontigua.
Último send_ticks782086 =4,888ms frente al período de nodo4,106ms.
No atribuir la pérdida al recorte sin reproducir la misma carga: el informe
confirma saturación y cierre del relay, no el origen de la pausa.
Evidencia `diagnosticos/resultados_v18/runtime_review_20261026_163056/`,
con dump decodificado y recuperación de la pareja aceptada por Preparar Q.
