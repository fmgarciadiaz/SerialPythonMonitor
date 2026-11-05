# Latencias del relay y del lector · 30/10/2026

La continuación separó costos en el relay, ensayó dos optimizaciones privadas
y midió la demora de ACK antes y después de leer el socket. No se incorporaron
relays ni tasas nuevas. El monitor, firmware y relay aceptados siguen intactos.

## Relay instrumentado

Una copia privada agrega tiempos de pared e histogramas a siete etapas. Acumula
datos en RAM y publica un resumen al abandonar ADC8/1.860.465 S/s. No publica
por frame ni cambia bytes SCP1, CRC, validación, DMA, reservas o relojes. Omite
los intercambios que atraviesan una transición de perfil/época.

En 30 s de RADIO/A0, FFT16k y ventana expuesta, se observaron 34.153 intercambios
en PLAY. Los promedios del control instrumentado fueron:

| Etapa | Media | Máximo observado |
|---|---:|---:|
| Preparar TX | 10,34 µs | 83,96 µs |
| Esperar READY | 267,23 µs | 1.190,53 µs |
| Llamada SPI | 483,62 µs | 608,28 µs |
| Validar las dos mitades | 7,86 µs | 81,09 µs |
| Política de perfil | 2,12 µs | 56,82 µs |
| Recibir comandos/aceptar cliente | 33,97 µs | 171,51 µs |
| Enviar al cliente | 73,85 µs | 221,30 µs |

Son tiempos secuenciales de pared, no utilización de CPU. READY incluye espera
por producción del MCU y planificación. La suma media cubierta fue 878,98 µs;
excluye acumulación de estadísticas y mensajes de progreso. No comparte el
denominador del margen por nodo del MCU. La cola TCP interna observada alcanzó
0 entradas pendientes; no mide las colas del kernel ni del puente ADB.

## Variantes privadas

| Variante | Audio | Margen MCU | Pico MCU | Resultado |
|---|---:|---:|---:|---|
| Control instrumentado, READY50 | 30 s | 10,44 % | 4 | Funcional; holgura FAIL |
| READY250, resto igual | 30 s | 11,70 % | 4 | Funcional; holgura FAIL |
| Envío TCP de las dos mitades juntas, READY50 | UNDERRUN, unos 29 s reproducidos | 11,43 % | 5 | Descartado |

READY250 pasó de 267,23 a 268,12 µs medios de espera observada: no demostró una
reducción de esa etapa. Su proceso consumió 15,05 s de CPU en una ventana de
48,38 s (31,11 % de un núcleo), que incluye arranque y restauración, no sólo
PLAY. El control inicial no registró CPU equivalente; no se infiere una
diferencia de utilización entre ambos.

El envío agrupado bajó la etapa de envío a 58,29 µs, pero no pasó audio ni
holgura. Su helper sólo opera con FIFO vacío y preserva el resto de cada
escritura parcial. El harness C recorrió 1.984 cortes por 64 posiciones del
FIFO (126.976 combinaciones), errores transitorios, desconexiones y wrap.
Pasar esos tests no anula el fallo físico.

Los tres relays se compilaron con la pareja detenida y respaldada. Cada ensayo
restauró fuentes, caché, firmware, relay y estado originales. La instrumentación
es diagnóstica: no se promueve como optimización ni se extrapolan sus resultados
a una versión sin instrumentación.

## ACK leído frente a ACK procesado

Con la pareja aceptada se añadió observación privada, correlacionada por RID y
sesión, de dos instantes: lectura del frame completo y entrada al handler del
decoder. Los contadores no cambian decisiones de refill ni créditos.

`raw_ack_latency_20261030` reprodujo el cierre de flujo al comienzo del audio:
401 ACK correlacionados, máximo 477,91 ms desde enviar CHUNK hasta leer su ACK,
y máximo 10,08 ms entre lectura y handler. Los ACK lentos concretos dejaron
7,70–10,08 ms en esa segunda etapa.

La lectura no es la marca temporal de llegada al kernel. El primer intervalo
incluye transporte, colas y posibles pausas del lector antes de `recv`; el
segundo incluye trabajo del observador, conversión y planificación. No se
atribuye la primera demora exclusivamente a USB/ADB ni se descarta una pausa
del proceso lector. Las fuentes diagnósticas de esa corrida coincidieron
antes/después.

El relay permaneció activo con `dropped=0`. Su log indica cierre en la ruta de
envío (`sent=-1`), pero no conserva `errno`: no distingue FIFO agotado de una
desconexión del puente. La corrida conservó restauración automática fallida;
no se reescribió como éxito. La recuperación externa verificada restauró el
snapshot original durante 10,022 s, sin reiniciar firmware ni relay.

Una segunda corrida con los temporizadores existentes del receptor completó
62,31 s de audio: 5.218 ACK, máximo 16,10 ms hasta lectura y 8,11 ms hasta handler.
No hubo etapas de ≥100 ms; los máximos de pump fueron unos 14 ms. Aun así, la
cola del MCU llegó a 5 y la holgura falló (margen 10,40 %). Esa repetición no
reprodujo la pausa larga: no identifica su causa ni demuestra que esté corregida.

## Estado y siguiente investigación

Hay que separar la pausa intermitente anterior al handler de los picos del MCU
que también aparecen con un lector rápido. Cambiar sólo ráfagas, espera activa
o cantidad de llamadas TCP no produjo una mejora calificable. El próximo
diagnóstico debe correlacionar los tiempos del productor/consumidor MCU y los
del lector; el polling de DMA de 1 ms frente al nodo de 1,875 ms es una hipótesis
de jitter por revisar, no una corrección validada.

Se ejecutaron 29 pruebas offline de instrumentación, parser, CPU, escrituras
parciales, ACK y propiedad/restauración. La comprobación final pasó 10,024 s y
313.344 muestras, `dropped=fatal=0`, snapshot e identidad aceptados iguales:
firmware `37f049fa…`, relay `27da0bc4…`. Sólo Scope V19 y su relay activos;
afinidad SPI original `0-3`, efectiva `0`. V17/V18 intactas.

[Consolidado](../diagnosticos/resultados_v19/relay_latency_final_20261030/summary.json)
· [Restauración final](../diagnosticos/resultados_v19/relay_latency_final_20261030/report.json).
