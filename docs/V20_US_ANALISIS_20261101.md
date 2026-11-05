# V20: Scan US y primera matriz de análisis · 1/11/2026

Misma pareja de firmware/relay SRAM3 corregida; no se modificó código de producto ni firmware durante esta tanda. Se amplió únicamente el lanzador privado y las comprobaciones de las herramientas.18tests locales PASS.

## Scan US real

| Caso | Perfiles capturados, MS/s | Restauró FS | Audio reanudado | Candidatos |
|---|---|---|---|---:|
|Antes de A0|1,860465 / 1,600000 / 1,403509|Sí|Reprodujo después|0|
|Durante A0|1,860465 / 1,600000 / 1,403509|Sí|Sí, sesión nueva confirmada|0|

Ambos cerraron correctamente y restauraron V19 exactamente. Se verificaron tres capturas, la FS original y, durante A0, la transición de pausa/reanudación. Detectar cero candidatos limita esta evidencia a captura, transporte y ciclo de restauración; no demuestra identificación correcta de emisoras o alias reales. No se pidieron WAV/Synth en estos dos casos.

Corrección del informe anterior: las corridas60s+3×120s no pidieron Scan. Su aserción opcional verdadera era vacua. La evidencia RADIO/A0, WAV y Synth sí corresponde a acciones solicitadas. Se corrigió el resumen derivado sin alterar los informes físicos originales.

## Dibujo y adquisición

| Caso | Perfil | Resultado |
|---|---|---|
|vt|8bits / 1860465S/s|Datos, dibujo visible, cierre y restauración PASS|
|fft|10bits / 1355932S/s|Datos, dibujo visible, cierre y restauración PASS|
|heatmap|16bits / 76226S/s|Datos, dibujo visible, cierre y restauración PASS|
|bode|14bits / 363636S/s|Datos, dibujo visible, cierre y restauración PASS (curvas sintéticas)|

V(t) tiene una repetición exitosa, pero el primer intento sufrió una caída nativa al cerrar (ver abajo). FFT usa16k. Heatmap16bits/76.226S/s es dual: se exigieron datos finitos en ambos paneles (770.142píxeles en cada uno al último registro). Bode usa adquisición real dual14bits/363.636S/s y actualiza curvas sintéticas; esto prueba presentación, no excitación, transferencia ni aceptación analógica. No se infiere equivalencia de FPS a partir de paint events totales.

## Fallo intermitente que sigue abierto

El primer V(t) adquirió y dibujó hasta el cierre, pero el proceso terminó por SIGSEGV antes de guardar gui.json. El coordinador restauró V19 exacta. macOS registró EXC_BAD_ACCESS en PySide::SignalManager::retrieveMetaObject, llamado al crear QTimer mediante singleShot. [Resumen nativo](../diagnosticos/resultados_v20/sram3_tail_analysis_vt_8_1860465_20261101/native_crash_summary.json).

Se repitió el mismo escenario con PYTHONFAULTHANDLER=1: pasó. FFT, heatmap y Bode posteriores también cerraron. La caída no se declara reparada: todavía no se identificó la llamada Python exacta. El lanzador ahora conserva trazas y reporta explícitamente salida anormal sin evidencia final, en vez de ocultarla como FileNotFoundError. No se cambió el cierre de la aplicación por una hipótesis no reproducida.

## Estado y continuación

Q libre con V19 exacta activa, V20 detenida; todas las restauraciones, incluida la del intento fallido, confirmadas. Prioridad: aislar el cierre nativo intermitente con trazas Python antes de aceptación de V20. Falta matriz completa, ventanas largas, otros bits y tasas de audio, detección con señal RF conocida y holgura2MS/s. No se promueven tasas públicas.

[Informes, selecciones y hashes](../diagnosticos/resultados_v20/sram3_tail_us_analysis_summary_20261101.json).
