> Continuación cerrada: [WORD corregido y medición sostenida](RESULTADOS_WORD.md).
> READY resuelto; sin ganancia sostenida adicional ni holgura aceptada.
> El fallo de arranque documentado abajo corresponde a la primera variante.

# ADC8 CH1 — 15/10/2026

BYTE con CRCSIZE=7 completó 60 s + tres arranques independientes de 120 s
a 160 MHz/112 = **1.428.571,429 muestras/s**, nodo3456. Incremento de 1,786%
respecto de ticks114 (1.403.508,772 muestras/s). Es el mayor punto ensayado,
no un máximo global ni una tasa incorporada a producción.

| Etapa | Muestras | dropped/fatal | Cola pico | Margen medio envío | Holgura |
|---|---:|---|---:|---:|---|
| 60 s | 85.666.464 | 0/0 | 3 | 12,179% | Sí |
| 120 s, 1 | 171.330.336 | 0/0 | 4 | 11,893% | No |
| 120 s, 2 | 171.329.472 | 0/0 | 3 | 12,023% | Sí |
| 120 s, 3 | 171.329.472 | 0/0 | 3 | 10,179% | Sí |

Total: 599.655.744 muestras íntegras. Slack positivo en todos los casos.
Aceptación de integridad de esta campaña: sí. Holgura conjunta: no; exige
cola pico<4 en todas las etapas además de margen>=10% y slack positivo.
Se conservaron validadores, CRC32 y protocolo. Sin aceptación analógica,
GUI, RADIO/FFT/FILTER, dual ni UART.

## Comparación y límite de interpretación

[Sondeo A/B](probe_1400_20261015_182804/report.json): BYTE pasó10s en
ticks114/113/112. WORD compiló y arrancó, pero el relay no recibió READY
para la primera trama (timeout); no hubo casos medidos WORD. No demuestra
un límite ADC ni una mejora o regresión de rendimiento debida al ancho DMA.
No se repitió ese arranque; queda abierto su diagnóstico.

Como BYTE también pasó ticks112, se agregó `qualify_byte.py` para completar
la aceptación de ese candidato sin modificar ni reutilizar como aceptación
los sondeos breves. No se atribuye causalidad a CRCSIZE7: no hubo comparación
controlada sostenida con CRCSIZE0 en esta campaña.

## Evidencia y restauración

- [Informe completo BYTE](probe_1400_20261015_183256/report.json),
  `ok/restored/restore_integrity_ok=true`.
- Q restaurado exactamente a V17, ADC10/1167883 SPI y generador apagado,
  con todos sus campos originales. 11.676.792 muestras íntegras en10s.
- Identidad firmware antes/después idéntica:
  `3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
- App experimental detenida y relay original restaurado.
- Sin cambios en fuentes, perfiles o selectores productivos.

Próximos experimentos posibles: diagnosticar READY en WORD y buscar una
tasa con holgura sostenida; aumentar la tasa más allá de ticks112 requiere una
campaña nueva. Incorporación a producción pendiente.
