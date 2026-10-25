# ADC8 V18: plan de transporte SPI16 y agrupación

El objetivo sigue siendo ADC8 cerca de 1,8 MS/s con integridad, holgura y carga combinada. V17 permanece congelada. Los cambios se prueban en apps privadas del Q, con respaldo, dueño único y restauración verificada. Las tasas públicas no cambian por estas pruebas.

## Evidencia y revisión

WordPing pasó transporte aislado 60 s + 3×120 s a 1,818181 MS/s, pero con colas pico 5/7/7 de 8. Las pruebas combinadas muestran tanto pérdida real de un nodo ADC con CRC correcto como UNDERRUN de audio sin rechazo ADC. La traza no confirmó una ráfaga larga de respuestas WAV como causa inmediata. En ventanas de 64 tramas, ioctl tomó ~278 µs y READY ~70–121 µs. AlignedPing ahorró sólo unos 3 µs y falló: no se promueve.

Astra revisó el diseño sin hardware ni modificaciones. SPI3 tiene un contador limitado y admite palabras físicas de 8/16 bits: no corresponde intentar DSIZE8/TSIZE1984. Con 16 bits, 992 palabras representan 1984 bytes manteniendo la señal EOT. Fuentes: [ST, tabla 23](https://www.st.com/resource/en/datasheet/stm32u585zi.pdf), [contrato de buffers SPI de Linux](https://docs.kernel.org/driver-api/spi.html). Linux define los buffers de palabras en orden nativo de CPU; dos extremos de 16 bits deben preservar los bytes SCP1 lógicos, aunque cambie el orden físico dentro de cada pareja.

Lectura del Q antes del experimento: controlador `/sys/bus/platform/drivers/geni_spi`, kernel `7.0.0-g122c2c22d838`, modalias `spi:unoq-mcu`. Esto identifica el controlador; no acredita todavía compatibilidad física con 16 bits.

## Paso 1: compatibilidad SPI16, sin agrupación

Sol prepara una app y un relay privados que usan SPI16 desde el arranque. Se mantiene una trama SCP1 de 992 bytes por intercambio. No se modifica el protocolo lógico, el CRC32, las secuencias, la capacidad ADC/DAC ni el reloj.

- MCU: DSIZE=15, CRCSIZE=15, TSIZE=496; BNDT permanece 992 bytes. DMA de al menos dos bytes también en perfiles iniciales y comandos; cuatro bytes en el camino rápido. FTHLV debe corresponder a la anchura real, evitando dejar el umbral de cuatro palabras de 8 bits después de cambiar a 16.
- Relay: bits_per_word=16 tanto en configuración como en cada transferencia. Readback debe confirmar 16; el readback por sí solo no acredita transmisión correcta.
- Todos los perfiles de esta app privada usan SPI16. Así el primer paso no introduce una transición DSIZE mientras se cambia adquisición.
- Tests previos: geometría de registros, ambos caminos DMA, vectores asimétricos y orden de bytes, rechazo del emparejamiento 8/16, CRC y clases de control, contrato packer C → relay estricto → decoder Python, compilación y mapa de memoria.
- Prueba física: arranque y perfil inicial, configuración de entrada/salida ADC8/88, integridad de datos y tráfico de control. Primero sondeo; ninguna promoción por el readback o por un test sintético.

Este paso prueba compatibilidad, no promete una aceleración del doble. La cantidad de bits de la trama no disminuye.

## Paso 2: dos SCP1 por intercambio físico

Sólo se implementa después de aprobar el primer paso. Mantener BLOCK_BYTES=992 como tamaño lógico. Dos tramas suman 1984 bytes físicos, TSIZE=992 palabras de 16 bits. Cada trama conserva su CRC y secuencia.

El prototipo privado usa siempre dos tramas por intercambio desde el arranque, en todos sus perfiles. No hay conmutación de geometría durante una configuración. APPLIED conserva su posición en el flujo lógico. Si una incorporación posterior necesitara geometría adaptable, deberá mantener estado propio y cambiar sólo después de completar físicamente el intercambio que contiene APPLIED; no puede derivarse directamente del perfil ADC.

El staging TX/RX requiere 3968 bytes, alineados y separados del área prestada de timestamps. Revisar stack real, mapa y mantenimiento de cache. Sólo los slots del camino word pueden devolver spi40_free después de copiarse al staging, porque spi40_node_sent mantiene una barrera independiente. En los caminos normal y pipelined no se adelanta frame_sent: también autoriza liberar el nodo. El nodo ADC sólo se libera después del DMA físico de su último fragmento. No publicar node_sent si el intercambio fue parcial o falló.

No esperar indefinidamente una segunda muestra: los controles pueden dejar un último fragmento impar y el productor espera su confirmación física. Completar esa posición con una trama idle válida. APPLIED siempre debe preceder datos de su nueva época, también cuando ambos estén dentro del mismo intercambio.

Permitir como máximo un comando PC por intercambio, siempre en la segunda posición; la primera lleva un PING interno. Esto conserva el eco de un PING del PC: un PING interno posterior sobrescribiría last_ping y perdería su confirmación. Procesar RX en orden después del DMA completo. Separar resultado físico 1984 del last_result lógico 992 que espera el validador existente. El relay valida ambas tramas antes de enviar sus bytes al socket; una sola transición READY autoriza un intercambio físico, nunca dos SPI independientes sin handshake.

## Criterios antes de hardware del paso 2

Modelar y comprobar APPLIED en ambas posiciones; ACK retrasado por WAV/generador; fragmento final impar; configuración duplicada, rechazada o pendiente; error en cada mitad; DMA parcial; wrap de secuencia; desconexión/reconexión; retorno al perfil normal. Demostrar ausencia de reutilización prematura, deadlock y conmutación adelantada. El mismo contrato estricto C/Python debe seguir rechazando corrupciones.

La aceptación física se separa en integridad aislada, margen/cola, carga GUI/RADIO/A0, WAV/Synth y aceptación analógica. Se restaura y verifica la pareja de producción tras cada campaña, incluso si falla el arranque.

## Resultados del primer paso y corrección de audio independiente

SPI16 de una trama pasó el sondeo físico de 15 s (`resultados/20261023_162948`): formato y CRC compatibles, cola pico 3/8, margen 15,41%, producción restaurada. La prueba combinada de 120 s (`gui_private_20261023_163519`) perdió un nodo ADC con CRC correcto; producción restaurada. La compatibilidad está demostrada en esos ensayos, pero el formato por sí solo no resuelve el margen bajo carga.

Se corrigió por separado el lock de RadioDacSource: el detector de realimentación calcula fuera del lock del buffer de audio, con segunda comprobación de cierre/error. La política de ráfaga permanece 8 en base y 16 en la subclase especializada. Tres pruebas de concurrencia y 24 regresiones pasaron. A 1,6 MS/s, RADIO/A0 pasó 120,3 s junto con Scan, WAV y Synth20 (`gui_radio_lockfix_1600_20261023.json`): detector máximo 53,28 ms y espera máxima del lock de audio 0,156 ms. Esto no califica aún el modo combinado a 1,818 MS/s.
