# V20: ventanas largas y otros bits · 1/11/2026

Se completaron seis ensayos cortos con la pareja SRAM3 corregida y el timer persistente de cierre. No se cambió producto, firmware, relay ni tasas en esta tanda. Se ampliaron las herramientas para elegir ventana/detalle, reconocer el raster como datos visibles y registrar la escala realmente aplicada. Pasaron 22 tests locales.

## Resultados funcionales

| Caso | Perfil | Datos/dibujo/cierre | Piso de pintura del diagnóstico |
|---|---|---|---|
| V(t), 2 s, detalle 100% | 8 bits / 1.860.465 S/s | PASS | NO |
| FFT16k | 12 bits / 1.103.448 S/s | PASS | PASS |
| V(t) CH1 | 16 bits / 150.943 S/s | PASS | PASS |
| RADIO→A0 40 kHz | 10 bits / 1.355.932 S/s | PASS | PASS |
| V(t), 2 s, detalle 50% | 8 bits / 1.860.465 S/s | PASS | PASS |
| V(t), 2 s, detalle 100%, repetición | 8 bits / 1.860.465 S/s | PASS | NO |

La ventana estuvo expuesta el 100% del tiempo observado. El piso del diagnóstico exige ocho eventos de pintura por segundo de duración solicitada; es un umbral del ensayo, no garantía del producto. No se confundió este resultado con integridad, visibilidad o aceptación pública.

## Coste del detalle completo

Las dos comparaciones finales confirmaron ventana de 3.720.930 muestras, eje temporal y detalle solicitado. Con detalle 50%, los intervalos registraron 9,76–10,80 eventos de pintura/s. Con 100%, el último intervalo registró 1,20 eventos/s y el raster auxiliar tardó 1.329 ms en la última imagen. La composición/pintura temporal máxima de GUI fue de unos 38 ms. Estos contadores son eventos de ventana; no todos equivalen a una imagen de señal nueva.

Las imágenes completas se publicaron sin error, y adquisición y cierre continuaron. Esto no convierte el detalle completo en fluido: la ventana larga NO pasa el piso de rendimiento. El proceso separa el trabajo pesado de la recepción, pero no elimina el coste de dibujar millones de puntos. No se redujo detalle ni se omitieron muestras para hacer pasar el ensayo. La comparación sólo cambia el detalle de dibujo seleccionado; no la adquisición.

El próximo trabajo de raster debe medirse fuera del Q con geometría, gaps, escalones, DPR y estilos comparables, antes de modificar el renderizador. No sustituir automáticamente el modo de todos los puntos por otro que cambie su representación sin demostrar equivalencia.

## RADIO/A0 a máxima tasa de 10 bits

Reprodujo y cerró sin errores reportados, pero su margen medio fue de 7,11% y el pico de cola 3 de 4. No cumple el objetivo de margen ≥10% ni el screen privado de reserva relativo a la capacidad. Es un sondeo corto, no aceptación sostenida ni prueba acústica/analógica. No se infiere una regresión frente a V19 sin comparación apareada.

Se detectó además un error de metadatos del lanzador privado: había fijado capacidad16 para todos los perfiles. Eso sólo corresponde a los perfiles SPI40 de ADC8; el perfil ADC10 ensayado tiene4. Ahora se consulta queue_slots del perfil real (o4 en legacy). El informe original se conserva y el resumen derivado incluye la reserva corregida: una posición libre al pico, no13. El cambio no altera buffers, firmware ni el resultado de margen insuficiente.

## Estado y límites

Las seis corridas confirmaron restauración exacta de V19: fuentes/caché/BIN/relay, snapshot, configuración y CPU iguales; lectura final de10s sin pérdidas/fatales. Q libre con V19 activa y V20 detenida. No hubo otra caída nativa en esta tanda; la causa original del cierre sigue sin confirmar.

No se calificaron todos los cruces de bits/análisis/audio ni audio a48/50kHz. Falta mejorar la reserva de ADC10/RADIO y2MS/s, y estudiar el rendimiento del raster completo. No se promueven tasas públicas.

[Resumen, hashes y métricas por intervalo](../diagnosticos/resultados_v20/matrix_long_bits_summary_20261101.json).
