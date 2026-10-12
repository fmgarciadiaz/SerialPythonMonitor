# CH1 ADC8 a 1,203 MHz: ensayo de nodos de 3584 muestras

Perfil aislado, no integrado en el monitor. Periodo de 133 ticks a 160 MHz, ADC8 nativo, SPI de 32 MHz y tramas de 992 bytes. Cada nodo sale en cuatro tramas: 904 + 904 + 904 + 872 muestras. Conserva CRC, rango ADC, continuidad por índice y timestamp, época, propiedad DMA y rechazo de nodos perdidos.

Primer ensayo: ampliar el nodo mejoró la duración, pero falló en seq=932 con dropped=1, fatal=0 y CRC correcto (first_results.json y first_relay_trial.log). SPI promedió 387,541 µs y READY 167,097 µs. La media de ciclo incluye el asentamiento inicial y no certifica margen sostenido.

Segundo ensayo: evitar tramas vacías mientras la adquisición está sana y no hay muestras ni respuestas de control listas. Se conserva la trama inicial de enlace y las respuestas de control pendientes. Tres tests locales pasaron y compiló en el Q.

Validación física digital: 10 segundos con 12031488 muestras y 120 segundos con 144277504 muestras; ambos dropped=0, fatal=0, con controles de CRC y continuidad temporal activos. Tasa observada de la prueba larga: 1202308,8 muestras/s, dentro de la tolerancia del ensayo respecto de 1203007,5. Restauración exacta a ADC16/71428, generador apagado; 712704 pares verificados.

No se ha medido aún ocupación de cola ni distribución de margen por nodo. Tampoco se han validado señal analógica, FFT, trigger, SINGLE, exportación ni transiciones de perfil en la interfaz con este modo. No equivale a aceptación completa para integración.
