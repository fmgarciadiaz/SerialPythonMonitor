# ADC8: revisión con Astra y documentación oficial — 15/10/2026

Objetivo: aumentar adquisición continua CH1, manteniendo integridad y
precisión analógica como verificaciones separadas. Usuario confirmó Q libre.
No se confunde tasa de adquisición con FPS, interpolación o tasa de audio.

## Fuentes consultadas

- [ST AN5593, revisión 9, junio de 2026](https://www.st.com/content/st_com/en/technical-documents/an5593-how-to-use-the-gpdma-for-stm32-mcus-stmicroelectronics.html):
  programación GPDMA orientada a rendimiento.
- [AN5593: SPI y otros periféricos](https://www.st.com/content/st_com/en/technical-documents/an5593-how-to-use-the-gpdma-for-stm32-mcus-stmicroelectronics_asset/chunk-004-topic-an5593-gpdma-config-comm-audio-math-periphs.html)
  y [HAL SPI oficial](https://raw.githubusercontent.com/STMicroelectronics/stm32u5xx-hal-driver/main/Src/stm32u5xx_hal_spi.c):
  accesos DMA anchos compatibles con frames SPI estrechos, respetando FIFO
  y tamaño del paquete.
- [ST ES0499, SPI](https://www.st.com/content/st_com/en/technical-documents/es0499-stm32u575xx-and-stm32u585xx-device-errata-stmicroelectronics_asset/chunk-006-topic-function-es-uart-usart.html):
  con CRCEN=0 y TSIZE>0 se debe conservar CRCSIZE=7 para evitar la posible
  corrupción del último dato recibido descrita por ST.
- [Datasheet STM32U585, DS13086 Rev10](https://www.st.com/resource/en/datasheet/stm32u585ai.pdf),
  tablas 104–106: ADC8 hasta 3,44 MS/s bajo condiciones especificadas a
  55 MHz de reloj ADC. Es una especificación del convertidor, no una tasa
  sostenida de nuestra cadena. El código usa 54 MHz y muestreo de cinco ciclos.
- [ST AN2834](https://www.st.com/resource/en/application_note/an2834-how-to-optimize-the-adc-accuracy-in-the-stm32-mcus-stmicroelectronics.pdf):
  el tiempo de adquisición debe permitir asentamiento con la impedancia y
  capacitancia de la entrada. Aumentar tasa no certifica precisión analógica.
- [NI: métodos de adquisición](https://www.ni.com/docs/en-US/bundle/pxie-6381/page/ai-data-acquisition-methods.html):
  adquisición continua con reloj hardware, FIFO y DMA hacia buffers del host.
  Es una referencia de arquitectura; su hardware no establece nuestros límites.
- [Analog Devices: jitter en DAQ de alta velocidad](https://www.analog.com/en/resources/analog-dialogue/articles/the-easy-steps-to-calculate-sampling-clock-jitter-for-isolated-precision-high-speed-daqs.html):
  el reloj de muestreo y su jitter influyen en el rendimiento AC; no basta
  contabilizar muestras sin pérdidas.

## Hallazgos aplicables al código

1. La ruta SPI MCU todavía usa accesos DMA BYTE y vuelve a imponer ese ancho
   en CTR1. Primer candidato: WORD en TX/RX con DSIZE8 intacto, FTHLV4 frames,
   burst1, bloque992 bytes y TSIZE992 frames. Reduce accesos internos, no los
   bits transferidos por el cable. No se promete una aceleración de 4×.
2. Las asignaciones CFG1 actuales dejan CRCSIZE=0; la variante experimental
   conserva CRCSIZE=7 en todas las asignaciones de CFG1, en BYTE y WORD.
   El CRC32 de SCP1 no se elimina ni reemplaza por CRC SPI.
3. Si la medida muestra coste de sellado importante, evaluar CRC hardware con
   equivalencia exacta a zlib/ISO-HDLC. No repetir el CRC anticipado dividido
   que ya había regresado en ensayos anteriores.
4. Si domina copia/packing, estudiar una cola ADC8 compacta después de validar
   el DMA original. Truncar a byte antes de validar perdería detección de bits
   altos prohibidos. Cambiar el formato interno exige otra campaña.
5. Canales, puertos y bursts GPDMA deben elegirse según FIFO real y prioridades;
   no trasladar recomendaciones de otro STM32 sin verificar U585/SPI3.

El máximo ADC8 integrado sigue siendo 160 MHz/114 = 1,4035 MS/s CH1,
nodo3456. No se cambia la whitelist productiva para sondear nuevos ticks:
se usa un motor experimental que acepta esos perfiles explícitamente.
No se propone interleaving ADC1+ADC4 sin nueva arquitectura y calibración.
Oversampling, decimación o muestreo equivalente no se contabilizan como más
muestras reales continuas por segundo.

## Primera comparación

[Plan aislado](../experimentos/adc8_spi_word_v17/PLAN.md): BYTE+CRCSIZE7
frente a WORD+CRCSIZE7 a ticks114/113/112, nodo3456. Tasa objetivo inicial
1,416–1,429 MS/s. Pantallas de 10 s y, sólo si hay finalista nuevo, 60 s
+ tres repeticiones independientes de 120 s. Se registran errores, cola,
envío, copia, polling y slack; restauración exacta del snapshot vivo del Q.

Pruebas locales previas: configuración de ambas variantes compilada en C++,
geometría SPI y contrato de packing/validación pasaron (2 pruebas).
