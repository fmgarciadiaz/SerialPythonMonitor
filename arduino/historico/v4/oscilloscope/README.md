# Osciloscopio DMA_TXRX V4 — 20 kHz, Core Zephyr 1.0.0

V4 parte de la V3 que el usuario comprobó funcionando. Conserva ADC de 14 bits,
DMA, sincronización de arranque, formato DATA y tratamiento de caché.
La V3 queda respaldada en `respaldos/unoq/osciloscopio-dma_txrx-v3-antes-20khz.zip`
y en su aplicación independiente del Q. Las tareas locales apuntan a V4.

## Configuración V4

- UNO Q / STM32U585, A0 y A1, ADC de 14 bits a 20.000 pares/s (20 kHz por canal; dos conversiones por disparo).
- TIM2 dispara la adquisición; TIM5 aporta timestamps de hardware en µs.
- GPDMA1 canales 0 y 1, dos nodos de 2048 pares (102,4 ms por nodo).
- Serial1 a 3.000.000 baudios, paquetes de 512 pares.
- A2 cambia de estado cada 200 ms; mismo hilo, pila y prioridad que V2.
- Arranque: observar adquisición en nodo 0, limpiar TC iniciales, esperar que
  ambos canales estén en nodo 1 con nuevas TC antes de entregar el primer nodo.
- Python del Q y protocolo de comunicación con el monitor/R4 sin cambios.

## Organización

- `sketch/scope_config.h`: pines, frecuencias, tamaños, prioridades y comprobaciones de compilación.
- `sketch/scope_protocol.h`: muestra de 8 bytes y paquete DATA de 4103 bytes, sin padding.
- `sketch/sketch.ino`: configuración de periféricos, hilos y consumidor serial.
- `sketch/sketch.yaml`: perfil fijado a `arduino:zephyr (1.0.0)`.

## Base V3 conservada respecto de V2

Se retiró la capa de compatibilidad de Core 0.90.0 que redefinía funciones LL
y operaciones de caché con símbolos débiles. ADC y temporizadores usan funciones
inline de los encabezados STM32 incluidos en Core 1.0.0. La construcción de los
dos anillos DMA usa una única función local para el formato lineal fijo
CTR1/CTR2/CBR1/CSAR/CDAR/CLLR, conservando los anchos y longitudes de origen/destino.

El enlace dinámico de App Lab no exporta `cache_data_flush_range` ni
`cache_data_invd_range`: figuran en `syms-static.ld`, pero no en
`syms-dynamic.ld`. Por eso se usa una función local con las operaciones LL inline
del controlador **DCACHE1 del STM32U585**, protegida por `irq_lock()` en este MCU
mononúcleo. Usa el rango inclusivo del buffer y barreras de memoria, y respeta la
alineación de 16 bytes del core. No redefine símbolos de Zephyr ni escribe en
registros SCB codificados manualmente.

El perfil fija además RouterBridge 0.4.3, RPClite 0.3.1, MsgPack 0.4.2,
DebugLog 0.8.4, ArxTypeTraits 0.3.2 y ArxContainer 0.7.0. Los perfiles versionados
usan un entorno aislado: estas dependencias deben declararse en `sketch.yaml`,
aunque estén instaladas en el equipo. Arduino CLI las descarga al compilar.

El consumidor consulta DMA cada 1 ms en lugar de solicitar esperas de 50 µs.
Esto reduce sus despertares durante la espera; no cambia el disparo de hardware.
Cada paquete se envía normalmente en una sola llamada `Serial1.write`, en vez de
cuatro. Se completan posibles escrituras parciales sin repetir cabeceras.
No se cambió el driver UART del core ni se agregó DMA de transmisión UART.

## Validación y límites

La prueba `tests/test_scope_protocol.py` compila y ejecuta en el Mac el formato
y la función de envío reales, verificando todos los bytes frente al protocolo
anterior, incluyendo wrap del timestamp, escritura parcial y retorno cero.

V4 compilada en el Q con el perfil fijado: 82.660 bytes de programa y
75.036 bytes de RAM global. R4 WiFi compilado con renesas_uno 1.6.0:
52.188 bytes de programa y 14.948 bytes de RAM. Compilar no prueba el caudal real.

El enlace necesita 160.273,44 bytes/s, o 1.602.734,38 bit/s en 8N1.
A 3 Mbps ocupa aproximadamente el 53,42 % del enlace. Un nodo ocupa 54,71 ms
de tiempo de línea y se adquiere en 102,4 ms; las demoras del driver consumen
parte del margen. A 2 Mbps se midieron sólo ~18.091 pares/s y saltos de dos
nodos DMA: el tiempo de CPU del driver impedía sostener la adquisición. El consumidor DMA sigue siendo ping-pong, sin control de flujo:
un bloqueo prolongado puede sobrescribir datos pendientes.

TIM2 pasa de ARR=99 a ARR=49 manteniendo el reloj de 1 MHz. No se acorta
el tiempo de adquisición analógica de 391,5 ciclos por canal. El devicetree
del core instalado selecciona HCLK (160 MHz) para ADC; el divisor de 4
configura 40 MHz. La ventana de muestreo de ambos canales suma 19,575 µs,
dejando margen para las conversiones dentro del período de 50 µs.

## Puente R4 y prueba

V4 está cargada y ejecutándose en el Q. El R4 tiene el puente V4 optimizado.
V3 permanece como aplicación independiente detenida.

Cargar `arduino/historico/v4/r4_bridge_v4/r4_bridge_v4.ino` en el **UNO R4 WiFi**.
El sketch original del IDE queda intacto y respaldado como
`respaldos/DebuggerRtRx_1100000.ino.bak`. **Q–R4 usa 3.000.000 baudios**.
En este R4, `Serial` usa otro UART hacia el ESP32/USB: el baud del monitor
**sigue en 2.000.000** (predeterminado de V6). No poner 3 Mbps en Python.

El puente usa una cola de 8 KiB y una ISR de recepción específica de SCI2,
sin las consultas/lecturas del SafeRingBuffer del core. La salida por SCI9
se alimenta directamente cuando TDRE indica espacio, sin ISR TX por byte.
Las pruebas con el puente estándar a 2 Mbps produjeron corrupción; optimizar
RX y TX permitió paquetes íntegros, pero fue necesario pasar Q–R4 a 3 Mbps
para eliminar las sobrescrituras DMA. Este sketch requiere R4 WiFi y se ha
compilado/probado con renesas_uno 1.6.0; reserva SCI2, SCI9 y su vector RX.
No usar Serial.write/Serial1.read simultáneamente con esta ruta.

El LED se enciende si desborda la cola propia; no cubre todos los errores
internos de UART/ESP32. Ver [detalles del puente](../r4_bridge_v4/README.md).

Prueba física de 15 s: **585 paquetes / 299.520 pares / 19.967,7 pares/s**,
**0 anomalías de timestamp, 0 ADC fuera de rango y 0 bytes descartados tras
sincronizar**. Un fragmento inicial/final es normal al abrir el puerto a mitad
de paquete. Resultado PASS; no equivale a una garantía de ausencia de errores
para cualquier cableado o duración.

También se ejecutó el monitor V6 con Qt fuera de pantalla, gráficos y grabación
CSV durante unos 20 s: **400.896 filas**, Fs mostrada **20.000 Hz**,
**0 anomalías de timestamp** en el archivo. Esto verifica recepción, procesamiento
y grabación con hardware real; no mide la fluidez visual en la pantalla del usuario.

Cerrar el monitor antes de usar la prueba sin gráficos:

```sh
python3 diagnosticos/verificar_enlace.py /dev/cu.PUERTO_R4 --seconds 15
python3 diagnosticos/analizar_captura.py capturas/archivo.csv --sample-rate 20000
```

Se esperan cerca de 20.000 pares/s, separación de 50 µs y cero saltos.
El verificador admite timestamps uint32 que dan la vuelta y fragmentos inicial/final.
El protocolo no tiene CRC: no detecta toda corrupción posible en las amplitudes.
Para la V3 usar `--sample-rate 10000` y su puente original a 1.100.000.
El receptor `recibir_diagnostico.py` conserva 2 Mbps hacia el PC; sus marcadores
pertenecen al firmware de diagnóstico histórico, que sigue siendo de 10 kHz.
`DebugRTRXread.py` y las versiones antiguas del monitor son históricos.

El respaldo exacto anterior está en
`respaldos/sketch_dma_txrx_v2_antes_zephyr1.ino.bak` en la raíz del repositorio.
Para recuperar V2, restaurar ese contenido en `sketch/sketch.ino` y recompilar;
los nuevos headers no se usan desde el sketch V2.

Referencias: [Arduino Core Zephyr 1.0.0](https://github.com/arduino/ArduinoCore-zephyr/tree/1.0.0),
[caché de Zephyr](https://docs.zephyrproject.org/latest/hardware/cache/guide.html),
[controlador DCACHE de ST](https://github.com/STMicroelectronics/stm32u5xx-hal-driver/blob/main/Src/stm32u5xx_hal_dcache.c).
