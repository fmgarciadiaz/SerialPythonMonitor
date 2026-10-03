# Plan de trabajo para Osciloscopio Arduino*

Este es el plan de la app completa. Pero lo tenemos que ir haciendo paso a paso. Te paso todo asi cada paso no hacemos cosas que sean incompatbles con los proximos.

1) Una vez testeado el link viable MCU MPU de UNO Q via SPI con DMA y velocidad suficiente, integraremos a nuestros codigos pero de la siguiente forma, paso a paso:
2) Paso uno, una version con todo lo mismo que la anterior, pero con conexion de Python al UNO Q sin pasar por el R4
3) Paso dos: una version con todo lo mismo que la anterior, pero pudiendo elegir port Generador/Osciloscopio (Va a ser siempre el UNO Q) y transmisor (Puede ser el R4 via UART como antes o el UNO Q mismo via SPI directo al MPU). Esa eleccion implica que el IDE de Python se comunique con la App del UNO Q y le indique el modo de operacion, UART (al R4) o SPI (al MPU->USB). Es decir el UNO Q hay que conectarlo igual, aunque este con el R4 como puente, para poder controlar todo el sistema (ahora se conecta solo el R4)
4) Paso tres: poder configurar la adquisición, con opciones que dependan de los máximos de cada transmisor: bits, frecuencia de sampleo (usar sólo válidas). Para eso Python debe controlar la App del Q, y ademas adaptar su propia lectura a los datos que van a llegar; sobre todo los bits (la frecuencia de sampleo no le cambia nada en principio)
5) Paso cuatro: Agregar panel deplegable generador de ondas. Actualmente solo genera on off, quiero un panel desplegable que permita hacer las operaciones tipicas de un generador: square, triangle, ramp, sine, ajustar frecuencia, hacer un swipe, un chirp, un spike.
6) Paso cinco: modo FFT, para analizar frecuencias. Espectro en cada t o evolucion en el tiempo por heatmap. Tambien trazar la curva de ganancia/transferencia en base al chirp, o swipe o spike.
7) Paso seis: panel para grabar sonido o reproducir sonidos grabados en formato wav.



## Estado al 2 de octubre de 2026

- **Paso uno:** implementado y validado en [V8](monitor/historico/v8/README.md), Q directo por USB.
- **Paso dos:** implementado en [V9](monitor/historico/v9/README.md): selector del Q de control, destino SPI/UART y puerto R4. Cambios en vivo y CSV continuo [validados con las placas](diagnosticos/MONITOR_V9.md).
- **Paso tres:** implementado en [V10](monitor/v10/README.md): panel plegable, ADC de 8/10/12/14 bits y once tasas válidas de 1 a 31,25 kHz para ambos destinos, más 40/50/62,5 kHz exclusivas de SPI ([ensayo](diagnosticos/TASAS_SPI_V10.md)). [Validación física y CSV](diagnosticos/ADQUISICION_V10.md).
- **Paso cuatro:** relevamiento iniciado; [recursos y decisión de salida física](docs/GENERADOR_PASO4.md). Decisión física: DAC0 en A0, entrada V_IN en A2 y entrada V_OUT en A3. La cuadrada de prueba se traslada al DAC; siguen pendientes el motor temporizado y el panel de formas de onda.
- Generador, FFT y audio siguen el orden indicado arriba.
