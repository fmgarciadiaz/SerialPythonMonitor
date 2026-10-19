# Perfil físico de etapas ADC8 CH1 — 15/10/2026

Medición terminada. Empaquetar no domina el trabajo del MCU: comprobar RX
cuesta **88,7–92,9µs/trama**, frente a33,3µs de packing y34,8–34,9µs de CRC TX.
El relay también tiene costes relevantes:ioctlSPI338–339µs y hostIO105–106µs.
No se suman ambos procesadores; hay solapamiento y esperas.

**Primer candidato de optimización elegido:** `valid_ping`, probando comparación
completa del patrón por palabras de32bits. Es un objetivo específico del camino
serial MCU y preserva el CRC completo y la comprobación de cada byte. Esta
campaña no implementa esa optimización ni demuestra una mejora de tasa.
El relay puede limitar la ganancia global; hostIO todavía agrupa recv/accept/send.
Si la optimización MCU no mejora la cadena, separar esos tres syscalls antes
de elegir cambios de transporte. No atribuir ioctl al tiempo puro del cable:
no se midió reloj SPI efectivo ni se separó coste del kernel.

## Evidencia

- [Control OFF,30s](probe_1400_20261015_222641/report.json).
- [Perfil ON,3×30s independientes](probe_1400_20261015_223109/report.json).
- WORD corregido,ticks114/112/114,N3456,trama992B,SPI solicitado38MHz.
- Integridad completa MCU/relay/host conservada en los cuatro casos:
  CRC,secuencia,epoch,índice/timestamps,rango ADC y propiedad DMA;dropped/fatal0.

| Caso | Ticks | Muestras | Cola pico | Margen medio envío |
|---|---:|---:|---:|---:|
| Control 1 | 114 | 42,081,984 | 3 | 10.475% |
| Perfil 1 | 114 | 42,081,984 | 2 | 9.794% |
| Perfil 2 | 112 | 42,833,664 | 3 | 10.369% |
| Perfil 3 | 114 | 42,081,984 | 3 | 9.064% |

Los perfiles son diagnósticos breves, no aceptación de holgura ni de tasa.
A ticks114 el control tuvo10,475% de margen y las dos ejecuciones ON9,794%
y9,064%. Puede haber perturbación instrumental y variación del sistema;
una sola serie no aleatorizada no permite atribuir causalidad a la diferencia.
No usar contadores ON para promover producción.

## MCU — medias de tiempo transcurrido en µs

| Etapa | Unidad | ticks114,1 | ticks112 | ticks114,2 |
|---|---|---:|---:|---:|
| cache | nodo | 0.990 | 0.986 | 0.990 |
| validate_copy | nodo | 229.774 | 229.384 | 229.993 |
| pack | trama | 33.290 | 33.327 | 33.285 |
| build_frame | trama; incluye pack | 35.256 | 35.294 | 35.255 |
| frame_free_wait | trama; espera | 126.309 | 126.478 | 126.905 |
| seal | trama | 34.823 | 34.880 | 34.857 |
| exchange_setup | trama | 7.495 | 7.472 | 7.501 |
| ready_to_done | trama; espera + SPI | 356.228 | 346.955 | 360.062 |
| exchange_cleanup | trama | 3.802 | 3.717 | 3.609 |
| rx_check | trama | 92.275 | 88.657 | 92.939 |
| probe | sonda vacía | 0.386 | 0.380 | 0.397 |

`validate_copy` comprueba rango/timestamps mientras copia, en una pasada:
no son dos medidas separadas. `build_frame` incluye `pack`. La espera de
buffer no es CPU de empaquetado. `ready_to_done` empieza antes de publicar
READY y termina tras la finalización por semáforo: incluye espera del Linux,
SPI,ISR y planificación. RX incluye principalmente `valid_ping` en estado
estable (CRC y patrón), además de dispatch de comandos ocasionales.
No se midió por separado el CRC RX del chequeo del patrón: proponer `valid_ping`
no demuestra que su patrón sea el componente dominante.

Los contadores son count/suma/max32bits; el MCU congela un triplete coherente
y lo envía en campos40/44 de DATA, antes del CRC32. El host primero valida
la trama completa. Las sumas se reconstruyen módulo2^32 entre snapshots
sucesivos (decenas de ms). Cada media usa su propia ventana entre snapshots,
casi30s; no todas empiezan/terminan en el mismo instante.
Máximos crudos MCU son desde arranque, incluyen startup/preempción y no
son máximos exclusivos de la ventana. La sonda vacía también puede sufrir
preempción: no se resta como constante al resto de los tiempos.

## Relay — medias por trama en µs

| Etapa | ticks114,1 | ticks112 | ticks114,2 |
|---|---:|---:|---:|
| ping_build | 11.621 | 10.626 | 12.044 |
| ready_wait | 147.421 | 137.687 | 145.662 |
| spi_ioctl | 338.585 | 338.328 | 339.005 |
| validate | 11.212 | 12.154 | 11.725 |
| host_io | 105.979 | 105.306 | 106.343 |
| loop_total | 615.636 | 604.861 | 615.594 |

Relay registra ventanas10s sin imprimir por trama. Se descarta la inicial y
se usan las dos últimas completas (aprox20s por caso); JSON contiene tiempos,
cuentas y máximos de esas ventanas. `loop_total` incluye el resto de etapas,
por lo que no se agrega a ellas. READY es espera,hostIO agrupa tres syscalls.
Los relojes MCU y Linux son independientes; no se restan etapas cruzadas
para estimar latencia exacta ni se presenta esto como CPU exclusivo.

## Restauración y pruebas

Ambas campañas: `ok/restored/restore_integrity_ok=true`. Restauración exacta
aV17,relay original,ADC10/1167883SPI,generadorapagado y campos originales;
11.676.096 muestras íntegras en10s al terminar cada campaña. Identidadfirmware
idéntica antes/después:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
App experimental detenida; ninguna fuente o perfil productivo modificado.

Tres pruebas locales pasan:fragmentación/tripletes/desborde,CRC inválido sin
aceptar métricas y descarte de ventana inicial relay. MCU y relay compilaron
y ejecutaron físicamente con instrumentación OFF y ON. Hashes de fuentes MCU
verificados al cierre (control reconstruye sólo profile_config.h=0).
No aceptación analógica,GUI,dual,UART,RADIO/FFT/FILTER.

## Experimento siguiente propuesto

Un único cambio: comparación PING por palabras, sin quitar CRC ni bytes.
Antes de hardware, comprobar equivalencia con referencia:secuencias arbitrarias,
cada posición de payload alterada y resellada,CRC incorrecto,longitud/tipo
inválidos. Luego A/B con perfil OFF y sondeos iguales desde arranques nuevos;
medir `valid_ping` separadamente sólo en diagnóstico. Si hay mejora repetida,
recién pasar a60+3×120s para integridad y holgura. Mantener respaldo y restore.
