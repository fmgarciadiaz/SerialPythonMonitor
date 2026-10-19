# READY spin50/0 — experimento cerrado, candidato descartado

Eliminar la espera activa empeoró envío medio7,342% en114ticks y9,583%
en112ticks. Conservar50µs;no incorporar spin0 a producción.

[Reporte físico](probe_1400_20261016_002140/report.json):ocho casos30sABBA,ADC8CH1,N3456,
339,659,136 muestras íntegras,CRC/secuencia/epoch/índices/timestamps/rangoDMA
validados,dropped/fatal0. Son sondeos comparativos,no calificación sostenida.

| Variante | Ticks | Muestras | Cola pico | Envío medio µs/nodo | Margen medio |
|---|---:|---:|---:|---:|---:|
| A | 114 | 42,081,984 | 3 | 2209.19 | 10.283% |
| A | 112 | 42,832,800 | 3 | 2142.01 | 11.458% |
| B | 114 | 42,081,984 | 2 | 2357.68 | 4.253% |
| B | 112 | 42,832,800 | 4 | 2348.31 | 2.930% |
| B | 114 | 42,081,120 | 3 | 2361.49 | 4.098% |
| B | 112 | 42,832,800 | 3 | 2343.70 | 3.121% |
| A | 114 | 42,081,984 | 2 | 2187.19 | 11.177% |
| A | 112 | 42,833,664 | 2 | 2139.69 | 11.554% |

B falló holgura en sus cuatro casos;A pasó en los cuatro. Gate previo exige
integridad,holgura y mejora>=2% sin solapamiento en ambas tasas. No habilitó
60+3×120s,ninguna promoción. Menos spin no implica mejor envío por el coste
de dormir/despertar y el solapamiento de etapas;no se midió CPU ni se atribuye
la causa a una función concreta del kernel.

Un mismo relay binario,env50/0 verificado enlogs;MCU idéntico22archivos de
referencia WORD,misma frecuenciaSPI solicitada38MHz. Sin perfilador adicional.
READY conserva lectura inicial,flanco nuevo,tiempo y secuencia por trama,
timeouts y errores. accept por vuelta,recv/send/backpressure yACK intactos.
Prueba local compila funciónC real con GPIO/poll/reloj simulados y verifica
ambas esperas,eventos antiguos,flanco/secuencia inválidos,lectura corta ytimeout.

Cuatro sondas de política fuera de ventanas:12lectores adicionales rechazados,
sin datos ni reemplazo del primario;continuidad yAPPLIED posteriores correctos.

Restauración exacta al snapshot vivo (no al estado de campañas anteriores):
ADC8/1403508SPI,generadorapagado con todos sus campos originales.
Firmware SHA256 antes/después:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
`ok/restored/restore_integrity_ok=true`;14,031,360 muestras
íntegras en10s de cierre. Relay/entorno originales restaurados,app experimental
detenida. Sin aceptación eléctrica,analógica,GUI,RADIO/FILTER,dual niUART.

El runner reutiliza infraestructura previa;runner_sha256/source_hashes/changes
heredados describen también esa base. closure_audit.json registra los scripts
y fuentes propios finales para evitar confundirlos con el runner base.
