# Captura temporal y validación de nodos

El timer TIM2 dispara secuencias ADC1 de dos conversiones: A2/CH1 y A3/CH2.
TIM5, a 1 MHz, captura por CH1/TRC el mismo disparo TIM2. GPDMA1 canal 1
transfiere ADC_DR a un anillo de dos nodos; canal 0 transfiere TIM5_CCR1 a
otro anillo. Cada nodo representa 2048 pares y 2048 timestamps.

La transferencia temporal no ejecuta código por muestra, pero genera tráfico
DMA y escrituras de RAM. El productor sí recorre después todos los timestamps.
Se conserva esta referencia real: reconstruir `t0+i*period` en el receptor
no permite, por sí solo, detectar una captura omitida.

## Validación optimizada

[node_validation.h](../arduino/v16/oscilloscope/sketch/node_validation.h)
valida el bloque contra una secuencia esperada de ticks enteros. Acumula las
diferencias y los bits ADC fuera de rango, y decide la validez una vez al final.
Dos instancias de la plantilla separan el caso con copia y el caso sin plaza
libre: no se pregunta por la propiedad de la cola en cada muestra.

Se mantienen todas las comprobaciones:

- Cada timestamp, no sólo el primero y el último; continuidad entre nodos.
- Aritmética unsigned que permite el wrap de TIM5 en 2^32 microsegundos.
- Rango de ambos canales según bits activos.
- Sincronización inicial de ambos DMA en nodo 0 y transición real al siguiente.
- Propiedad DMA antes y después de copiar; errores hardware y tiempo límite.
- Una cola llena sigue contando un nodo perdido; un bloque inválido nunca se publica.

No cambia la estructura del protocolo, la tasa ADC, los timers, los DMA ni sus
buffers. Es una simplificación de la validación CPU; **no se cuantifica todavía
una ganancia de CPU ni un aumento de tasa debido a este cambio**.

## Antes de reducir el DMA temporal

Un timestamp tomado desde la tarea o una IRQ tiene latencia de ejecución.
Los flags TC pueden acumularse y no cuentan cuántas vueltas dio un anillo.
Tampoco un contador de triggers demuestra por sí solo que el ADC convirtió cada
trigger: hay que correlacionarlo con la progresión ADC/DMA y el comienzo real.
Una variante de captura temporal reducida requiere una evidencia independiente
del tiempo y del número de conversiones, más un ensayo de errores inducidos.
No se habilita una reconstrucción que oculte huecos.

Base técnica: [manual STM32U575/585 RM0456 de ST](https://www.st.com/resource/en/reference_manual/rm0456-stm32u575585-armbased-32bit-mcus-stmicroelectronics.pdf),
capítulos ADC, TIM2–TIM5 y GPDMA. La elección y aceptación de un nuevo mecanismo
quedan pendientes; el timer y el DMA temporal actuales permanecen activos.

## Pruebas

El ensayo C++ cubre los cinco tamaños ADC, seis períodos, wrap del reloj,
continuidad entre bloques, corrupción en cada una de las 2048 posiciones,
rango de ambos canales y el caso de validación sin copiar.
Se integra en `tests/v16/test_compact_protocol.py`. El sketch completo compila
con Arduino Zephyr 1.0.0: 104 844 bytes de programa y 159 756 bytes de RAM.
La compilación y las pruebas de host no certifican rendimiento físico.

## Ensayo físico del validador optimizado

Instalado V16 con el nuevo validador, conservando ambos DMA y todos los
timestamps. ADC14/200 kHz: 60 s y 11 992 848 pares; ADC14/250 kHz: 60 s
y 14 991 360 pares. Ningún dropped/fatal ni error del decoder estricto.
Seno concurrente de 1 kHz durante 10 s con ADC200 pasó. WAV de 5 s a 20 y
40 kHz con ADC200 terminó con las 100 000 y 200 000 muestras completas.
No se repitió la combinación WAV/ADC250 que falló en el ensayo anterior.

Estado final confirmado: V16 con validación optimizada activa, ADC14/40 kHz,
salida apagada. No se aumentaron tasas en este incremento ni se cuantificó
ahorro CPU. [Evidencia](../diagnosticos/resultados_v16/20261009_163557_tasas_altas.json).
Respaldo anterior: `respaldos/unoq/osciloscopio_20261009_163347_787744.zip`.
Suite local: 154 pruebas pasan. Compilación App Lab en el Q: 108 264 bytes de
programa y 160 520 bytes de RAM (61 %).
