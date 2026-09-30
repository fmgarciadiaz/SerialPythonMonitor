# Validación V5 / V7 — 30/09/2026

Objetivo: 31.250 pares/s (31,25 kHz por canal), TIM2=1 MHz, período de 32 µs.
ADC de 14 bits, adquisición y DATA/512 conservados.

## Referencia previa

Q V5 instalado a 25 kHz y enlaces de 3 Mbps: ensayo de 5 s,
124.416 pares recibidos, 24.883,2 pares/s, cero saltos de timestamp,
cero ADC fuera de rango y cero bytes perdidos después de sincronizar.

Respaldo anterior a los cambios:
`respaldos/unoq/osciloscopio_20260930_093039_647165.zip`.

## Ensayo a 31,25 kHz con enlaces de 3 Mbps — rechazado

30 s: 1.787 paquetes, 914.944 pares, 30.498,0 pares/s.
385 saltos/repeticiones de timestamp; cero ADC fuera de rango y cero bytes
perdidos después de sincronizar. No alcanza con el margen de línea teórico.

## Variante con enlaces de 4 Mbps

Q y R4 compilaron y se cargaron a 4 Mbps; 30 s de lectura no entregaron
ningún byte. Variante descartada, sin atribuir la causa a un componente
específico. Se restauró R4 a 3 Mbps. Fue necesario reiniciarlo otra vez después de que
el Q volviera también a 3 Mbps para recuperar la recepción.

## Variante TX directo del Q a 3 Mbps

Se reemplaza la cola/ISR TX de Serial1 por `uart_poll_out` desde el hilo serial.
La adquisición sigue con TIM2/ADC/GPDMA; no se deshabilitan interrupciones para
transmitir. Es polling que ocupa CPU, no DMA TX. Se conserva DATA byte por byte.

Q compilado: 82.676 bytes de programa, 75.056 bytes de RAM.
R4 compilado: 52.196 bytes de programa, 14.948 bytes de RAM.
Prueba breve (5 s): 304 paquetes, 155.648 pares, 31.128,3 pares/s; cero saltos
de timestamp, cero ADC fuera de rango y cero pérdidas tras sincronizar.
Ensayo de 30 s: 1.829 paquetes, 936.448 pares, 31.214,9 pares/s.
Cero saltos/repeticiones de timestamp, cero ADC fuera de rango y cero bytes
perdidos después de sincronizar. 4.039 bytes iniciales descartados al abrir a
mitad de paquete y 1.403 bytes de cola final; no son pérdidas en régimen.
V7 real con Qt fuera de pantalla, dos trazas, ventana de 50.000 muestras y
CSV durante aproximadamente 20 s: **608.768 filas**, Fs=31.250 Hz,
dt=32 µs, contador final ~28,6 FPS, sin errores del lector serial.
Los **608.767 intervalos** del CSV son exactamente 32 µs; cero líneas inválidas,
cero timestamps duplicados/invertidos y cero ADC fuera de rango.

Captura temporal: `/private/tmp/v7_31250_capture.csv`.
Imagen temporal: `/private/tmp/v7_31250_capture.png`.
El contador FPS corresponde a actualizaciones del monitor, no a presentación
física. El analizador marca muchos outliers estadísticos en el canal cuadrado;
esa métrica no distingue los dos niveles de una onda cuadrada de un fallo ADC.

30 pruebas automáticas pasaron, incluidas temporización, igualdad binaria de
la nueva ruta TX, continuidad, wrap uint32 y cálculo de Fs en V7.

Estado final: Q V5 con TX polling y R4 V5 cargados a 3 Mbps; V7 mantiene
3.000.000 por defecto. La aplicación Q quedó arrancada; el monitor de prueba
cerró y liberó el puerto R4.

## Alcance

La continuidad temporal y el rango ADC no certifican la exactitud de amplitud.
DATA no lleva CRC; falta comparación analógica con señal conocida y prueba
prolongada. Las mediciones Qt fuera de pantalla no equivalen a medir la
presentación física de cuadros en la pantalla del usuario.
