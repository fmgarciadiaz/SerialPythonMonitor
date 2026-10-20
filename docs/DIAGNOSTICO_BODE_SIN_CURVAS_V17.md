# Bode sin curvas — 2026-10-19

El usuario confirmó perfil dual y CH1 conectado a antena. El par predeterminado de Bode es referencia CH1, respuesta CH2: una antena no proporciona la referencia del estímulo del generador. No se debe representar como transferencia válida una medición sin referencia coherente.

Se corrigió un defecto independiente en `bode_pulse.py`: la detección de inicio de Pulso/Sweep leía CH1 fijo en lugar de la referencia elegida. El mensaje de estímulo ausente ahora identifica el canal seleccionado.

Prueba física en ADC14/40 kHz, CH2 como referencia y respuesta, sin cambiar cableado:
- `diagnosticos/resultados_bode/gui_v17_20261019_153515/report.json`: antes de corregir, ningún método produjo puntos válidos.
- `diagnosticos/resultados_bode/gui_v17_20261019_153746/report.json`: después, Sweep produjo 2545 ganancias válidas y ambas curvas visibles con datos finitos.
- `diagnosticos/resultados_bode/gui_v17_20261019_153820/report.json`: repetición, Sweep produjo 2546 ganancias válidas. Tonos con asentamiento reducido de 20 ms siguió rechazando todas las referencias; Pulso no detectó el estímulo. Estos dos métodos no quedan validados físicamente por estas pruebas. Se conservaron capturas de tonos para análisis; no se atribuye todavía su rechazo a una causa única.
- Todas las ejecuciones restauraron la configuración previa y conservaron el firmware SHA256 96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9. Recuperación sin drops/fatales.

Regresiones: detección con referencia CH2, arranque de los tres métodos con FILTER OFF y fase de loopback: 3 tests correctos. Suite completa en Qt minimal: 10/11, fallo de dimensiones de controles (no de cálculo). Cocoa sin escalación no pudo abrir pantalla; no se declara esa suite completa aprobada.

Para medir un circuito: A0 a su entrada y CH1; salida a CH2, masa común. CH2/CH2 sirve como autocomprobación de transferencia unitaria, no mide la respuesta del circuito. Mientras CH1 se use como antena no utilizarlo como referencia de Bode.

## Ampliación posterior de selectores

Tonos y Sweep/Chirp permiten hasta 150 kHz; Pulso hasta 200 kHz. Se mantiene el límite final <0,45×Fs. Se comprobó localmente cada máximo y una frecuencia intermedia de 123456,7 Hz. Esto no agrega aceptación física del rango ampliado ni resuelve por sí solo la referencia del montaje.

## Orden de confirmaciones y muestras · 19/10/2026, bloque 20:00

Se reprodujo localmente un defecto de entrega: si quedaba un bloque ADC acumulado, el callback del generador emitía la confirmación antes de publicar esas muestras. Con DSP activo también podía adelantar el trabajo pendiente. Bode podía comenzar el intervalo de asentamiento con muestras anteriores todavía pendientes.

`OutputWorker` ahora publica el bloque acumulado al recibir la confirmación del generador y utiliza la misma barrera de orden del executor que las confirmaciones de adquisición. No descarta muestras, no amplía presupuestos y no espera al DSP bloqueando la recepción. El bloque de frontera puede publicarse aunque la agrupación normal esté reteniendo lotes por presión; se conservan los límites de entrega.

La regresión nueva falló antes del cambio, tanto con FILTER OFF como con DSP activo; después pasó. Suites de procesamiento, RADIO UI y fuente A0: 69 pruebas correctas. Además, nueva prueba de recepción/dibujo RADIO a ADC8/1,6 MS/s sin fuente A0: correcta (70 pruebas en total entre ambas ejecuciones).

Resultados físicos CH2/CH2 a ADC14/40 kHz, sin cambiar firmware:

| Informe | Tonos | Pulso | Sweep/Chirp |
|---|---|---|---|
| `gui_v17_20261019_200007/report.json` | Asentamiento 20 ms: 1/5 válido | 1000 µs: estímulo no detectado | 2547 ganancias válidas, curvas con datos |
| `gui_v17_20261019_200109/report.json` | Asentamiento normal 200 ms: 5/5 válidos, ambas curvas dibujadas | 10000 µs: estímulo no detectado | 2546 ganancias válidas, curvas con datos |

Informes y capturas en `diagnosticos/resultados_bode/`. Ambos restauraron la configuración previa y verificaron firmware idéntico. La prueba de Tonos cubre 20–1000 Hz, no 150 kHz ni un circuito distinto. Cambiar el asentamiento entre corridas impide atribuir toda la diferencia de puntos al cambio de orden; la regresión local sí aísla ese defecto. La confirmación no incluye un timestamp físico del cambio DAC, por lo que esta barrera no certifica que todo el pipeline del Q ya contenga muestras posteriores al cambio.

Pulso sigue abierto. No reducir controles de referencia ni inventar puntos para llenar la curva. El caso de asentamiento corto tampoco queda cerrado como válido.

Se inspeccionó la captura real `gui_v17_20261019_200109/method0.png`: cinco marcadores visibles y líneas de ganancia 0 dB/fase 0° en CH2/CH2. Esto confirma dibujo visible en esa captura, no una medición de FPS.

## Control RADIO/A0 tras corregir el orden de ACK

`diagnosticos/resultados_v17/generador_radio_20261019_200206/report.json`: Python 3.13/Cocoa, ADC8/1,6 MS/s y A0 40 kHz, 60 s con resintonías, sin underrun ni dropped/fatal. Se restauró la configuración previa, ADC8/1,6 MS/s y generador OFF; firmware idéntico. Recuperación posterior de 10 s: 15991776 muestras íntegras. Este control comprueba compatibilidad del cambio, no resuelve el corte intermitente previo ni califica el rango ampliado de Bode.
