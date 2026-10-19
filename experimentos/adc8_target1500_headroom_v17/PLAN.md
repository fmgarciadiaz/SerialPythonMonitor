# Holgura del candidato de 1,5094 MS/s

Recomendación Astra: comparar N3456 (B) y N4320 (C), orden BCCB, 30s por reinicio independiente. Mantener ticks106, SPI40, preparación112/2s bombeando, MCU/relay idénticos. Diagnóstico host persistente de primer estado/cambios del pico y entradas a cola>=3; no reiniciar pico ni quitar arranque de aceptación.

Si ambos C pasan integridad y holgura, calificar C60s+3x120s independientes. Criterio: integridad completa, margen medio>=10%, pico<4 desde arranque y slack positivo. Restauración exacta con continuidad10s y reloj original. Sin promoción productiva ni aceptación analógica.
