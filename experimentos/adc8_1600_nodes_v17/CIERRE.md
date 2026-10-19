# Intento de 1,6000 MS/s: dos vías medidas

Se probaron nodos4320/5184 con fuentes MCU/relay de referencia y, por separado, intervalos solicitados de productor500/750µs con N3456. CPU2/performance/SPI40 y preparación112/2s constantes. Dos pilotos independientes por alternativa; ninguno cumplió todos los criterios, por lo que no se ejecutó calificación larga.

Los nodos mayores no resolvieron la acumulación y redujeron margen. El intervalo500µs redujo poll_max y cola pero bajó margen a~8%;750µs tampoco cumplió. Esto no demuestra una causa exclusiva del atasco. Se preservaron CRC, continuidad, epoch, timestamps, rango, DMA y cuatro slots. No se aumentaron slots para ocultar el umbral.

Cada campaña terminó con restauración verificada, continuidad10s y governor original. Los RESULTADOS.md y closure_audit.json de las tres carpetas registran los valores. El único perfil con aceptación completa sigue siendo106ticks/1,5094MS/s. No declarar1600aceptado.

Siguiente investigación fundamentada: capturar por etapas el relay a100ticks durante una congestión. El diagnóstico anterior a106ticks no reprodujo pico4; no permite elegir aún una optimización concreta de SPI, READY o TCP a100. No se implementó esa instrumentación en este bloque.
