# V5 experimental — 31,25 kHz por canal

Objetivo: **31.250 pares/s, período exacto de 32 µs** con el reloj nominal del
UNO Q. **Probado físicamente: 30 s de recepción y CSV de V7 sin saltos de
timestamp**. Ver [resultados y límites](../../diagnosticos/VALIDACION_V5.md).
V4/monitor V6 sigue siendo la alternativa estable de 20 kHz.

## Configuración

- Q: TIM2 a 1 MHz, PSC=159, ARR=31; TIM5 conserva timestamps de 1 µs.
- ADC: 14 bits, A0/A1 en secuencia; se conserva prescaler y adquisición de V4.
- DMA: dos nodos de 2048 pares, 65,536 ms de adquisición por nodo.
- Q: transmisión por `uart_poll_out` desde el hilo serial, sin cola ni ISR TX
  del core. No mezclar esta ruta con `Serial1.write`; las interrupciones
  permanecen habilitadas. Usa CPU mientras transmite; no es DMA TX.
- Q–R4 y R4–PC: 3.000.000 baudios, 8N1.
- R4: mismo puente con ISR RX, cola de 8 KiB y TX por TDRE.
- Monitor: V7, `python iniciar_monitor.py --version v7`; calcula Fs desde timestamps.
- DATA: cabecera de 7 bytes y 512 pares de 8 bytes, sin cambio de protocolo.

El tráfico es **250.427,246 bytes/s**, equivalente a **2.504.272,46 bit/s** 8N1
(83,48 % de 3 Mbps). Cada nodo tarda al menos 54,707 ms en salir por UART:
quedan 10,829 ms para empaquetado, driver y planificación. El margen debe
comprobarse físicamente: el cálculo de caudal por sí solo no demuestra continuidad.

31,25 kHz permite 32 µs enteros; no se usa el período truncado de 33 µs que
produciría 30.303 Hz al intentar configurar 30 kHz sobre un reloj de 1 MHz.
La exactitud física depende además de la tolerancia del reloj de la placa.

## Verificación

1. Compilar Q y R4. Respaldar la app Q instalada antes de reemplazarla.
2. Usar R4 V5 a 3 Mbps y arrancar únicamente la app Q V5.
3. `python3 diagnosticos/verificar_enlace.py PUERTO_R4 --baud 3000000 --sample-rate 31250 --seconds 30`
4. Exigir 32 µs entre timestamps, caudal cercano a 31.250 pares/s y cero pérdidas.
5. Probar V7 dibujando y grabando CSV; analizar con `--sample-rate 31250`.
6. Comparar amplitud, ruido y respuesta con una señal conocida. DATA no lleva CRC.

No se acortó la adquisición ADC. Si el transporte no alcanza, evaluar DMA TX
o un protocolo más compacto antes de aumentar más la frecuencia.

## Restauración

Para volver a 25 kHz con V5: `SAMPLE_RATE_HZ = 25000U` y recompilar/cargar Q;
R4 V5 y V7 siguen a 3 Mbps. También se puede restaurar el respaldo original
del Q a 25 kHz indicado en la validación; usa el mismo baudrate de 3 Mbps.
Para volver a V4: detener V5, cargar R4 V4, iniciar Q V4 y usar V6 a 2 Mbps.
