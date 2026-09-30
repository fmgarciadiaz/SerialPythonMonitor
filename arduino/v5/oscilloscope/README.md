# Osciloscopio DMA_TXRX V5 Experimental

Preparación para 25 kHz, aún sin prueba física.



- Q: `arduino/v5/oscilloscope/`, TIM2 a 25.000 pares/s (40 µs), UART a 3 Mbps.
- R4: `arduino/v5/r4_bridge_v5/r4_bridge_v5.ino`, recepción y salida a 3 Mbps.
- Monitor V7: `python iniciar_monitor.py --version v7`, USB a 3.000.000.
- ADC: 14 bits, dos canales; se conserva el tiempo de adquisición de V4.
- Protocolo DATA sin cambios; 512 pares/paquete y dos nodos DMA de 2048 pares.

El tráfico esperado es 200.341,8 bytes/s (~2.003.418 bit/s con 8N1).
Por eso 2 Mbps hacia el PC ya no alcanza. A 3 Mbps el tiempo de línea por nodo
es 54,71 ms, contra 81,92 ms de adquisición. El tiempo del driver consume parte
de ese margen: estos números no garantizan que funcione en las placas.

## Orden de pruebas

1. Compilar ambos sketches. Mantener V4 recuperable.
2. Cargar el R4 V5 y arrancar únicamente la app Q V5; abrir USB a 3 Mbps.
3. `python3 diagnosticos/verificar_enlace.py PUERTO_R4 --baud 3000000 --sample-rate 25000 --seconds 30`
4. Verificar 40 µs entre timestamps, caudal cercano a 25.000 pares/s y cero pérdidas.
5. Probar V7 dibujando y grabando CSV. Analizar con `--sample-rate 25000`.
6. Comparar amplitud, ruido y respuesta con V4 usando la misma señal conocida.

Si no alcanza: evaluar DMA TX en el Q o un formato binario más compacto.
Antes de acortar la adquisición ADC, identificar la impedancia del circuito
que alimenta A0/A1. No se redujo ese tiempo en esta preparación.
No configurar 30 kHz dividiendo enteros: el reloj de 1 MHz no representa un
período exacto de 33,333 µs; esa etapa requiere revisar la base del temporizador.

Para volver: detener V5, cargar R4 V4, iniciar Q V4 y abrir monitor V6 a 2 Mbps.

Compilación comprobada: Q/Core 1.0.0, 82.660 bytes de programa y 75.036 de RAM;
R4/core 1.6.0, 52.188 bytes de programa y 14.948 de RAM. Pendiente ensayo físico.
