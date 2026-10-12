# UNO Q · V16

Pareja aislada del monitor V16: app Scope V16, sketch C/C++ y relay Linux C.

El formato inicial SCP1 V4 conserva tramas de 992 bytes y CRC en byte 988. Metadata hasta byte 79; t0 uint32 en 80 y CH1/CH2 uint16 desde 84. Máximo 226 pares por fragmento; diez fragmentos por nodo de 2048 pares. La cola guarda pares compactos y un timestamp inicial por nodo. El timestamp de cada fragmento se deriva después de comprobar todos los timestamps originales con TIM5 CCR1/GPDMA0.

El primer incremento conservó el DMA temporal como referencia independiente de continuidad. En ese estado no cambió reloj ADC, períodos, límites ni el DAC. En UART se expanden las muestras al DATA heredado para el R4. La regularidad temporal no se acredita comparando tiempos reconstruidos con su misma fórmula.

Herramientas explícitas:

```sh
python tools/unoq.py compile --version v16
python tools/usb_stream.py build --firmware v16
python tools/prepare_q.py --serial NUMERO --firmware v16
```

Preparar compila e instala firmware/app y relay y modifica el Q. Se ejecutó y validó la pareja V16 en el Q; el relay Linux completo compiló en ARM. El sketch compiló con el core Arduino Zephyr 1.0.0: 104 844 bytes de programa y 159 644 bytes de RAM estática. Los validadores de protocolo C/C++ se compilaron en el host.

Ver [plan de implementación y aceptación](../../docs/ETAPA_II_V16.md). V15/v13_pulse conservan sus fuentes y configuración anterior.

Ensayo físico inicial completado: 120 s por perfil ADC14/40 y 125 kHz, ADC16/62,5 kHz, sin pérdidas ni errores; WAV20/40 con ADC14/100 kHz completo. V16 quedó activa en el Q a ADC14/40 kHz y salida apagada. Ver límites y evidencia en el informe Etapa II.

Perfiles ADC14 de **200 y 250 kHz** disponibles como experimentales en V16, con captura temporal conservada. Ambos pasaron 120 s de integridad; WAV concurrente a ADC250 falló. Esos límites corresponden al ensayo inicial; la integración siguiente amplía
las tasas disponibles. Synth limita actualmente ADC a40kHz. [Evidencia y límites](../../docs/ETAPA_II_V16.md#tasas-altas-con-dma-temporal--9-de-octubre-de-2026).

## Integración dual nativa · 12/10/2026

Whitelist común de14 perfiles: cinco CH1 y nueve dual de las campañas físicas.
Kind20 conserva timestamps TIM5 a160MHz y empaquetado especializado por bits;
ADC8 dual mantiene432 pares/trama. CH1 conserva capacidades864/696/496.
acquisition_storage.h comparte las arenas estáticas de los modos excluyentes:
ADC y timestamps completos, cuatro slots, sin heap. Legacy CH1 conserva pares;
UART usa scratch posterior a sus dos nodos de timestamps. WAV mantiene16 bloques.
117908 bytes flash,259132 bytes RAM,3012 libres. Arranque y14 perfiles nativos
verificados120s cada uno, junto con transiciones y restauración de parámetros.
Margen integrado de ADC10/495356 y ADC12/410256 menor que10%; flags del monitor
reconciliados sin alterar las aceptaciones aisladas. Firmware integrado instalado.
[Evidencia y respaldo](../../experimentos/maxfreq_dual_v16/RESULTADOS.md#incorporación-a-producción-completada).

### Frecuencias disponibles

Todas las tasas son **por canal**, en **kHz**. En dual se capturan CH1 y CH2
por disparo; en CH1 sólo A2. Se muestran tres decimales cuando hace falta para
identificar la tasa en Hz enteros; la tasa efectiva depende del período aplicado.

| Salida / resolución | Tasas dual comunes (kHz) |
| --- | --- |
| SPI y UART · 8/10/12/14/16 bits | 1; 2; 4; 5; 8; 10; 12,500; 15,625; 20; 25; 31,250 |
| Sólo SPI · 8/10/12/14/16 bits | 40; 50; 62,500; 66,666; 71,428 |
| Sólo SPI · 8/10/12/14 bits | 100; 125; 200; 250; 333,333 |

| Bits | CH1 · sólo SPI (kHz) | Dual adicional · sólo SPI (kHz) |
| --- | --- | --- |
| 8 | 1118,881 ✓; 1203,007; 1221,374 | 597,014 ✓; 632,411 |
| 10 | 909,090 ✓ | 495,356; 519,480 |
| 12 | — | 410,256; 437,158 |
| 14 | 599,250; 661,157; 701,754 ✓; 747,663 | 355,555 ✓; 363,636 |
| 16 | — | 76,226 ✓ |

**✓**: perfil nativo con margen de envío ≥10%, cola máxima menor de cuatro y
margen positivo antes de sobrescritura, confirmado también en producción.
ADC10/495,356 y ADC12/410,256 kHz conservan integridad pero midieron 9,03% y
9,39% de margen integrado; no llevan esta marca.

UART conserva dos canales y un máximo de 31,250 kHz. En **Synth**, SPI limita
la adquisición a **40 kHz** y UART a **31,250 kHz**; los perfiles CH1 y dual
nativos altos no se ofrecen en ese modo. El selector filtra por resolución,
salida y Synth. Los perfiles heredados conservan la evidencia y límites de sus
ensayos; disponibilidad en el selector no equivale a certificación analógica.

[Contrato y tabla de referencia](../../docs/CONFIGURACION_ADQUISICION.md#perfiles-de-adquisición).
