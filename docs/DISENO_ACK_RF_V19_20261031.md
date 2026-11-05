# Diseño privado de ACK WAV combinado con RF — 2026-10-31

Estado: propuesta para Arduscopio Q, pendiente de implementación y pruebas
offline. Este documento no cambia firmware, relay, receptor ni tasas públicas.
La pareja V19 aceptada permanece como control y destino de restauración; V17 y
V18 no se modifican. Los identificadores de despliegue se conservan.

## Evidencia y pregunta pendiente

El perfilado privado de WAV separó los costes dentro de `submit`: en las
muestras seleccionadas durante PLAY, el tramo con interrupciones enmascaradas
promedió aproximadamente 50,10 µs; validación 24,94 µs y copia 18,87 µs. El
candidato `memcpy` instrumentado empeoró la copia a 37,46 µs y el tramo IRQ a
68,67 µs, según el sondeo comunicado por el coordinador. Se descarta ese
candidato. El estado final de restauración debe consultarse en el informe de
su campaña, no inferirse de este documento.

A 40 ksample/s y 480 muestras por CHUNK, unos 83,33 CHUNK/s requieren ACK. Un
ACK independiente de 992 bytes representa aproximadamente 82,7 kB/s de frames
lógicos de salida, además de sus efectos sobre lotes y planificación. Los
50 µs medidos por CHUNK representan aproximadamente 0,42 % de un segundo a
esa cadencia; esto no cuantifica el perjuicio de bloquear IRQ en momentos
críticos. El coste del framing y de intercalar respuestas con RF es una
**hipótesis de trabajo, todavía no una causa demostrada** del margen observado.

El siguiente experimento debe comprobar si transportar un ACK exitoso dentro
de un frame RF ya disponible reduce esos costes. No debe esperar muestras
para responder ni reducir el contenido RF.

La campaña `wav_validation_gui20_20261031` aporta esta composición observada
durante aproximadamente 20,043 s de PLAY:

| Observación | Cantidad |
| --- | ---: |
| Frames ACK12 recibidos | 2046 |
| Frames DATA20 recibidos | 43504, incluidos 702 estados vacíos |
| CHUNK enviados | 1670 |
| QUERY enviados | 375 |
| STOP enviados dentro de la ventana | 1 |
| Lotes `rf+rf` | 20171 |
| Lotes `wav+rf` | 1897 |
| Lotes `wav+idle` | 148 |
| Lotes `rf+idle` | 554 |

ACK12 representa aproximadamente 4,49 % de los frames recibidos en esa
ventana. La propuesta sólo busca combinar ACK de CHUNK: QUERY y STOP mantienen
sus respuestas completas. La mezcla de lotes favorece estudiar la hipótesis,
pero no demuestra cuánto margen recuperará ni que todos los ACK puedan
combinarse. Los límites de fase se observan desde el host y no son fronteras
sincrónicas de las colas del MCU.

Como otra referencia de escala, el máximo IRQ instrumentado de 51,66 µs por
unos 83 CHUNK/s equivale a unos 4,3 ms/s, aproximadamente 0,43 % del tiempo de
pared. No es utilización total de CPU, no incluye todo el trabajo WAV y no
explica por sí solo diferencias de unos ocho puntos de margen. Las
microoptimizaciones de ese tramo no permiten prometer resolver el problema
completo; los bloqueos puntuales y la planificación aún requieren evidencia.

## Contrato propuesto del frame

Se reservan provisionalmente dos nombres, con números **22 y 23 tentativos**:
`RF_CHUNK_OK_BUFFERING` y `RF_CHUNK_OK_PLAYING`. Antes de implementar, auditar
las asignaciones de kinds en MCU, relay, receptor, herramientas y experimentos;
los números sólo se fijan después de esa auditoría.

| Campo | Contrato privado |
| --- | --- |
| Kind | ACK CHUNK exitoso; estado BUFFERING o PLAYING según el snapshot de respuesta |
| Offset 40, uint32 LE | Request ID del CHUNK confirmado |
| Offset 44, uint32 LE | `played` del mismo snapshot de respuesta |
| Offsets 16–39 | Diagnósticos SPI originales, conservados |
| Offsets 48–987 | Metadatos, muestras y padding RF nativos originales, conservados |
| Offset 988 | CRC del frame completo, calculado después de insertar kind y ACK |

Se mantienen tamaño 992, versión, longitud de payload, secuencia global,
índices, timestamps, bits, canales, época ADC, número de muestras y geometría
del nodo. Los nuevos kinds requieren RF real (`count > 0`); no se crean
frames vacíos combinados. `prepare_us/check_us` no existen en esos dos kinds:
ningún agregador puede interpretar 40/44 como tiempos. DATA20 conserva su
contrato habitual. Esta variante no se combina inicialmente con el schema de
perfilado WAV que también utiliza 40/44.

## Elegibilidad y orden en el MCU

La cola de respuestas WAV debe transportar un wrapper interno con la respuesta
completa y una marca de elegibilidad derivada del comando realmente procesado.
No inferir CHUNK a partir del estado BUFFERING/PLAYING: QUERY puede devolverlos.
El snapshot completo se congela al producir la respuesta; no volver a leer
`queue.played`, estado o sesión al preparar el frame.

Una respuesta sólo es combinable si corresponde a CHUNK, reason OK, estado
BUFFERING/PLAYING, sesión coincidente y `reply.accepted == request.offset +
request.count`, con suma comprobada sin overflow. El MCU comprobará también
que el crédito reconstruible coincide con `reply.free`. Cualquier discrepancia
usa ACK12 completo. Inicialmente, los reenvíos/duplicados usan ACK12 completo;
no es necesario compactarlos para probar la hipótesis.

Se respeta el orden FIFO de respuestas: sólo se considera la cabecera de la
cola, sin buscar una respuesta posterior que sea combinable ni sobrepasar
respuestas de control. Se conserva la prioridad vigente entre las colas.
Si esa respuesta es elegible y hay RF disponible de inmediato, se consume una
respuesta y un frame RF para formar una sola mitad lógica. En cualquier otro
caso se emite el ACK12 original, sin esperar RF. BEGIN, PLAY, STOP, QUERY,
errores y estados terminales siempre conservan ACK12.

La decisión de consumir RF debe ser única: no retirar un token para después
perderlo al elegir fallback. Ambas mitades del lote físico se resuelven con
esta misma regla; no se agrega una espera para completar la segunda mitad.

## Ownership RF y créditos tras EOT

Una mitad combinada tiene la fuente RF que realmente utilizó: Normal,
Pipelined o Word. **No** se clasifica como `Source::Reply`. La marca ACK es
ortogonal a esa fuente y no genera créditos RF adicionales.

Se mantienen las reglas existentes de `scope_batch2`: Word devuelve su slot
scratch después de copiar, pero el nodo sólo se libera tras el éxito físico
si era su fragmento final; Normal/Pipelined liberan el crédito correspondiente
después del intercambio físico completo. Un fallo de DMA, longitud o comando
no devuelve propiedad del nodo ni inventa una nueva política de reintentos.
La respuesta y las muestras se sellan juntas y comparten el resultado físico.

## Ledger de requests y reconstrucción del ACK

El `wav_inflight` actual guarda sólo tiempo de envío y kind. No basta para este
protocolo. La variante privada necesita un registro inmutable por request con
generación de conexión/sesión, kind, session, offset, count, total, rate,
queue_slots y capacidades confirmadas por el ACK completo de BEGIN. No tomar
estos datos de la sesión que casualmente esté activa al recibir el frame.

Para un CHUNK elegible, usando su registro verificado:

```text
accepted = offset + count
used = ceil((accepted - played) / 480)
free = queue_slots - used
```

La igualdad es exacta con el contrato vigente: los bloques no finales tienen
480 muestras, el único bloque corto es el final, y `played` avanza al liberar
bloques completos. Validar rango y ausencia de overflow, `played <= accepted
<= total`, geometría de bloques, alineación de `played` mientras quedan datos,
y `0 <= used <= queue_slots`. No generalizar esta fórmula a futuros bloques
variables. Los créditos se aplican con las mismas comprobaciones de monotonía
y una sola confirmación por request que hoy usa la ruta ACK12.

El receptor cancela inflight al enviar comandos no CHUNK, incluido STOP. Por
eso debe conservar tombstones acotados con el contexto de requests confirmados
o cancelados, suficiente para distinguir un ACK tardío de uno inventado.
Dimensionar el límite según ventanas y colas máximas; no expulsar silenciosamente
contexto que aún pueda estar en vuelo. No reutilizar IDs mientras estén vivos
o retenidos. Un nuevo BEGIN/conexión crea una generación distinta.

Un ACK repetido o cancelado reconocido no otorga créditos, no revierte estado
y no se entrega dos veces. Su RF sigue siendo procesable. Un ACK sin contexto
verificable es un error del protocolo ACK y no se reconstruye usando valores
actuales. Debe distinguirse en el diagnóstico de un error RF; no se contabiliza
como corrupción de muestras sólo por desconocer el request. La recuperación
de ese error conserva la política estricta existente, sin continuar concediendo
créditos por suposición.

## Validación íntegra en relay y host

El relay privado debe aplicar a los nuevos kinds **las mismas validaciones RF
de DATA20**, incluidos CRC, secuencia, perfil, época, límites de cola, índices,
timestamps, padding, continuidad y contadores de fallo. No convertir el frame
en DATA20 modificando bytes antes de comprobar su CRC original.

La compresión tampoco habilita debilitar las comprobaciones semánticas de ACK.
El relay actual valida ACK12 sin necesitar un ledger de salida; el nuevo ACK
omite campos que antes estaban presentes. Por tanto, el diseño requiere un
ledger privado también en el relay para reconstruir y validar esos campos a
partir de comandos completos verificados y efectivamente enviados al MCU,
con contexto de BEGIN y política de duplicados/cancelación equivalente. Si no
puede garantizarse esa validación independiente, el bloque queda pendiente:
no sustituirla silenciosamente por confianza exclusiva en el host.

El host valida íntegramente el frame combinado antes de modificar créditos o
publicar muestras. La ruta debe producir los dos resultados, RF y ACK, sin el
`continue` que hoy termina una respuesta ACK12 independiente. Un error RF/CRC
impide aceptar también su ACK. Un ACK duplicado o cancelado reconocido no
suprime el RF válido. Se conserva el procesamiento temprano del ACK antes del
trabajo costoso de conversión ADC, después de validar ambos componentes.

Los observers cuentan el frame físico una sola vez y registran separadamente
ACK combinados, ACK12 fallback por motivo, RF transportado y comandos CHUNK.
Los costes prepare/check excluyen los nuevos kinds de forma explícita.

## Compatibilidad y aislamiento

La capacidad se habilita exclusivamente mediante una identidad privada
verificada de MCU + relay + host/schema. Rechazar antes de operar cualquier
combinación incompleta. Los consumidores normales mantienen el rechazo de
kinds desconocidos; no ampliar globalmente sus whitelists ni relajar la pareja
aceptada. El fallback ACK12 es una decisión de disponibilidad/semántica dentro
de la pareja privada, no una negociación que permita usar un relay antiguo.

El experimento inicial modifica sólo el transporte del ACK: no combina cambios
de copia PCM, validación, cadencia host, tamaño de nodo ni tasa ADC. Los fuentes,
BIN/ELF, relay y código host privados quedan vinculados en manifiestos exactos.

## Próximos bloques y criterios de cierre

1. **Contrato y pruebas offline.** Auditar kinds; implementar la selección como
   operación comprobable; verificar la reconstrucción frente a respuestas
   completas. Cubrir chunks de 480 y finales de 1/479, cola llena, duplicados,
   conflictos de ID, STOP/BEGIN con respuestas tardías, IDs y épocas próximos
   a wrap, padding/CRC incorrectos y estados terminales. Probar combinaciones
   de las dos mitades del lote, fuentes RF, fragmento final y fallos físicos;
   cada muestra y cada crédito deben conservarse exactamente una vez. Probar
   también fragmentación del stream TCP y mezcla de ACK12/DATA20/nuevos kinds.
2. **Binding y compilación privada.** Exigir todas las pruebas anteriores;
   compilar control y candidato aislados con la pareja detenida, comparar el
   control con el BIN aceptado y registrar hashes y diferencias exactas.
   Restaurar y verificar la pareja antes de cerrar la compilación. No cargar
   el candidato sólo porque haya compilado.
3. **Sondeo privado breve, con un propietario del Q.** Sólo después de cerrar
   los bloques anteriores: comparar el mismo escenario y cadencia, registrar
   cuántos ACK realmente se fusionan, fallback, mezcla de lotes, integridad,
   continuidad WAV, margen y pico de cola. La ausencia de ahorro o una regresión
   detienen esta línea. Al finalizar, restaurar y verificar firmware, relay,
   fuentes, configuración e identidad aceptados, incluso ante fallo.

El resultado de estos bloques decide si merece una campaña posterior. Una
mejora aislada, una ejecución íntegra o una compilación correcta no habilitan
tasas públicas ni constituyen aceptación de rendimiento, audio o comportamiento
visible de la GUI.

Referencias locales: [perfilado WAV](PERFILADO_WAV_V19_20261031.md),
[validación IRQ](VALIDACION_WAV_IRQ_V19_20261031.md) y
[métricas del sondeo base](../diagnosticos/resultados_v19/wav_timing_profile20_20261031/wire_metrics.json).
La composición de tráfico procede de las
[métricas de validación con GUI](../diagnosticos/resultados_v19/wav_validation_gui20_20261031/wire_metrics.json).

## Prototipo offline pausado al retomar V20 de Gemini

`tools/ack_rf_contract_v19.py/.h` y sus11tests son un prototipo aislado,
sin integración en monitor/firmware/relay. La revisión posterior de Astra encontró
pendientes que impiden cargarlo: resolver CHUNK con fallback ACK12 completo,
reservar tombstones para todas las solicitudes antes de enviarlas, comprobar
monotonía por sesión y garantizar checkpoints FIFO antes de llenar el historial.
Los tests actuales no cierran esos casos. El trabajo activo pasó a validar la
pareja V20/SRAM3; este prototipo NO habilita una prueba física ni una aceptación.
