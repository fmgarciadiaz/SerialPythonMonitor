# Arduscopio Q · arquitectura

El STM32 del UNO Q adquiere A2/A3 y genera A0 con temporizadores y DMA. La
pareja **Scope V19** de MCU y relay tiene fuentes y nombres de despliegue
propios, derivados de V18; se instaló usando su recibo independiente. La primera
recuperación física y un smoke visible de adquisición/FFT pasaron. V18 permanece
intacta como respaldo pareado de `monitor/v18` y `arduino/v18`. [Presentación con imágenes de
cada módulo](../README.md).

```mermaid
flowchart LR
 ADC[A2 / A3 ADC] --> MCU[STM32 · DMA y temporizadores]
 MCU <--> Relay[Relay Linux del Q]
 Relay <-->|USB / ADB| RX[Proceso receptor del monitor]
 RX --> DSP[DSP / RADIO / FILTER]
 DSP --> GUI[V(t) / FFT / Heatmap / Bode]
 DSP --> Raster[Proceso de raster · V(t) denso completo]
 Raster -->|Imagen terminada + snapshot de cursor| GUI
 DSP --> PCM[Cola PCM]
 WAV[WAV / Synth] --> PCM
 PCM --> RX
 MCU --> DAC[A0 DAC]
```

El receptor valida CRC, secuencia, época y continuidad. La GUI consume lotes
con presupuesto acotado; no se descartan muestras para esconder atrasos. Los
buffers y conversiones conservan alineación entre canales y marcas de tiempo.
Las confirmaciones de configuración preservan el orden de la historia; el
audio tiene canal de pedidos independiente.

V(t) con detalle completo y ventanas densas rasteriza todos los segmentos en
un proceso sin acceso al Q. Hay una captura en vuelo; se conservan los datos
originales y se publican imagen y datos de cursor juntos. La GUI compone esa
imagen y mantiene ejes/trigger/cursores vectoriales. STOP, SINGLE y cambios de
vista invalidan resultados antiguos. [Contrato y pruebas](RASTER_TEMPORAL_V19_20261029.md).
La recepción RADIO a 40 kHz utiliza ACK CHUNK validados para posponer consultas
QUERY redundantes, sin cambiar créditos, timeouts ni el fallback.

`monitor/v19` contiene GUI PySide6, DSP, receptor y soporte para preparar la
pareja V19. `arduino/v19` contiene su copia propia de app MCU y relay; el
manifiesto registra qué archivos son idénticos a V18. «Preparar Q» compara el
recibo y verifica la pareja existente; sólo actualiza mediante respaldo y
rollback. «Conectar» no programa la placa.

[Guía del monitor](../monitor/v19/README.md) ·
[Validación y plan de pruebas](PYSIDE_V19_COMPARACION.md) ·
[Versiones y respaldos](VERSIONES.md) ·
[Preparación V19](PREPARAR_Q_V19.md).
