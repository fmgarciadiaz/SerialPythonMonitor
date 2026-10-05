# Punto de continuación · 5 de octubre de 2026

Pareja actual: Monitor V12 y firmware V11 P992, SCP1 V3/992, SPI 32 MHz.
Antigravity integró ADC a 50 MHz con PLL2 (HSE16/M2/N25/R4), para todos
los perfiles; ADC16 por oversampling ×16 hasta 62,5 kHz, ADC14 hasta 125 kHz.
UART hasta 31,25 kHz; validación física R4 pendiente.

Revisión posterior: diagnóstico corregido para observar el perfil real antes
de guardarlo, preservar stream.scp y comprobar restauración exacta. Prueba
sostenida final de 120 s aprobada: 7.495.906 pares sin errores. 206 pruebas locales pasan.
Firmware local prepara/verifica PLL2 antes del generador, usa esperas acotadas
y evita conmutar el reloj compartido ADC/DAC durante reconfiguración.
Cambios compilados y cargados; respaldo previo conservado. Perfil del usuario
restaurado: ADC16/62,5 kHz, seno 26 Hz (niveles 186–3909), habilitado.

Documentación actualizada en README, monitor/, arduino/ y docs/, sin mover
versiones históricas. Margen nominal ADC16 / 62.500 Hz: 14,08 µs antes de latencias,
no 12,16 µs. Calibración Bode anterior corresponde al reloj ADC a 40 MHz.
Cableado directo A0 a A2/A3 confirmado. Comparación a 2/10/20 kHz:
amplitud cambia menos de 0,23%; residuo crece a 20 kHz (1,6→3,4 mV).
Ver diagnosticos/ADC16_V12.md para evidencia y límites.
Audio WAV sigue pendiente; no se inició su implementación.

40 etapas de transición ADC14/125k ↔ ADC16/50k/62,5k aprobadas,
con consultas concurrentes y restauración exacta.
