# UNO Q · candidato V16

Pareja aislada del monitor V16: app Scope V16, sketch C/C++ y relay Linux C.

SCP1 V4 conserva tramas de 992 bytes y CRC en byte 988. Metadata hasta byte 79; t0 uint32 en 80 y CH1/CH2 uint16 desde 84. Máximo 226 pares por fragmento; diez fragmentos por nodo de 2048 pares. La cola guarda pares compactos y un timestamp inicial por nodo. El timestamp de cada fragmento se deriva después de comprobar todos los timestamps originales con TIM5 CCR1/GPDMA0.

Este primer incremento conserva el DMA temporal como referencia independiente de continuidad. No cambia reloj ADC, períodos, límites ni el DAC. En UART se expanden las muestras al DATA heredado para el R4. La regularidad temporal no se acredita comparando tiempos reconstruidos con su misma fórmula.

Herramientas explícitas:

```sh
python tools/unoq.py compile --version v16
python tools/usb_stream.py build --firmware v16
python tools/prepare_q.py --serial NUMERO --firmware v16
```

Preparar compila e instala firmware/app y relay y modifica el Q. Se ejecutó y validó la pareja V16 en el Q; el relay Linux completo compiló en ARM. El sketch compiló con el core Arduino Zephyr 1.0.0: 104 844 bytes de programa y 159 644 bytes de RAM estática. Los validadores de protocolo C/C++ se compilaron en el host.

Ver [plan de implementación y aceptación](../../docs/ETAPA_II_V16.md). V15/v13_pulse conservan sus fuentes y configuración anterior.

Ensayo físico inicial completado: 120 s por perfil ADC14/40 y 125 kHz, ADC16/62,5 kHz, sin pérdidas ni errores; WAV20/40 con ADC14/100 kHz completo. V16 quedó activa en el Q a ADC14/40 kHz y salida apagada. Ver límites y evidencia en el informe Etapa II.

Perfiles ADC14 de **200 y 250 kHz** disponibles como experimentales en V16, con captura temporal conservada. Ambos pasaron 120 s de integridad; WAV concurrente a ADC250 falló. El monitor limita el audio a ADC100; 16 bits mantiene 62,5 kHz. [Evidencia y límites](../../docs/ETAPA_II_V16.md#tasas-altas-con-dma-temporal--9-de-octubre-de-2026).
