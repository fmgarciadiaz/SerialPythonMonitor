# Comparación física de telemetría V18 · 26/10/2026

Sólo adquisición/transporte, sin RADIO/A0. No es aceptación de carga combinada.

| Bits | Ticks | Margen control | Margen instrumentado | Cola control / instrumentado |
|---|---:|---:|---:|---|
| 8 | 86 | 18.34% | 18.44% | 2 / 2 |
| 8 | 104 | 32.97% | 33.04% | 2 / 2 |
| 10 | 118 | 13.67% | 13.73% | 2 / 2 |
| 12 | 145 | 12.08% | 12.10% | 2 / 2 |
| 14 | 160 | 16.02% | 16.09% | 2 / 2 |
| 16 | 1060 | 71.15% | 71.15% | 1 / 1 |

Seis casos por relay: ADC8 máximo120s; otros cinco30s. Doce casos pasaron integridad y tasa observada. Sin pérdidas/fatales. Las diferencias son pequeñas en una sola comparación secuencial; no prueban equivalencia estadística ni ausencia de latencias raras.

El primer intento comparison_20261026_151023 falló en el arranque del candidato porque el MCU seguía en otra época. Se conserva falso. Su recuperación posterior recovery.json pasó. El controlador se corrigió para reiniciar la app aceptada sin cambiar fuentes/binario y verificar hash antes del candidato; recuperación final ahora comprueba snapshot, identidad y contenedor original.

El historial acotado de ocho intervalos sobrescribió cinco intervalos antiguos, incluido el máximo8 temprano. Los máximos de latencia impresos no representan toda la matriz. Usar una corrida dedicada por perfil para diagnóstico de fallo; no interpretar READY ni intervalo de servicio como retraso puro de scheduling. El candidato registró cero fallos SPI en los intervalos retenidos.

Compilación: build_20261026_150815/report.json, con restauración aprobada. Comparación aceptada: comparison_20261026_151628/report.json, restauración10s, misma identidad de firmware/relay original y contenedor original. El relay instrumentado está retirado, no promovido.

Pendiente: medición combinada RADIO/A0 con telemetría en un ensayo dedicado por perfil y carga visible cuando esté disponible. El fallo original ADC8 no se considera resuelto. Las37 pruebas RADIO/A0 anteriores pertenecen a la pareja aceptada; no trasladar ese resultado al candidato.

## Comparación RADIO/A0 dedicada

`audio_comparison_20261026_152755/report.json`: dos recorridos120s ADC8/86,
sintonía550kHz, salida40kHz, audio/progreso/cierre y restauración aprobados en
ambos. Restituidos snapshot, identidad exacta y contenedor original. El MCU
siempre usó el binario aceptado. Relay experimental retirado, sin promoción.

- Control aceptado: exposición100%,2417 eventospaint, criterioGUI aprobado.
  `diagnosticos/resultados_v18/radio_rate_check_20261026_152756/report.json`.
- Instrumentado: exposición100%,2393 eventospaint frente al mínimo2400;
  criterioGUI falso, conservado. Sin errores funcionales ni fallos de cierre.
  `diagnosticos/resultados_v18/radio_rate_check_20261026_153040/report.json`.

En el intervalo ADC8 instrumentado:148811 intentosSPI, todos completos;
SPImax808,6µs, intervalo entreiniciosmax3550,4µs, READYmax2948,0µs,
backlogpico1;sinEAGAIN,parciales,erroresTCPnicolaTCPllena. Estos máximos incluyen
la transferenciaACKdesalida atribuidaalperfilprevio; no describen exclusivamente
régimenestacionario ni equivalen por sí solos a scheduling. Historialsin sobrescritura.

No se reprodujo ni se explicó el dropped1original. No afirmar holguraconjunta:
la GUI no captura métricas ADC de cola en esta corrida. Los márgenes físicos
anteriores pertenecen a adquisición sin audio. La evidenciahost del máximoADC8
ahora enlaza sólo el controlaceptado120svisible aprobado, sin heredar el candidato.
