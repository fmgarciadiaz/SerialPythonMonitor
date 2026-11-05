# V20: temporizador persistente de desconexión · 1/11/2026

Se mitigó la creación repetida de callbacks y timers nativos durante el cierre. La caída original de PySide6 no se reprodujo; no se declara causa confirmada ni reparación definitiva por ausencia de fallo en pocos intentos.

## Diagnóstico y cambio

Tres repeticiones físicas de V(t), ADC8/1.860.465S/s, cerraron y restauraron V19 correctamente. Las trazas antes/después de cada llamada nativa mostraron 10, 10 y 11 llamadas a QTimer.singleShot desde stop_input, todas con retorno. Cada reintento creaba una función finish_disconnect y un timer nuevos a 100 ms. Esto identifica una ruta compatible con la traza nativa anterior, pero no demuestra causalidad.

Sólo en monitor/v20/app.py se añadió un QTimer hijo de la ventana, single-shot, conectado una vez a un slot estable. stop_input reutiliza ese timer con el mismo plazo de 100 ms. Al liberarse el worker, cancela el timer y el estado pendiente; si había cierre pendiente, continúa entonces. No se termina el receptor antes de restaurar el Q. La ruta de espera de carga WAV no fue modificada.

La fuente anterior y su hash quedaron en respaldos/parejas/v20_monitor_before_close_timer_20261101/. Firmware, relay y tasas permanecen iguales. V17/V18/V19 no se editaron.

## Comprobaciones

21 tests locales PASS. Tres ejercitan el timer real de Qt sin placa: paradas repetidas con worker pendiente, wait=False sin programar reintento, y cierre que sólo continúa después de liberar el worker. El test controla el estado de thread/worker; no sustituye validación física.

Después del cambio, V(t) y RADIO/A0 a 40 kHz con ADC8/1.860.465S/s pasaron datos/progreso, dibujo visible, cierre y liberación del worker. La instrumentación estaba instalada (PySide6/Qt 6.11.2) y registró cero llamadas a singleShot en ambos. Se conservaron hashes de todas las fuentes del monitor y de las herramientas para vincular cada ensayo al cambio exacto.

Las cinco corridas restauraron V19 exactamente: fuentes/caché/firmware/relay, configuración, snapshot y CPU verificados, lectura final de 10 s sin pérdidas/fatales. Estado final: Q libre con V19 activa y V20 detenida.

## Límites y continuación

Es una mitigación del ciclo de vida, no una prueba de mayor velocidad ni de causa raíz. La instrumentación puede alterar el timing del fallo. Si vuelve a ocurrir, conservar faulthandler y la última entrada nativa sin retorno; no marcar V20 aceptada todavía. Siguen pendientes ventanas largas, matriz completa de bits/análisis/audio, RF conocida y holgura a 2 MS/s.

[Informes, hashes y trazas](../diagnosticos/resultados_v20/close_owned_timer_summary_20261101.json) · [Fallo original](V20_US_ANALISIS_20261101.md).
