# TCP batch1/2 — cerrado, candidato descartado

Agrupar dos frames por envío TCP no mejoró la cadena:envío medio por nodo
empeoró0,632% en114ticks y4,517% en112ticks. Conservar un frame por envío.
No atribuir la diferencia a una función concreta ni concluir que todo
batchingTCP es peor:se ensayó esta política y esta carga.

[Reporte completo](probe_1400_20261016_004318/report.json):8×30sABBA,ADC8CH1,N3456,
339,658,272 muestras íntegras,dropped/fatal0,CRC/secuencia/epoch/índices/
timestamps/rango yDMA conservados. No calificación sostenida ni promoción.

| Variante | Ticks | Muestras | Cola pico | Envío medio µs/nodo | Margen medio |
|---|---:|---:|---:|---:|---:|
| A | 114 | 42,081,984 | 3 | 2216.23 | 9.997% |
| A | 112 | 42,832,800 | 2 | 2172.69 | 10.190% |
| B | 114 | 42,081,984 | 2 | 2238.37 | 9.098% |
| B | 112 | 42,833,664 | 2 | 2274.88 | 5.965% |
| B | 114 | 42,081,984 | 2 | 2230.87 | 9.403% |
| B | 112 | 42,833,664 | 2 | 2266.61 | 6.308% |
| A | 114 | 42,079,392 | 2 | 2224.97 | 9.642% |
| A | 112 | 42,832,800 | 2 | 2172.52 | 10.197% |

Las cuatroB fallaron margen>=10%,aunque cola pico2 yslack positivo.
A112 pasó holgura en ambas repeticiones;A114 quedó9,997% y9,642%.
Gatefalse en ambas tasas:no mejora>=2%,ni separación favorable,niholguraB.
No se ejecutó60+3×120s. Integridad y holgura son resultados distintos.
La métrica de envío está tomada enMCU por nodo,no es duración exclusiva
sendTCP. No hubo perfilador por syscall ni medición deCPU en esta campaña.

## Cambio aislado

Mismo binario relay,envSCOPE_TCP_BATCH1/2 confirmado al arranque.MCU idéntico
22archivos a referenciaWORD,SPI solicitado38M yREADYspin50µs intactos.
A mantiene send directo sin copia adicional;B guarda hasta1984bytes de
frames ya validados y los envía en orden. Primera entrega,control/noDATA,
comandos pendientes/parciales yACK fuerzan vaciado. Si hayDATA pendiente,
precede al control en el mismo envío. No hay protocoloTCP nuevo.

Para DATA sin pareja,la esperaREADY se acorta al objetivo de1ms de antigüedad,
vacía y vuelve a esperar el flanco fresco dentro del deadline original.
No es garantía temporal dura enLinux.Se descartan pendientes al cerrar;
un envío parcial/EAGAIN/EINTR/error cierra la sesión,sin seguir ese stream.
accept por vuelta yvalidaciónSPI se conservan.El wrapper nuevo de deadline
es común aA/B;A nunca retiene datos.Se compara contraA del mismo binario,
no contra métricas absolutas de campañas anteriores.

## Controles funcionales

Después de cada bloque,fuera de rendimiento:admisión primaria,3lectoresextra
rechazados,sindatos ni sustitución del principal,continuidad yAPPLIED.
12rechazos correctos,latencia observada cliente1.146–4.258ms;
incluyeADB/host,no límite universal del relay.
Cuatro cambios aADC8ticks640(250kS/s),con35424–36288muestras continuas por
ventana de~0,15s,yvueltaAPPLIED112.Ejercitan separación entre frames mayor
que1ms.No constituyen medición precisa del tiempo de vaciado.

Prueba local compila el helperC real consend simulado:bytes yorden idénticos,
parejas,control trasDATA,primera entrega inmediata,vencimiento sin pareja,
backpressure/EAGAIN yenvío corto,descartar bytes abandonados antes de cliente
nuevo.Pasó.MCU/relay compilaron y ejecutaron físicamente.

## Restauración

`ok/restored/restore_integrity_ok=true`. Snapshot yestado final exactos:
ADC8/1403508SPI,generadorOFF con todos sus campos restaurados,relay/entorno
originales,app experimental detenida.14,031,360 muestras
íntegras en10s de cierre.Firmwareoriginal SHA256 antes/después:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.

Sin cambios productivos ni aceptación eléctrica,analógica,GUI,RADIO/FILTER,
dual/UART.closure_audit.json registra fuentes propias;runner_sha256 yotros
campos heredados del reporte incluyen referencias a infraestructura base.

Siguiente opción con mayor alcance:estudiar formatoADC8alta velocidad con
más muestras útiles por intercambioSPI,aún sin implementar ni afirmar ganancia.
