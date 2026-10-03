# Arduino UNO Q · MCU, DMA y circuito

[Proyecto](../README.md) · [Firmware V8 config](../arduino/v8_config/README.md)

## Cableado de medición

```mermaid
flowchart LR
 A0[A0 / DAC0: estímulo] --> IN[Entrada del circuito]
 IN --> A2[A2: V_IN / ADC1_IN11]
 IN --> DUT[Circuito bajo prueba]
 DUT --> OUT[Salida del circuito]
 OUT --> A3[A3: V_OUT / ADC1_IN12]
 G[GND común] --- DUT
```

Para calibrar, quitar el circuito de la medición y conectar **A0 directamente
a A2 y A3**. La masa es común. La referencia compara ambos canales, no mide
exactitud absoluta del DAC. Pines MCU: A0=PA4, A2=PA6, A3=PA7.

## Adquisición y generación por hardware

```mermaid
flowchart TB
 T2[TIM2: disparo ADC] --> ADC[ADC1: secuencia A2, A3]
 ADC --> D1[GPDMA1 canal 1: conversiones]
 T2 --> T5[TIM5 CH1: captura temporal en CCR1]
 T5 --> D0[GPDMA1 canal 0: timestamps]
 D0 --> RAM[Buffers ping-pong]
 D1 --> RAM
 RAM --> PACK[Paquetes DATA]
 PACK --> SPI[SPI: DMA canales 2/3 y READY]
 PACK --> UART[Serial1: salida al puente R4]
 LUT[Tabla de onda y parámetros] --> D4[GPDMA1 canal 4]
 T6[TIM6: reloj DAC] --> DAC[DAC0: A0]
 D4 --> DAC
```

TIM2/TIM5 conservan una base de 1 MHz; tasas válidas corresponden a períodos
enteros en microsegundos. El timestamp procede de captura CCR1, evitando el
jitter de leer CNT por DMA. ADC y timestamps usan dos nodos de 2048 pares.
El motor DAC tiene temporizador y DMA independientes de adquisición.

## Fuentes y responsabilidades

| Archivo | Función |
|---|---|
| [sketch.ino](../arduino/v8_config/oscilloscope/sketch/sketch.ino) | Inicio, servicio de comandos y envío |
| [scope_config.h](../arduino/v8_config/oscilloscope/sketch/scope_config.h) | Pines, relojes, recursos y tamaños |
| [acquisition.h](../arduino/v8_config/oscilloscope/sketch/acquisition.h) | ADC, timers, DMA y continuidad |
| [generator.h](../arduino/v8_config/oscilloscope/sketch/generator.h) | Formas de onda y cambios de generador |
| [generator_dma.h](../arduino/v8_config/oscilloscope/sketch/generator_dma.h) | Motor DAC temporizado |
| [control_protocol.h](../arduino/v8_config/oscilloscope/sketch/control_protocol.h) | Selección SPI/UART |
| [acquisition_protocol.h](../arduino/v8_config/oscilloscope/sketch/acquisition_protocol.h) | Configuración ADC |
| [generator_protocol.h](../arduino/v8_config/oscilloscope/sketch/generator_protocol.h) | Comandos del generador |

## Perfiles y transiciones

8/10/12/14 bits nativos; 16 bits mediante 16 conversiones de 14 bits y
desplazamiento de dos bits. SPI llega a 62,5 kHz, o 50 kHz con oversampling;
UART llega a 31,25 kHz. Ventanas más cortas cambian el tiempo de carga del ADC.

Cambiar bits/tasa reinicia adquisición con una época nueva; el monitor cierra
el CSV anterior. Cambiar transporte o generador conserva la época. El protocolo
confirma aceptación, aplicación o rechazo antes de dar el cambio por efectivo.

[Tabla ADC y ventanas](CONFIGURACION_ADQUISICION.md) ·
[Motor DAC y límites](GENERADOR_PASO4.md) ·
[Protocolos y relay](TRANSPORTE_TECNICO.md) ·
[Validación de generación](../diagnosticos/GENERADOR_AUDIO_V10.md)
