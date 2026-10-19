# ADC8 CH1: envío mejorado para 1,4 MHz

Fuentes y aplicación independientes de V16 y del barrido maxfreq anterior.
v1–v4 solicitan SPI a 32 MHz; v5 solicita 36 MHz. Tramas kind20/SCP1 V4 de
992 bytes conservadas. La frecuencia solicitada no certifica el reloj físico.

Variantes ensayadas (fuentes previas archivadas en ZIP):

- v2: sustituye el pipeline por la espera original y reutiliza la configuración
  DMA SPI sólo después de confirmar que los canales quedaron detenidos/reset.
- v3: agrega O3 y desenrollado de cuatro iteraciones a validación/copia;
  sigue comprobando cada timestamp y cada valor ADC.
- v4: agrega O3 al productor, construcción de fragmentos e hilo de salida;
  desenrolla ocho muestras en el empaquetado ADC8, conservando sus colas.

- v5: parte de v3 y solicita SPI a 36 MHz en el relay. Antes de compilar
  el relay se detienen adquisición y aplicación estable después del snapshot
  y respaldo; el snapshot se conserva hasta la restauración exacta.

Cambios v1:

- Preparar hasta tres fragmentos mientras SPI transmite el anterior. La copia
  del nodo sigue siendo inmutable y sólo se libera al completar físicamente
  el último fragmento. Los ACK de control conservan prioridad.
- En ADC8 cada byte representa un valor válido. El relay conserva CRC,
  metadatos, padding y límites de nodo; comprueba continuidad de índice y
  timestamp por los extremos del fragmento, cuya progresión interna es fija.
  No se eliminan bytes ni timestamps del protocolo.
- Consumir un evento READY ya encolado antes de llamar poll. Se mantienen
  secuencia de eventos, timeout y descarte de créditos anteriores al I/O.

Pruebas locales: constructor/decodificadores C y Python con wraps y corrupción;
comparación del validador anterior contra el optimizado con tramas válidas y
campos/padding/CRC corruptos. Compilación MCU/relay antes de medir.

Ensayo físico: un dueño Q, snapshot vivo y respaldo antes de preparar;
caffeinate y diferencia pared/monotónico. Referencia ADC8/131 ticks/N6912
durante 10 s. Después ticks115 y114 (1,391304 y1,403509 MHz), nodos3456,
6912 y8192 durante 5 s más 1 s de estabilización, con reinicio independiente.

Sólo perfiles que pasan avanzan a 60 s + 3×120 s + 600 s. Exigir CRC,
secuencia, epoch, índices/timestamps, DMA, dropped=fatal=0. Informar integridad
por separado del margen: >=10% envío medio, cola pico<4 y slack positivo.
No se promueve ninguna tasa a la UI de producción en esta campaña.

Finalmente se restaura la aplicación y el relay de producción, todos los
campos previos, identidad/hash de firmware y diez segundos de continuidad.
Resultados por caso persistidos, con fuentes/hashes y errores de arranque
separados de los resultados de adquisición. Precisión analógica no evaluada.

Pruebas adicionales v4: `test_validation.py` comprueba CH1, wraps, colas
de bucles (1/3/4/7/8/9/257/416/864/8192 muestras), corrupción en cada
posición y que el empaquetado ADC8 no escriba fuera de su salida.

## Continuación: SPI38 y esperas (v6)

Solicitar 38MHz en el relay, sin compresión. El MCU cede CPU sin la
pausa artificial de5us; el relay lee READY en espera activa acotada a50us
antes de poll. Conserva timeout, secuencia estricta y rechazo de flancos
anteriores al I/O. Prueba local test_ready.py cubre flanco fresco/antiguo,
secuencia incorrecta, EINTR, espera acotada y timeout. Se repite la misma
matriz y restauración; sólo se acepta una tasa tras60+3x120+600s.

## Comparación de planificación Linux (v7)

Conservar SPI38, MCU y espera READY de v6. Sólo el relay experimental
usa SCHED_FIFO prioridad10 y su contenedor recibe SYS_NICE. El arranque
exige confirmación del scheduler y primera trama válida; si no puede activar
la prioridad, falla y restaura. El launcher de producción se conserva para
la restauración, sin SYS_NICE ni variable RT. Espera activa50us acotada,
poll con timeout y SPI bloqueante mantienen puntos de espera del proceso.
Misma referencia/matriz/aceptación/restauración. No compresión.

## V8: buffers por referencia y preparación solapada (2026-10-13)

Se conserva SPI solicitado a 38 MHz, READY acotado y relay FIFO10 de V7.
Tres buffers alineados se encolan por referencia; el productor prepara el siguiente
fragmento mientras el actual se transmite por DMA. Se elimina la copia de payload
en loop(). El crédito vuelve sólo tras EOT y detención/reset comprobados de ambos
DMA; el último fragmento confirma el nodo entero antes de acquisition::release().
Los mensajes de control conservan prioridad y un buffer independiente.

Pruebas locales: código real de preparación y devolución de buffers con consumidor
lento, colas llenas, pausas de control, 20 nodos consecutivos por caso, ADC8/10/12
y N3456/N6912/N8192, incluidas colas y fragmentos finales parciales.
Prueba física: referencia 10 s, seis pantallas 5 s, aceptación 60 + 3x120 + 600 s
con reinicios independientes y restauración exacta de V16.
Fuentes archivadas en sources_spi38_pointer_v8.zip.

## V9: CRC de payload solapado y observación del pico acumulado

La aceptación V8 registró cola pico4 en un ensayo60s, con ocupación observada1/2;
el pico es acumulado desde reconfigure(). El reporte no identifica cuándo ocurrió.
No se descarta ese pico ni se modifica el criterio de aceptación.

V9 calcula CRC de los940bytes de payload en el productor. Antes de DMA calcula
CRC de los48bytes de cabecera y combina ambos con una transformación GF(2)
precalculada, equivalente a CRC32 sobre988bytes. El protocolo no cambia.
Prueba contra zlib: todos7904bits de una trama, patrones extremos, aleatorios
y100cabeceras distintas con payload idéntico. Propiedad de buffers sin cambios.

qualify_margin.py observa cada trama mediante el decoder original, registra
transiciones de epoch/pico y estado justo al iniciar medición. Dos pruebas
comprueban equivalencia con lecturas fragmentadas, fallos CRC e índices.
La aceptación conserva el pico acumulado, incluso si ocurrió al arrancar.
Campaña enfocada: baseline10s y ADC8/114/N3456 a60+3x120+600s, reinicios
independientes, restauración exacta. No se vuelve a barrer bits ni tamaños.
