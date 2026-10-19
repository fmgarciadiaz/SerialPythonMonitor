# ADC8 compacto directo — íntegro, sin mejora global; campaña cerrada

Formato experimental implementado y validado físicamente:908muestrasADC8 por
tramaSPI992B,sóloCH1alta velocidadticks78..114. Kind20 ycontroles conservados
para otrosformatos ytasas. Cabecera80B yCRC32,payload908 (+5,093%geométrico).
No subir reloj:SPI33,333MHz,READYspin50µs,TCPporframe yWORDDMA de referencia.

**Resultado:**no incorporar porrendimiento. Envío normalizado por muestra
empeoró0,695%114 y1,060%112. DosdecuatroB fallaron margen>=10%,aunque todos
pasaron integridad,colapico<4 yslack positivo. Gatefalse:sin60+3×120s ni
promoción. Másmuestras porframe no demostraron máscaudal con esta geometría.

[Reporte físico completo](probe_1400_20261016_012602/report.json):8×30sABBA,
339,661,888muestras íntegras,dropped/fatal0,CRC/secuencia/epoch/índices/
timestamps/rango ypropiedadDMA verificados. A N3456=4×864,B N3632=4×908.
Se comparaformato+nodo;tiempoµs/nodo dividido porN paraevitar comparar
longitudes distintas. No calificación sostenida ni aceptación analógica/eléctrica.

| Var | Ticks | Nodo | Muestras | Envío µs/muestra | Margen medio | Cola pico | Preparación MCU µs/frame |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 114 | 3456 | 42,081,984 | 0.635591 | 10.794% | 2 | 35.21 |
| A | 112 | 3456 | 42,832,800 | 0.624599 | 10.772% | 3 | 35.15 |
| B | 114 | 3632 | 42,081,260 | 0.636708 | 10.637% | 2 | 34.80 |
| B | 112 | 3632 | 42,835,808 | 0.634542 | 9.351% | 3 | 34.77 |
| B | 114 | 3632 | 42,081,260 | 0.641886 | 9.911% | 2 | 34.78 |
| B | 112 | 3632 | 42,833,992 | 0.629524 | 10.068% | 2 | 34.78 |
| A | 114 | 3456 | 42,081,984 | 0.634183 | 10.992% | 2 | 35.17 |
| A | 112 | 3456 | 42,832,800 | 0.626210 | 10.541% | 3 | 35.14 |

## Qué cambió

El worker construye metadata ypayload directamente enposición final.
c8_finish completa header/estadoSPI/tiempos justoantes del únicoCRC.
No memmove delpayload enfirmware;buffers992B,mismaRAM que referencia.
c8_pack se conserva sólo comooráculo enpruebas. Lasversiones previas se
conservan:../adc8_compact_v17 y../adc8_compact_o2_v17,ambas íntegras pero
prepare~80µs. O2 solo no lo corrigió. Construcción directa bajóprepare a
~34,8µs,vs~35,2µs delcontrol;eso no produjo mejora global por muestra.
No atribuir el coste restante aSPI,kernel oADC sin nueva medición por etapas.

Wireformatidéntico alcodec previo:ADC8/canales1 implícitos,tasa derivada de
ticks explícitos,config/epoch/índice/timestamp preservados. Cola/pico0..4 en
8bits yfuera derango activa faultbit. Todoslos campos dinámicos deadquisición
ytiming permanecen32bits. ErroresSPI/PING/short/retorno/errno se agregan en
faultbit que siempre rechaza:no conservar valoresde contadoresdefallo pero
sí detectarsu presencia. Relay primeroCRC/secuencia,luego normaliza a1024B
locales parareutilizar validación;Python decodifica wire21 ylegacy20 directamente.

## Validaciones

Seis testsC/Python conASAN/UBSAN pasan:encoder directo byteidéntico aloráculo
para todoscounts4..908 yfallos,CRC mutando cada byte,metadata inválida,
continuidad/wrap,padding,legacy yroundtrip exacto de métricas32bits.
MCU yrelay compilaron yejecutaron físicamente.12lectores extra rechazados sin
datos ni reemplazo delprimario;APPLIED,continuidad yperfil640legacy correctos
enloscuatrobloques. NoTCPnuevo niagrupación,notocarREADYporframe.

## Restauración

`ok/restored/restore_integrity_ok=true`. Snapshot yfinal coinciden:
ADC8/1403508SPI,generadorOFF ytodos suscampos,relay/entornooriginales.
14,032,224muestras íntegras en10s decierre. Firmwareoriginalantes/después:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
App experimental detenida.Sin cambios productivos;selectorlocalA0 al cierre.
Hashes de variantes/runner enreporte yfuentesfinales enclosure_audit.json.

## Resultado de la secuencia autorizada

Primero se completó ../adc8_spi40_pilot_v17:40MHzconfigurados y118.479.456
muestras íntegras,piloto10/30s. ADC8ticks112 pasó30s con17,37% demargen ycola2;
ticks110 sólo10s,cola4,sinholgura. No garantíaeléctrica ni perfilestable nuevo.
Después se implementó ycomparócompactación a33,333M paraaislar cambios.
No se combinó40M+compacto ni se modificaron perfiles/UI deproducción.
