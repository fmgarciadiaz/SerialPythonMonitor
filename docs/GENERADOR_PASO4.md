# Paso cuatro: generador de ondas

Decisión física del 2 de octubre de 2026: **DAC0 en A0, V_IN en A2 y V_OUT en A3**.
El firmware actual adquiere ADC1_IN11 (PA6) y ADC1_IN12 (PA7). El DAC1 canal 1
usa PA4 y salida de 12 bits; se invoca `analogWrite(DAC0, valor)` del core Zephyr
1.0.0 para seleccionar el DAC real. `analogWrite(A0, valor)` corresponde a la
sobrecarga de pines digitales/PWM y no debe usarse para este DAC.

La prueba actual es una cuadrada nominal de 2,5 Hz (0/4095 cada 200 ms),
temporizada por hilo. El ADC conserva TIM2/TIM5 y GPDMA1 canales 0/1;
SPI3 conserva DMA 2/3. El DAC de prueba no agrega DMA ni usa esos timers.
Cambiar bits/tasa reinicia sólo la adquisición y mantiene el hilo generador.

Cableado: A0 a A2 para medir la señal generada; salida del circuito a A3,
con masa común. A1 queda disponible. La precisión del DAC y el asentamiento
ADC deben comprobarse con el circuito real.

Referencia: [pinout oficial UNO Q](https://docs.arduino.cc/resources/pinouts/ABX00162-full-pinout.pdf).

## Próxima integración

1. Motor temporizado en MCU para cuadrada, seno, triángulo y rampa.
2. Comandos y estado confirmado por el Q, accesibles por SPI y UART.
3. Panel de generador con frecuencia, amplitud, offset y habilitación.
4. Sweep, chirp y pulso, con inicio, duración y finalización explícitos.

El PC configura; el MCU temporiza. Cambiar el generador no debe reiniciar
el ADC ni cerrar el CSV. Validar captura, trigger, RUN/STOP, SINGLE y CSV en
ambas salidas y con los perfiles de adquisición habilitados.

## Validación del cambio de pines

Las 115 pruebas locales de protocolo, configuración, interfaz y capturas pasaron.
El mapeo se verificó con el overlay del core Zephyr 1.0.0 y el pinout oficial.
La carga y medición física de DAC0 junto a A2/A3 quedan pendientes: el UNO Q
no estaba conectado por USB durante este cambio. Para cargar, conectar la
placa y ejecutar `python3 tools/unoq.py deploy`, luego
`python3 tools/usb_stream.py start`. Revisar el cableado A0 salida / A2-A3 entradas.

La compilación local con Arduino CLI 1.5.1 y el perfil Zephyr 1.0.0 pasó:
91.840 bytes de programa, 151.872 bytes de variables y 110.272 bytes libres.
Se compiló el uso real de `analogWrite(DAC0, ...)`; falta validarlo cargado en hardware.
