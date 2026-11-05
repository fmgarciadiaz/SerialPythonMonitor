# Salida A0: DMA y trabajo por bloque · 31/10/2026

La salida RADIO/WAV de A0 ya usa DMA: TIM6 dispara el DAC y GPDMA1 canal4
transfiere muestras mediante descriptores enlazados. En40kHz, un bloque de
480muestras dura12ms. Las30reservas equivalen a360ms de muestras; no son
una garantía de tolerancia ante cualquier pausa.

La CPU todavía decodifica/valida CHUNK, copia los códigos al buffer,
gestiona caché/descriptores y responde por RPC. `wav::submit` contiene una
región irq_lock que incluye poll, validación y publicación. Se revisó el
código; no se cambió DMA, prioridades, IRQ, propiedad ni protocolo.

## Medición sin cambiar firmware

Se añadió observación privada de request id/sesión de CHUNK/QUERY y metadatos
nativos de la segunda mitad del mismo lote. El orden del bucle prepara las
respuestas antes de actualizar prepare_us y procesa los comandos después
del exchange; por eso prepare/check describen la iteración anterior.
El ACK identifica el comando respondido, pero la métrica check NO es una
medición aislada de duración irq_lock: incluye decode_pair y procesamiento.
No se clasifica una primera mitad RF sin haber observado el par completo.
Pares sólo de ACK o RF+ACK no tienen la cobertura necesaria y se excluyen.

Sondeo sobre pareja aceptada: ADC8/1.860.465 S/s, FFT16k, RADIO/A0 a40kHz,
sintonía fija710kHz,30,052s de audio y100% de exposición periódica. Sin cortes,
con cola pico4, margen10,12% y slack positivo: funcional, holgura FAIL.

| Respuesta que acompaña metadatos en PLAY | Observaciones | prepare medio | check medio | check máximo |
|---|---:|---:|---:|---:|
| CHUNK | 2502 | 155,18µs | 156,08µs | 392µs |
| QUERY | 520 | 128,22µs | 95,68µs | 350µs |
| Sin ACK WAV en ese lote | 31064 | 145,15µs | 63,31µs | 320µs |

Se correlacionaron3060replies por id/sesión, sin desconocidos, pendientes ni
evicciones al finalizar. Ese contador incluye consultas de ciclo de vida en
otros perfiles; la tabla de tiempos sólo cubre el perfil objetivo. Ausencia
de ACK WAV no significa ausencia de cualquier comando ni costo CPU puro.
La diferencia CHUNK frente a otros lotes es observacional, no aislamiento
causal de copia, caché o IRQ. Tampoco permite atribuir toda la pérdida de
margen vista con A0 al procesamiento CPU: se añaden respuestas/transferencias
y cambia el aprovechamiento de las mitades SPI.

## Qué mejorar y cómo seguir

El objetivo es alimentar el DMA con menos interferencia sobre adquisición,
no sustituir una salida muestra-a-muestra (ya no existe). Priorizar:

1. Separar el costo de validación, publicación/caché y región IRQ en un
   experimento aislado, revisando antes un mecanismo diagnóstico explícito
   que respete el protocolo estricto y la identidad de firmware.
2. Medir el costo de tráfico/respuestas y mitades desperdiciadas por nodo.
3. Elegir la modificación más pequeña según esas medidas, preservando
   CRC, créditos, guardas DMA, reservas y liberación sólo tras EOT.

No mover copias fuera de la sección crítica ni elevar prioridad DMA a ciegas.
No se aplicó ninguna optimización al firmware aceptado ni se habilitaron tasas.

24tests PASS: IDs/sesiones, consultas globales, registros acotados, fixture de
protocolo completo fragmentado entre lecturas, deduplicación y regresiones
de contadores/ACK. Sólo cambiaron herramientas privadas/tests/documentación.

Restauración y verificación final10,025s/313.344muestras, cero pérdidas/fatales,
snapshot/hashes aceptados iguales. Q libre; V17/V18 intactas.

[Resumen y tiempos originales](../diagnosticos/resultados_v19/ack_timing_visible_20261031/summary.json)
· [Código DMA](../arduino/v19/oscilloscope/sketch/wav_dma.h)
· [Servicio WAV](../arduino/v19/oscilloscope/sketch/wav.h).
