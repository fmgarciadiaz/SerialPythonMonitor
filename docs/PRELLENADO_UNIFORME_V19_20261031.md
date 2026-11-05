# Prellenado uniforme: un bloque/8ms · 31/10/2026

Se probó un candidato privado que limita el prellenado a un bloque por
turno, con intervalo de8ms. Al enviar PLAY recupera el régimen8/6ms.
Las reservas/créditos siguen en30bloques; no cambia el transporte,
ADC, tamaño de bloques ni propiedad de nodos. Runtime y V17/V18 intactos.

El harness exige `--startup-only` para ráfaga1; sin esa declaración rechaza
la orden antes de operar el Q. El descriptor se copia y sólo afecta RADIO40k.
Los tests verifican reservas intactas y restauración del régimen PLAY.

## Tres ensayos físicos

ADC8/1.860.465 S/s, FFT16k y RADIO/A0 a40kHz. Exposición periódica100%
en los tres; todas las aserciones funcionales y de dibujo pasaron.

| Caso | Audio | Margen MCU | Pico acumulado | Holgura |
|---|---:|---:|---:|---|
| Firmware aceptado + relay de ciclo, sondeo | 20,084s | 10,29% | 3 | Sondeo PASS |
| Mismo caso, extensión | 60,015s | 9,98% | 4 | FAIL |
| O2 + READY250 + IPC500 + prellenado1/8 | 20,074s | 12,39% | 4 | FAIL |

La extensión de60s no se continuó a120s. La combinación tampoco se extendió.
No se incorporó el candidato ni se habilitaron tasas. Las diferencias de media
entre corridas no acreditan mejora causal del prellenado durante PLAY, cuyo
régimen se mantuvo igual en estos experimentos.

## Qué aisló

En las tres corridas, el prellenado no elevó la cola por encima del pico2
que ya tenía la adquisición sin audio. Los30 CHUNK iniciales no tuvieron
intervalos menores de6ms. El sondeo pasó a pico3 durante PLAY; en la extensión
apareció pico4 también durante PLAY, nodo13404. En la combinación el pico4
se observó durante PLAY, nodo3142, después del pico3 en nodo2841.

La combinación registró1086 intervalos CHUNK menores de1ms durante PLAY,
de1670 intervalos observados. Es consistente con reposición en ráfagas, pero
el agregado no prueba que esas ráfagas causaran el pico. Los timestamps del
host y contadores acumulados MCU no son el mismo reloj ni instante causal.

Por tanto el prellenado más uniforme redujo el pico observado en el arranque
en estos casos, pero no resolvió la holgura sostenida. No descartar el pico
acumulado del arranque ni reemplazarlo por ocupación muestreada.

## Verificación

15 tests del harness/relay/ciclo PASS antes del primer sondeo; después
16 tests de binding firmware y ráfaga PASS al habilitar explícitamente
la combinación. Las suites se solapan y no se suman como31 casos únicos.

Los tres ensayos restauraron snapshot, identidad, fuentes, configuración
del relay y CPU. Última verificación10,024s/313.344muestras, cero pérdidas/
fatales, pareja aceptada activa y Q libre. La combinación restauró además
el firmware aceptado; no queda ningún candidato instalado.

## Próximo bloque

Registrar una ventana acotada de envíos CHUNK alrededor de los aumentos de
pico observados. Después contrastar una reposición más uniforme durante
PLAY con opción privada separada, preservando capacidad de recuperación,
créditos, reservas y Stop. No relajar silenciosamente la restricción actual
de ráfaga1 sólo para prellenado. Validar primero tokens/ACK/recovery y luego
sondeo breve con el mismo perfil. No subir tasas con esta evidencia.

[Resumen y restauraciones](../diagnosticos/resultados_v19/prefill1_consolidated_20261031/summary.json)
· [Ciclo completo previo](CICLO_RELAY_V19_20261031.md).
