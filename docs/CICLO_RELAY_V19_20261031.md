# Ciclo completo del relay · 31/10/2026

Se generó un relay de diagnóstico aislado desde las fuentes aceptadas V19.
No cambia SPI, READY, empaquetado, colas, validación ni propiedad hasta EOT.
Sólo registra tiempos de pared y un conjunto acotado de observaciones;
no son porcentajes CPU ni conserva muestras RF. No se promovió ningún
artefacto ni se habilitaron tasas. V17/V18 y runtime permanecen intactos.

## Qué se midió

La instrumentación anterior cubría siete etapas hasta terminar el envío al
PC. Ahora se cierra el ciclo al comenzar la siguiente iteración:
`ciclo = etapas cubiertas + hueco`. El hueco incluye agregación diagnóstica,
mensajes de progreso y lo restante del bucle. Se guardan ocho ciclos más
lentos y hasta16 aumentos de pico observado, con secuencia SPI y contadores
MCU. El resumen se imprime al salir del perfil objetivo, sin logging por frame.

Los contadores MCU corresponden a replies: copia/sondeo son máximos
acumulados y send al nodo anterior. El hueco de un evento ocurre DESPUÉS
de la respuesta registrada; no debe atribuirse como causa del pico observado.
La cronología se compara por secuencia, no sólo por compartir una fila.

## Corrección conservada

La primera implementación leyó la época desde offset80 (timestamp) en lugar
de flags76. Sus tiempos de ciclo y etapas no dependían de ese campo y se
conservan, pero su asociación de épocas/eventos de pico es inválida. El
`cycle_summary.json` inicial está marcado explícitamente; logs, binario y
report original no se reemplazaron. La repetición usa otro directorio/build.
Una regresión en C basada en el fixture de protocolo existente verifica
ahora que todos los eventos tengan la época correcta.

## Dos mediciones corregidas

ADC8/1.860.465 S/s, firmware aceptado, FFT16k y RADIO/A0 a40kHz. Mismo relay
instrumentado en ambos casos. Control con cadencia de producción; variante
con prellenado4/8ms y retorno a8/6ms al enviar PLAY. Reservas y tamaños iguales.

| Caso | Audio | Exposición periódica | Ciclo medio PLAY | Hueco medio / máximo PLAY | Margen MCU / pico |
|---|---:|---:|---:|---:|---:|
| Control | 30,039s | 100% | 881,80µs | 1,45 / 59,27µs | 10,10% / 4 |
| Prellenado suave | 30,080s | 100% | 881,95µs | 1,63 / 64,11µs | 10,02% / 3 |

Ambos pasaron audio, progreso, Stop, datos FFT, dibujo visible y cierre. El
control falla holgura por pico4. La variante pasa sólo esta medición breve,
con apenas0,02 puntos porcentuales sobre el umbral de margen. No acredita
estabilidad sostenida; existen fallos históricos de variantes de prellenado.
No se extendió como aceptación60s+3×120s ni se promovió el relay diagnóstico.

En el control, el pico4 se observó durante PREPARING, nodo2730, antes de
PLAY. El prellenado suave sólo llegó a pico3, nodo2751, también PREPARING.
Después no hubo nuevos aumentos del pico acumulado en ninguna de las dos
corridas. El criterio sigue usando ese acumulado completo; no se lo reinicia
al entrar en PLAY ni se sustituye por ocupación muestreada.

Los ciclos PLAY más lentos registrados tenían cola1: un ciclo largo puede
incluir espera por datos, por lo que no equivale por sí solo a congestión.
El hueco externo fue0,16–0,18% del ciclo, pequeño en estas ventanas. Esto no
excluye pausas raras que no aparecieron en30s.

Etapas del control durante PLAY, medias: preparaciónTX9,76µs, READY260,03µs,
SPI ioctl486,03µs, validación8,09µs, política2,79µs, recepciónPC36,77µs,
envíoPC76,88µs. Son paredes secuenciales, no uso CPU. READY incluye trabajo
MCU y planificación; no es enteramente costo del GPIO.

## Verificación y continuación

22 tests dirigidos PASS: compilación/ejecución C, partición temporal exacta,
límite de eventos, época compatible con protocolo, parser, artefactos,
bindings privados e integridad de contadores. Dos builds y tres ensayos
restauraron la pareja aceptada. Última recuperación10,023s/313.344muestras,
cero pérdidas/fatales, snapshot/hashes/fuentes/configuración del relay/CPU
iguales. No queda candidato activo; Q disponible.

El siguiente sondeo debe apuntar al prellenado: medir las etapas y la mezcla
RF/ACK alrededor de los aumentos de pico y contrastar una reposición inicial
más uniforme. Mantener el régimen de PLAY y las reservas, y validar primero
cualquier cambio del harness. No optimizar el hueco externo como supuesto
cuello principal ni subir tasas con esta evidencia breve.

[Consolidado](../diagnosticos/resultados_v19/relay_cycle_consolidated_20261031/summary.json)
· [Control corregido](../diagnosticos/resultados_v19/relay_cycle_epochfix_gui_20261031/cycle_summary.json)
· [Prellenado suave](../diagnosticos/resultados_v19/relay_cycle_prefill4_gui_20261031/cycle_summary.json).
