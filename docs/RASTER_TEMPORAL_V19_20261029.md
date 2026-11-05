# V(t) completo sin bloquear la recepción · 29/10/2026

El caso de 10 bits a 1.355.932 S/s, RADIO y Scan US con detalle 100 %
reprodujo `FlowLimitExceeded`: una pintura Qt de 1.049,94 ms agotó el
presupuesto de RF pendiente de 1 s. La cadencia adaptativa por sí sola no
resuelve una pintura individual tan larga.

## Implementación

`monitor/v19/temporal_raster.py` dibuja ventanas densas de detalle completo en
un proceso `spawn` dedicado, sin acceso al Q. La GUI compone la imagen y
conserva ejes, rejilla, trigger y cursores vectoriales. Los demás modos de
análisis y las ventanas pequeñas conservan su camino habitual.

Se envían todos los puntos del snapshot: no se cambia el detalle, la tasa,
el DSP, los límites de flujo ni las muestras guardadas. La geometría de
escalones y cortes es común al trazado normal y al raster. Los segmentos
finitos se pintan con el primitivo usado también por pyqtgraph; NaN/Inf
separan trazos. Color, ancho y antialiasing respetan el estilo elegido.
Puede haber diferencias menores de píxeles en uniones antialiasadas;
no se afirma identidad binaria de la imagen.

Un hilo no bastó: el benchmark registró raster de 388,83 ms y pausa de
heartbeat de 382,47 ms. El proceso usa memoria compartida para arrays e
imagen; los mensajes de control son pequeños. Hay un trabajo en vuelo y,
sólo cuando cambia la configuración o se congela una captura, un reemplazo.
Se omiten refrescos visuales intermedios mientras trabaja; no datos adquiridos.

Los tokens identifican adquisición, continuidad de audio, vista, DPR,
canales, estilo y escala. No se usan estimadores fluctuantes de Fs como
identidad. STOP/SINGLE reemplazan el frame live pendiente con su snapshot
independiente. Imagen y arrays de cursor se publican juntos; las lecturas se
invalidan al retirar una imagen incompatible. Cambiar de análisis o cerrar
termina exclusivamente este proceso gráfico y libera su memoria.

## Validación

Las pruebas cubren mutación del historial, liberación de memoria, respuesta de
la GUI, orientación Y, comparación contra pyqtgraph para Línea/Escalón y tres
estilos a DPR 1/2, SINGLE, STOP seguido de zoom, limpieza de datos, cambios de
modo y rechazo de snapshots con otro contexto. Se mantiene la reserva de
adquisición original de 1 s.

El benchmark de 724.000 muestras con Escalón a DPR 2 encontró rutas/polilíneas
que no terminaban en 12 s; los mismos segmentos completos terminaron en
413,36 ms, con heartbeat máximo de 54,09 ms. Son mediciones sintéticas,
no aceptación física ni prueba de holgura del Q.

Los ensayos físicos iniciales completaron US con 26 candidatos sin repetir el
límite de flujo, pero la publicación de imagen falló antes de corregir el
trazado y el arranque A0 desbordó su buffer. Esos informes se conservan como
fallos, sin convertirlos en aceptación. El cierre restauró la pareja aceptada.


## Resultado físico del raster por segmentos

`us10_raster_segments_20261029`: 30 s, RADIO + US, 26 candidatos,
22 imágenes completas publicadas, sin error de flujo ni de raster. Máximo de
pintado Qt 75,52 ms; preparación del frame en GUI 70,26 ms. El trabajo del
proceso es separado y puede tardar más: esto mejora respuesta y entrega,
no promete 60 FPS con cientos de miles de puntos. La sesión restauró el
snapshot aceptado con recuperación continua, sin pérdidas ni fatales.

El caso combinado `us10_raster_a0_20261029` no pasó: el relay rechazó un
frame válido de CRC que informaba `dropped_nodes=1`, cola actual 3/pico 4,
ADC10/CH1/ticks118/pairs5568. El campo 56 es el contador del MCU, no un error
del raster ni una corrupción CRC. El cierre automático no pudo restaurar
porque el relay había terminado. Se preservaron frame y logs; fue necesario
reiniciar únicamente Scope V19 y su mismo contenedor de relay, verificando
BIN/relay aceptados iguales y 10,022 s de recuperación: 313.344 muestras,
cero pérdidas/fatales y snapshot idéntico. Prueba: `restart_recovery.json`.

No se aumentaron buffers ni se ocultó la pérdida. El candidato privado O2
continúa por separado, con respaldo/rollback, antes de decidir mejoras MCU.


## ACK-refresh: corrección host independiente

Se incorporó inline en `receiver/unoq_config_receiver.py` la renovación del
plazo de elegibilidad de QUERY cuando llega un CHUNK ACK válido que ya trae
estado DAC actual. Sólo RADIO a 40 kHz, reproducción iniciada, PLAYING y sin
error; se valida request/sesión/tasa antes de renovar. El tipo CHUNK se conserva
antes de retirar su reserva. No cambia créditos, reservas, burst, tamaño de
cola, timeout ni fallback de consulta. El plazo no promete una consulta cada
40 ms: el camino de refill y los comandos pendientes mantienen su política.

El replay privado deshabilita inline dentro de su contexto y lo restaura al
salir; nunca se renueva dos veces. Las pruebas comparan ambos caminos para
ACK válidos/duplicados/desconocidos, terminales, errores, sesiones/tasas,
clamp del plazo, callbacks que fallan y timeout/cola llena. O2 no se incorpora.

El brazo B ADC10, firmware aceptado + wrapper ACK-refresh, pasó 27,174 s de
reproducción y 1.086.720 muestras DAC. Margen 6,5873 %, pico 4: funcionalidad
PASS, holgura FAIL. El brazo C O2 + mismo wrapper pasó 20,019 s sin errores de
la GUI ni de audio; margen 7,1619 %, pico 4: holgura FAIL. El controlador de C
reportó además fallo del umbral de pinturas, porque reutilizaba el requisito
FFT de 8 FPS para el nuevo V(t) completo. Se corrigió esa condición para
futuros ensayos, conservando intacto el informe fallido. Ambos restauraron
exactamente la pareja aceptada. Ninguno acredita O2 ni tasas nuevas.

La aceptación inline se mide aparte con la pareja aceptada, sin wrapper:
120 s ADC10 tras STOP/reinicio y Scan US mientras A0 reproduce, más un control
ADC8 de 60 s con FFT. Los resultados se añaden al finalizar las sesiones.


## Aceptación funcional inline: ADC10 con transiciones

`inline_us10_transitions_120s_20261029`, pareja aceptada, sin wrapper ni O2:

- STOP solicitado a los 12,804 s; reinicio confirmado a los 13,553 s.
- Scan US con A0 activo a los 18,621 s; resultados a los 21,394 s y nueva
  reproducción confirmada a los 22,078 s. Se identificó un candidato real.
- Después de reanudar: 120,014 s de PLAYING, 4.799.520 muestras DAC reportadas;
  todas las comprobaciones funcionales PASS, sin errores.
- 276 imágenes completas publicadas; pintado Qt máximo 81,91 ms y preparación
  GUI máxima 88,16 ms. Los hashes de fuentes no cambiaron durante el ensayo.
- STOP final confirmado y snapshot restaurado; recuperación continua sin
  pérdidas/fatales. El ensayo no modificó fuentes/binarios del Q.

Holgura permanece FAIL: margen medio 6,7296 %, pico MCU 4, slack positivo.
Aceptar la corrección de consultas host no equivale a calificar esta tasa
con reserva ni a promover O2. Los límites/buffers y la detección de pérdidas
permanecen intactos. Se conserva la separación entre funcionamiento en el
ensayo y reserva ante cargas peores.


## Cierre y control ADC8

`inline_adc8_fft_60s_20261029`: 60,093 s de reproducción, 2.403.840 muestras DAC,
FFT con avance y 1.435 pinturas; resintonía incluida, sin errores. Snapshot
restaurado. Margen 10,3296 %, pico 4: funcionalidad PASS, holgura FAIL.

Verificación final independiente: pareja aceptada igual antes/después,
10,025 s y 313.344 muestras, sin pérdidas/fatales, snapshot idéntico. El Q se
entrega con firmware/relay aceptados, no con O2. Se aprobaron 98 pruebas
dirigidas en 37,530 s. El último guard de contexto incluye cambios de trigger;
su regresión confirma que un frame del trigger anterior no se publica.

[Resumen y referencias de evidencia](../diagnosticos/resultados_v19/host_radio_validation_20261029/summary.json).
No se cambiaron ni habilitaron tasas, no se elevaron límites y no se modificó
V17/V18. La reserva del MCU sigue pendiente en las tasas máximas indicadas.
