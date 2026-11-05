# Reposición durante PLAY · 31/10/2026

Se añadieron dos variantes privadas de ráfaga PLAY, conservando prellenado1/8ms,
intervalo de recuperación6ms y reservas/créditos30. Se probaron con O2,
READY250 e IPC500 ya verificados. No se cambió runtime, tasas públicas,
transporte, ADC ni propiedad de nodos. V17/V18 permanecen intactas.

## Registro acotado

El observador conserva los últimos8 envíos CHUNK exitosos (request id,
monotonic del host y fase), y adjunta esa ventana al observar un aumento de
pico MCU. Sin PCM/arrays RF. Se conserva el pico acumulado desde arranque.
`host_observed_at` indica lectura/observación en el host, no el instante MCU
del pico. Que el último envío esté cerca no prueba causalidad; la respuesta
puede describir un estado anterior.

## Resultados

ADC8/1.860.465 S/s, FFT16k, RADIO/A0 a40kHz.

| Caso | Audio | Exposición periódica | Margen MCU | Pico | Resultado |
|---|---:|---:|---:|---:|---|
| PLAY1/6ms, sondeo | 20,015s | 0% | 11,70% | 5 | Holgura y GUI visible FAIL; audio funcional |
| PLAY2/6ms, sondeo | 20,073s | 100% | 11,27% | 3 | Sondeo breve PASS |
| PLAY2/6ms, extensión | 60,014s | 7% | 11,02% | 4 | Holgura y GUI visible FAIL; audio funcional |

Ninguno presentó cortes/errores de audio o adquisición. El sondeo PLAY1
no se extendió. PLAY2 pasó el sondeo visible, pero falló a60s: no se
hicieron3×120s ni se promovió ningún candidato. Las distintas exposiciones
impiden atribuir causalmente diferencias numéricas de rendimiento entre casos.
La ventana oculta no acredita carga de dibujo; el fallo de pico es además
independiente de esa falta de validación visual.

En PLAY1 no hubo intervalos CHUNK menores6ms, pero aun así apareció pico3
antes del audio, sin CHUNK enviados, y luego picos4/5 enPLAY, nodos4310/4317.
Los8 envíos anteriores al pico5 estaban separados entre6,94 y8,43ms.
Las micro-ráfagas no son una explicación suficiente de esos picos.

PLAY1 produjo1370 lotesRF+idle en20s, frente a565 del caso anterior PLAY8,
con volumen de audio parecido. Distribuir RPC uno por uno puede empeorar
el aprovechamiento de las dos mitades físicas. Es una hipótesis compatible
con el registro, no demostración causal. En PLAY2 se observaron1222RF+idle
en el sondeo20s; por eso tampoco se lo presenta como mejora de eficiencia.

En la extensión PLAY2 el pico3 llegó en nodo9352 y el pico4 en33653, ambos
PLAY. La recuperación de audio funcionó, pero no contuvo el pico acumulado.
No se descarta ese evento por aparecer tarde o por tener ocupación muestreada3.

## Harness y tests

`--play-burst 1/2` es una selección privada separada y registrada en el binding.
Requiere prellenado explícito; no relaja silenciosamente el gate de ráfaga1
sólo para arranque. El hijo rechaza declaraciones PLAY distintas del binding.
Sin opción PLAY, el harness conserva el retorno anterior8/6ms.

La ráfaga es capacidad del token bucket, no un límite absoluto de mensajes
por llamada si pasa tiempo suficiente para recargar tokens dentro de ella.
Con6ms hay capacidad nominal166,7bloques/s frente a consumo83,3bloques/s;
las corridas físicas no convierten esa capacidad nominal en garantía temporal.

31 tests dirigidos PASS: reserva/intervalo, agotamiento de tokens acumulados,
reposición de créditos, binding explícito, ventana acotada sin PCM y regresiones
previas. Se corrigió el texto de informes futuros para distinguir el PLAY
privado del retorno estándar; los informes físicos originales siguen intactos.

## Restauración y siguiente diagnóstico

Los tres casos restauraron exactamente snapshot, hashes, fuentes,
configuración del relay y CPU. Última verificación10,025s/313.344muestras,
cero pérdidas/fatales. Pareja aceptada activa; Q disponible.

No seguir afinando cadencias a ciegas. Próximo bloque: comparar, en sondeos
privados acotados, la interferencia RPC y el aprovechamiento real de mitades
SPI por nodo, con un control RF sin audio. Mantener identificaciones,
CRC, dos mitades y EOT. Antes de modificar transporte, revisar propiedad de
buffers, límites de RAM y validación; no liberar nodos antes de tiempo para
bajar artificialmente el pico. Dibujo visible sigue siendo requisito para
aceptación combinada, y ningún caso fallido habilita tasas superiores.

[Consolidado](../diagnosticos/resultados_v19/play_pacing_consolidated_20261031/summary.json)
· [Prellenado previo](PRELLENADO_UNIFORME_V19_20261031.md).
