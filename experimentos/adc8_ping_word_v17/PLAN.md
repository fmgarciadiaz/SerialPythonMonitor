# PING por palabras — A/B aislado

Autorizado al continuar el ensayo A/B de valid_ping. Un único dueño Q.
Fuentes copiadas del ensayo WORD corregido, sin profiler por etapas.
A:valid_ping referencia. B:tabla constante256bytes + comparación32bits.
CRC32,header,tipo,longitud y cada byte de patrón conservados; sin cambiar
protocolos,DMA,READY,tamaños ni validadores. Sólo se modifica experimento.

Prueba local compila ambas selecciones:2048 secuencias,alteración de cada
byte en cinco secuencias límite,CRC incorrecto y recalculado,paquetes
aleatorios y entrada desalineada. Compara referencia y candidato.

Físico ABBA:en cada bloque30s ticks114 y30s112,N3456,ADC8CH1.
Todos los casos desde arranques independientes. Se conservan las fuentes
y hashes de cada variante en el informe; no mezclar resultados entre ellas.
Sin profiler añadido; se leen tiemposprepare/check ya presentes en DATA.
Son µs enteros de la trama previa,incluyen preempción y dispatch RX,por
lo que no se presentan como tiempo puro exclusivo de valid_ping.

Gate conservador para ampliar:los ocho casos íntegros;ambos B cumplen
holgura en ambas tasas;media envío B>=2% menor que A y sin solapamiento
de medias de los dos casos por variante. Sólo entonces B ticks112 intenta
60s+3×120s con arranques independientes. No600s. Se distinguen integridad
y holgura. Si no pasa el gate, cerrar sin repetir selectivamente los fallos.

Snapshot vivo ADC/generador/WAV/relay/firmware y backup antes de tocar Q.
Finally restaura exactamente y comprueba identidad y10s de continuidad.
No incorpora perfiles ni firmware productivo. No aceptación analógica,
GUI,dual,UART ni carga combinada RADIO/FFT/FILTER.
