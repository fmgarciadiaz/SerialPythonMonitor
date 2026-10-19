# Firmware V17 · estado actual

Scope V17 es la única app de usuario instalada en el Q después de la limpieza del 19/10/2026. [Estado y firmware verificado](../../docs/ESTADO_ACTUAL_V17.md) · [Apps y respaldos](../APPS_APPLAB.md) · [Generador ampliado](../../docs/GENERADOR_200K_V17.md).

El generador productivo admite seno hasta 150 kHz y cuadrada hasta 200 kHz; los demás límites se conservan. Las secciones siguientes documentan la base heredada y campañas fechadas, no una nueva aceptación de todos los modos.

# UNO Q · V17

Pareja del monitor V17: app Scope V17, sketch C/C++ y relay Linux C.

Estado y límites vigentes: [Etapa III](../../docs/ETAPA_III_V17.md).
Las secciones V16 siguientes describen la base heredada y sus ensayos.

El formato inicial SCP1 V4 conserva tramas de 992 bytes y CRC en byte 988. Metadata hasta byte 79; t0 uint32 en 80 y CH1/CH2 uint16 desde 84. Máximo 226 pares por fragmento; diez fragmentos por nodo de 2048 pares. La cola guarda pares compactos y un timestamp inicial por nodo. El timestamp de cada fragmento se deriva después de comprobar todos los timestamps originales con TIM5 CCR1/GPDMA0.

El primer incremento conservó el DMA temporal como referencia independiente de continuidad. En ese estado no cambió reloj ADC, períodos, límites ni el DAC. En UART se expanden las muestras al DATA heredado para el R4. La regularidad temporal no se acredita comparando tiempos reconstruidos con su misma fórmula.

Herramientas explícitas:

```sh
python tools/unoq.py compile --version v17
python tools/usb_stream.py build --firmware v17
python tools/prepare_q.py --serial NUMERO --firmware v17
```

Preparar compila e instala firmware/app y relay y modifica el Q. Se ejecutó y validó la pareja V16 en el Q; el relay Linux completo compiló en ARM. El sketch compiló con el core Arduino Zephyr 1.0.0: 104 844 bytes de programa y 159 644 bytes de RAM estática. Los validadores de protocolo C/C++ se compilaron en el host.

Ver [plan de implementación y aceptación](../../docs/ETAPA_II_V16.md). V15/v13_pulse conservan sus fuentes y configuración anterior.

Ensayo físico inicial completado: 120 s por perfil ADC14/40 y 125 kHz, ADC16/62,5 kHz, sin pérdidas ni errores; WAV20/40 con ADC14/100 kHz completo. V16 quedó activa en el Q a ADC14/40 kHz y salida apagada. Ver límites y evidencia en el informe Etapa II.

Perfiles ADC14 de **200 y 250 kHz** disponibles como experimentales en V16, con captura temporal conservada. Ambos pasaron 120 s de integridad; WAV concurrente a ADC250 falló. Esos límites corresponden al ensayo inicial; la integración siguiente amplía
las tasas disponibles. Synth limita actualmente ADC a40kHz. [Evidencia y límites](../../docs/ETAPA_II_V16.md#tasas-altas-con-dma-temporal--9-de-octubre-de-2026).

## Integración dual nativa · 12/10/2026

Tabla principal de 14 máximos: cinco CH1 y nueve dual de las campañas físicas.
Se suman diez intermedias/de audio en additional_profiles.h, con ensayo de 60 s
por perfil; sync_additional_profiles.py mantiene ambas copias MCU/relay.
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
| SPI y UART · 8/10/12/14/16 bits | 1; 5; 10; 20; 31,250 |
| Sólo SPI · 8/10/12/14/16 bits | 40 |

| Bits | CH1 · sólo SPI (kHz) | Máximos dual · sólo SPI (kHz) |
| --- | --- | --- |
| 8 | 1118,881 ✓; 1221,374 | 597,014 ✓; 632,411 |
| 10 | 909,090 ✓ | 495,356; 519,480 |
| 12 | — | 410,256; 437,158 |
| 14 | 701,754 ✓; 747,663 | 355,555 ✓; 363,636 |
| 16 | — | 76,226 ✓ |

| Bits | Intermedias / audio · dual SPI (kHz por canal) |
| --- | --- |
| 8 | 225,670; 411,311 |
| 10 | 191,847; 343,348 |
| 12 | 163,432; 286,738 |
| 14 | 145,191; 250,391 |
| 16 | 44,1 nominal; 48 nominal |

Estas diez tasas adicionales usan el reloj nativo de 160 MHz. Los diez perfiles pasaron 60 s físicos cada uno, sin pérdidas ni errores de
integridad; aceptación prolongada de margen y precisión analógica pendientes. En ADC16, las tasas reales son **44.101,43 y 48.004,80 Hz**;
el selector muestra 44,1/48,0 kHz y el detalle informa la tasa real.

**✓**: perfil nativo con margen de envío ≥10%, cola máxima menor de cuatro y
margen positivo antes de sobrescritura, confirmado también en producción.
ADC10/495,356 y ADC12/410,256 kHz conservan integridad pero midieron 9,03% y
9,39% de margen integrado; no llevan esta marca.

UART conserva dos canales y un máximo de 31,250 kHz. En **Synth**, SPI limita
la adquisición a **40 kHz** y UART a **31,250 kHz**; los perfiles CH1 y dual
nativos altos no se ofrecen en ese modo. El selector filtra por resolución,
salida y Synth. Se ofrecen seis tasas bajas comunes, los 14 máximos nativos con aceptación
prolongada y diez tasas adicionales intermedias/de audio. Los perfiles heredados
siguen siendo compatibles con el protocolo, pero ya no aparecen en el selector.
La integridad validada no equivale a certificación analógica.

[Contrato y tabla de referencia](../../docs/CONFIGURACION_ADQUISICION.md#perfiles-de-adquisición).

### Duty de cuadrada continua

La cuadrada continua incorpora un dial de duty de **1–99 %**, con **50 %**
por defecto. Sólo aparece en ese modo. La frecuencia seleccionada se conserva;
la resolución de la tabla DAC puede redondear el duty: a 5 kHz los pasos son de 1 %; a 50 kHz, de 5 % (1 % solicitado produce
5 %, y 99 % produce 95 %). El 50 % mantiene el camino previo de dos puntos.
El Q informa capacidad de duty; en firmware anterior el control queda deshabilitado.
Preparar Q instala app, firmware y relay compatibles. Las capturas ADC conservan
sus bits, tasas y comprobaciones de integridad. El duty efectivo es el calculado
para la tabla del DAC, no una medición analógica de la señal.

Contrato: SET_GENERATOR conserva configuración base de 20 bytes; byte36
codifica duty (0 significa 50 %). GENERATOR_STATUS usa byte64 para duty activo
y65 para solicitado; byte23 anuncia capacidades (bit0 pulso µs, bit1 duty).
La tabla de cuadrada usa100 puntos hasta10 kHz; por encima usa floor(1 MHz/f),
hasta20 puntos a50 kHz. No se aumenta el presupuesto de1 MHz del DAC.


### Tasas intermedias y audio — 12 de octubre de 2026

Se agregaron dos intermedias duales por resolución entre 40 kHz y el primer
máximo: ADC8 225,670/411,311; ADC10 191,847/343,348; ADC12 163,432/286,738;
ADC14 145,191/250,391 kHz. ADC16 agrega audio nominal 44,1/48 kHz con tasas
reales 44.101,43/48.004,80 Hz, usando ticks enteros del reloj de 160 MHz.
Los diez perfiles están en additional_profiles.json/header, separados de los
14 máximos con aceptación prolongada. Se mantienen filtros por bits/SPI/Synth.

Firmware y relay instalados con respaldo osciloscopio_20261012_232758_157182.zip:
118896 bytes flash, 259292 RAM, 2852 libres. Los diez perfiles pasaron 60 s cada
uno con generador normal cuadrado de 5 kHz: CRC, secuencia, epoch, índices y
timestamps continuos; dropped=fatal=0, cola máxima de dos nodos. Se restauró y
verificó ADC16/40000 por SPI y generador apagado con todos sus campos originales.
Son ensayos de integridad de 60 s; no aceptación prolongada de margen ni analógica.
293 pruebas V16, 32 comprobaciones de tramas/GUI y dos pruebas nuevas de tasas
pasaron. El primer intento usó una tolerancia demasiado estrecha entre relojes
host/MCU; se conservó como evidencia y se repitió con caudal >=99% del nominal,
sin relajar los controles exactos de continuidad del MCU.

[Evidencia](../../diagnosticos/resultados_v16/additional_rates_60s_20261012.json) ·
[Estado previo](../../diagnosticos/resultados_v16/additional_rates_prior_20261012.json) ·
[Primer intento](../../diagnosticos/resultados_v16/additional_rates_wall_gate_failure_20261012.json).
