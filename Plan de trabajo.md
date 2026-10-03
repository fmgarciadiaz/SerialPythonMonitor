# Plan de trabajo para Osciloscopio Arduino*

Este es el plan de la app completa. Pero lo tenemos que ir haciendo paso a paso. Te paso todo asi cada paso no hacemos cosas que sean incompatbles con los proximos.

1) Una vez testeado el link viable MCU MPU de UNO Q via SPI con DMA y velocidad suficiente, integraremos a nuestros codigos pero de la siguiente forma, paso a paso:
2) Paso uno, una version con todo lo mismo que la anterior, pero con conexion de Python al UNO Q sin pasar por el R4
3) Paso dos: una version con todo lo mismo que la anterior, pero pudiendo elegir port Generador/Osciloscopio (Va a ser siempre el UNO Q) y transmisor (Puede ser el R4 via UART como antes o el UNO Q mismo via SPI directo al MPU). Esa eleccion implica que el IDE de Python se comunique con la App del UNO Q y le indique el modo de operacion, UART (al R4) o SPI (al MPU->USB). Es decir el UNO Q hay que conectarlo igual, aunque este con el R4 como puente, para poder controlar todo el sistema (ahora se conecta solo el R4)
4) Paso tres: poder configurar la adquisición, con opciones que dependan de los máximos de cada transmisor: bits, frecuencia de sampleo (usar sólo válidas). Para eso Python debe controlar la App del Q, y ademas adaptar su propia lectura a los datos que van a llegar; sobre todo los bits (la frecuencia de sampleo no le cambia nada en principio)
5) Paso cuatro: Agregar sección de generador de ondas a la izquierda del aparato. Actualmente solo genera on off, quiero un panel desplegable que permita hacer las operaciones tipicas de un generador: square, triangle, ramp, sine, ajustar frecuencia, hacer un swipe, un chirp, un spike.
6) Paso cinco: modo FFT, para analizar frecuencias. Espectro en cada t o evolucion en el tiempo por heatmap. Tambien trazar la curva de ganancia/transferencia en base al chirp, o swipe o spike.
7) Paso seis: panel para grabar sonido o reproducir sonidos grabados en formato wav.



## Estado al 2 de octubre de 2026

- **Paso uno:** implementado y validado en [V8](monitor/historico/v8/README.md), Q directo por USB.
- **Paso dos:** implementado en [V9](monitor/historico/v9/README.md): selector del Q de control, destino SPI/UART y puerto R4. Cambios en vivo y CSV continuo [validados con las placas](diagnosticos/MONITOR_V9.md).
- **Paso tres:** implementado en [V10](monitor/v10/README.md): panel plegable, ADC de 8/10/12/14 bits y once tasas válidas de 1 a 31,25 kHz para ambos destinos, más 40/50/62,5 kHz exclusivas de SPI ([ensayo](diagnosticos/TASAS_SPI_V10.md)). [Validación física y CSV](diagnosticos/ADQUISICION_V10.md).
- **Paso cuatro:** [salida física implementada y probada](docs/GENERADOR_PASO4.md): DAC0 en A0, entrada V_IN en A2 y entrada V_OUT en A3. Firmware cargado y cuadrada de 2,5 Hz observada en el circuito; captura continua y perfiles SPI de 14/16 bits hasta 50 kHz verificados. Motor DAC con TIM6 + DMA4 y columna permanente a la izquierda: cuadrada, seno, triángulo, rampa, sweep lineal, chirp exponencial y pulso; rango ampliado 0,1 Hz–20 kHz, dial logarítmico, selector con dibujos de onda y valores numéricos. Generador SPI validado con señales reales, CSV continuo, STOP y SINGLE; reinicio DMA corregido; timestamps capturados en TIM5 CCR1 para evitar jitter de lectura CNT, con 40 perfiles repetidos de 14/16 bits sin discontinuidades ni intercambio de canales. Captura UART/R4 pendiente de comprobar el enlace físico.
- **Paso cinco (avance al 3 de octubre):** FFT en vivo y heatmap deslizante implementados en V10, con hasta dos canales apilados y controles de tamaño, ventana, solapamiento, escala, DC e historia. [Uso y pruebas locales](docs/FFT_V10.md). Agregados ejes de frecuencia logarítmicos y Bode automático mediante barrido senoidal por pasos: ganancia y fase V_OUT/V_IN, restauración del generador al terminar. Bode [validado físicamente entre 2 y 100 Hz; recorrido ampliado hasta 1 kHz](diagnosticos/BODE_V10.md) con ADC de 16 bits, CSV sin saltos y restauración exacta del generador. Control de puntos por década, opciones con checks neutros y escalas FFT enlazables con margen e histéresis. Asentamiento y ciclos de medición independientes, con tiempo mínimo estimado del barrido. Calibración relativa de ganancia/fase y recorrido hasta 20 kHz completados con ADC de 16 bits a 50 kHz; detalles en el avance de Bode al final del plan.
- Después de completar transferencia, sigue el paso seis de audio.

### Último avance de Bode

- Marcadores en cada frecuencia medida y contador de puntos válidos de ganancia y fase.
- **Agregar** conserva hasta cinco barridos con colores de la paleta de entradas; **Repetir** borra la comparación e inicia un nuevo barrido.
- Sombra translúcida tenue agregada a las curvas y corrección instrumental por referencia de ganancia/fase implementada.
- Validación física y calibración relativa entre canales completadas entre 20 Hz y 20 kHz, ADC 16 bits / 50 kHz: 31/31 puntos, CSV sin saltos y restauración exacta. Referencia anterior invalidada por cableado incorrecto; reemplazada por el ensayo 20261003_123522_633848, con 581 579 filas CSV sin saltos. La repetibilidad de la nueva referencia aún no fue medida. [Evidencia y límites](diagnosticos/BODE_V10.md). Otros perfiles ADC requieren su propia referencia.
