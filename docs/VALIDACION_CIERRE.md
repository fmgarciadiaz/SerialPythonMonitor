# Validación física del conjunto actual

Ensayos del 8 de octubre de 2026 sobre UNO Q `1060031107`, monitor V15 y
firmware V13 Pulse actualizado desde las fuentes locales. Se utilizó un solo
cliente del relay en cada prueba. Se confirmó apagado al cerrar ambos ensayos.

## Preparación y recuperación

Preparar Q validó Python, compiló MCU, guardó respaldo, comprobó el relay,
actualizó las fuentes e inició app y relay correctamente.

- [Respaldo anterior](../respaldos/unoq/osciloscopio_20261008_175913_099224.zip).
- [Respaldo posterior](../respaldos/unoq/osciloscopio_20261008_181600_727517.zip).
- [Inventario de fuentes y dependencias](../diagnosticos/resultados_cierre/20261008_inventario.json).

El firmware activo reportó capacidad de pulso de 100 µs. Su SHA256 es
`25ac2bc079108e243e3e96593d9202f3b413ea56a25035085ed2bb1644a92f72`.

## Audio y adquisición simultáneos

| Ensayo | ADC | Duración | Resultado |
|---|---|---|---|
| Wav 20 kHz | 14 bits / 100 kHz | 120 s | 2.400.000 muestras reproducidas, 12.009.924 pares ADC |
| Wav 40 kHz | 14 bits / 100 kHz | 120 s | 4.800.000 muestras reproducidas, 12.019.712 pares ADC |
| Synth 20 kHz, nueve notas | 14 bits / 40 kHz | 600 s | Sin interrupciones, 23.984.128 pares ADC |

Se usaron el receptor y motor actuales, sin GUI ni teclado MIDI físico.
Las notas se modificaron y liberaron cada dos segundos. El decodificador
verificó CRC, índices, timestamps y errores del MCU; no lanzó errores.
Seno, pulso de 100 µs, sweep y chirp recibieron confirmación del generador:
estos disparos adicionales no constituyen medición analógica de sus formas.

Synth registró render máximo de 48,756 ms y pausa máxima entre ACK de
102,253 ms. La cola adaptativa pasó de cinco a nueve bloques: reserva de
aproximadamente 216 ms, sin underrun. **No es una medición MIDI→A0**.
Wav 40 kHz aprobado aquí no implica aceptación de Synth 40 kHz.

[Resultado completo](../diagnosticos/resultados_cierre/20261008_175946_v15.json) ·
[Telemetría Synth](../diagnosticos/resultados_cierre/20261008_175946_synth20.jsonl) ·
[Script reproducible](../diagnosticos/verificar_cierre_v15.py).

## Bode con conexión directa

Conexión A0→A2 y A3 confirmada por el usuario antes del ensayo definitivo.
Qt ejecutó los paneles reales mediante plataforma offscreen, con ADC14/40 kHz
y banda de 20 a 5.000 Hz. Los cuatro métodos finalizaron y produjeron curvas.

| Método | Puntos válidos / totales | Ganancia absoluta P95 sin calibrar |
|---|---|---|
| Tonos | 25 / 25 | 0,022 dB |
| Pulso, promedio de ocho | 2.740 / 2.740 | 0,713 dB |
| Sweep | 12.886 / 12.886 | 0,143 dB |
| Chirp | 12.836 / 13.144 | 0,437 dB |

La fase sin corregir incluye el desfase de la conversión secuencial ADC.
Las referencias existentes compatibles de tonos y sweep redujeron su error
P95 a 0,344° y 1,078° respectivamente. El contraste utiliza la previsualización
conservada de las curvas. Pulso y chirp no encontraron referencia aceptada
compatible en este perfil; no se crearon ni sobrescribieron calibraciones.
Este ensayo funcional no certifica precisión en todas las resoluciones/tasas.

[Resultado de loopback](../diagnosticos/resultados_cierre/20261008_181632_bode_v15.json) ·
[Script reproducible](../diagnosticos/verificar_bode_cierre_v15.py).

El primer ensayo Bode se hizo antes de confirmar el cableado y presentó
ganancias incompatibles con loopback. Se conserva como
[diagnóstico previo](../diagnosticos/resultados_cierre/20261008_181459_bode_v15.json);
no debe usarse como aceptación de precisión.

## Límites y pendientes

La prueba sostenida de Synth no incluyó render gráfico ni pedal MIDI real.
La prueba Bode sí ejecutó Qt, pero offscreen no valida apariencia ni respuesta
visual en macOS. Quedan la medición temporal MIDI→A0, pedal real, reproducción
con gráfica bajo carga, seek/nivel/EOF silencioso medido, SINGLE y reconexión
después de desenchufar físicamente el Q. Synth 40 kHz sigue experimental.

La primera prueba restauró el perfil leído después de preparar el Q
(ADC14/31,25 kHz); no conservó el perfil previo a la carga de firmware.
El ensayo final Bode dejó ADC14/40 kHz y **salida apagada confirmada**.
