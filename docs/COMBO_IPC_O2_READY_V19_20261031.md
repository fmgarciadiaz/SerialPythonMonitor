# Combinación IPC500 + O2 + READY250 · 31/10/2026

Dos sondeos privados a ADC8/1.860.465 S/s, FFT16k, RADIO/A0 a40kHz.
La pareja aceptada se respaldó y restauró en cada caso. No se incorporó
la combinación ni se habilitaron tasas. V17/V18 y el runtime siguen intactos.

## Composición exacta

- O2 sólo en `prepare_batch_half`, artefacto ya compilado y verificado.
- Relay instrumentado con espera READY activa acotada a250µs.
- Prellenado ráfaga4/8ms; al enviar PLAY vuelve a8/6ms. QUERY40ms.
- Backoff de500µs tras encontrar vacías las colas de entrada del receptor.

Las reservas, créditos, tamaños y propiedad de nodos hasta EOT permanecen
iguales. El backoff se registra explícitamente en el binding privado;
el hijo rechaza una selección distinta de la declarada y escribe sus
contadores en `ipc_backoff.json`. No se alteró el recibo aceptado.

## Resultados

| Sondeo | Audio RADIO | Margen MCU | Pico acumulado | Slack mínimo | Exposición | Resultado |
|---|---:|---:|---:|---:|---:|---|
| screen20 | 20,035s | 12,60% | 3 | 68.470ticks | 67% | Holgura breve PASS; GUI visible FAIL |
| screen20_repeat | 20,069s | 12,61% | 4 | 81.088ticks | 0% | Holgura FAIL; GUI visible FAIL |

Ambos pasaron las aserciones de reproducción/progreso/Stop/cierre, sin
errores de audio o flujo. El `report.ok=false` se conserva: las comprobaciones
visuales fallaron, y la repetición además incumplió pico<4. Con la ventana
oculta no se acredita carga de dibujo real ni FPS sostenidos. Los contadores
preparados por temporizadores no sustituyen `paintEvent`/exposición Cocoa.

El primer sondeo aislado no constituye aceptación. La segunda medición ya
falló holgura; no se extendió a60s ni3×120s. Los porcentajes no demuestran
una mejora causal frente a casos históricos con distinta exposición.

El backoff difirió403.912/452.398 sondeos vacíos y ejecutó112.700/114.006
lecturas reales respectivamente. No son tiempos CPU ni prueba de menores
colas MCU. El costo del host y la holgura MCU siguen separados.

## Verificación

19 tests dirigidos PASS, incluidos binding de la combinación, coincidencia
de ambos hashes, declaración IPC explícita, restauración del parche, FIFO
real y PCM/créditos/cancelación con spawn. Los cambios son sólo herramientas
privadas y tests; no se cambió el monitor de producción.

Cada rollback verificó fuentes/cache, firmware/relay, configuración del relay,
CPU, snapshot e integridad. Última recuperación10,025s,313.344muestras,
cero pérdidas/fatales. Ningún candidato queda activo; Q disponible.

## Continuación

La combinación contiene el promedio pero no garantiza pico<4. Antes de
combinar más cadencias, medir el ciclo completo del relay y los huecos entre
sus etapas, correlacionándolos con aumentos de cola y envíos de nodo lentos.
Las medidas agregadas previas de etapas no cubren todos los huecos entre
iteraciones. Mantener EOT, tamaños, reservas y criterios; no promover tasas.
La aceptación de dibujo queda pendiente de exposición real suficiente.

[Informes originales y resumen](../diagnosticos/resultados_v19/combo_ipc500_o2_ready250_20261031/summary.json)
· [Pruebas funcionales IPC500](IPC_TRANSICIONES_V19_20261031.md).
