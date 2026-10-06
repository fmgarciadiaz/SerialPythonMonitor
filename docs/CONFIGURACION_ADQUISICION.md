# Configuración de adquisición

## Perfiles de adquisición

SPI: hasta 125 kHz por canal en 8/10/12/14 bits, y 62,5 kHz en
16 bits por oversampling ×16 de conversiones de 14 bits, shift derecho 2.
UART: hasta 31,25 kHz. Los valores de 16 bits no certifican ENOB de 16 bits.
ADC a 50 MHz mediante PLL2; la ventana indicada por Python corresponde a
ciclos/50 MHz. A 62,5 kHz/16 bits se usan 5 ciclos de adquisición.
Con 17 ciclos de conversión, dos canales ×16 requieren nominalmente
32×(5+17)/50 = 14,08 µs frente a un período de 16 µs, antes de latencias.
El aumento acorta también las ventanas de los perfiles anteriores y requiere
comprobar ruido, asentamiento y referencias Bode compatibles.

SCP1 V3 usa 992 bytes, payload 972 y CRC32 en 988–991; los tipos de
comando y campos iniciales se conservan. Firmware, relay y receptor deben
aceptar juntos 16 bits/período 16 µs y rechazar 100/125 kHz en 16 bits.

## Contrato anterior V8 / V10 (V2/512)


SCP1/v2 conserva 512 bytes, little-endian, payload de 492 bytes y CRC32 sobre
0–507 en 508–511. Los nuevos tipos son SET_ACQUISITION=6 y ACQUISITION_STATUS=7.
Los tipos PING, DATA y SET_TRANSPORT se conservan.

| Offset | SET_ACQUISITION | ACQUISITION_STATUS |
|---|---|---|
| 8 | Identificador PC | Secuencia global SPI |
| 16 | Bits solicitados, uint8 | Identificador PC, uint32 |
| 20 | Período solicitado, uint32 µs | Bits solicitados, uint8 |
| 21 | Parte del período | Bits activos, uint8 |
| 22 | Parte del período | Fase, uint8 |
| 23 | Parte del período | Motivo, uint8 |
| 24 | Cero | Período solicitado, uint32 |
| 28 | Cero | Período activo, uint32 |
| 32 | Cero | Época de adquisición, uint32 |

En la solicitud, 17–19 y 24–507 son cero; en la respuesta, 36–507 son cero.
Identificadores PC: `0x80000000` a `0xfffffffe`. Fases y motivos son los del
[contrato de transporte](PROTOCOLO_CAMBIO_TRANSPORTE.md).

- ACCEPTED reserva una petición; informa los parámetros que siguen activos.
- APPLIED se emite después de detener ADC/DMA, reconstruir los buffers y
  arrancar adquisición con los parámetros nuevos. Incrementa una época de
  31 bits; los nuevos nodos comienzan en índice cero.
- REJECTED admite UNSUPPORTED, BUSY, ID_CONFLICT o HARDWARE. La adquisición sólo
  se configura con salida SPI y sin cambio de transporte pendiente. V10 vuelve
  primero a SPI si estaba en UART y luego restaura el destino elegido.
- Repetir la última solicitud devuelve el estado guardado sin volver a reiniciar.
  Un ACK APPLIED de la misma época no reinicia los lectores.
- Configuración inválida se rechaza en MCU; CRC válido no equivale a valores
  válidos. Python limita las opciones y también valida la respuesta aplicada.
- Si falla el reinicio físico, se detienen los disparos y el flujo no continúa
  como si hubiese una configuración aplicada; el cliente informa el fallo o
  timeout. No se garantiza recuperar la adquisición anterior automáticamente.

DATA tipo 3 conserva timestamp uint32 + dos ADC uint16 por par. La metadata
informa bits, tasa y período reales. El campo de offset 76 conserva el bit 0
para error fatal y usa bits 1–31 para la época. Los lectores exigen que la época
y la configuración cambien sólo con APPLIED. Una nueva época empieza una
captura nueva; no se exige continuidad temporal entre reinicios.

El consumidor aplica la petición entre nodos completos y sin frame SPI en
vuelo. Detiene el productor, TIM2, ADC y DMA 0/1 antes de reiniciar colas/RAM.
El SPI DMA 2/3 y el generador A2 permanecen disponibles. La preparación de
tramas toma el mismo mutex: metadata nueva no puede adelantarse a APPLIED.

[Contrato C++](../transport/acquisition_protocol.h), [Python](../transport/unoq_acquisition.py),
[relay C](../transport/config_relay_protocol.h) y [pruebas cruzadas](../tests/test_acquisition_config.py).
La tabla de bits y períodos coincide entre los tres lenguajes.

[Opciones, límites y uso de V10](../monitor/historico/v10/README.md).

## Perfiles rápidos SPI

Los perfiles con período inferior a 32 µs son exclusivos de SPI. La ventana ADC
se deriva del período: 391 ciclos de reloj hasta 40 kHz; 68 ciclos por encima.
El reloj ADC conserva 40 MHz, las resoluciones y el formato de 8 bytes por par.
No hace falta un nuevo campo en el protocolo. El MCU rechaza SET_TRANSPORT UART
con UNSUPPORTED si la adquisición activa supera 31,25 kHz. Python valida la
misma condición y el panel limita las opciones según el destino.

Reducir el tiempo de carga requiere menor impedancia de la fuente para conservar
la precisión; el control de continuidad no mide el error analógico de asentamiento.
Referencia: [ST AN2834, precisión del ADC](https://www.st.com/resource/en/application_note/cd00211314-how-to-get-the-best-adc-accuracy-in-stm32-microcontrollers-stmicroelectronics.pdf).

## Oversampling de 16 bits

El valor de bits 16 identifica un perfil fijo: resolución ADC1 nativa de 14
bits, ratio numérico 16 y desplazamiento de 2 bits. Un disparo TIM2 inicia
las 16 subconversiones consecutivas de cada canal; el DMA sigue guardando
un uint16 por canal. No se modifican tamaños de nodos ni paquetes.

Se aceptan períodos de 20 µs o mayores (hasta 50 kHz SPI; UART hasta
31,25 kHz). Las ventanas se acortan según la tasa:

| Tasas de pares | Ciclos por subconversión | Tiempo de ambos canales a 40 MHz |
|---|---:|---:|
| 1–2 kHz | 391 | 326,4 µs |
| 4–12,5 kHz | 68 | 68 µs |
| 15,625–20 kHz | 36 | 42,4 µs |
| 25–31,25 kHz | 20 | 29,6 µs |
| 40 kHz | 12 | 23,2 µs |
| 50 kHz | 5 | 17,6 µs |

Cada par usa 32 subconversiones de 14 bits (17 ciclos de conversión cada una).
62,5 kHz tiene un período de 16 µs, menor que los 17,6 µs mínimos de este
perfil, y se rechaza. Los timestamps representan el disparo, no el final del
promedio, y los canales se convierten secuencialmente. Una ventana más corta
reduce el tiempo para asentar la entrada; debe validarse con la fuente real.
El máximo matemático es 65532 (16 × 16383 / 4); la escala nominal de interfaz
es 65535. Volver a 8–14 bits deshabilita el oversampling. Esta opción promedia
ruido y señales dentro de la ventana; no promete 16 bits de precisión efectiva.

Referencia: [ST RM0456](https://www.st.com/resource/en/reference_manual/rm0456-stm32u5-series-armbased-32bit-mcus-stmicroelectronics.pdf).

## Captura física del timestamp

TIM5 conserva su contador de 1 MHz. Su canal 1 captura TIM2 TRGO mediante TRC/ITR1 y DMA0 lee CCR1 usando TIM5_CH1. La captura precede la petición DMA, por lo que los tiempos no dependen de la demora de lectura de CNT en el bus. Se verifica CC1OF además de los errores DMA/ADC y de los intervalos exactos del productor. [Causa y prueba de 40 perfiles](../diagnosticos/CIERRE_16BITS_20261002.md).
