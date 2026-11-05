# Recibo de aceptación V19

El recibo `acceptance.json` habilita la instalación de la pareja normal V19.
El firmware y el relay tienen los mismos SHA256 que la pareja V18 aceptada; la
prueba privada de restauración cubre esa misma identidad de binarios. La
evidencia V19 adicional registra 120 s a 8 bits/1,860 MS/s: 255.876 frames,
cola pico 2 y cero pérdidas, fatales o errores SPI. La configuración anterior
se restauró y V17 se verificó al finalizar.

El recibo no promueve tasas públicas. La primera instalación se completó con
`Prepare Q`, seguida por smokes de FFT 16K, Scan/US, Radio/A0, WAV y Synth FM
20 voces en ADC8/1,860 MS/s. Comprobaron adquisición, finalización de Scan,
reproducción/parada y salida apagada/restaurada. La aceptación no cubre otras
tasas/modos ni la respuesta analógica; los recorridos de audio fueron acotados,
no campañas prolongadas. Evidencias en
`diagnosticos/resultados_v19/prepare_q_20261027/`.
