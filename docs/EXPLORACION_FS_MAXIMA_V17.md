# Exploración de FS máxima V17 — 19/10/2026

Las cinco resoluciones pasaron un primer sondeo físico CH1 de 15 s por candidato, con el mismo binario experimental. Cada una tuvo un control a su máximo actual durante 10 s y regresos a ADC14/40 kHz durante 10 s. ADC16 tuvo además un control CH1/80 kS/s de 10 s.

**La tabla siguiente es el sondeo inicial, no la aceptación final.** La calificación sostenida se detalla abajo. Las tasas siguen fuera de producción; no hay aceptación conjunta GUI/RADIO/A0 ni analógica. No se redujo el sobremuestreo de16bits.

| Bits | Máximo actual kS/s | Candidato CH1 kS/s | Margen medio envío | Cola pico |
|---|---:|---:|---:|---:|
| 8 | 1600 | 1632.653 | 22.45% | 3 |
| 10 | 1250 | 1290.323 | 16.47% | 2 |
| 12 | 1066,667 | 1095.890 | 14.42% | 2 |
| 14 | 851,064 | 909.091 | 20.07% | 2 |
| 16 | 76,227 dual | 145.455 | 82.94% | 1 |

Todos los candidatos conservaron CRC, secuencia, epoch, índices/timestamps y validación DMA, sin dropped/fatal y con slack mínimo positivo. Los márgenes y colas corresponden solamente a estos sondeos. El máximo actual de16bits es dual; el candidato de145,455kS/s utiliza únicamente CH1, por lo que no duplica la tasa de ambos canales.

El experimento parte del firmware actual (incluido generador150/200kHz y colaDAC vigente), conserva la recetaSPI/CPU y tamaños de nodo vigentes para8/10/12/14, y agrega16CH1 little-endian y su capacidad436 muestras/frame sólo en la copia. El test local ejecuta empaquetadorC real, validadorC relay y ambos decodificadoresPython para las cinco resoluciones, extremos, wrap y corrupción; pasó con sanitizadores.

## Restauración verificada

Firmware/relay/montajes/entorno/políticaCPU y configuración originales restaurados. SHA256 antes y después: `96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9`. Configuración previa y final: ADC8/632411 SPI dual, generador apagado y sus campos originales. Recuperación final10s: 6321024 muestras, sin errores.

## Próximo bloque

1. Repetir y ampliar búsqueda de ticks de forma aislada; los candidatos no son máximos absolutos.
2. Para cada finalista,60s y tres arranques independientes de120s con idéntico binario. Registrar cualquier fallo sin reintento selectivo.
3. Validar GUI/RADIO/FILTER/A0 y calidad analógica aparte antes de incorporar.
4. Los perfiles dual requieren su propia búsqueda; no se reemplazan por cifrasCH1.

[Informe físico](../experimentos/fs_max_all_bits_v17/qualification_20261019_221603/report.json) · [Plan y matriz](../experimentos/fs_max_all_bits_v17/PLAN.md)

## Resultado de la calificación sostenida

Se completó la matriz autorizada:60s+3×120s por candidato que conservó integridad. ADC12 falló durante su primera120s y no se reintentó. Los cuatro restantes completaron las cuatro etapas desde arranques independientes, con controles de regreso. No se incorporaron tasas públicas.

| Bits | Candidato CH1 kS/s | Integridad sostenida | Holgura estricta | Margen medio por etapa | Colas pico60/120/120/120 |
|---|---:|---|---|---:|---|
| 8 | 1632.653 | Pasa | No | 22.04–22.17% | 4/4/5/4 |
| 10 | 1290.323 | Pasa | No | 16.18–16.47% | 4/3/4/3 |
| 12 | 1095.890 | Falla: dropped1 | No | 14,39% sólo60s | 2 / falla / — / — |
| 14 | 909.091 | Pasa | Pasa | 20.05–20.22% | 3/2/3/2 |
| 16 | 145.455 | Pasa | Pasa | 82.87–82.95% | 1/1/1/1 |

8/10bits conservan integridad, pero los picos de cola incumplen<4: no son perfiles con holgura aunque el margen medio supere10%. ADC14/909kS/s yADC16/145,45kS/s pasaron ambos criterios. ADC16 sigue siendo CH1 con sobremuestreo16 y desplazamiento2; no reemplaza ni duplica la tasa dual.

[Resumen auditable](../experimentos/fs_max_all_bits_v17/qualification_summary.json). El runner/auditor conserva la cadena de informes y rechaza etapas repetidas, faltantes, duraciones insuficientes o restauraciones no verificadas.

### Restauración final

Los tres informes de calificación/restauración de la cadena verificaron firmware original `96685eb64cc722adebc7f345f40c3500e22642814bbfc6f182c66c0f992a7ec9`, relay/montajes/entorno/políticaCPU originales y ADC8/632411SPI dual con generador apagado y sus campos previos. El último verificó10s de continuidad sin errores. El candidato físico compartido por todas las etapas fue `cc46e4f798a39edfb8e5bd2db8ecd510dd40fee3f10e89c69978de4191156223`.

### Siguiente etapa

Validar cargaGUI/RADIO/FILTER/A0 y límites analógicos antes de incorporar los finalistas. Para12bits, investigar el dropped1 y preparar una variante aislada; su perfil actual1,067MS/s permanece. Para8/10bits, conservar la distinción entre integridad y holgura y reducir los picos de cola antes de presentarlos con margen. Los perfiles dual requieren campañas propias.

## Calificación sostenida: incidencias previas y diagnóstico corregido

El usuario autorizó60s+3×120s para las cinco resoluciones. El intento `qualification_20261019_224222` cerró antes del snapshot por un dropped1 del relay de producción en ADC8 dual632411; no instaló candidatos. La recuperación `recovery_20261019_2242/report.json` reinició producción, comprobó el mismo SHA256 y restauró configuración con10s sin pérdidas.

`qualification_20261019_224348` rechazó métricas al pasar al candidatoADC8 y luego restauró completamente. Se identificó una omisión del diagnóstico: el perfil privadoADC8 no declaraba `queue_slots=8`, mientras la recetaSPI40 MCU ya usaba8. El decoder asumía4; por eso un pico mayor de4 era rechazado como métrica inválida. No se atribuye este rechazo a pérdida de muestras ni se elimina el informe. La holgura sigue exigiendo cola<4, aunque la capacidad física sea8.

La corrección sólo agrega capacidad de cola al JSON privado y al preparador. MCU/relay conservan los hashes del sondeo. Regresión con empaquetadorC/relayC/decoderPython acepta pico8 y rechaza9. El runner guarda hash del JSON privado y de sus helpers, verifica identidad del binario y ejecuta60s+3×120s por resolución. Integridad y holgura se califican por separado. Un fallo de integridad no se reintenta selectivamente.

## Avance sostenido conservado antes de continuar con14/16

`qualification_20261019_224818/report.json` restauró producción y verificó10s sin errores. ADC8/1,633MS/s yADC10/1,290MS/s completaron60+3×120 sin pérdida, pero ambos incumplieron cola<4: ADC8 tuvo picos4/4/5/4, ADC10 tuvo4/3/4/3. No se declaran perfiles con holgura. ADC12/1,096MS/s pasó60s con cola2; en la primera120s el relay rechazó una trama con CRC correcto y dropped1. No se califica ese candidato12 ni se reintenta selectivamente.

La continuación verifica fuentes, JSON privado, identidad y restauración del informe anterior, y excluye toda resolución que ya tenga una etapa candidata intentada. Sólo mide14/16. La falta de continuación de12 es deliberada: su fallo queda vigente. El informe previo conserva sus casos íntegros y el error original.

## Screening conjunto posterior

[Carga conjunta GUI/RADIO/FILTER/A0](CARGA_CONJUNTA_FS_V17.md):14/909kS/s y16CH1/145,45kS/s pasan ventanasFFT60s por entrada y temporal30s, con holgura.8/1,633MS/s perdió un nodo en carga conjunta y10/1,290MS/s cerró el flujo conFILTER; no se aceptan esos incrementos para uso conjunto. En la campaña prolongada posterior14/909kS/s perdió un nodo en la tercera corrida120s (cola4/4).16CH1 pasó audio/transporte60s+3×120s con cola1 y margen77,88–77,92%, pero una corrida parcialmente oculta impide aceptación visual completa. Producción restaurada. Las tasas siguen privadas; completar validación visible de16 e investigar colas de8/10/14.
