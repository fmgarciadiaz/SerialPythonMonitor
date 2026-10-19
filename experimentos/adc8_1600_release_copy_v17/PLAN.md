# Liberar memoria del nodo tras la última copia

ADC8/100ticks únicamente: después de construir/enlistar todos los frames del nodo, liberar su slot de muestras antes de esperar frame_sent. El nodo deja de leerse antes de liberar; los3buffersSPI contienen copias propias y conservan propiedad hastaDMA/EOT. Seguir esperando frame_sent antes de tomar siguiente nodo, por lo que consumer_started no se modifica antes de finish_send. send_previous conserva inicio take -> finaltransmisión física. Resto perfiles conserva releaseoriginal. No cambiar cuatro slots, CRC, validación, periodos, payload, prioridadniIRQ.

Dos pilotos30s independientes a100ticks/N3456/CPU2/performance/SPI40,warm112/2s. Ambos íntegros,margen>=10%,pico<4desdearranque,slackpositivo ->60+3x120. Cortar primerfallo,sinreintentosselectivos. Esta mejora cambia ocupación real de memoria: no es aumento de slots ni reseteo de pico. Comparación con anteriores debe explicitar semántica de propiedad conservada con liberación más temprana.

Restauración firmware/relay/entorno/config/generador/governor/reloj ycontinuidad10s. Perfil106intacto.
