# Apps de App Lab

## Nueva pareja V12

**Scope Acquisition P992 V11** usa [Monitor V12](../monitor/historico/v12/README.md),
relay propio SCP1 V3/992 a 32 MHz y TCP 8766. Iniciar con
`python3 tools/usb_stream.py start --firmware v11_p992`.
[Guía y manifiesto](historico/v11_p992/README.md). No usar monitor V11/V10 con esta app.


Para V10 usar **Scope Acquisition Config V8** con el relay configurable de la
[guía de V10](../monitor/historico/v10/README.md). Para el monitor V9 usar **Scope Output Select V7** con el relay dual de la
[guía de V9](../monitor/historico/v9/README.md). Para V8 usar **Scope ADC SPI V6** e iniciar el relay según la
[guía de V8](../monitor/historico/v8/README.md). Los nombres se conservan para que las
herramientas sigan encontrando cada app.

Las descripciones siguientes se basan en las fuentes locales y en la lectura
del código instalado en el Q. Las cifras históricas describen la configuración
del código; no implican una nueva validación física.

| Nombre en App Lab | Descripción |
|---|---|
| Scope Acquisition Config V8 | PASO 3 — Monitor V10, bits y tasa configurables (SPI hasta 62,5 kHz; UART hasta 31,25 kHz), Q conectado para control. |
| Scope Output Select V7 | EXPERIMENTAL PASO 2 — Q siempre en control; salida SPI o UART al R4. Usar [monitor V9](../monitor/historico/v9/README.md) o verificador dual; no usar V8. |
| Scope ADC SPI V6 | ACTUAL — Monitor V8 por USB del Q, sin R4. ADC 2 canales, 14 bits, 31,25 kHz. Iniciar con tools/usb_stream.py; relay externo. |
| Osciloscopio DMA_TXRX V5 Experimental | RESPALDO UART — Monitor V7 con puente R4 V5. ADC 2 canales, 14 bits, 31,25 kHz; UART 3 Mbps. No usa SPI. |
| Osciloscopio DMA_TXRX V4 | HISTORICO UART — Monitor V6 con puente R4 V4. ADC 2 canales, 14 bits, 20 kHz; UART 2 Mbps. Referencia anterior. |
| Scope SPI Benchmark V6 | ENSAYO HISTORICO 1 — SPI por driver/IRQ, datos sinteticos y CRC. Sin ADC ni monitor. Primer benchmark MCU-MPU. |
| Scope SPI Polling V6 | ENSAYO HISTORICO 2 — SPI por registros TXDR/RXDR y polling, datos sinteticos. Sin ADC ni monitor. |
| Scope SPI DMA V6 | ENSAYO HISTORICO 3 — SPI con DMA TX/RX y espera por polling. Datos sinteticos; sin ADC ni monitor. |
| Scope SPI IRQ READY V6 | ENSAYO HISTORICO 4 — SPI DMA con IRQ y READY, sin pausa fija. Datos sinteticos; sin ADC. Base de la version actual. |
| Osciloscopio DMA_TXRX V3 | HISTORICO V3 — ADC y timestamps por DMA, 2 canales a 10 kHz. Salida DATA por Serial1 a 1 Mbps. Anterior a V4. |
| Osciloscopio DMA_TXRX V2 | HISTORICO V2 — ADC por DMA, 2 canales a 10 kHz. Salida DATA por Serial1 a 1,1 Mbps; compatibilidad Core Zephyr 0.90. |
| Debugger Rx Rt | DIAGNOSTICO — Emite DATA sintetico por Serial1 a 1 Mbps: senoidales de 100 y 200 Hz con timestamps de 10 kHz. Sin ADC. |
| Generador | GENERADOR HISTORICO — Seno por DAC0 con tabla de 32 puntos y analogWrite de 12 bits; temporizacion por micros. Sin adquisicion. |
| Osciloscopio | HISTORICO — Lee A0/A1 con analogRead de 12 bits en hilo Zephyr; envia bloques binarios por Serial a 2 Mbps. Sin DMA ADC. |
| Osciloscopio debug | DEBUG HISTORICO — Lee A0/A1 con analogRead de 12 bits; imprime timestamp y dos ADC en texto CSV por Serial a 2 Mbps. |
| Osciloscopio DMA | HISTORICO DMA — ADC y timestamps por hardware a 5 kHz; salida DATA por Serial a 2 Mbps. Anterior a la variante TX/RX. |
| Osciloscopio DMA_TXRX | HISTORICO DMA TX/RX — ADC y timestamps por hardware a 5 kHz; salida DATA por Serial1 a 1 Mbps. Anterior a V2/V3. |
| Osciloscopio Test | DIAGNOSTICO DMA — Adquisicion a 10 kHz y Serial1 a 1 Mbps; registra arranque, nodos DMA y discontinuidades. No es el monitor actual. |
| Potentiometer | EJEMPLO ADC — Lee potenciometro en A0 a 14 bits e imprime el valor por Serial a 9600 baudios, con pausa de 50 ms. |

Catálogo de metadatos: [apps_catalogo.json](apps_catalogo.json).
Actualizar una descripción no requiere cargar firmware ni reiniciar la app.

## App experimental de tasas altas

**Scope Fast SPI V9 Experimental**, carpeta remota
`/home/arduino/ArduinoApps/scope-fast-spi-v9-experimental`. App separada, compilada
y ensayada con SPI a 32 MHz y ADC a 100 kHz por canal. Usa el
[monitor V11](../monitor/historico/v11/README.md) o receptor CLI de `experimentos/tasas_spi`.
Continuidad digital de 120 s a 14 bits aprobada; exactitud analógica de ambos
canales pendiente. V8 config conserva su app y fuentes originales.
[Estudio y estado](../experimentos/tasas_spi/README.md).
