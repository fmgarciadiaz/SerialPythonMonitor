# Diagnóstico causal a1,6000MS/s

Una corrida120s,100ticks,N3456,CPU2,performance,SPI40,warm112/2s. Productororiginal1ms. Relay con anillo1024previos/128posteriores primerpico4 prioritario sobrepico3, top64ciclos y agregados de etapas. Volcar al terminar fuera de medida, sin repetir selectivamente si no reproduce. CRC/continuidad/READY intactos.

Los agregados cubren todo epoch100 hasta SIGUSR1, incluido tramo antes/después de ventana120. Usar estadofinal del receptor yseq/eventos para localizar pico dentro/fuera de medida. Tiempos transcurridos inclusivos, no CPU exclusivo ni SCK eléctrico. between_loops incluye costo propioinstrumentación; fila posteriortrigger puede contener copia delanillo. No restar relojes MCU/Linux. Diagnóstico no es aceptación.

Restauración exacta governor/firmware/relay/entorno/ADC/generador,reloj ycontinuidad10s. Perfil106protegido. No compilar durante medida.
