# Paso cuatro: generador de ondas

Decisión física del 2 de octubre de 2026: **DAC0 en A0, V_IN en A2 y V_OUT en A3**.
El firmware actual adquiere ADC1_IN11 (PA6) y ADC1_IN12 (PA7). El DAC1 canal 1
usa PA4 y salida de 12 bits; se invoca `analogWrite(DAC0, valor)` del core Zephyr
1.0.0 para seleccionar el DAC real. `analogWrite(A0, valor)` corresponde a la
sobrecarga de pines digitales/PWM y no debe usarse para este DAC.

El generador usa **TIM6 TRGO + GPDMA1 canal 4** para transferir una tabla
circular al DAC sin una interrupción por muestra. El ADC conserva TIM2/TIM5 y
DMA 0/1; SPI conserva DMA 2/3. La prioridad del DMA del DAC es menor que la de
adquisición. Se comprueba que TIM6 y DMA4 no estén activos antes de reservarlos.
El `k_timer` de 2 kHz supervisa errores y duración de pulsos/barridos; no escribe
cada muestra. Arranca con cuadrada de 2,5 Hz, códigos 0/4095.

La cuadrada utiliza dos valores. Seno, triángulo y rampa utilizan 256, 128, 64 o
32 puntos por período, escogidos por la máxima frecuencia del recorrido, con
un máximo de 1 MS/s de transferencias. A 20 kHz hay 32 puntos y 640 kS/s; el
DAC conserva 12 bits. El divisor de TIM6 aproxima la frecuencia solicitada:
las pruebas de cálculo limitan el error a menos de 0,3 % en todo el rango.
El reloj real, los tiempos de establecimiento y la carga del circuito también
influyen; no se promete precisión calibrada ni respuesta plana en audio.
Configuración de DMA basada en [ST AN5593, sección DAC](https://www.st.com/resource/en/application_note/an5593-how-to-use-the-gpdma-for-stm32u5-series-microcontrollers-stmicroelectronics.pdf).

Cableado confirmado por el usuario: A0 excita el circuito, A2 mide el primer
punto y A3 el segundo, con masa común. A1 queda disponible. Los nombres
V_IN=A2 y V_OUT=A3 se mantienen; en la captura física A3 presenta la cuadrada
y A2 la carga/descarga del circuito. Revisar los puntos del circuito si se
pretende que los nombres describan su entrada y salida.

Referencia: [pinout oficial UNO Q](https://docs.arduino.cc/resources/pinouts/ABX00162-full-pinout.pdf).

## Uso desde V10

El bloque **GENERADOR · A0** ocupa una columna permanente a la izquierda
de conexión, visualización y osciloscopio. Cambios automáticos con
confirmación del Q; conectar consulta el estado actual, sin imponer valores del PC.

- **Forma:** selector con dibujos: cuadrada (50% duty), seno, triángulo, rampa ascendente o pulso positivo.
- **Frecuencia:** 0,1 Hz–20 kHz, con dial logarítmico y entrada numérica. El
  número se confirma con Enter o al salir; no exige completar tres decimales.
  Para observar 20 kHz sin alias, seleccionar ADC a 50 o 62,5 kHz.
- **Amplitud:** Vpp; **offset:** centro de la señal. Ambos extremos deben quedar
  entre 0 y 3,3 V nominales. DAC de 12 bits, independiente del ADC de 16 bits.
- **Modo:** continuo, sweep lineal o chirp exponencial. Sweep/chirp recorren la
  frecuencia inicial a la final una vez durante la duración elegida y terminan
  en el nivel inferior. El estado muestra `Finalizado`; el botón permite repetir.
- **Pulso:** sostiene el nivel superior por la duración seleccionada y vuelve al
  inferior. El ancho se ingresa en **milisegundos**, de 1 a 600.000 ms.
  La frecuencia, el dial y el modo se ocultan en pulso.
- **Salida encendida:** habilita el generador; apagar lleva A0 a código cero.

Cada cambio válido reinicia la fase y, si corresponde, el recorrido/pulso. Una
petición repetida con el mismo ID no reinicia el motor. La consulta periódica
refleja finalización y permite recuperar el estado al reconectar. El generador
continúa funcionando si se desconecta el control del PC.

Los niveles se expresan usando 3,3 V nominales, sin calibración. Los ciclos
continuos los marca TIM6. Sweep/chirp conservan la tabla y cambian el divisor
en 128 tramos de frecuencia; el tiempo de cambio y el final del pulso dependen
de la supervisión de 0,5 ms del kernel. No son chirps de resolución arbitraria.
La preparación y los cambios de tabla ocurren con el DMA detenido; se limpian
caché y registros antes de volver a habilitarlo. Un error DMA/underrun del DAC
se informa como HARDWARE y detiene esa salida, sin ocultar errores del ADC.

## Control y convivencia con adquisición

SCP1 v2 conserva paquetes de 512 bytes y CRC32. Agrega `SET_GENERATOR=8`,
`GENERATOR_STATUS=9` y `GET_GENERATOR=10`, con IDs del PC, estado APPLIED/REJECTED,
configuración solicitada/activa y bandera de ejecución. La salida de muestras
puede ser SPI o UART; el control siempre se mantiene en el Q.

El cambio de generador no reinicia el ADC, no cambia su época, no cierra el CSV y
no cambia los índices. El relay C y el decoder Python validan los nuevos estados
sin relajar la comprobación de muestras. La interfaz consulta al Q cada segundo
para mostrar el final de sweep/chirp/pulso.

## Validación previa (motor de software a 2 kS/s)

Firmware compilado y cargado en el Q. Pasaron 122 pruebas locales y los ensayos
físicos de las formas de onda, amplitud/offset, pulso, sweep y chirp. Se verificó
convivencia con ADC de 14/16 bits a 50 kHz y 24 perfiles repetidos sin intercambio
de canales. El panel mantuvo un único CSV de 381.246 filas sin discontinuidades,
incluyendo cambios del generador, STOP y SINGLE.

Se corrigió también el arranque del anillo DMA al cambiar perfil: se limpian
los registros que conservaban un bloque parcial, antes de cargar la cabeza.
Los pines siguen A2/V_IN y A3/V_OUT. No se retiró ningún validador de integridad.

[Informes, capturas, límites y diagnóstico](../diagnosticos/GENERADOR_V10.md).
[Panel con señal real](../assets/monitor_v10_generador.png).

SPI está validado en estos ensayos. El control del generador respondió en UART,
pero el R4 no entregó muestras; la captura UART con este cableado queda pendiente.
El siguiente paso del plan es FFT/transferencia. La ampliación actual a audio
usa el motor DMA; su evidencia se documenta separadamente. El fallo intermitente
de adquisición en 16 bits descrito en [este diagnóstico](../diagnosticos/CIERRE_16BITS_20261002.md)
no se considera resuelto por el cambio de motor.

## Motor DMA y audio: validación del 2 de octubre de 2026

El firmware actual compila con 100.992 bytes de programa, 156.264 bytes de
variables globales y 105.880 bytes libres. Pasaron 126 pruebas locales. La
[prueba física de audio](../diagnosticos/resultados_usb/20261002_230826_357101_generador_audio.json)
completó 18 casos con 1.230.061 pares en sus intervalos medidos: cuadrada, seno,
triángulo y rampa a 1/10/20 kHz con ADC 14 bits / 62,5 kHz; seno a esas frecuencias
con ADC 16 bits / 50 kHz; sweep y chirp de 1 a 20 kHz en un segundo; pulso de
5 ms observado en 5,16 ms. Las frecuencias dominantes medidas en A3 quedaron
dentro de la tolerancia del ensayo. No se midió THD ni respuesta calibrada.

También completó un minuto continuo con seno DAC de 20 kHz y ADC de 16 bits a
50 kHz, conservando todos los validadores. Este minuto no demuestra estabilidad
prolongada ni explica el fallo intermitente previo del ADC.

La primera versión DMA usaba transferencias de medio word y produjo DTEF;
al continuar sin la supervisión de software, el DAC marcó underrun. Una prueba
SWD aislada verificó descriptor y datos, y el acceso de 32 bits mantuvo el DMA
habilitado sin DTEF. La versión actual usa palabras alineadas de 32 bits para
transportar códigos DAC de 12 bits. La parada del DAC limita la espera DMA a
100 µs por fase; las esperas del ADC/SPI conservan sus valores anteriores.
[Detalles de diagnóstico e inventario](../diagnosticos/GENERADOR_AUDIO_V10.md).

## Validación final con timestamps capturados

Se reprodujo una causa de parada ADC: leer TIM5 CNT por DMA generaba pares de
intervalos 33/31 µs en un perfil de 32 µs. Ahora TIM5 CH1 captura TIM2 TRGO
mediante TRC/ITR1; DMA0 lee CCR1 después del latch. El productor mantiene la
validación exacta y también detecta overcapture CC1OF.

- [40 perfiles de 14/16 bits](../diagnosticos/resultados_usb/20261002_231937_033811_generator_channels.json): 1.142.746 pares en los intervalos comparados, sin discontinuidades ni intercambio de canales.
- [Audio final](../diagnosticos/resultados_usb/20261002_232028_292878_generador_audio.json): 18 casos, 1.226.165 pares, cuatro formas hasta 20 kHz, sweep/chirp y pulso de 5 ms medido en 5,26 ms; minuto adicional con ADC 16 bits / 50 kHz y DAC seno 20 kHz, sin fallos.
- [Interfaz final](../diagnosticos/resultados_usb/20261002_232217_882337_generador_qt_v10.json): CSV de 381.545 filas, cero discontinuidades, controles, STOP y SINGLE correctos. [Captura del aparato](../assets/monitor_v10_generador.png).
- Respaldo final: `respaldos/unoq/osciloscopio_20261002_232326_092996.zip`.

El primer cierre histórico solo tenía el contador fatal, sin RAM, por lo que la
atribución retrospectiva sigue limitada. La causa reproducida sí se corrigió y
se validó en los ensayos descritos; no se promete estabilidad ilimitada.
