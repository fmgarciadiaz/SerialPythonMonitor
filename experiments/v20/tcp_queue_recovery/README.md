# V20: recuperación de FIFO TCP llena (privado)

Candidato separado; no está importado por el relay de producción ni cargado en el Q.

La implementación vigente devuelve ENOBUFS inmediatamente al encontrar 64 cuadros. Esta variante intenta drenar los cuadros antiguos antes de aceptar el nuevo, manteniendo FIFO, capacidad 64 y un presupuesto compartido máximo de dos llamadas send. Si no libera un slot, rechaza el nuevo; un envío parcial conserva offset y contenido anteriores. EAGAIN/EINTR terminan el intento sin espera activa. Los errores fatales se propagan.

Validación local 1/11/2026: compilación C11 con Wall/Wextra/Werror y AddressSanitizer/UndefinedBehaviorSanitizer; ejecutable PASS. Casos: recuperación llena, bloqueo, envío parcial sin espacio y recuperación posterior, EPIPE y camino normal. No mide rendimiento físico ni demuestra corregir underruns. Una prueba falló inicialmente por esperar dos llamadas ante EAGAIN; se corrigió la expectativa a una, consistente con terminar sin reintentar bloqueo.

Reproducir desde raíz:

```sh
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined experiments/v20/tcp_queue_recovery/test_queue.c -o /tmp/v20_queue_recovery_test
/tmp/v20_queue_recovery_test
```

Antes de promover: comparar contra relay vigente bajo contrapresión real, verificar todos los bytes/orden, ACK y RF, límite de llamadas y errores. Después, campaña Q con respaldo/restauración y RADIO/A0. No cambia tasas ni resuelve la holgura ADC/SPI por sí misma.

## Comparación y TCP local · 1/11/2026

`test_backpressure.c` ejecutó 100.000 operaciones por variante con bloqueo periódico, EAGAIN/EINTR y tamaños parciales pseudoaleatorios. En cada paso compara la cola y sus offsets contra un flujo de referencia byte por byte y exige como máximo dos llamadas. Candidato: 15.939 aceptados, 84.061 rechazados, 15.869 recuperaciones desde lleno. Original: 64 aceptados y 99.936 rechazados, sin recuperación: una vez llena ya no llama send. Son condiciones artificialmente saturadas; no representan throughput de adquisición.

`test_tcp.c` usa TCP IPv4 loopback, buffer de envío pequeño, lector intermitente y descriptores explícitamente no bloqueantes. Resultado observado: 3.650.560 bytes íntegros, 3.680 cuadros aceptados, 6.320 rechazos y 13 recuperaciones desde lleno. Sin fallos ASan/UBSan. Los contadores TCP dependen del sistema/planificador. Dos primeras ejecuciones del harness se detuvieron por espera excesiva (una por alarma30s); se corrigió el harness configurando O_NONBLOCK en ambos extremos. Esto no se atribuye a un defecto del relay Linux ni a una corrección de producción.

```sh
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined experiments/v20/tcp_queue_recovery/test_backpressure.c -o /tmp/v20_queue_random_candidate
/tmp/v20_queue_random_candidate
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined '-DQUEUE_HEADER="../../../arduino/v20/relay/frame_send_queue.h"' experiments/v20/tcp_queue_recovery/test_backpressure.c -o /tmp/v20_queue_random_baseline
/tmp/v20_queue_random_baseline
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined experiments/v20/tcp_queue_recovery/test_tcp.c -o /tmp/v20_queue_tcp
/tmp/v20_queue_tcp
```

Q no operado; firmware/relay de producto sin cambios. Próximo paso: candidato privado de relay ARM64, identidad y restauración verificadas, pruebas RADIO/A0 y tasas; no habilitarlo aún por este resultado local.

## Herramienta de campaña privada

`tools/probe_v20_sram3.py --tcp-queue-recovery` compila la variante en un directorio remoto temporal: sustituye sólo el header enviado al compilador, archiva sus bytes y registra todos los hashes. Es incompatible con el experimento READY sin yield. No modifica `arduino/v20/relay/`. El wrapper existente guarda la pareja activa y restaura al terminar.

El binding GUI acepta este tipo de prueba sólo con evidencia física restaurada, contrato BSP/fuentes exactos y coincidencia byte a byte del header privado archivado con el candidato local. No habilita la preparación pública ni sustituye recibos aceptados. La regresión V20 completa pasó54tests en Python3.13habitual con permisos locales de procesos/memoria compartida; dentro del sandbox tres casos fallaban por permisos de shm/nice, no por aserciones de producto.

## Atención host de ADC8/86: NO incorporada

`service_profile86.patch` conserva el cambio privado original→candidato para atender `service_wav()` entre cuadros de ADC8/86/CH1/3488. No está aplicado ni habilitado por defecto: el host conserva el guard original de 88 ticks. El ensayo `frame86_service_radio60_retry_20261101` falló con RADIO state=4/reason=2 y FlowLimitExceeded; no constituye aceptación ni prueba una causa. Ver [seguimiento y restauración](../../../docs/V20_TCP_AUDIO_SEGUIMIENTO_20261101.md).
