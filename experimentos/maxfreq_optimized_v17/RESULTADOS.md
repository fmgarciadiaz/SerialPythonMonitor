## 14/10/2026 — Incorporación a producción completada

Seis perfiles CH1 ADC10/12/14 instalados y habilitados: 60 s + tres
arranques independientes de 120 s por perfil, sin errores de integridad.
Propuesta relay autorizada e incorporada; márgenes de integridad y holgura
separados. Q restaurado a ADC10/909090 SPI y generador apagado; firmware
nuevo permanece instalado. Detalles: [incorporación CH1](../../docs/INCORPORACION_CH1_V17.md).
Las secciones anteriores sobre ausencia de incorporación son históricas.

# Máximos CH1 con envío optimizado — 14/10/2026

Campaña aislada ADC10/12/14; cada finalista pasó 60 s y tres repeticiones
independientes de 120 s. Sin ensayo de 600 s por instrucción del usuario.
Integridad y holgura se aceptan por separado; no aceptación analógica,
dual, GUI visible ni carga RADIO/FILTER/FFT sobre estos perfiles.
Los máximos son los finalistas aceptados dentro de la matriz del PLAN,
con búsqueda inicial monotónica y retroceso tras fallos sostenidos.

| ADC | Integridad (muestras/s CH1) | ticks / nodo | Holgura (muestras/s CH1) | ticks / nodo |
|---|---:|---|---:|---|
| 10 bits | 1.167.883,212 | 137 / 5568 | 1.142.857,143 | 140 / 2784 |
| 12 bits | 981.595,092 | 163 / 4608 | 930.232,558 | 172 / 4608 |
| 14 bits | 851.063,830 | 188 / 1984 | 833.333,333 | 192 / 1984 |

Todos los finalistas conservaron CRC, secuencia, epoch, índices, timestamps
y DMA, con dropped=fatal=0. Los máximos de integridad no cumplen holgura:
ADC10 tiene margen medio 6,864–7,687%; ADC12 5,955–6,219%;
ADC14 8,093–8,947% y cola pico 4/4.

En los finalistas con holgura, todas las etapas superan 10% de margen medio,
cola pico menor que cuatro y slack positivo:

| ADC | Margen medio entre etapas | Cola pico |
|---|---|---:|
| 10 bits | 10,659–11,342% | 3/4 |
| 12 bits | 10,403–10,670% | 2/4 |
| 14 bits | 10,393–11,434% | 3/4 |

Evidencia inicial preservada: `probe_1400_20261014_011909/report.json`.
El proceso anterior se interrumpió durante la última repetición ADC14;
ese ensayo parcial no se cuenta. Reanudación: `resume.py`, que verifica
hashes de fuentes locales/desplegadas y dueño exclusivo del Q, completa
acceptance_3 desde un arranque independiente y restaura el snapshot original.
Informe de cierre: `probe_1400_20261014_084703/report.json`.
`ok/restored/restore_integrity_ok=true`: V17 activa con hash de firmware
idéntico al snapshot, ADC10/909090 SPI y todos los campos del generador
restaurados (apagado). Recuperación: 9.087.712 muestras íntegras en 10 s.
La app experimental quedó detenida; se reinstaló el relay previo con sus
capacidades y entorno originales. ZIP previo conservado en
`respaldos/unoq/osciloscopio_20261014_012010_455047.zip`.

No se incorporan tasas a los selectores ni firmware/relay de producción.
Los ensayos usan SPI solicitado 38 MHz, FIFO10, tres buffers por referencia
y espera READY acotada de 50 µs, sin compresión adicional; ADC12 usa
empaquetado real de 12 bits. El reloj SPI físico no fue medido.
