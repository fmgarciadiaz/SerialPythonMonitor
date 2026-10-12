# CH1 cerca de 660 kHz — V16 aislado

Aplicación `Scope V16 CH1 660 Experimental`, separada del monitor y firmware V16.
TIM2 dispara ADC1_IN11 / A2 cada **242 ticks de 160 MHz**: **661157,025 muestras/s**.
Se mantienen ADC14, ventana de 36 ciclos ADC (0,72 µs), SPI32, cola de cuatro nodos,
DMA TIM5 con timestamps independientes por muestra y validación original adaptada
a un canal. El contador TIM5 conserva ticks de 6,25 ns y comprobación uint32 de wrap.

El ADC empieza sólo después del primer PING SPI válido, después de la espera
inicial READY/loader. Tipo 16: cuatro muestras en siete bytes; 516 por trama,
cuatro tramas por nodo de 2048 muestras. Período/timestamps en ticks de 160 MHz.
No reduce resolución, aumenta colas, omite CRC ni descarta muestras para sostener
la tasa. UART no está disponible. No incorpora este perfil al menú de V16.

`run.py` guarda el perfil real y comprueba que no haya otro monitor ni salida
activa; admite WAV terminado sin errores. Compila y respalda V16, ejecuta la
aplicación/relay independientes durante 10 y 120 s y, ante éxito o fallo, restaura
MCU/relay y perfil previos y comprueba otros 10 s. `results.json` registra resultados
 y restauración; `relay_trial.log` conserva los mensajes originales del relay.

```sh
python -m unittest experimentos.ch1_660_v16.test_contract
python experimentos/ch1_660_v16/run.py
```

La validación digital no certifica precisión, impedancia de entrada o ancho de
banda analógico, ni margen mínimo de cola. Esta aplicación no usa la GUI estable.

## Resultado físico — 11 de octubre de 2026

10,000758 s: 6.608.396 muestras. 120,000257 s: **79.294.964 muestras**.
Tasa recibida en la ventana del host: 660.789,95 muestras/s; tasa programada
661.157,025 muestras/s. ADC14, dropped=0, fatal=0, CRC/secuencia/índice y todos
los timestamps conservados, incluidos varios desbordamientos TIM5.

Se restauraron MCU/relay V16 y el perfil previo CH1/599250 con generador apagado.
La comprobación posterior de 10 s recibió 5.988.352 muestras sin errores.
La aplicación experimental quedó detenida. Este resultado no incorpora la tasa
al menú de V16 ni certifica margen mínimo de cola o precisión analógica.
