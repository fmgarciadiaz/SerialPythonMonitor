# Evaluación de tasas WAV · 5 de octubre de 2026

La reproducción inicial validada era de 20.000 muestras/s. El
límite estaba fijado por software en wav_source.py, unoq_wav.py, wav_protocol.h,
el validador del relay y las etiquetas/contadores del monitor. Cambiar sólo
el remuestreo Python alteraría duración y tono: la MCU seguiría a 20 ksps.

El código programa TIM6 con reloj DAC_TIMER_HZ de 160 MHz. 40 y 50 ksps
tienen divisores enteros (4000 y 3200); son candidatos sin error nominal
de división. Esto no certifica calidad analógica ni entrega sostenida.

| Tasa | Reserva 16×480 | Bloques/s | Tramas de envío/s ×992 bytes |
|---|---:|---:|---:|
| 20 ksps | 384 ms | 41,67 | 41,3 kB/s |
| 40 ksps | 192 ms | 83,33 | 82,7 kB/s |
| 50 ksps | 153,6 ms | 104,17 | 103,3 kB/s |

A esto se añaden ACK, consultas y adquisición. El envío espera una
confirmación por bloque, por lo que importa la latencia de reposición y
el mínimo de bloques disponibles, no sólo el ancho de banda SPI/USB.

Se implementaron candidatos 40 ksps y después 50 ksps (banda teórica
inferior a 25 kHz). Se conserva 20 ksps como alternativa. La tasa se negocia por sesión entre Python, relay y MCU;
no reemplazar constantes sin mantener compatibilidad con firmware existente.

Validar tonos y duración, ausencia de underrun/discontinuidades, créditos,
STOP/restauración y adquisición simultánea a tasas usadas por el usuario.
Ensayo sostenido mínimo 120 s, comprobación con osciloscopio externo y
restauración de la pareja previa si falla. La pareja candidata se cargó después de compilar y respaldar V12 Audio de 20 ksps.

## Evidencia física inicial de tasas negociadas

Firmware MCU y relay compilados; pruebas locales de remuestreo, negociación,
rechazo de tasa no anunciada y selección Qt6 aprobadas.

- 40 ksps + ADC14/40 kHz: 120 s, 4.800.000 códigos DAC completos, 4.810.865 pares ADC, reserva mínima observada 96 ms. STOP y restauración confirmados.
- 50 ksps + ADC14/40 kHz: 120 s, 6.000.000 códigos DAC completos, 4.813.591 pares ADC, reserva mínima observada 86,4 ms. STOP y restauración confirmados.
- 50 ksps + ADC14/125 kHz: dos intentos fallidos; el relay detectó fallo de integridad de adquisición con CRC correcto. El segundo preparó las muestras antes de abrir el ADC y volvió a fallar. No habilitar esta combinación en Play.

Se comprobaron tonos 997 y 12.003 Hz en A2/A3; esto verifica frecuencia y
continuidad, no una caracterización analógica completa de toda la banda.
La amplitud del tono alto difiere entre entradas y requiere evaluación
analógica aparte. No se hizo observación con osciloscopio externo en este ensayo.
Informes compactos en diagnosticos/resultados_wav; sin guardar capturas pesadas.

- 50 ksps + ADC14/100 kHz: 120 s, 6.000.000 códigos DAC, 12.005.828 pares ADC; reserva mínima observada 86,4 ms. STOP y restauración confirmados. La interfaz bloquea Play si el ADC supera 100 kHz.

La reserva mínima se mide por ACK como (aceptadas−reproducidas)/tasa,
excluyendo el final de archivo; no representa una certificación de margen
para todas las condiciones del sistema. Los ensayos son del receptor directo,
sin carga de renderizado de la pantalla. Evaluación visual/audio del usuario pendiente.

Regresión física del perfil 20 ksps aprobada: L/R/Mix, tonos 997/2003 Hz,
Stop y restauración; informe 20261005_20ksps_regresion.json.
