# Alternativas con Astra para 1,5094 MS/s

Objetivo: ADC8/CH1, 106 ticks, SPI de 40 MHz y preparación a 112 ticks durante 2 segundos, bombeando continuamente. Mantener formato kind20, WORD DMA, READY fresco, spin de 50 µs y un frame por envío TCP.

Criterios: integridad completa, margen medio de envío ≥10%, cola pico <4 desde el arranque y slack positivo.

| Alternativa | Márgenes de los pilotos | Picos | Validación larga | Resultado |
|---|---|---|---|---|
| N4320, relay libre | 9,942% / 9,993% | 2 / 3 | No elegible | Cerca del umbral |
| N4320, CPU0 | 9,037% / 8,600% | 4 / 2 | No elegible | Rechazada |
| N4320, CPU2 | 10,090% / 10,324% | 3 / 2 | 60 s: 9,8335%, pico 3 | No cumple margen |
| N3456, CPU2 | 12,306% / 11,679% | 3 / 3 | 60 + 120 + 120 s: 11,638 / 11,887 / 11,964%, picos 3 / 3 / 4 | No cumple cola |

Todas las ventanas citadas preservaron integridad. Ninguna alternativa nueva consiguió aceptación conjunta. No se redondeó 9,993 a 10 para aprobar, no se borraron picos ni se repitieron selectivamente fallos. Cada calificación nueva se detuvo al primer incumplimiento. La aceptación anterior completa de N3456 (60 s + tres de 120 s) sigue siendo exclusivamente de integridad.

En CPU2/N3456, el primer pico 4 se observó a los 85,489 segundos desde el primer frame de 106 ticks. Al terminar el asentamiento, el pico era 2: se confirma congestión durante el régimen sostenido. La marca del host fecha la observación, no la causa física ni el instante exacto del pico.

Astra revisó el plan y los runners. Recomendó cerrar esta búsqueda sin probar CPU1/3 por unas décimas. El siguiente bloque con fundamento sería un diagnóstico causal del relay por etapas, con un anillo acotado y correlación por secuencias durante 120 segundos. Ese instrumental no se implementó en esta campaña.

Q fue restaurado y verificado al terminar cada campaña: firmware original, relay y entorno originales, ADC8/1403508 por SPI, generador apagado y reloj configurado de 33,333 MHz. Las fuentes MCU/relay coinciden con la referencia. Los archivos closure_audit.json y report.json conservan la evidencia. No hubo promoción a producción. Esta evidencia no certifica precisión analógica, GUI, dual ni margen eléctrico universal de SPI a 40 MHz.

Reportes:

- [Comparación de nodos](probe_1400_20261016_092800/report.json).
- [Afinidad con N4320](../adc8_target1500_affinity_v17/probe_1400_20261016_093403/report.json).
- [CPU2 con N3456](../adc8_target1500_cpu2_n3456_v17/probe_1400_20261016_094211/report.json).
