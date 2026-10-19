# Candidato aceptado: ADC8/CH1 a 1,5094 MS/s

La política de frecuencia `performance` permitió cerrar la aceptación experimental de integridad y holgura. La política se comparte entre CPU0–3: no se atribuye el efecto exclusivamente al relay.

Comparación FRRF de30s, CPU2/N3456 constante: schedutil11,940%/11,751%; performance18,854%/18,939%. Los dos pilotos performance superaron a ambos controles.

Receta:106ticks,N3456,SPI40,relayCPU2/FIFO10,governorperformance, generadorOFF. Preparar112ticks durante2s bombeando y validando, esperarAPPLIED y cambiar106. Formato kind20/864,WORDDMA,READYfresco,spin50us,unframeTCP sin cambios.

| Corrida | Muestras | Margen medio | Cola pico | Slack mínimo µs |
|---|---:|---:|---:|---:|
| finalist | 90513504 | 19.033% | 2 | 952.706 |
| acceptance_1 | 181027872 | 18.852% | 3 | 952.538 |
| acceptance_2 | 181027872 | 18.770% | 3 | 952.706 |
| acceptance_3 | 181027008 | 18.870% | 3 | 952.763 |

Total: 633596256 muestras íntegras. CRC, secuencia, epoch, índices/timestamps, rango y propiedadDMA preservados; dropped/fatal0. Las cuatro corridas cumplieron margen>=10%, pico<4 incluyendo arranque y slackpositivo. Sin reintentos selectivos ni600s.

Q restaurado y verificado: governor schedutil, firmware/relay/entorno originales, ADC8/1403508SPI, generadorOFF, reloj33,333MHz y continuidad10s. Ver closure_audit.json y reporte completo.

Perfil experimental cerrado; no incorporado al selector ni producción. No certifica precisión analógica, carga conjunta GUI/DSP/RADIO, dual/UART ni margen eléctrico universal deSPI40. Reloj configurado verificado, no medición eléctrica deSCK.
