# Perfil de etapas ADC8 — 15/10/2026

Diagnóstico aislado autorizado al continuar la medición de costes. Un dueño Q.
Se clona el experimento WORD corregido; no cambia producción ni califican tasas.

Control con instrumentación compilada OFF:30s ADC8/ticks114/N3456.
Luego instrumentación ON:30s ticks114/112/114,arranques independientes.
Ambas campañas hacen snapshot vivo,backup y restauración exacta verificada10s.
Si hay fallo de integridad,cortar la campaña;no tomar el fallo como límite ADC.

MCU:cache,validación+copia,packing,construcción (incluye packing),espera buffer,
CRC TX,preparación DMA/SPI,READY hasta fin,limpieza DMA y comprobación RX.
Una sonda vacía mide resolución/coste mínimo de las lecturas del reloj.
Contadores count/sum/max de32bits; snapshots coherentes,se transmiten por
slots temporales40/44 de DATA experimental con etiquetaD17A,antes de sellar.
Decoder acepta primero integridad completa y luego reconstruye los tripletes;
sumas se desenvuelven módulo2^32 entre snapshots,ventanas de decenas de ms.
No toca CRC32,padding,índices,timestamps,errores,propiedad DMA ni READY.

Relay:prepararPING,esperaREADY,ioctlSPI,validación completa,hostIO y bucle.
Logs acumulados por ventanas10s,sin imprimir por trama. Se descarta ventana
inicial y se usan hasta las últimas dos completas. Máximo MCU es desde boot;
máximo relay corresponde a esas ventanas. Intervalos incluyen preempción,
espera y planificación; se solapan entre threads/MCU/relay y no son sumables
como CPU exclusivo. Sólo orientar una optimización posterior.

Control e instrumentación no están aleatorizados. Una diferencia de throughput
no prueba causalidad; señalar perturbación y conservar todos los informes.
