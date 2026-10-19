# Radio V17: margen, resoluciones y tasas

1. Probar funciones WAV críticas compiladas con O2 en copia aislada; sin
cambiar formato, tasas, resolución DAC ni tamaño de búfer. Comparar cola,
check_us y continuidad conjunta ADC8/1600000 + audio40k. Respaldar y restaurar
headers exactos, firmware, relay, ADC/generador; 10s de recuperación.
2. Reproducir RADIO en ADC10/12/14/16 y transición de perfiles; habilitar
entrada CH1 de perfiles duales sin reinterpretar muestras ni llamar CH1 a
un formato de transporte nuevo. Aplicar límites de sintonía reales.
3. Retomar checkpoint ADC10/12 aceptados aislados, completar ADC14; estudiar
ADC16 conservando sobremuestreo y separar transporte, analogía y holgura.
No promover tasas nuevas sin evidencia. Una sola instancia dueña de Q.

## CRC por hardware: candidato posterior, todavía aislado

Mantiene CRC-32/ISO-HDLC, initFFFFFFFF, polinomio04C11DB7, inversión de
entrada por palabra y salida por bit, xorFFFFFFFF. El primer frame988 se
compara con la versión software; si no coincide, se conserva software.
Acceso serializado por irq_lock en el MCU; no altera el CRC del periférico SPI.
Pruebas host con modelo independiente de polinomio normal, 250 longitudes
múltiplo4 y direcciones desalineadas, comparadas contra zlib y la referencia.
Fuente primaria: https://dev.st.com/stm32cube-docs/stm32u5-hal2/2.0.0-beta.1.1/docs/drivers/ll_drivers/crc/api/ll_crc_exported_constants.html
También contrastado con stm32u5xx_ll_crc.h/ll_bus.h del core instalado1.0.0.
No se habilita en producción hasta cerrar la prueba física y restauración.

## Reserva de audio (ensayo 2026-10-17, aún sin promover)

El CRC por palabras alineadas dio ~17% de margen medio de envío; el ensayo de 120 s mantuvo ADC íntegro pero agotó la reserva de audio. Se conserva como fallo documentado en `probe_20261017_104144/report.json`.

Candidato siguiente: muestras DAC de 16 bits, 30 bloques de 480 muestras (360 ms a 40 kHz), capacidad informada en el estado WAV y validada por relay y PC. RAM PCM/tabla compartida 28.800 bytes, menor que los 30.720 previos. Tabla Radio Test conserva formato de 32 bits. Cambio de propietario explícito con DMA detenido. Referencia primaria: ST AN5593, tabla 10, ancho DMA de 16 bits permitido para DAC.

Primer ensayo de 60 s; sólo si pasa, 120 s. Cada ensayo verifica PCM → Radio Test → PCM a baja carga antes de restaurar. La matriz RADIO de otros bits exige evidencia de 120 s del mismo candidato. Firmwares anteriores siguen negociando 16 bloques.

El primer candidato 16→16 falló al iniciar DAC (`probe_20261017_110316`); ADC sin drops/fatals. Coincide con la advertencia ya existente en `generator_dma.h` sobre accesos de 16 bits al DAC de esta Q. No promover. Siguiente candidato conserva RAM de 16 bits pero escribe palabras de 32 bits al periférico con `LL_DMA_DATA_ALIGN_ZEROPADD` (sin empaquetar dos muestras en una escritura); BNDT y propiedad se miden en bytes del origen. Contrastar continuidad, número de muestras reproducidas y cambio de propietario en el próximo ensayo de 60 s.

Candidato PCM16→DAC32: `probe_20261017_110901` pasó 60 s y `probe_20261017_111453` pasó 120 s. Ambos verificaron PCM → Radio Test → PCM y restauraron firmware original 23bc0e...; 10 s de recuperación íntegros. Margen conjunto 16,97% / 17,15%, cola pico 5 en ambas corridas: integridad y audio correctos, holgura completa no aceptada.

Matriz `probe_20261017_112140`: RADIO40k pasó ADC10/1167883 y ADC12/981595 durante 20 s cada uno, colas pico 3 y 2. El siguiente caso ADC14/851063 cerró flujo antes de registrar configuración aplicada; ADC16 no ejecutado. Diagnóstico ahora persiste la excepción original antes del cleanup y el runner captura logs del relay en fallos. Repetir ADC14 aislado antes de promover. La matriz incompleta no acredita ADC14/16.

El usuario pidió posponer 14 y 16 bits mientras `probe_20261017_112739` ya estaba restaurando. No continuar pruebas de esas resoluciones. El caso aislado ADC14 volvió a cerrar flujo; se guardó `failure_relay.log` (CRC correcto; rechazo de integridad y contadores MCU de pérdida/fatal). No investigar ni promover ADC14/16 hasta retomar explícitamente ese alcance. Continuar sólo ADC8/10/12.
