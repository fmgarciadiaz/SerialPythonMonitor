# accept con lector activo — A/B aislado

A:accept cada trama. B:accept cada16tramas sólo con cliente activo.
Sin cliente,se consulta cada vuelta en ambas variantes. Un mismo binario
acepta únicamente SCOPE_ACCEPT_INTERVAL1/16 al arrancar;se verifica en log.
MCU de referencia WORD corregido idéntico en ambos;sin PING optimizado ni
perfilador por etapas. Ningún cambio productivo.

OrdenABBA,30s ticks114/112,N3456,ADC8CH1,arranques independientes.
Se mantienen CRC,continuidad,ACK,READY,send por trama y backpressure.
Medir sólo campos temporales MCU existentes y métricas de cola/envío.
Mismo gate previo:todos íntegros,B con holgura en ambos casos/tasas,
mejora envío>=2% en ambas tasas,sin solapamiento de medias. Sólo entonces
B ticks112 intenta60+3×120s. Sin600s ni promoción automática.

Después de cada bloque,prueba de política (fuera de ventanas de rendimiento):
abrir lector primario con datos válidos y verificar admisión;3 conexiones
extra no bloqueantes a su mismo túnelADB,sin enviar comandos. El coordinador
bombea continuamente el primario y exige rechazo de extras en1s,sin datos
para extras y sin pérdida/errores del primario. Luego APPLIED112 y muestras.
No hay otro dueño deQ:las conexiones son sondas controladas por el runner.
Latencia medida desde cliente incluye ADB/host y tiempo de bombeo,no tiempo
exclusivo accept. No prometer demora universal por consultar cada16tramas.

Snapshot vivo ADC/generador/WAV,relay/entorno y firmware;backup nuevo.
Finally restaura exactamente y comprueba firma y10s íntegros. Cortar ante
fallo de integridad o política;no repetir selectivamente para aceptar.
No aceptación analógica,GUI,dual,UART,RADIO/FFT/FILTER.
