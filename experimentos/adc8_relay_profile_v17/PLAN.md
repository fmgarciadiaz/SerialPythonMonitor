# Perfil detallado de syscalls del relay

Alcance autorizado:medir recv/accept/send por separado,con SPI y READY.
Un único dueño Q;snapshot,backup,firma firmware/relay,restauración exacta y
comprobación10s al terminar. Sin modificar producción ni políticas del relay.

MCU copiado de WORD corregido con PING de referencia;sin perfilador MCU ni
optimización PING. Relay agrega sólo contadores/timestamps de diagnóstico.
Preserva errno tras medir cada syscall para no alterar decisiones de error.
Se conservan CRC,validación completa,READY y backpressure/desconexión.

Cuatro casos30s,ticks114/112/112/114,N3456,ADC8CH1,arranques independientes.
Cortar ante fallo de integridad. No60+3×120s:esto no califica tasas ni holgura.

Se miden preparePING,READY,ioctlSPI,validación,hostIO,total,recv,accept,send.
Cada syscall cuenta éxito,EAGAIN,EINTR,otros errores,bytes y envíos cortos.
Logs por ventanas10s;descartar inicial y usar dos últimas completas por caso.
Medias por llamada,tiempo transcurrido inclusive (kernel/planificación),
no CPU exclusivo. hostIO contiene las tres syscalls y la instrumentación;
no sumarlo con sus partes ni con loop_total. MCU y relay se solapan.
No estimar reloj SPI efectivo a partir de38MHz solicitado o del ioctl.
