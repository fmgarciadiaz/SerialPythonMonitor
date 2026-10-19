# Continuidad de V16 a 1,4035 MHz — ensayos de envío

**Todos estos ensayos pertenecen a V16. “Ensayo 8/9” es el número del experimento, no la versión del monitor.**

## Ensayo 9: CRC de payload anticipado — descartado

Se conservó la cola de tres buffers por referencia del ensayo8. Se calculó el
CRC de940bytes de payload en el productor y se combinó con el CRC de48bytes
cabecera al enviar. La equivalencia contra zlib pasó todos7904bits alterados
individualmente, patrones extremos y100cabeceras diferentes. También pasó
propiedad de buffers, errores, empaquetado, READY, relay y contrato.

Físicamente produjo una regresión: margen medio7,3% y7,0% a1,4035MHz,
frente a aproximadamente11% del ensayo8. Se detuvo de forma controlada durante
el siguiente ensayo y se restauró V16; no se completó ni acepta la campaña.

| Etapa completada | Duración | Muestras recibidas | Margen de envío | Cola pico |
|---|---:|---:|---:|---:|
| baseline | 10 s | 12,208,320 | 19.290% | 2/4 |
| finalist | 60 s | 84,162,240 | 7.292% | 3/4 |
| acceptance_1 | 120 s | 168,326,208 | 7.031% | 4/4 |

En la repetición120s se observaron ocupaciones de cola1/2/3/4. El pico acumulado
no se borra al iniciar medición. La observación de cada trama registra epoch,
secuencia, muestras vistas y estado cuando cambia el pico; registra también
el estado justo antes de comenzar medición. El origen del pico4 del reporte
anterior del ensayo8 sigue desconocido, porque no contenía este registro.

- [Reporte descartado con restauración](probe_1400_20261013_172129/report.json).
- Fuentes archivadas `sources_spi38_split_crc_v9.zip`; el sufijo v9 conserva el identificador histórico del ensayo9, no monitorV9.
- `restored=true`, `restore_integrity_ok=true`, firmware original/final idéntico; ADC y generador restituidos al snapshot vivo.
- CRC descartado conservado en `rejected_split_crc/split_crc.h` para reproducir su prueba local.
- Se recuperaron exactamente las fuentes Arduino/relay del ensayo8, comprobando hashes contra su aceptación anterior.

## Ensayo 8 repetido: aceptación de integridad y holgura

**La repetición completa cumplió integridad y holgura a 1.403.508,772 muestras/s
nominales en ADC8/CH1, 114 ticks/N3456.** Pasó60+3x120+600s con reinicios
independientes, CRC/secuencia/epoch/índices/timestamps, DMA, dropped=fatal0.
Se recibieron **1.430.754.624 muestras** en aceptación. Fuentes Arduino/relay
idénticas a la aceptación anterior; sólo cambia la observación del host.

| Etapa | Duración | Muestras | Margen medio de envío | Cola pico | Slack mínimo |
|---|---:|---:|---:|---:|---:|
| finalist | 60 s | 84.163.104 | 10.979% | 3/4 | 1128.2 µs |
| acceptance_1 | 120 s | 168.324.480 | 11.399% | 3/4 | 1126.8 µs |
| acceptance_2 | 120 s | 168.323.616 | 10.906% | 3/4 | 1127.6 µs |
| acceptance_3 | 120 s | 168.324.480 | 11.841% | 3/4 | 1126.9 µs |
| endurance | 600 s | 841.618.944 | 11.225% | 3/4 | 1114.5 µs |

En600s: margen11,225%, envío medio2186,0us frente a2462,4us disponibles,
cola pico3/4 y slack mínimo1114,5us. No hubo discontinuidad del reloj host.
La referencia10s a1,221374MHz pasó con20,449% de margen y cola2/4.
SPI solicitado38MHz (reloj físico no medido); READY50us y relay FIFO10 sólo
experimentales. No se evaluaron precisión analógica, GUI ni WAV sostenidos.

### Evidencia temporal de picos

Tiempo host desde conexión; se observa cuándo se recibió el primer estado con
cada pico, con resolución de trama, no el instante exacto del evento en MCU.
Al iniciar medición cada etapa tenía pico2; todos los picos3 aparecieron durante
medición. Se conservó el pico acumulado, sin resetearlo ni excluir el arranque.

| Etapa | Primer reporte de cada pico en epoch objetivo |
|---|---|
| finalist | 1 a 0.030 s, 2 a 0.032 s, 3 a 27.182 s |
| acceptance_1 | 1 a 0.030 s, 2 a 0.033 s, 3 a 47.983 s |
| acceptance_2 | 1 a 0.033 s, 2 a 0.036 s, 3 a 35.810 s |
| acceptance_3 | 1 a 0.028 s, 2 a 0.030 s, 3 a 18.664 s |
| endurance | 1 a 0.036 s, 2 a 0.039 s, 3 a 61.743 s |

**El pico4 de la campaña anterior no se borra ni se reclasifica.** Su instante
sigue desconocido. La nueva campaña cumple el criterio en todas sus etapas,
pero el antecedente demuestra variabilidad y debe acompañar una futura
incorporación. El ensayo9 con CRC anticipado está descartado.

### Restauración, reproducción y límites

- [Reporte aceptado y restaurado](probe_1400_20261013_172922/report.json): ok/headroom_accepted/restored/restore_integrity_ok=true.
- ADC original/final10bit/909090Hz SPI, generador apagado con campos originales; WAV IDLE antes del cambio. 9.088.408 muestras íntegras en10s de recuperación.
- Firmware original/final `79b0bd376fe26b11b82cbef98fb1cba57ef752f7528c14434c6fef4de295092c`.
- Relay original, política Linux0/prioridad0, CapAddNone y sin SCOPE_EXPERIMENT_RT comprobados. Aplicación experimental detenida.
- Fuentes actuales corresponden aV16/ensayo8. `qualify_margin.py` reproduce esta campaña enfocada; `run.py` conserva el barrido original. No se añadió el perfil a producción/UI.
- `sources_spi38_pointer_observed_ensayo8.zip` conserva fuentes, runners y pruebas. Hashes de firmware/relay y runner observador comprobados contra reporte.
- Pruebas locales: propiedad de buffers y retención al fallar, equivalencia del observador con fragmentación y rechazo, READY, validación/empaquetado, relay y contrato. CRC descartado conserva su prueba independiente contra zlib.
- Pendiente antes de incorporar: validación analógica y de GUI/FFT/trigger/SINGLE/WAV, y tratamiento del antecedente de cola4 bajo carga real.
