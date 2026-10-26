# Cadencia FFT larga · 26/10/2026

FFT de16384 muestras o más adquiridas con receptor activo: antes máximo10Hz.
Ahora empieza10Hz y permite15Hz cuando las ocho actualizaciones nuevas más
recientes de análisis/preparación de dibujo tardaron cada una como máximo25ms.
Una actualización pesada vuelve al límite previo hasta salir de esa ventana.
No cuentan llamadas que no producen un resultado nuevo. No se reutilizan costes
después de reset o cambio de configuración del análisis.

Se conserva el aplazamiento completo del análisis largo cuando hay más de un
loteGUI pendiente. No cambia FFT, promedios, muestras, adquisición, DSPaudio,
firmware ni buffers. Heatmap conserva su presupuesto anterior. SINGLE no pasa
por el límite vivo ni alimenta esta medición.

Medición local sintética, CH1/four-promedios, sin Q, incluyendo análisis y
procesamiento de eventos de una ventana offscreen:

| FFT | Normal mediana/p95 ms | Recortada mediana/p95 ms |
|---|---|---|
|16384|4,2 /5,0|4,8 /5,3|
|32768|6,2 /8,2|6,3 /8,1|
|65536|12,3 /15,5|11,2 /14,6|

Evidencia `diagnosticos/resultados_v18/fft_adaptive_20261026/analysis_cost.json`.
Esto mide coste local; no certifica15FPS de pintura bajo adquisición/audio.
La medida adaptativa en producto cubre comprobación temporal, análisis y
preparación, no la pintura Qt
posterior. La presión de la colaGUI sigue siendo el guardarraíl adicional.
El usuario tiene V18 abierta: no se operó Q ni se interrumpió esa sesión.

En FFT Radio recortada también se redujo la altura reservada para el ejeX
vertical de100 a70px, acercando el título a las etiquetas sin cambiar los6px
de separación de éstas respecto de la línea del eje.

Validación:250 pruebas de regresión y27 focales aprobadas. No se midieron
FPS físicos con el Q en esta modificación.

## Validación integrada y ajuste final

La prueba integrada ejercita render(), no sólo la función de cálculo de intervalo:
calentamiento con ocho resultados nuevos, subida, caída por frame pesado,
aplazamiento por backlog y nuevo calentamiento. Al observar más de un lote
pendiente se borra la ventana de costes y la fase anterior para evitar ráfagas
al recuperarse. No se modifica la cadencia del heatmap.

Comparación con Qt y RF sintética, 65536 puntos y cuatro promedios, sin Q:
tras1,5s de calentamiento se contaron unos3,5s de actualizaciones y paintEvents.
Con el umbral inicial20ms se observó ~11FPS normal y ~10recortada; el coste
completo resultó mayor que el benchmark inicial de sólo análisis. El umbral
final25ms produjo ~12,2FPS normal y ~13,1 actualizaciones/s recortada (~13,4
paintEvents/s), frente a~10 en los controles. Son corridas cortas offscreen,
no una garantía de FPS ni una medición de carga combinada con el Q.

Evidencia: cadence_simulation_20ms.json y cadence_simulation.json del directorio
fft_adaptive_20261026. Scriptreproducible simulate_cadence.py. El coste de pintura
Qt posterior todavía no entra en el presupuesto adaptativo; por eso la guarda
de backlog y la futura comprobación física siguen siendo necesarias.

Cierre final: 250 pruebas generales y30 focales de GUI/cadencia aprobadas.
Se verificaron175archivosV17 y47fuentesArduinoV18 intactos. La sesión abierta
del usuario no se tocó. Los cambios se aplican al próximo arranque de V18.

## Política final después de adquisición real

Las pruebas con el Q mostraron que no corresponde promover la subida durante
la salida de audio al DAC: una corrida de control10 sufrió UNDERRUN y otra
recortada reprodujo el cierre original del relay con dropped1 y colaADC8/8.
Los intentos fallidos se conservan, aunque sus restauraciones pasaron.

Por eso el producto conserva10Hz en FFT larga mientras `_wav_active` indica
reproducción DAC (RADIO/A0, WAV o Synth). Sin reproducción DAC mantiene el techo
adaptativo15Hz, con ocho resultados ligeros<=25ms y aplazamiento por cola.
Esto no certifica estabilidad de todas las combinaciones de reproducción.

Se corrigió además el reinicio de fase tras backlog: poner la fase a cero podía
saltar el intervalo incluso en el control fijo. La reanudación ahora espera el
intervalo desde el último comienzo y establece una fase nueva, sin ráfagas de
recuperación. Las primeras mediciones anteriores a esa corrección no son una
referencia limpia de FPS. Sólo se cuentan resultados con last_end válido.

El eje recortado reutiliza sus etiquetas si las columnas no cambian y se invalida
al reconfigurar los ejes. Es una reducción de trabajo gráfico, no una corrección
probada de la saturación MCU.

### Mediciones y fallos conservados

- `radio_rate_check_20261026_180641`: control10/FFT65536/RADIOA0, UNDERRUN; había
 19709 muestras disponibles en el padre y ACK procesados con hasta498ms.
- `fft_final_physical_20261026_182105`: fuente de fase ya corregida. Control10
 pasó120s visible100%,9,717FFT/s; adaptativa normal pasó120s visible100%,10,144FFT/s.
 La recortada falló con cierre del Q: dropped1,fatal0,cola8/8,CRC/secuencia correctos.
 Todos los intentos fueron restaurados, pero el informe agregado permanecefalse.
- `experimentos/relay_telemetry_v18/fft_crop_diagnosis_20261026_183300`: corrida
 dedicada instrumentada120s, posterior a caché del eje, pasó con ventana visible;
 SPI148601 intentos completos, backlog1, sin EAGAIN/parciales/errores. No capturó
 el instante de pérdida porque no reprodujo el fallo. Originalcontainer/hash/estado
 restaurados. No atribuir la mejora de esa corrida a la caché ni promover el relay.
- `radio_rate_check_20261026_183757`: política final, pareja aceptada,
 recortada65536+RADIOA0 durante120s, pasó funcionalidad/visibilidad/restauración.
- `fft_no_a0_20261026_184142`: sólo FFT recortada con Scan real, sin reproducción
 RADIO ni A0. Dos recorridos60s con adquisición8bits máxima y ventana visible:
 9,995FFT/s control,12,674FFT/s adaptativa (~27% más). No equivale a medir RADIO
 reproduciendo en PC ni a una prueba sostenida de margen de transporte.

La medición compara resultados FFT nuevos, no callbacks del timer ni todos los
paintEvents. Se conserva exposición, duración observada y evidencia por caso.
El fallo de pérdida ADC y el UNDERRUN son modos distintos y siguen sin causa
única demostrada. No se cambió firmware, tasa, reloj o tamaño de cola.

Cierre físico final:251 pruebas generales y36 focales aprobadas;
PrepareQ verificó pareja y10s finales de adquisición. Q restaurado y libre.
Se conservaron175 archivos V17 y47 fuentes ArduinoV18.

## Repetición instrumentada 19:08 · RADIO/A0 y FFT recortada

ADC8/86 ticks (1,860465 MS/s), FFT de 65.536 puntos, Scan real y
RADIO hacia A0 durante 120 segundos: prueba funcional y visible aprobada
(exposición 100%). Sin cambios de código, tasas, buffers ni firmware.
Restauración exacta e integridad posterior durante 10 segundos aprobadas;
salida apagada confirmada. Evidencia:
`diagnosticos/resultados_v18/radio_rate_check_20261026_190845/report.json`.

El fallo intermitente no se reprodujo. Esta repetición no demuestra que esté
resuelto ni permite atribuir los fallos anteriores a una etapa concreta.
Mantener el límite FFT de 10 Hz durante reproducción DAC.
