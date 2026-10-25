# Exploración de FS máxima por resolución — 19/10/2026

Autorizada por el usuario con V17 cerrado y Q exclusivo. Copia aislada de la producción actual, incluyendo el generador de 150/200 kHz y la cola DAC vigente. No modifica tasas públicas.

| Bits | Control actual S/s | Candidato CH1 S/s | Ticks | Nodo |
|---|---:|---:|---:|---:|
| 8 | 1600000 | 1632653,061 | 98 | 3456 |
| 10 | 1250000 | 1290322,581 | 124 | 5568 |
| 12 | 1066666,667 | 1095890,411 | 146 | 7488 |
| 14 | 851063,830 | 909090,909 | 176 | 5952 |
| 16 | 76226,775 dual | 145454,545 CH1 | 1100 | 3488 |

16 bits conserva ADC14 con sobremuestreo16 y desplazamiento2; primero CH1/80k durante10s. Se agrega empaquetado16CH1 explícito sólo en la copia. Controles actuales10s; candidatos15s; regreso a ADC14/40k con10s de verificación entre pruebas. Fallos quedan registrados y no se reintentan silenciosamente. Una pantalla corta no califica tasas ni holgura sostenida.

Criterios separados: integridad de CRC/secuencia/epoch/índices/tiempo/DMA; envío medio >=10%, cola<4 y slack>0 para holgura. Preservar errores y contrastar con control del mismo binario. Finalistas requieren60s y3×120s con el mismo binario y aceptación de carga GUI/RADIO aparte.

Un dueñoQ; respaldo y snapshot antes de cambios. Compilar con adquisición detenida. Restaurar headers/firmware/relay/entorno/políticaCPU/configuración/generador previos y verificar identidad y10s de continuidad. No compilar durante medición. Sin aceptación analógica ni sustitución de los perfiles dual.
