# Reloj SPI configurado y ventana NSS

Sólo diagnóstico,sin calificar ni cambiar tasas/reloj/producción.
GENI4a94000.spi;lectura fija de configuración con /dev/mem O_RDONLY,
mmap PROT_READ,contenedor aislado sin red,device r y SYS_RAWIO único.
Fuente leída en debugfs. No se leen FIFOs ni registros clear-on-read.
Evidencia inicial:fuente100MHz,serialclock0x31(div3,enable1),wrapper3.0,
DMA1,GSI0. Configuración derivada33,333MHz,no medición eléctrica deSCK.
Kernel7.0 no tiene ftrace,kprobes ni dynamicdebug;no instalar otro kernel.

Para acotar tiempo activo:firmware aislado agrega callbackGPIO EXTI aPG12
NSS en ambos flancos,sin gpio_pin_configure;verifica MODER/AF sin cambios.
No interfiere con GPIO13READY. Temporiza mediante k_cycle_get_32 existente.
Campos experimentales40/44 llevan duración en ticks y secuencia de trama
capturada. Relay valida todo primero y alinea con ioctl de esa secuencia
previa,no con el ioctl de la trama que contiene los datos de diagnóstico.
Contabiliza mismatch y diferencias negativas;no descartar valores negativos.

Dos casos30s,ticks114/112,N3456,con arranques independientes. Logs por
ventanas10s,descartar primera y seleccionar dos últimas completas. Si
NSS no se captura o match<95%,abortar diagnóstico y restaurar. Tolerar a
lo sumo1% de pares negativos para poder interpretar el residual.
ISR introduce latencia/perturbación;NSS activo no es tiempo puro de bits.
Residual ioctl-NSS es estimación del intervalo fuera deNSS,con relojes
independientes,IRQy planificación;no etiquetarlo CPU puro del kernel.

Snapshot/backup previo,un dueñoQ.Finally restaura V17,relay y campos exactos,
hashfirmware y10s de continuidad,además de releer configuración SPI.
Sin mayor frecuencia ni aceptación analógica,GUI,dual,UART,RADIO/DSP.
