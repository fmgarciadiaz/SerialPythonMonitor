# Sondear cómo llegar a 1,5 MS/s: arranque y tamaño de nodo

El usuario redirigió la búsqueda hacia 1500 kHz, no validar tasas inferiores.
Se interrumpió y restauró la búsqueda anterior. Objetivo de este sondeo:
ADC8/CH1,106 ticks=1.509.433,962S/s,el punto fijo inmediatamente superior
a1,5M con reloj160M.107ticks daría1.495.327,103,por debajo;no usar jitter
de períodos ni cambiar relojADC para fingir tasaexacta.

Evidencia previa:106 pasó10s y60s,pero perdió un nodo durante asentamiento
tras reinicio para120s;cola4,slackpositivo,fatal0.105 tuvo igualpatrón.
108 completó60+3×120 íntegros,pero sinholgura. No aceptar106 por reintentos
selectivos ni descartar fallos de arranque.

Hipótesis a contrastar sin cambiar código MCU/relay:
calentamiento de la cadena antes del salto de tasa ycapacidad temporal de
la cola ante una demora transitoria. N6912 duplica tiempo por nodo ybuffer,
no reduce transferencias por muestra ni garantiza mayorcaudal. Ya se probó
antes conSPI33,333;esta combinaciónSPI40/contexto es distinta.

| Esquema | Preparación | Nodo |
|---|---|---:|
|A|directo106 desde arranque|3456|
|B|112 durante2s bombeando yvalidando,luego106|3456|
|C|directo106 desde arranque|6912|
|D|112 durante2s bombeando yvalidando,luego106|6912|

Tres arranques independientes de10s poresquema,enordenABCDBCDACDAB.
Primeros512frames válidos de106 guardan índice/node/cola/peak/send/slack y
tiempo de recepciónhost para diagnóstico. No confundirlo con trazadoCPU.
Controles/APPLIED/epoch ycontinuidad estrictos enambos saltos. Error corta
elcaso yreinicia antes delsiguiente;ningún error se ignora para aceptar.

A sólo control:fallosprevios impiden reclamar resuelto por3pantallas nuevas.
B/C/D son elegibles si sus3casos pasan integridad yholgura. Pororden de
menor cambio:B,C,D,validar elegibles60+3×120 sintraza extra,abortando perfil
alprimer error. Si alcanza4/4 integridad yholgura,terminar. No600s.
Si ninguna alternativa funciona,se documenta el límite sin promocionar.

SPI40,WORDDMA,kind20/864,READY50us yTCPporframe intactos;fuentesidénticas
a40sostenido. No compilar enQ durante medida. LecturasSPI fuenteNOCACHE,
DFS6/div3 fuera deventanas. Siempre snapshot/backup/restauración exacta de
firmware/relay/ADC/generador/entorno,hash,10scontinuidad yclockoriginal.
Sinproducción ni aceptacióneléctrica/analógica/GUI/dual/UART/RADIO.
