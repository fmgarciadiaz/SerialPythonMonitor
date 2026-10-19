# Diagnóstico causal a 1,5094 MS/s

Una corrida de 120 s a ADC8/CH1, 106 ticks, N3456, CPU2, SPI40, preparación112/2s. No repetir selectivamente si no reproduce. MCU idéntico; relay agrega marcas de tiempo y anillos acotados. Conserva CRC, READY fresco, continuidad y políticas de desconexión. No modifica producción ni califica tasas.

Registrar por secuencia preparación PING, READY, ioctl SPI, validación, recepción/control, accept, envío y total, además del intervalo entre iteraciones. Los tiempos son transcurridos inclusivos, no CPU exclusivo. Agregados completos, los 64 ciclos más lentos y contexto de 1024 frames previos/128 posteriores al primer pico4. Si no aparece4, contexto al primer pico3 o cola reciente. Volcado sólo al finalizar vía SIGUSR1, fuera de la medición. No restar reloj MCU y Linux.

Snapshot/backup, dueño Q único, sin compilación durante medidas. Restaurar firmware, relay/entorno, configuración, generador y reloj; verificar continuidad10s. Toda instrumentación agrega costo: diagnóstico no es aceptación.
