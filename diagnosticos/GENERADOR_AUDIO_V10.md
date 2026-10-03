# Generador DMA hasta 20 kHz

Actual: columna permanente izquierda en V10, selector de onda con iconos dibujados, dial logarítmico y frecuencia numérica. TIM6 + GPDMA1 canal 4 exclusivos para DAC0/A0; ADC DMA0/1 y SPI DMA2/3 conservados. DAC nativo de 12 bits. La interfaz y el protocolo validan 0,1 Hz–20 kHz.

## Evidencia física

- [Ensayo final de 18 casos y minuto continuo](resultados_usb/20261002_230826_357101_generador_audio.json): PASS. Cuatro formas a 1/10/20 kHz en ADC 14 bits / 62,5 kHz; seno en ADC 16 bits / 50 kHz; sweep/chirp de 1 a 20 kHz, pulso 5 ms medido en 5,16 ms. Más de 1,23 millones de pares durante los casos, y 60 segundos adicionales de continuidad estricta a 16 bits / 50 kHz con DAC 20 kHz. Restaurados cuadrada 2,5 Hz, ADC 14 bits / 31,25 kHz, SPI.
- [Capturas e inventario](../capturas/generador_audio/README.md): 4096 pares originales por caso; se validó el intervalo completo, el CSV preservado es una muestra del intervalo.
- Respaldo del motor anterior de software: `respaldos/unoq/osciloscopio_20261002_224809_586584.zip`. Respaldo del primer prototipo DMA: `respaldos/unoq/osciloscopio_20261002_230326_946932.zip`.
- Compilación final con captura TIM5: programa 100.992 B, globales 156.264 B, libres 105.880 B. Suite local: 126 pruebas.

## Problemas encontrados durante la implementación

1. [Primer ensayo](resultados_usb/20261002_225227_161950_generador_audio.json): ADC continuo pero generador se detuvo. El acceso de 16 bits al registro DAC causó DTEF. [Descriptor y datos leídos por SWD](resultados_usb/20261002_dac_dma_arranque_swd.txt) eran correctos. [Core detenido](resultados_usb/20261002_dac_dma_swd_halt.txt) para conservar banderas: DMA CSR=0x10601 incluye DTEF; DAC SR=0x2800 incluye underrun. Este ensayo aislado invalida cualquier evaluación del ADC, y se reinició luego la aplicación. [Accesos de 32 bits](resultados_usb/20261002_dac_dma_swd_word.txt): CSR=0x10300 sin error, CCR=0x20001 habilitado. Se adoptaron palabras de 32 bits, conservando 12 bits de salida DAC.
2. [Segundo ensayo](resultados_usb/20261002_230633_520996_generador_audio.json): 17 casos correctos; comprobación del pulso incorrecta porque el script borraba las muestras recibidas mientras esperaba el ACK. Se corrigió para recoger el pulso antes de enviar el comando; ensayo final mide 5,16 ms.

Los validadores de DATA, CRC, secuencia, índice y timestamp siguen activos. No se imprime diagnóstico en el flujo binario. La prueba por SWD fue aislada, y luego se verificó adquisición con el firmware recargado.

## Límites

Seno/triángulo/rampa usan 32–256 puntos por período, escogidos por la máxima frecuencia del recorrido; a 20 kHz, 32 puntos / 640 kS/s. Cuadrada usa dos niveles. Barridos de 128 tramos supervisados por un timer de 2 kHz, resolución temporal nominal 0,5 ms. No se certifican THD, jitter ni amplitud calibrada. Para observar 20 kHz sin alias se necesita Fs superior a 40 kHz (perfiles actuales 50 o 62,5 kHz). El minuto probado no resuelve el [fallo ADC intermitente previo](CIERRE_16BITS_20261002.md). Captura UART/R4 sigue pendiente de prueba física.

Repetir: `python diagnosticos/verificar_generador_audio.py`, con el relay activo y la interfaz desconectada. Restaura configuración predeterminada al finalizar.

## Timestamps: corrección posterior al primer ensayo de audio

Al repetir perfiles apareció el cierre ADC previo, en 16 bits / 31,25 kHz. [Ensayo interrumpido](resultados_usb/20261002_231141_412947_generator_channels.json), [registro](resultados_usb/20261002_audio_reconfigure_16bits_fatal.log). Se preservaron [registros](resultados_usb/20261002_audio_adc_fatal_swd.txt), [timestamps RAM](resultados_usb/20261002_audio_fatal_timestamps.bin), [ADC RAM](resultados_usb/20261002_audio_fatal_adc.bin) y [análisis](resultados_usb/20261002_audio_fatal_ram.json). Los intervalos 33/31 µs provienen de leer CNT en un instante de servicio variable; el productor rechaza correctamente esa RAM. DMA0 ahora lee CCR1 latched por TIM5 CH1 / TRC / ITR1 ante TIM2 TRGO y se agrega detección de overcapture CC1OF.

[40 perfiles posteriores](resultados_usb/20261002_231937_033811_generator_channels.json): PASS, 1.142.746 pares en los intervalos comparados, 14/16 bits, 31,25/50 kHz, canales estables. El primer ensayo de audio y CSV anteriores preceden esta corrección; las repeticiones finales se registran abajo. [Diagnóstico completo](CIERRE_16BITS_20261002.md).

## Resultado final con captura TIM5

- [Audio final](resultados_usb/20261002_232028_292878_generador_audio.json): PASS, 18 casos / 1.226.165 pares en sus intervalos, pulso 5 ms observado en 5,26 ms, 60 segundos adicionales ADC 16 bits / 50 kHz + DAC 20 kHz.
- [Interfaz final](resultados_usb/20261002_232217_882337_generador_qt_v10.json): PASS, 381.545 filas CSV, cero gaps, STOP/SINGLE y cambios de forma sin cerrar CSV. [Captura](../assets/monitor_v10_generador.png).
- Respaldo final: `respaldos/unoq/osciloscopio_20261002_232326_092996.zip`.
- Restaurados ADC 14 bits / 31,25 kHz, cuadrada 2,5 Hz, SPI. El fallo de timestamps reproducido se corrigió y pasó los 40 cambios de perfil; no se atribuye con certeza retrospectiva todo cierre histórico que solo tiene fatal=1.
