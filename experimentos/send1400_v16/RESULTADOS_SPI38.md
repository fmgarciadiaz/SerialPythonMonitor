> Actualización V16: el ensayo 8 se repitió y cumplió integridad y holgura en toda la campaña a 1,4035 MHz. El antecedente de cola4 se conserva; el ensayo9 se descartó. [Resultado posterior](RESULTADOS_CONTINUIDAD_1400.md).

# SPI38 con buffers por referencia — V16 ADC8 CH1, ensayo 8

**Se alcanzaron 1.403.508,772 muestras/s en la versión aislada. Integridad aceptada; V16 restaurada y verificada.**

Configuración: ADC8/CH1, 114 ticks de timestamp a 160 MHz nominales,
nodos de 3456 muestras, SPI solicitado a 38 MHz, relay SCHED_FIFO10.
El reloj físico SPI no fue medido. No se usó compresión.

Tres buffers alineados se encolan por referencia. El productor arma el siguiente
fragmento mientras SPI DMA envía el actual, sin copiar nuevamente el payload en
loop(). El buffer vuelve al productor sólo después de EOT y detención/reset
verificados de ambos DMA. El nodo ADC se libera tras confirmar físicamente su
último fragmento. Los controles conservan prioridad y usan un buffer independiente.

## Aceptación física completa

Pasaron 60 s + tres repeticiones independientes de 120 s + 600 s, con reinicio
entre ensayos, CRC, secuencia, epoch, índices/timestamps, propiedad DMA y
`dropped=fatal=0`. Total recibido en aceptación: **1,430,756,352 muestras**.

| Etapa | Duración | Muestras recibidas | Margen medio de envío | Cola pico | Slack mínimo |
|---|---:|---:|---:|---:|---:|
| finalist | 60 s | 84,163,104 | 10.984% | 4/4 | 1122.5 µs |
| acceptance_1 | 120 s | 168,325,344 | 11.378% | 3/4 | 1126.8 µs |
| acceptance_2 | 120 s | 168,324,480 | 11.237% | 3/4 | 1126.5 µs |
| acceptance_3 | 120 s | 168,323,616 | 11.088% | 2/4 | 1126.7 µs |
| endurance | 600 s | 841,619,808 | 11.209% | 3/4 | 1122.3 µs |

En los 600 s: envío medio 2186,4 µs frente a 2462,4 µs disponibles por nodo,
margen 11,209%, cola pico 3/4 y slack mínimo 1122,3 µs. Deriva entre relojes
host wall/monotonic: -0,0034 s. Las tres repeticiones y la prueba larga cumplen
holgura; **la campaña completa acepta integridad pero no holgura**, porque el
ensayo de 60 s llegó a cola 4/4. No se incorpora aún a producción ni al selector.
Precisión analógica, Bode y uso sostenido de GUI/WAV no evaluados.

## Comparación y pantallas

ensayo 7 no superó la primera repetición de 120 s a 1,4035 MHz. ensayo 8 completó todas
las etapas a esa tasa. La referencia de 10 s a 1,221374 MHz pasó con margen
19,709% y cola 2/4, frente a 16,73% en ensayo 7.
Las cuatro pantallas de 5 s con 114/115 ticks y N3456/N6912 pasaron. Ambas con
N8192 cerraron el flujo; quedan rechazadas, sin atribuir ese cierre a conversión
ADC. N6912 y 115 ticks sólo tienen pantalla en ensayo 8, sin aceptación sostenida.

## Restauración y evidencia

- Reporte: [ensayo 8 aceptado y restaurado](probe_1400_20261013_165327/report.json), `ok=true`, `restored=true`, `restore_integrity_ok=true`.
- Snapshot de esta campaña restituido exactamente: ADC10 a 909090 Hz, SPI; generador apagado con todos sus campos originales; WAV IDLE antes del cambio.
- Recuperación: 9.088.408 muestras íntegras en 10 s.
- Firmware original/final: `79b0bd376fe26b11b82cbef98fb1cba57ef752f7528c14434c6fef4de295092c`.
- Relay original con política Linux normal 0/prioridad 0, sin CapAdd y sin SCOPE_EXPERIMENT_RT; aplicación experimental detenida.
- Fuentes/runner actuales: ensayo 8; archivo `sources_spi38_pointer_v8.zip`, fuentes Arduino/relay comprobadas contra hashes del reporte.
- Pasaron pruebas de READY, relay, validación/empaquetado y tres de contrato. `test_pipeline.py` ejecuta el código real de productor y confirmación con consumidor lento, ring lleno, pausas de control, ADC8/10/12, N3456/N6912/N8192 y 20 nodos por combinación. Comprueba orden, colas, fragmentos parciales, conservación durante DMA y retención de propiedad al fallar.

---

## Antecedentes ensayo 6–ensayo 7 (estado anterior)

# SPI a 38 MHz y reducción de esperas — ADC8 CH1

**Resultado: integridad aceptada en el experimento a 1.391.304,348 muestras/s en CH1. Margen de envío insuficiente. V16 restaurada y verificada.**

Se completaron 60 s + tres repeticiones independientes de 120 s + 600 s,
con reinicio entre ensayos. Configuración: ADC8, 115 ticks de timestamp
a 160 MHz nominales y nodos de 3.456 muestras. Sin compresión.
CRC, secuencia, epoch, índices/timestamps, propiedad DMA y `dropped=fatal=0`
se comprobaron durante los ensayos. El reloj físico SPI no se midió: se
solicitaron 38 MHz al controlador Linux. Precisión analógica y GUI no evaluadas.

| Etapa aceptada | Duración | Muestras recibidas | Margen medio de envío | Cola pico | Slack mínimo |
|---|---:|---:|---:|---:|---:|
| finalist | 60 s | 83.431.296 | 3.59% | 2/4 | 1137.1 µs |
| acceptance_1 | 120 s | 166.860.864 | 3.60% | 3/4 | 1136.6 µs |
| acceptance_2 | 120 s | 166.860.864 | 3.57% | 3/4 | 1144.3 µs |
| acceptance_3 | 120 s | 166.860.864 | 3.57% | 3/4 | 1147.4 µs |
| endurance | 600 s | 834.301.728 | 3.59% | 4/4 | 1146.8 µs |

Total de aceptación: **1.418.315.616 muestras recibidas**. En los 600 s finales:
834.301.728 muestras; envío medio 2394.9 µs
frente a 2484.0 µs disponibles por nodo.
El margen medio de aproximadamente 3,6% está por debajo del criterio de 10%;
además hubo pico de cola 4/4. Por eso la tasa acepta integridad, pero no
acepta margen. No se añadió a la UI ni se incorporó firmware/relay a producción.

## Comparación de variantes

**v6:** SPI solicitado a 38 MHz, pausa artificial de 5 µs del MCU eliminada
y espera READY activa acotada a 50 µs antes de `poll`. Conserva timeout,
secuencia estricta y rechazo de flancos anteriores al I/O. La referencia de
10 s a 1,221374 MHz dio 14,04% de margen. Un ensayo de 5 s a 1,403509 MHz
con N3456 pasó (7.021.728 muestras, 2,04% de margen y cola 4/4); la repetición
para 60 s perdió un nodo a los 44,279 s, tras recibir 62.051.616 muestras.
No aceptada. Restauración exacta y 10 s íntegros.

**v7:** mantiene v6 y aplica `SCHED_FIFO` de prioridad 10 al relay
experimental, con `SYS_NICE` sólo en su contenedor. El arranque exige
confirmar el scheduler y una primera trama SPI válida. La referencia de
10 s a 1,221374 MHz dio 16,73% de margen. Pasaron cuatro de seis ensayos
cortos: 115/114 ticks con nodos 3456/6912; los dos de N8192 fallaron.

A **1.403.508,772 muestras/s**, N3456 y N6912 completaron 60 s íntegros,
pero fallaron al reiniciar para la primera repetición de 120 s: N3456
durante estabilización y N6912 tras 0,129 s de medición. Márgenes medios de
los minutos íntegros: 2,68% y 2,33%, respectivamente. Ninguno está aceptado.
A 1.391.304,348 muestras/s, N3456 completó la aceptación mostrada arriba.
N6912 a ese ritmo sólo tiene ensayo corto; no se certificó sostenido.

Los fallos registraron cola 4/4, `dropped=1`, `fatal=0` y slack positivo.
Los resultados apuntan a saturación del envío; no prueban un límite de
conversión ADC. Las mejoras de espera/prioridad permitieron avanzar desde
ensayos cortos fallidos a una aceptación completa cercana a 1,4 MHz.
Para 1,4035 MHz reproducibles sigue siendo necesario reducir el coste por
fragmento o superponer preparación y transferencia mediante buffers por referencia.

## Restauración final

- ADC original/final: `{'bits': 14, 'rate': 363636}`; corresponde a ADC14 dual a 363636 Hz por canal, SPI.
- Generador apagado, con todos sus campos originales restituidos. WAV estaba IDLE antes del cambio.
- 3.634.688 pares íntegros en 10 s de recuperación.
- Hash de firmware original/final: `79b0bd376fe26b11b82cbef98fb1cba57ef752f7528c14434c6fef4de295092c`.
- Relay original restaurado; comprobación adicional: política Linux 0 (normal), sin `CapAdd` y sin variable `SCOPE_EXPERIMENT_RT`.
- Aplicación experimental detenida y Scope V16 activa.

## Evidencia y reproducción

- [Reporte v6](probe_1400_20261013_160946/report.json).
- [Reporte v7 aceptado y restaurado](probe_1400_20261013_161545/report.json).
- `sources_spi38_ready_v6.zip` y `sources_spi38_fifo_v7.zip` conservan las fuentes y runners; hashes de fuentes Arduino/relay verificados contra los reportes.
- Las fuentes de esta campaña ensayo 7 se conservan en `sources_spi38_fifo_v7.zip`. El runner requiere un solo dueño del Q, captura snapshot vivo y respaldo, detiene adquisición antes de compilar el relay y restaura al finalizar.
- Pruebas locales: tres tests de READY, equivalencia relay y validación/empaquetado, más tres del contrato experimental; todos pasaron.
- `test_ready.py` ejercita flancos frescos/antiguos, secuencia incorrecta, EINTR, lectura incompleta, espera acotada y timeout.
