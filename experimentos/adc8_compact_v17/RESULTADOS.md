# Compactación ADC8 inicial — íntegra, sin mejora de rendimiento

[Reporte](probe_1400_20261016_010412/report.json):8×30sABBA,339,659,120muestras íntegras,
dropped/fatal0. Kind21ADC8alta velocidad908muestras/992B implementado enMCU,
relay ydecoder experimental. Otrosformatos ytasas mantienen kind20.

La versión inicial empeoró envío normalizado por muestra3,724%114 y6,254%112.
Los4casosB fallaronholgura;gatefalse,sinpruebas largas ni promoción.

| Variante | Ticks | Nodo | Envío µs/muestra | Margen medio | Preparación MCU µs/frame |
|---|---:|---:|---:|---:|---:|
| A | 114 | 3456 | 0.633425 | 11.098% | 35.21 |
| A | 112 | 3456 | 0.626133 | 10.552% | 35.15 |
| B | 114 | 3632 | 0.660480 | 7.301% | 80.51 |
| B | 112 | 3632 | 0.660801 | 5.600% | 80.51 |
| B | 114 | 3632 | 0.659849 | 7.390% | 80.36 |
| B | 112 | 3632 | 0.661682 | 5.474% | 80.51 |
| A | 114 | 3456 | 0.639500 | 10.246% | 35.16 |
| A | 112 | 3456 | 0.618512 | 11.641% | 35.20 |

Preparación B~80µs frente~35µs enA:coste adicional~45µs/frame. El helpernuevo
no tenía atributos de optimización explícitos que sí usan data_frame,
put/get delprotocolo ybuild_samples. No atribuirlo sólo a compilación sin
comparar:se prepara revisión aislada O2MCU en ../adc8_compact_o2_v17,con
misma representación binaria ymisma matriz. No reemplazar este resultado.

A N3456=4×864,B N3632=4×908,mismaSPI33,333MHz. Se comparaformato+nodo,
con envíoµs/nodo dividido porN;no comparar tiempos brutos de nodosdistintos.
CRC,secuencia,epoch,índice,timestamps,errores y métricas32bits conservados.
Relay normaliza localmente después delCRC;Python decodifica elwire directo.
Buffers internosMCU+192B;SPI sigue992B yREADYfresco porframe.

Cinco pruebas locales conASAN/UBSAN pasan:codecC/decoderPython,mutación de
cada byte,CRC,metadata inválida,continuidad/desbordes,legacy,padding yroundtrip
exacto de métricasdinámicas32bits. MCU yrelay compilaron ycorrieron enQ.
12lectores adicionales rechazados sin sustituir primario;APPLIED yperfil
lento640 conkind20 correctos enlos4bloques.No mediciónCPU ni analogíaeléctrica.

Restauración exacta firmware/relay/entorno/ADC8/1403508SPI,generadorOFF ytodos
sus campos;hashfirmwareidéntico:
`3e275a52cb560bf08bca481972a18ff21debc9442236b65f55b74c566c9cac8c`.
`ok/restored/restore_integrity_ok=true`;14,032,224muestras/10s.
App experimental detenida,producción sin cambios.La revisiónO2 esotra campaña.
