# Capturas del generador DMA

- [20261002_232028_292878](20261002_232028_292878/): ensayo final con TIM5 CCR1 PASS; 18 CSV / 4096 pares por caso, minuto adicional validado al vuelo. [Informe](../../diagnosticos/resultados_usb/20261002_232028_292878_generador_audio.json).
- [20261002_230826_357101](20261002_230826_357101/): ensayo DMA previo a la corrección de timestamps, PASS. Dieciocho CSV de hasta 4096 pares originales por caso, ADC A2/A3, timestamps e índices. El minuto de estabilidad se valida al vuelo y conserva el resultado en JSON, sin CSV completo. [Informe](../../diagnosticos/resultados_usb/20261002_230826_357101_generador_audio.json).
- [20261002_230633_520996](20261002_230633_520996/): 17 casos correctos antes de corregir el recolector de pulso (el script descartaba muestras durante el ACK). [Informe](../../diagnosticos/resultados_usb/20261002_230633_520996_generador_audio.json).
- `20261002_225227_161950`: primer prototipo detenido por error DMA; no produjo CSV. [Informe](../../diagnosticos/resultados_usb/20261002_225227_161950_generador_audio.json).

Volts nominales calculados con 3,3 V; no son datos calibrados. Se verificó continuidad sobre todos los pares recibidos, no solo sobre la muestra preservada en cada CSV. [Procedimiento y limitaciones](../../diagnosticos/GENERADOR_AUDIO_V10.md).
