# ADC8 alta velocidad: formato compacto experimental kind21

Se ejecuta después del pilotoSPI40 y de restaurarQ. Este experimento vuelve
aSPI38solicitados/33,333configurados,READYspin50µs yTCPporframe de referencia.
No acumular ganancias ni incorporar40MHz al evaluar compactación.

## Contrato

SCP1v4 kind21 sóloADC8CH1 ticks78..114. OtrosADC ytasas conservan kind20.
Físico992B/CRC32original;cabecera80B,payload908B. Comandos/APPLIED idénticos.
Kind20 tiene864muestras por frame;kind21,908 (+5,093% geométrico).
Se eliminan repeticiones de bits/canales/tasa (implícitos o derivados de
configuración explícita) y se compactan cola/pico a8bits cadauno.
Config ticks/n en32bits;resultadoSPI0/992 enbit15 delcount;fallos de transporte
enbit14,que siempre rechaza el validador. No se descartan errores silenciosamente.
Todas las métricas dinámicas de adquisición ytemporización se conservan32bits.

| Offset | Contenido |
|---:|---|
|0..15|SCP1,v4,kind21,secuencia,length972|
|16|ACK últimoPING|
|20|n<<16 \| ticks|
|24,28,32,36|índice,node,epoch/flags,timestamp|
|40..43|count14bits,faultbit14,result992bit15,cola8,pico8|
|44,48|dropped,fatal|
|52,56|prepare_us,check_us|
|60,64,68,72,76|copy_max,poll_max,slack_min,send_previous,produced|
|80..987|hasta908muestras8bit,paddingcero|
|988..991|CRC32 de0..987|

MCU usa scratchinterno1056B por bufferalineado,tresbuffers:+192B vsreferencia.
Construye canónico conhasta908muestras ycompacta antes del únicoCRC yDMA.
SPI sigue992B/DSIZE8/WORDDMA,sin cambiarTSIZE ni propiedad de buffers.
Relay primeroCRC/secuencia,normaliza kind21 a1024B locales yreutiliza
las comprobaciones de configuración,epoch,índice,timestamp,DMA/estado/rango.
Python experimental decodifica20/21 directamente,sin expandir frames falsos.

## Comparación yrestauración

A selector0,kind20,N3456=4×864. B selector1,kind21,N3632=4×908.
Nodos múltiplos16 paraDMA. Geometría ajustada al payload paraevitar quinto
frame parcialmente vacío. Se compara el conjunto formato+nodo,no sólocabecera.
ABBA30s114/112,cada caso conreinicioindependiente. Comparar envío por muestra
(µs/nodo dividido porN),no tiempos brutos de nodos distintos.
Gate:todos íntegros,Bholgura>=10%,cola<4,slackpositivo,mejora normalizada>=2%
en ambas tasas ysin solapamiento de medias. Si pasa:60+3×120sB112,N3632.
No600s ni promoción automática. Corte primer fallo,restauración siempre.

Después de cada bloque:lectorprimario,3extras rechazados,continuidad yAPPLIED;
vuelta a perfil lento640 confirma que B usa kind20 fuera dealta velocidad.
Snapshots/backup,hash,relay/entorno yADC/generador originales,10scontinuidad.
No tocar producción,GUI,dual,UART,RADIO/FILTER ni reclamar aceptación eléctrica.
