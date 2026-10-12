# CH1 rápido cerca de 600 kHz — experimento V16

Aplicación independiente `Scope V16 CH1 600 Experimental`. V16 habitual no se
modifica. Captura exclusivamente A2 / ADC1_IN11, 14 bits, sin oversampling.
TIM2 genera un disparo cada 267 ticks de 160 MHz: **599250,936 muestras/s**.
TIM5 captura cada disparo con reloj independiente de TIM2, también a 160 MHz.
Cada tick representa 6,25 ns; su contador de 32 bits desborda cada 26,84 s.
La validación contempla ese desbordamiento y comprueba los 2048 timestamps de
cada nodo, además del rango ADC y propiedad/avance de ambas listas DMA.
La ventana de adquisición permanece en 36 ciclos ADC / 0,72 µs.

El protocolo experimental conserva SCP1 V4/992 pero usa **tipo 16**, `channels=1`
y período/timestamp **en ticks de 160 MHz**. No se conecta con el receptor estable.
Cuatro muestras de 14 bits se empaquetan sin pérdida en siete bytes. Cada trama
lleva hasta 516 muestras; el nodo de 2048 muestras ocupa cuatro tramas, la última
con 500 muestras. CH2 no se adquiere ni se transmite. La cola sigue en cuatro
nodos y SPI en 32 MHz. UART no está admitido en este experimento.

El arreglo interno de la cola conserva la estructura anterior; su segundo campo
se pone en cero únicamente para reutilizar almacenamiento del consumidor. El
receptor diagnóstico devuelve códigos CH1 y ticks; todavía no adapta la GUI,
mediciones ni exportaciones a este reloj ni ofrece este modo en el monitor.

`run.py` comprueba un único dueño del Q y salidas apagadas, guarda el perfil
actual, compila y respalda la aplicación estable. Inicia MCU/relay experimentales. El ADC permanece detenido hasta el primer PING
SPI válido, después de la espera inicial READY del relay. Luego
prueba 10 y 120 segundos, luego recarga la aplicación/relay estables, restaura el
perfil previo y comprueba otros 10 segundos. No cambia la cola ni desactiva
comprobaciones para ocultar errores. Un WAV terminado y sin errores no cuenta
como reproducción activa. La restauración deja WAV inactivo.

```sh
python -m unittest experimentos.ch1_600_v16.test_contract
python experimentos/ch1_600_v16/run.py
```

`results.json` conserva el resultado digital y la restauración; `relay_trial.log`
conserva los mensajes originales del relay. Las pruebas locales verifican el
empaquetador MCU real, el validador de nodos real, el relay C, continuidad,
CRC, padding, límites, reloj y desbordamiento. Integridad digital no certifica
precisión analógica, ancho de banda, impedancia de fuente ni margen mínimo de cola.

## Primer ensayo: arranque rechazado

`startup_results.json` y `startup_relay_trial.log` conservan el primer rechazo.
El relay validó la primera trama y rechazó seq=2 con CRC correcto, `dropped=2`,
`fatal=0`. La captura estaba activa durante la espera inicial de 20 ms del relay:
a esta tasa la cola de cuatro nodos sólo abarca 13,67 ms. Esa combinación es
incompatible con el arranque. La revisión inicia el ADC tras el primer PING válido,
sin aumentar la cola, saltar muestras ni ignorar errores. La hipótesis de arranque
se comprueba mediante un segundo ensayo, no implica aceptación de captura sostenida.
Se restauró V16 ADC14/333333 y generador apagado; 3.330.048 muestras posteriores
pasaron la validación durante 10 segundos.

## Segundo ensayo: captura sostenida validada — 11 de octubre de 2026

Con el ADC iniciado después del primer PING válido:

- 10,0017 s: 5.990.916 muestras; tasa recibida 598.992,44 muestras/s.
- 120,00035 s: 71.869.448 muestras; tasa recibida 598.910,32 muestras/s.
- Ambos casos: dropped=0, fatal=0, ADC14, período fijo de 267 ticks.
- Se mantuvo continuidad de muestras y timestamps a través de varios wraps TIM5.
- Se restauró MCU/relay V16, dos canales ADC14/333333 y generador apagado.
- Verificación posterior de 10 s: 3.330.306 pares sin errores.

La tasa programada es 599.250,936 Hz; la tasa recibida es un conteo durante la
ventana del host y no una calibración del reloj. Aplicación experimental detenida.
Pasaron 25 pruebas locales del experimento y protocolo estable. El modo todavía
no está integrado en el selector de la GUI ni valida respuesta analógica.
