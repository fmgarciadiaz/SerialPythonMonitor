# Ensayo de tasas SPI · V9 Fast

**Experimental, separado de Python V10 + UNO Q V8 config.** No cambia las tasas
ni el decodificador estables. Firmware: [V9 Fast](../../arduino/v9_fast/README.md).
El monitor estable conserva sus perfiles existentes. El [monitor V11](../../monitor/v11/README.md)
ofrece 100 kHz; los candidatos superiores sólo están disponibles en el CLI.

## Estudio de viabilidad

Se conserva ADC1 con dos canales, ADC a 40 MHz, TIM2/TIM5 a 1 MHz, DMA ADC y
 timestamps, nodos de 2048 pares, DAC TIM6/DMA4, CRC y protocolo SCP1 de 512 bytes.
El relay experimental usa SPI a 32 MHz; el estable conserva 20 MHz.
No se cambia el tamaño del registro ni se permite pérdida silenciosa de muestras.

| Perfil nativo candidato | Período | Ventana ADC | Tiempo estimado del par a 14 bits |
|---|---:|---:|---:|
| 62,5 kHz (referencia) | 16 µs | 68 ciclos / 1,7 µs | 4,25 µs |
| 100 kHz | 10 µs | 68 ciclos / 1,7 µs | 4,25 µs |
| 125 kHz | 8 µs | 68 ciclos / 1,7 µs | 4,25 µs |
| 200 kHz | 5 µs | 68 ciclos / 1,7 µs | 4,25 µs |
| 250 kHz | 4 µs | 36 ciclos / 0,9 µs | 2,65 µs |

Estimación conservadora: `2 × (ventana + 17) / 40` microsegundos. ST documenta
17 ciclos de conversión en 14 bits. [Formación oficial ADC/DAC](https://www.st.com/content/ccc/resource/training/technical/product_training/group1/e5/54/d5/2b/c4/54/48/cf/STM32U5-Analog-ADC-DAC_ADC-DAC/files/stm32u5-analog-adc-dac-adc-dac.pdf/jcr%3Acontent/translations/en.stm32u5-analog-adc-dac-adc-dac.pdf).
Estas estimaciones no certifican precisión analógica ni funcionamiento físico.

16 bits ×16 se mantienen hasta 50 kHz: el par requiere al menos
`32 × (5 + 17) / 40 = 17,6 µs`. No cabe a 62,5 kHz / 16 µs. El prescaler del
ADC no ofrece división por tres; pasar de DIV4 a DIV2 daría 80 MHz, por encima
del máximo de 55 MHz documentado. Elevar los 16 bits exige estudiar el reloj
kernel ADC por separado, dentro de especificaciones.
[Datasheet STM32U585](https://www.st.com/resource/en/datasheet/dm00639779.pdf).

El SPI estable de 20 MHz entrega como máximo 2,5 MB/s bruto. Cada nodo requiere 39
tramas de 512 bytes, porque entran hasta 53 pares por trama. Su límite ideal
es unos 256 410 pares/s; 250 kHz consume aproximadamente el 97,5 % de ese
presupuesto antes de tiempos de handshake, CRC, preparación y comandos.
El candidato de 32 MHz entrega hasta 4 MB/s bruto, unos 410 256 pares/s ideales.
Eso no elimina los costos por trama. Se ensayó 32 MHz, dentro del rango del
STM32 para las condiciones indicadas en la tabla 150; no se aumentó a 40 MHz
porque 38,5 MHz es el máximo de full duplex a 2,7–3,6 V bajo las condiciones
de la tabla. La placa y el maestro requieren prueba real adicional.

Otros límites a medir: preparación/CRC en el MCU, cambios de contexto, GPIO/ioctl
Linux, contrapresión TCP y capacidad del receptor. El consumidor dispone de
cuatro nodos en cola; ampliar una cola absorbe ráfagas pero no arregla un déficit
continuo de caudal. No se relajan validaciones de CRC, timestamps, índices,
propiedad DMA, fatal ni dropped.

## Versiones y respaldos

- MCU: `arduino/v9_fast`, app independiente **Scope Fast SPI V9 Experimental**.
- Relay Linux: `experimentos/tasas_spi/relay`, binario con hash separado.
- Monitor: `monitor/v11`, copia completa de V10 con imports y assets independientes.
- Receptor Python: `experimentos/tasas_spi/receiver`, copia aislada del contrato
  configurable con los candidatos nuevos.
- Fuente estable congelada: `respaldos/experimentos/20261003_134709/`.
- Export App Lab estable: `respaldos/unoq/osciloscopio_20261003_135022_310134.zip`.
- El firmware estable, su relay y Python V10 conservan los mismos archivos;
  las herramientas sólo agregan la selección explícita `v9_fast`.

## Pruebas y resultados · 4 de octubre de 2026

Compilaciones MCU y relay ARM Linux realizadas; **168 pruebas locales pasaron**.
Pruebas cruzadas firmware C++,
relay C y decodificador Python cubren 8/10/12/14 bits a las cuatro tasas altas,
rechazo del receptor estable y límites de oversampling.

El [benchmark sintético](resultados/benchmark_receptor.json) procesa unas
1,02 millones de pares/s en este equipo, sin dibujo, conexión ni escritura a
disco. No prueba el enlace físico; sugiere margen en el decodificador básico.

### Resultado medido

| Ensayo | Resultado digital |
|---|---|
| SPI 20 MHz, versión inicial | 62,5 kHz pasó 10 s; 100 kHz perdió un nodo |
| SPI 20 MHz, CRC por byte y sellado único | Preparación bajó de 180–190 a 60–80 µs; 100 kHz aún perdió un nodo |
| SPI 20 MHz, optimización puntual CRC/PING | 100 kHz aún perdió un nodo |
| SPI 32 MHz, mismas optimizaciones | 62,5 y 100 kHz pasaron 10 s; 125 kHz perdió un nodo |
| SPI 32 MHz, 100 kHz / 14 bits, DAC a ~2 kHz | **120 s, 11 991 093 pares, cero huecos/rangos inválidos/dropped/fatal** |
| Transiciones nativas ↔ 16 bits | 18 segmentos de 3 s sin errores, 8/10/12/14 bits a 100 kHz, 16 bits a 50 kHz |
| Generador concurrente | Cambios 2/10/20 kHz, apagado y encendido sin pérdida digital |
| V11 con USB real, V(t) / FFT / heatmap | ~100 000 pares/s; heatmap 30 s; CSV de 734 350 filas sin huecos |

[Ensayo de 120 s](resultados/20261004_052438_882212/informe.json) ·
[Transiciones y generador](resultados/transiciones_20261004_052711_160875.json) ·
[Matriz de 32 MHz y fallo a 125 kHz](resultados/20261004_002019_529284/informe.json) ·
[Log del rechazo](resultados/20261004_002019_529284/relay.log) ·
[Revisiones anteriores](resultados/revisiones.json) ·
[Monitor completo y CSV](resultados/monitor_20261004_103421_457561.json).

Todos los rechazos conocidos mostraron CRC correcto, un nodo perdido y cero
fatal de DMA. No se ocultó ni toleró esa pérdida. **200/250 kHz no se probaron
físicamente:** la matriz se detuvo al fallar 125 kHz. Sólo 100 kHz se ofrece
como opción nueva en el monitor experimental. El ensayo de 120 s demuestra
continuidad en esa sesión; no certifica funcionamiento indefinido ni todas las
cargas posibles de Linux.

El CRC conserva el polinomio y bytes originales; usa tabla de 256 entradas,
compilación O2 sólo en CRC/PING para GCC y un único sellado al completar DATA.
Se eliminó el llenado de un patrón sintético que luego se reemplazaba por ADC.
Se mantienen CRC en ambos extremos, padding, índices, timestamps, epochs,
fronteras DMA, dropped y fatal.

### Monitor completo

V10 rechaza los metadatos de 100 kHz por contrato, por eso se creó V11 completo,
con imports y assets propios; no bastaba cambiar una etiqueta de Fs. Ofrece
únicamente la nueva tasa que pasó los ensayos. 125/200/250 kHz siguen fuera de
su selector; 16 bits ajusta automáticamente a 50 kHz y UART a 31,25 kHz.

El primer ensayo de heatmap rindió ~94 188 pares/s en pantalla, por debajo del
umbral del test. Otro intento quedó en un diálogo fuera de pantalla al detectar
contrapresión; se cerró únicamente ese proceso de prueba. El harness final usa
un bucle Qt temporizado y registra diálogos como errores, evitando quedar bloqueado.
A 100 kHz V11 limita el pintado FFT/heatmap a 20 Hz, manteniendo los pasos FFT
y muestras originales. Con USB real: V(t) ~99 737 pares/s, FFT ~100 424 pares/s,
heatmap ~99 952 pares/s durante 30 s. El CSV de V(t) tiene 734 350 filas y cero
saltos. Los conteos por segundo en pantalla pueden variar por límites de lote;
la continuidad se verifica por índices y timestamps.

[Primer ensayo gráfico](resultados/monitor_20261004_052846_196514.json).
No se probó Bode completo ni UART/R4 a las nuevas tasas: UART permanece limitado
y las curvas Bode de nuevos perfiles requieren su propia calibración.

### Señal analógica y cableado

A2 recibió una senoide de amplitud pico ~1,216 V, offset ~1,616 V y residuo RMS
~8,7 mV tanto a 62,5 como a 100 kHz. A3 recibió sólo ~4 mV pico y residuo
~11 mV: **no se aprobó la comprobación analógica de ambos canales**. Se pidió
confirmar si A3 sigue a través del circuito; no se presupone conexión directa.
No se reemplazó la calibración Bode existente ni se extrapoló a 100 kHz.

Para evaluar ganancia, fase y precisión hacen falta A0 unido directamente a A2
y A3, masa común, monitor desconectado y los ensayos de ambas entradas. La Fs de
100 kHz mantiene 68 ciclos / 1,7 µs de carga, igual que a 62,5 kHz. El tono pedido
como 2 000 Hz es ~1 996,805 Hz por divisor entero del temporizador DAC (313 ticks
para 256 puntos); el ajuste analiza esa frecuencia medida. No es una
calibración absoluta del reloj: ADC y DAC comparten referencias.

### Qué limita el siguiente aumento

El ADC nativo tiene margen para 125 kHz, según el cálculo del par; la pérdida
de cola y CRC correcto apuntan al consumidor/transporte. Antes de acortar más
la ventana ADC conviene reducir el armado DMA por trama, las copias y el
handshake de hilos/GPIO. Una alternativa requiere protocolo nuevo con tramas
mayores, amortizando costos fijos. SPI3 tiene TSIZE de 10 bits: **1 024 bytes no
entran en una única transferencia** con el esquema actual (máximo 1 023).
Aumentar sólo la cola amortigua ráfagas, pero no resuelve caudal insuficiente.

## Ejecutar explícitamente

```sh
python3 tools/unoq.py compile --version v9_fast
python3 tools/unoq.py create --version v9_fast  # ya importada en este ensayo
python3 tools/usb_stream.py build --firmware v9_fast
# Con monitor desconectado y circuito de prueba preparado:
python3 tools/usb_stream.py stop
python3 tools/unoq.py stop --version v8_config
python3 tools/usb_stream.py start --firmware v9_fast
python experimentos/tasas_spi/verificar.py --rates 62500 100000 125000 200000 250000 --seconds 10
# Tras reiniciar si un candidato falló:
python experimentos/tasas_spi/verificar.py --rates 100000 --seconds 120
python experimentos/tasas_spi/transiciones.py
QT_QPA_PLATFORM=offscreen python experimentos/tasas_spi/verificar_monitor.py
python monitor/v11/app.py
```

El análisis de tono se hace después de cerrar el enlace para evitar contrapresión
durante recepción. El receptor restaura exactamente el perfil y generador que encontró al abrir
la app experimental. Si el enlace aborta, registra el fallo de restauración;
puede hacer falta reiniciar la app antes del siguiente ensayo.

## Volver al conjunto estable

```sh
python3 tools/usb_stream.py stop --firmware v9_fast
python3 tools/unoq.py stop --version v9_fast
python3 tools/usb_stream.py start --firmware v8_config
python monitor/v10/app.py
```

Iniciar la app puede cargar su firmware y restablece su estado inicial; elegir
los ajustes anteriores en el monitor. No se reemplazó la app estable.

## Estado al cerrar el ensayo

Se detuvo V9 Fast y se volvió a cargar **V8 config + relay estable**, con 14 bits,
31,25 kHz y generador cuadrado de 2,5 Hz / códigos 0–4095. Ese es el estado
recuperado y guardado antes de probar V9. [Verificación posterior](resultados/restauracion_estable.json).
Las fuentes estables coinciden por SHA-256 con el respaldo.

Al comenzar, el relay estable ya estaba detenido por un nodo perdido, antes
de iniciar V9. Se registró por separado y se reinició V8 para obtener una
base recuperable: [fallo previo](resultados/fallo_previo_relay_estable.json) y
[estado previo recuperado](resultados/estado_estable_previo.json). No se atribuye
ese fallo inicial al firmware experimental.

## Repetición solicitada de 125 kHz

[Ensayo](resultados/20261004_190527_143796/informe.json) y
[diagnóstico de la trama rechazada](resultados/20261004_190527_143796/diagnostico_125.json):
100 kHz / 14 bits pasó 10 s (997 429 pares); 125 kHz abortó después de recibir
65 396 pares, equivalentes a 0,52316 s de señal ADC, sin huecos en ese tramo.
La siguiente trama válida en CRC reportó dropped=1 y fatal=0. Preparación 51 µs,
verificación 71 µs en la trama de rechazo; esos dos tiempos no incluyen todo
el envío, configuración DMA ni espera de Linux y no bastan para atribuir el atraso
a una única etapa.

Antes de este ensayo el relay ya estaba detenido por otro nodo perdido a
14 bits / 50 kHz: [registro separado](resultados/20261004_190527_143796/fallo_previo.json).
Por eso el caudal es una hipótesis fuerte para el fallo repetible de 125 kHz,
pero aún deben medirse latencias máximas y posibles pausas del consumidor para
explicar los fallos esporádicos a tasas menores. No se cambió código de firmware
en esta repetición.

## Medición del consumidor a 125 kHz

[Diagnóstico de latencias](DIAGNOSTICO_125.md): ciclo medio 473 µs con PC y
465 µs sin PC, frente a 420 µs disponibles. Ambos ensayos llenaron la cola
(dropped=1, fatal=0, CRC válido). El atraso existe también sin enviar al PC;
falta separar preparación/handoff MCU de driver y planificación Linux.
