# V8 configurable: adquisición y generador DAC para monitor V10

Aplicación **Scope Acquisition Config V8**, independiente de V7 dual.
Conserva ADC y timestamps con DMA, nodos de 2.048 pares, SPI DMA/READY y UART
DATA a 3 Mbps. Agrega SET_ACQUISITION y confirmación de resolución/período.

[Uso del monitor V10](../../../monitor/historico/v10/README.md).
[Contrato y reinicio seguro](../../../docs/CONFIGURACION_ADQUISICION.md).
[Validación física](../../../diagnosticos/ADQUISICION_V10.md).

Bits nativos: 8, 10, 12, 14. Oversampling: 16 bits (16 conversiones de 14 bits, desplazamiento 2), hasta 50 kHz SPI / 31,25 kHz UART con ventanas escalonadas de 391, 68, 36, 20, 12 y 5 ciclos. Tasas: 1, 2, 4, 5, 8, 10, 12,5, 15,625, 20, 25 y 31,25 kHz para ambos destinos; SPI agrega 40, 50 y 62,5 kHz.
El cambio de bits/tasa termina la adquisición anterior y crea una época nueva.
El cambio de salida conserva la misma época. Cambiar el generador conserva la época, los índices y el CSV.

```bash
python3 tools/unoq.py compile --version v8_config
python3 tools/unoq.py create --version v8_config  # sólo la primera importación
python3 tools/usb_stream.py build --firmware v8_config
python3 tools/usb_stream.py start --firmware v8_config
python monitor/historico/v10/app.py
```

Cerrar el monitor y detener el relay antes de cargar otra app. El Q necesita
USB en ambos modos; UART requiere el puente R4 V5 y el cableado anterior.

La configuración no reduce el ancho de los registros binarios: ADC sigue en
uint16 para todas las resoluciones. Los tiempos de muestreo de los canales,
relojes y generador no se cambian al elegir resolución/tasa.

## Ampliación SPI

V10 agrega 40, 50 y 62,5 kHz exclusivamente en SPI. Hasta 40 kHz mantiene
391 ciclos ADC; 50 y 62,5 kHz usan 68 ciclos. UART continúa hasta 31,25 kHz
y el MCU rechaza cambiar a UART con un perfil más rápido activo.
[Ensayo y límites](../../../diagnosticos/TASAS_SPI_V10.md).

## Pines actuales del UNO Q

- **A0 / DAC0 / PA4:** salida DAC de 12 bits. Generador temporizado en MCU
  con TIM6 + GPDMA1 canal 4, rango 0,1 Hz–20 kHz; arranca con cuadrada de 2,5 Hz entre códigos 0 y 4095.
- **A2 / PA6 / ADC1_IN11:** V_IN / ADC_IN, primer canal adquirido.
- **A3 / PA7 / ADC1_IN12:** V_OUT / ADC_OUT, segundo canal adquirido.

Trasladar las señales de medida a A2/A3. Para medir el generador, conectar A0
con A2; la salida del circuito bajo prueba se conecta a A3, con masa común.
La resolución del DAC (12 bits) es independiente de la resolución/oversampling
seleccionados para el ADC. [Uso y límites del generador](../../../docs/GENERADOR_PASO4.md).

TIM5 CH1 captura TIM2 TRGO mediante TRC/ITR1; DMA0 lee CCR1 con petición TIM5_CH1. Se evita jitter por lectura de CNT y se detecta overcapture sin relajar validadores. Generador dedicado TIM6/DMA4 hasta 20 kHz: [evidencia final](../../../diagnosticos/GENERADOR_AUDIO_V10.md).

## Documentación del sistema actual

[Proyecto y pantalla](../../../README.md) ·
[MCU, pines, temporizadores y DMA](../../../docs/UNO_Q_TECNICO.md) ·
[Relay Linux y protocolos](../../../docs/TRANSPORTE_TECNICO.md) ·
[Historia de todas las versiones](../../../docs/HISTORIA.md).

La referencia Bode actual fue adquirida con A0 conectado directamente a A2 y
A3: 31 puntos entre 20 Hz y 20 kHz, ADC 16 bits / 50 kHz.
[Ensayo y límites](../../../diagnosticos/BODE_V10.md).
