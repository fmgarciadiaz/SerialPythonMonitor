# PING por palabras — A/B físico cerrado

La variante B reduce la comprobación RX del MCU **24–27%**, manteniendo
CRC32 y validación del patrón completo. La mejora del envío por nodo es
**2,583% a ticks114** y **0,815% a ticks112**. No cumple el criterio previo
de mejora>=2% en ambas tasas: **no se amplía a60+3×120s ni se incorpora**.
No se declara mayor tasa aceptada ni holgura sostenida.

## Cambio aislado

A conserva el cuerpo de valid_ping de referencia. B compara el patrón por
palabras32bits y usa una tabla constante256B (repetición del patrón cada256B).
La carga usa memcpy de4bytes,con orden little-endian explícito. Ambos conservan
chequeo de header,versión,tipo,longitud,CRC32 y todos los972bytes del patrón.
No cambia SPI,READY,DMA,protocolo ni validadores. No se incluye el perfilador
por etapas; se recogen solamente prepare/check ya presentes en DATA.

Pruebas C++ compilaron ambas selecciones y verificaron2048 secuencias,
alteración de cada byte para cinco secuencias límite,CRC inválido y resellado,
paquetes aleatorios y entrada desalineada. Otra prueba comprueba que el gate
rechaza falta de holgura o medias solapadas. Dos pruebas locales pasan.

## A–B–B–A,30s por caso

Cada caso tiene arranque independiente;ADC8CH1,N3456,ticks114/112.
Ticks114=1.403.508,772 muestras/s;ticks112=1.428.571,429 muestras/s.
Todos pasaron CRC,secuencia,epoch,índices/timestamps,rango,propiedad DMA y
contadores dropped/fatal0. Total: 339,656,544 muestras.

| Bloque | Variante | Ticks | Muestras | RXcheck µs/trama | Envío µs/nodo | Margen medio | Cola pico |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | A | 114 | 42,081,120 | 92.806 | 2237.849 | 9.119% | 4 |
| 1 | A | 112 | 42,831,936 | 88.359 | 2129.245 | 11.986% | 3 |
| 2 | B | 114 | 42,081,120 | 67.572 | 2168.761 | 11.925% | 2 |
| 2 | B | 112 | 42,832,800 | 66.280 | 2114.593 | 12.591% | 2 |
| 3 | B | 114 | 42,081,984 | 67.443 | 2138.876 | 13.139% | 3 |
| 3 | B | 112 | 42,832,800 | 66.430 | 2110.563 | 12.758% | 3 |
| 4 | A | 114 | 42,081,984 | 90.984 | 2184.027 | 11.305% | 2 |
| 4 | A | 112 | 42,832,800 | 86.238 | 2130.630 | 11.928% | 2 |

Los cuatro casos B cumplen holgura **sólo en estos sondeos30s**. A del primer
bloque ticks114 no cumple holgura (cola4,margen9,119%); pasó integridad.
No se elimina esa observación ni se repiten selectivamente los casos.

## Interpretación

El gate compara las medias de envío por nodo de dos casos por variante y
por tasa:requiere mejora>=2%,sin solapamiento de medias,y todos B íntegros
con margen>=10%,cola pico<4,slack>0. Ticks114 pasa;ticks112 falla por mejora
pequeña. No es una prueba estadística formal;ABBA reduce sesgo de orden,
pero dos repeticiones no caracterizan toda la variabilidad del sistema.

RXcheck incluye valid_ping y dispatch ocasional,tiempos enterosµs de la trama
previa,además de preempción. No es tiempo exclusivo CPU del patrón ni separa
CRC RX. El CRC y validación completa se mantienen en ambos casos.
La reducción consistente de RX no se traduce proporcionalmente al envío:
las etapas se solapan con relay/SPI/host. El resultado no identifica por sí
solo cuál syscall o espera domina el límite global.

Siguiente diagnóstico elegido:separar recv,accept y send dentro de hostIO
(antes105–106µs/trama),sin modificar todavía su política ni agrupar tramas.
Complementarlo con tiempo ioctlSPI y READY en las mismas ventanas. Después
seleccionar un único cambio según el componente medido;no asumir el reloj
SPI efectivo a partir del valor solicitado38MHz.

## Evidencia y restauración

[Reporte completo](probe_1400_20261015_230008/report.json):
`ok/restored/restore_integrity_ok=true`. `ok` significa A/B completado,
no aceptación productiva. `winners` vacío;no validación sostenida nueva.

Q restaurado exactamente aV17,relay original,ADC10/1167883SPI,generador
apagado y sus campos originales;11,675,400 muestras íntegras en10s.
Hash firmware original idéntico antes/después:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
App experimental detenida;ninguna fuente,selector o perfil productivo cambiado.
Selector experimental local queda A;B se conserva en el mismo header de
protocolo y se selecciona con SCOPE_WORD_PING1. Hashes de ambas variantes
verificados al cierre reconstruyendo sólo ese selector. No aceptación
analógica,GUI,RADIO/FFT/FILTER,dual ni UART.
