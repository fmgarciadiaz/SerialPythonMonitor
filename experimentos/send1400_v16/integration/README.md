# Incorporación en V16 de ADC8/CH1 a 1,4035 MHz

La mejora de transporte se activa sólo con bits=8, CH1, 114 ticks y N3456.
Las demás tasas conservan SPI solicitado a 32 MHz, SCHED_OTHER/prioridad0,
READY con poll, configuración DMA completa y entrega de un fragmento seguida
por su confirmación. El perfil alto usa SPI solicitado38MHz, FIFO10, espera
READY acotada50us, configuración DMA reutilizada tras reset y un anillo3.
El relay comprueba la política y prioridad reales al cambiar de perfil.

Los buffers adicionales sólo usan el final libre de los timestamps del perfil
alto. Los nodos DMA ocupan27648bytes; esos buffers empiezan en63552bytes dentro
del almacenamiento SingleMemory de65536bytes. Las pruebas comprueban alineación,
no superposición, orden y que el nodo sólo se libera tras todos los ACK físicos.
Se reutilizan los semáforos existentes; no se añade una cola de kernel.

El core Zephyr carga también código del sketch en RAM. Para mantener espacio
de carga, TX/RX temporales se alojan en la pila principal de32KiB. Permanecen
vivos hasta detener/resetear ambos DMA; ante fallo el hilo no abandona esa pila
antes del reinicio. No se reducen los cuatro slots ADC ni los buffers WAV.
Uso informado del sketch:259140bytes; anterior259292bytes,152bytes más libres.

Los ensayos iniciales descartados están conservados: fallo de copia de caché,
preprocesado Arduino, espacio de arranque y errores del verificador (reloj usado
antes de APPLIED, pausa del lector al consultar Docker, y lector de filas Python
frente al camino numérico de la GUI). Siempre se verificó recuperación, salvo
un fallo inicial de snapshot que se recuperó posteriormente. Esos ensayos no
son aceptación física ni límites del ADC. Las fuentes aceptadas se archivan
junto con cada campaña en sources.zip.

La validación final usa el decoder de producción con numeric=True, datos de
NumericBatch y timestamps escalados, sin consultas externas en el arranque del
perfil alto. CRC, secuencia, epoch, índices/timestamps, DMA, dropped y fatal
continúan comprobándose. No se borra el pico acumulado ni se relaja el criterio
de holgura10%. La aceptación de integridad se separa de la de holgura.

Estado: incorporación física y comprobación GUI completadas. Reporte físico:
`physical_20261013_192502/report.json` (`ok=true`, `restored=true`).
ADC8/CH1 pasó 60 s + tres arranques independientes de 120 s + 600 s,
con CRC/secuencia/epoch/índices/timestamps/DMA y dropped=fatal=0.
Los márgenes medios fueron 9,822%, 9,362%, 7,017%, 9,268% y 9,679%;
la primera repetición alcanzó cola4/4. **Acepta integridad, no holgura**.
La aceptación con holgura del ensayo aislado no se transfiere a producción.
Los retornos ADC10/909090 y las comprobaciones ADC14 dual/363636 y
ADC16/40000 pasaron con scheduler normal/prioridad0.

Reporte GUI: `gui_20261013_195708.json` (`ok=true`, `restored=true`).
Con Qt offscreen y el Q real se recibieron 8.832.672 muestras en 6,31 s
a 1,4035 MHz; CH2 deshabilitado, dt=0,7125 us y WAV bloqueado para ese perfil.
Después se grabaron 233.730 frames PCM16 estéreo ADC14/40000, cabecera válida
y 934.964 bytes. Restauración ADC8/1221374 SPI, generador apagado con todos
sus campos previos; 3.664.224 muestras de recuperación en 3 s.
Esta comprobación no acredita inspección visual, FFT/trigger/SINGLE bajo carga
ni precisión analógica a la tasa alta. Las referencias Bode del firmware anterior
conservan su identidad y requieren nueva medición para el firmware incorporado.
