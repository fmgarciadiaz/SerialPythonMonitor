# ADC8 alta velocidad: construcción directa de kind21

Objetivo:908muestras8bit por tramaSPI992B,frente864 del formato20 (+5,093%
geométrico),sin subir reloj ni perder verificaciones. SóloADC8CH1ticks78..114.
OtrosADC ytasas conservan kind20. Tipo experimental21,SCP1v4,length972,CRC32.
Comandos yAPPLIED sin cambios. Producciónintacta.

Las campañas adc8_compact_v17 yadc8_compact_o2_v17 se conservan porseparado:
ambas íntegramente correctas,pero sin mejora concompactación tras construir
un frame canónico. O2 delhelper no redujo preparación~80µs vscontrol~35µs.
Aquí el worker construye header80 ypayload directamente,sinmemmove de908B.
c8_finish completa cabeceraSPI/tiempos antes del únicoCRC. Framebuffers992B,
mismaRAM que referencia. c8_pack queda sólo comooráculo de prueba,no enfirmware.

## Wireformat

| Offset | Campo |
|---:|---|
|0..15|SCP1/v4/kind21/secuencia/length972|
|16|últimoPING válido|
|20|node_pairs<<16 \| ticks|
|24,28,32,36|índice,node,epoch/flags,timestamp|
|40..43|count14bits,faultbit14,result992bit15,queue8,peak8|
|44,48|dropped,fatal32bits|
|52,56|prepare_us,check_us32bits|
|60,64,68,72,76|copy,poll,slack,send_previous,produced32bits|
|80..987|hasta908muestras,paddingcero|
|988..991|CRC32de0..987|

bits8/canales1 implícitos enkind21;tasa derivada deticks explícitos. Se retienen
todas las métricas dinámicas. Cualquier errorSPI/PING/short/retorno/errno ocola
inválida activa faultbit yel validador rechaza.No truncar fallos silenciosamente.
Relay validaCRC,secuencia,configuración/epoch ycontinuidad,index/timestamp/rango,
normalizando metadatos localmente.Python decodifica los bytes originales.

Seis testsC/Python conASAN/UBSAN:bytes directos idénticos aloráculo para cada
count4..908 yfallos,CRC cada byte,metadata,continuidad/wrap,padding,legacy,
roundtrip de métricas32bits. Compilar ymedirQ sólotrasrestaurar campaña previa.

## Matriz ycriterio

SPI38solicitados/33,333configurados,WORDDMA,READYspin50µs,fresco portrama,
TCPporframe.A N3456=4×864,B N3632=4×908,ambosDMAalineados16samples.
ABBA,114/112ticks,30s porcaso,reinicios independientes.Se evalúa conjunto
formato+nodo;normalizar envíoµs/nodo porN,no comparar nodos de distinta longitud.
Gate:todos íntegros,Bmargen>=10%,cola<4inclstartup,slackpositivo ymejora>=2%
por muestra enambas tasas,conmedias sinsolapamiento.Sólo si pasa:
60+3×120sB112/N3632,máximo120s porrun,sin promoción automática.

Fuera deventanas,lectorprimario/3extrasrechazados,APPLIED yperfil640legacy
conmuestras,regreso112.Snapshotvivo/backup,un dueñoQ.Finally restaura firmware,
relay/entorno,ADC ygenerador exactos,hash y10scontinuidad.App experimental
inactiva al cierre.No aceptación eléctrica/analógica/GUI,dual/UART/RADIO/FILTER.
