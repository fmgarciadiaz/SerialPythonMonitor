# Perfil recv/accept/send — campaña cerrada

Diagnóstico ADC8CH1 completado:cuatro arranques independientes30s a
114/112/112/114ticks,N3456. MCU de referencia con WORD corregido,sin perfilador
MCU ni PING por palabras. Sólo se añadió temporización al relay aislado.

**Hallazgo:** `accept` consume30.4–32.5µs por llamada y devuelveEAGAIN en todas
las llamadas de las ventanas estables medidas. Es trabajo repetido sin
conexiones nuevas que atender. `recv` cuesta unos5µs y también devuelveEAGAIN;
`send` cuesta67–74µs y siempre envía la trama completa. Los valores exactos
se tabulan abajo; no equivalen a CPU exclusivo ni a tiempo puro de red.

**Siguiente candidato elegido:** probar menor frecuencia de `accept` mientras
exista un cliente activo, manteniendo comprobación por vuelta cuando no lo haya.
Propuesta inicial A/B:una consulta cada16tramas frente a cada trama,con MCU y
resto de política idénticos en ambas variantes. Mantener un único lector y
rechazar conexiones adicionales sin reemplazarlo; declarar el nuevo retardo
para rechazar conexiones mientras haya un lector. La demora depende del ritmo
de vueltas, no prometer un límite universal enms. No tocar recv/send todavía.
El candidato no se implementó en esta campaña.

## Integridad y alcance

[Reporte físico completo](probe_1400_20261015_232227/report.json),
`ok/restored/restore_integrity_ok=true`. Total 169,830,432 muestras,
CRC,secuencia,epoch,índices/timestamps,rango y propiedad DMA íntegros;
dropped/fatal0. Son sondeos diagnósticos,no aceptación de tasas ni holgura.

| Caso | Ticks | Muestras | Cola pico | Margen medio envío |
|---:|---:|---:|---:|---:|
| 1 | 114 | 42,081,984 | 3 | 11.281% |
| 2 | 112 | 42,832,800 | 2 | 11.920% |
| 3 | 112 | 42,833,664 | 2 | 11.058% |
| 4 | 114 | 42,081,984 | 3 | 11.249% |

## Medias por llamada o vuelta,µs

| Etapa |114,caso1|112,caso2|112,caso3|114,caso4|
|---|---:|---:|---:|---:|
| recv | 4.715 | 4.931 | 4.883 | 4.800 |
| accept | 31.201 | 32.196 | 32.496 | 30.419 |
| send | 71.126 | 70.877 | 67.051 | 73.522 |
| host_io | 108.512 | 109.549 | 105.927 | 110.294 |
| ping_build | 11.666 | 10.520 | 10.796 | 11.629 |
| ready_wait | 142.729 | 133.318 | 136.495 | 142.370 |
| spi_ioctl | 340.311 | 337.927 | 338.475 | 338.775 |
| validate | 11.361 | 12.269 | 12.179 | 11.529 |
| loop_total | 615.614 | 604.799 | 604.787 | 615.595 |

Para recv/accept/send,unidad=llamada;para el resto,unidad=vuelta de relay.
En las ventanas seleccionadas hay una llamada a cada syscall por vuelta,
de modo que se puede comparar su contribución a hostIO. En todas las ventanas:

- recv:100% EAGAIN,0bytes recibidos;comandos de configuración ocurrieron antes.
- accept:100% EAGAIN,ninguna conexión nueva aceptada.
- send:100%992bytes enviados,sin EAGAIN,envíos cortos ni otros errores.

JSON conserva cuentas,bytes,máximos y ventanas exactas por caso. Alrededor de
20s por caso:ventanas10s,descartar primera y usar dos últimas completas.
No extrapolar la ausencia de comandos a una GUI en interacción continua.

## Interpretación y límites

HostIO contiene las tres syscalls,decisiones y coste de sus contadores;
loop_total contiene el resto. No sumarlos con sus partes. READY es espera.
Tiempo transcurrido incluye kernel,preempción y planificación;SPI solicitado
38MHz no es medida de reloj efectivo. No se deriva velocidad de cable desde
el ioctl. Instrumentación puede perturbar tiempos;no hubo controlOFF nuevo
ni se usa este diagnóstico para promover perfiles.

Reducir accept no garantiza ganar esos30.4–32.5µs en la cadena:MCU y Linux se
solapan y la espera READY puede crecer al liberar el relay. Tampoco sumar esta
posible ganancia con la de PING anterior. El A/B debe medir envío,nodos,cola,
slack y latencia/rechazo de conexión antes de concluir. El envío por trama,
CRC,continuidad,backpressure y ACK deben conservarse.

## Restauración y verificación

Q restaurado exactamente aV17,relay original,ADC10/1167883SPI,generadorapagado
con todos sus campos;11,676,096 muestras íntegras en10s. Identidad firmware original
igual antes/después:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
App experimental detenida;sin cambios productivos. Fuentes MCU coinciden con
sus hashes capturados. Fuentes relay,runner y tests registradas al cierre.

Tres pruebas locales pasan:contadoresC y JSON reales (éxito,EAGAIN,EINTR,error,
envío corto),medias ponderadas/descarte de ventana incompleta y exclusión de
startup. Relay compilado y ejecutado enQ. Se preservó errno después de medir
cada syscall para mantener las decisiones originales de error.
No aceptación analógica,GUI,RADIO/FFT/FILTER,dual ni UART.
