# Búsqueda moderada por encima de 1,5094 MS/s

Receta constante: CPU2, performance, N3456, SPI40 y preparación112/2s bombeando. Fuentes MCU/relay idénticas al candidato aceptado. Dos sondeos15s por tasa pasaron integridad y holgura. Las ventanas largas descartaron los tres candidatos por cola pico4, sin pérdidas.

| Tasa nominal | Ventana que incumplió | Margen medio | Cola pico |
|---|---|---:|---:|
| 1600000.000 S/s | acceptance_1 (120s) | 12.117% | 4 |
| 1568627.451 S/s | finalist (60s) | 14.494% | 4 |
| 1538461.538 S/s | acceptance_1 (120s) | 16.471% | 4 |

Cada calificación se cortó al primer incumplimiento, sin reintentos selectivos. Ninguna tasa nueva tiene aceptación larga completa; la integridad de estas ventanas no sustituye60+3x120. El perfil106 de1,5094MS/s con aceptación completa previa queda protegido e intacto.

Q restaurado: governor schedutil, firmware/relay/entorno, ADC8/1403508SPI y generadorOFF originales; continuidad10s y reloj33,333MHz verificados. Ver closure_audit.json y reporte completo. Sin promoción a producción.
