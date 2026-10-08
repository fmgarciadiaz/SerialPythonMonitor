# Historia y evolución del proyecto

[Volver a la presentación del proyecto](../README.md).

Este documento reúne la evolución del osciloscopio y los detalles de versiones,
organización y operación que antes estaban en el README principal. Los documentos
originales se conservan como referencia; sus rutas, velocidades y estados pueden
corresponder a etapas anteriores.

## Versiones actuales y catálogo completo · 5 de octubre de 2026

La entrada usada actualmente es **Python V13 + UNO Q V12 Audio**;
Python V12 + UNO Q V11 P992 se conserva como pareja anterior. Las secciones de
operación antiguas más abajo son historia, no instrucciones para el conjunto
actual. [Arranque actual](../README.md#probar-el-proyecto).

| Monitor | Firmware / destino de referencia | Evolución |
|---|---|---|
| Consola, notebook, Tkinter | Serial | Primeros registros y visualización |
| Qt V1–V5 | UART | Interfaz de osciloscopio y dos canales |
| [V6](../monitor/historico/v6) | Q V4 + R4 V4 | Conjunto UART a 20 kHz |
| [V7](../monitor/historico/v7) | Q V5 + R4 V5 | 31,25 kHz, estilos y reducción visual |
| [V8](../monitor/historico/v8/README.md) | Q V6 ADC | USB directo por SPI al Linux del Q |
| [V9](../monitor/historico/v9/README.md) | Q V7 dual | Control Q permanente y selección SPI/UART |
| [V10](../monitor/historico/v10/README.md) | [Q V8 config](../arduino/historico/v8_config/README.md) | ADC configurable, generador, FFT, heatmap y Bode |
| [V11 experimental](../monitor/historico/v11/README.md) | [Q V9 Fast](../arduino/historico/v9_fast/README.md) | SPI rápido: 100 kHz por canal, estable conservado |

| [V12](../monitor/historico/v12/README.md) | [Q V11 P992](../arduino/historico/v11_p992/README.md) | SCP1 V3/992, ADC14/125 kHz y ADC16/62,5 kHz |

### Firmware conservado

| Versión | Objetivo |
|---|---|
| [V4](../arduino/historico/v4) | Adquisición Q y puente R4 a 20 kHz |
| [V5](../arduino/historico/v5/README.md) | UART de 31,25 kHz |
| [V6](../arduino/historico/v6/README.md) | SPI con datos sintéticos |
| [V6 polling](../arduino/historico/v6_polling/README.md) | Acceso a registros SPI |
| [V6 DMA](../arduino/historico/v6_dma/README.md) | DMA SPI con espera por polling |
| [V6 IRQ](../arduino/historico/v6_irq/README.md) | Interrupciones y READY |
| [V6 ADC](../arduino/historico/v6_adc/README.md) | Integración de adquisición real y SPI |
| [V7 dual](../arduino/historico/v7_dual/README.md) | Selección de salida y control permanente |
| [V8 config](../arduino/historico/v8_config/README.md) | Perfil ADC configurable y generador DAC por DMA |

### Evolución reciente de V10

Configuración aplicada automáticamente en la franja principal, color por canal,
escalas editables y ajuste detalle/FPS. Generador en columna propia con dial,
formas de onda e intervalos de sweep/chirp; DAC A0, ADC A2/A3. FFT y heatmap
con hasta dos canales, log frecuencia, escalas enlazadas y margen estable.
Bode por pasos con asentamiento independiente, ciclos de medida, puntos por
década, hasta cinco curvas, relleno de área y referencia instrumental.

La referencia inicial fue invalidada por cableado incorrecto. La vigente es
el ensayo `20261003_123522_633848`: 20 Hz–20 kHz, ADC 16 bits / 50 kHz,
31/31 puntos, CSV continuo y restauración exacta. [Detalle](../diagnosticos/BODE_V10.md).
El panel WAV sigue pendiente. Los números Python y firmware son independientes.

### 4 de octubre: V11 + V9 Fast SPI

Nueva versión experimental de firmware, relay, receptor y monitor aislados.
SPI de 32 MHz, CRC más rápido y un único sellado por trama: 100 kHz por canal
a 14 bits pasó 120 s, casi 12 millones de pares sin discontinuidades ni errores
DMA. 125 kHz perdió nodos; 200/250 kHz no se probaron tras ese fallo. V11 ofrece
sólo 100 kHz como tasa nueva. La exactitud analógica de ambos canales queda
pendiente. V10 + V8 config siguen siendo el conjunto estable.
[Estudio y pruebas](../experimentos/tasas_spi/README.md).

### Archivos originales y documentación de época

[Inventario de monitores](../monitor/historico/README.md) ·
[Scripts Qt V1–V5 y programas iniciales](../monitor/historico) ·
[Inventario Arduino](../arduino/historico/README.md) ·
[README UART anterior](historico/README_uart_v5_v7.md) ·
[README original](historico/README_anterior.md).

---

## Historia anterior (instrucciones de época)

## De monitor serial a osciloscopio de dos canales

Los primeros receptores incluían una consola Python, un notebook y una interfaz
Tkinter/Matplotlib. Las versiones Qt incorporaron visualización de dos canales,
lectura de formatos de texto/CSV, controles de osciloscopio, trigger y mediciones.
La adquisición actual utiliza paquetes binarios DATA con timestamps y dos ADC;
el CSV se genera en el receptor para guardar las capturas.

Se conservan los [programas anteriores](../monitor/historico), el
[README original completo](historico/README_anterior.md), el
[inventario anterior](historico/INVENTARIO_anterior.md) y las
[notas de contexto del UNO Q](historico/CONTEXTO_UNO_Q_Codex.md).

## Adquisición por hardware y V4 a 20 kHz

En el Q, el temporizador dispara una secuencia ADC de dos canales; DMA mueve
las conversiones y captura los timestamps. El puente R4 se optimizó con una ISR
RX propia y transmisión por consulta del registro de salida. El conjunto V4/V6
se validó a 20 kHz por canal, con Q–R4 a 3 Mbps y R4–PC a 2 Mbps.

La [validación V4](../diagnosticos/VALIDACION_V4.md) documenta los problemas de
caudal previos, la solución y las pruebas de continuidad y grabación.

## V6/V7: fluidez y visibilidad

El receptor incorporó desplazamiento continuo suavizado, reducción visual que
conserva extremos y cortes, y preparación de trazas y mediciones con NumPy.
V7 añade los estilos Rápido, Intenso y Suave para elegir entre costo de dibujo
y visibilidad. Estos ajustes no reducen las muestras del CSV.

La [guía del monitor](../monitor/README.md) conserva los detalles de controles,
mediciones, grabación y pruebas de rendimiento. Los FPS dependen de la ventana,
el equipo y la carga de adquisición; son distintos de la frecuencia de muestreo.

## V5/V7: de 25 a 31,25 kHz — 30/09/2026

V5 comenzó con 25 kHz por canal y ambos enlaces a 3 Mbps. Para subir la tasa se
eligieron 31,25 kHz: corresponden a 32 µs enteros con la base de tiempo de 1 MHz.
La transmisión original del Q no sostuvo esa frecuencia sin saltos. Se ensayó
4 Mbps, sin recepción en esa prueba, y se volvió a 3 Mbps.

El cambio que pasó la validación fue transmitir desde el hilo del Q mediante
`uart_poll_out`, evitando la cola y las interrupciones TX del core. La adquisición
sigue usando temporizador, ADC y DMA; el envío es polling y ocupa CPU. Se mantuvo
el protocolo, la resolución ADC y el tiempo de adquisición de cada canal.

La prueba de 30 s recibió 936.448 pares sin saltos de timestamp ni pérdidas de
sincronización. V7 guardó 608.768 filas con todos los intervalos de 32 µs; con
50.000 muestras visibles y grabación, el contador final fue de unos 28,6 FPS en
Qt fuera de pantalla. Pasaron 30 pruebas automatizadas.

Los [resultados completos de V5](../diagnosticos/VALIDACION_V5.md) incluyen los
ensayos descartados, el respaldo anterior y los límites de la comprobación.
La [guía de V5](../arduino/historico/v5/README.md) describe configuración y restauración.

---

## Organización y operación del repositorio

Los siguientes apartados conservan la información del README principal anterior,
con enlaces ajustados y el estado de las placas actualizado al último ensayo.

[Características y uso del SerialMonitor](../monitor/README.md) ·
[README anterior completo](historico/README_anterior.md).

## Qué usar

| Conjunto | Firmware Q + R4 | Monitor | Muestreo | Q → R4 | R4 → PC | Estado |
|---|---|---|---|---|---|---|
| **Estable** | **V4** | **V6** | 20 kHz por canal | 3 Mbps | **2 Mbps** | Probado en las placas y CSV |
| Experimental | V5 | V7 | 31,25 kHz por canal | 3 Mbps | **3 Mbps** | Probado 30 s + CSV; ver validación V5 |

La versión experimental se elige explícitamente. Al cierre de la validación del
30/09/2026, las placas quedaron con V5 a 31,25 kHz y enlaces de 3 Mbps;
V4 se conserva en el repositorio y los respaldos para restaurarla.
Los números del firmware y del monitor son independientes: V4 se usa con V6.

## Abrir el monitor

```sh
python monitor/historico/v6/app.py                      # V6 estable
python monitor/historico/v7/app.py         # V7 experimental
python monitor/historico/v8/app.py         # USB directo del Q
```

Seleccionar el puerto **R4**. La V6 usa 2.000.000 baudios; V7 usa 3.000.000.
Instalar dependencias en el entorno elegido con `python -m pip install -r requirements.txt`.
En VS Code también están las tareas **Monitor V6: Abrir estable** y
**Monitor V7: Abrir experimental**, y las mismas opciones para ejecutar con F5.

## Dónde está cada cosa

```text
monitor/
  v6/app.py                   Monitor estable
  v7/app.py                   Monitor UART experimental
  v8/app.py                   Monitor USB directo, independiente
  historico/                  V1–V5, Tkinter, consola y notebook originales
arduino/
  v6_adc/                    Adquisición actual SPI y USB directo
  historico/v4/oscilloscope/            App Lab Q estable (sketch + Python + perfil)
  historico/v4/r4_bridge_v4/            Sketch R4 estable
  historico/v4/unoq.json                Destino de las tareas V4
  historico/v5/oscilloscope/            App Lab Q experimental
  historico/v5/r4_bridge_v5/            Sketch R4 experimental
  historico/v5/unoq.json                Destino independiente V5
capturas/                     Capturas existentes y nuevas de V6
  experimental_v7/            Capturas nuevas de V7
respaldos/                    Respaldo de firmware y exportaciones de App Lab
  unoq/                       Incluye la V3 original
diagnosticos/                Herramientas y resultados de validación
tests/                       Pruebas automatizadas
tools/                       Operaciones sobre el Q
docs/historico/              Documentación anterior, sólo referencia
```

## Firmware y versiones

[Guía Arduino y comandos](../arduino/README.md) ·
[Detalle V4 estable](../arduino/historico/v4/oscilloscope/README.md) ·
[Configuración V5](../arduino/historico/v5/README.md) ·
[Validación física V4](../diagnosticos/VALIDACION_V4.md) ·
[Validación física V5](../diagnosticos/VALIDACION_V5.md).

```sh
python3 tools/unoq.py status                  # por defecto, V4 estable
python3 tools/unoq.py compile --version v5    # compilar V5 sin cargar
```

Arduino IDE: los sketches del Sketchbook se llaman `r4_bridge_v4` y
`r4_bridge_v5`. Son copias de las carpetas versionadas del repositorio.
El código de referencia está aquí: después de editar en el IDE, incorporar
esos cambios a la carpeta de la versión correspondiente antes de desplegar.
El antiguo `DebuggerRtRx` se conserva como histórico a 1,1 Mbps.

Las familias V4 y V5 usan carpetas y destinos independientes de App Lab.
Sólo se marca estable tras compilar, medir continuidad y comprobar captura.
No promover una versión únicamente porque el gráfico se vea bien.

Pruebas: `python -m unittest discover -s tests`.

## 2 de octubre de 2026: monitor V9 con control Q y destino SPI/R4

Se completó el paso dos del plan con una versión independiente del monitor:
CONTROL Q por USB/ADB, DESTINO SPI/UART y PUERTO R4. El Q conserva control
y estado en ambos modos. Aplicar destino espera confirmación del MCU y
completa las muestras de la frontera antes de avanzar en gráfico y CSV.
La prueba física incluyó cambios en vivo y reconexiones en ambos modos:
712.192 pares recibidos y 475.136 filas CSV sin huecos.
[Guía de V9](../monitor/historico/v9/README.md) y [validación](../diagnosticos/MONITOR_V9.md).

## 2 de octubre de 2026: adquisición configurable V10

Se completó el paso tres con panel plegable para control Q, bits, tasa y salida SPI/UART. La vista principal refleja valores confirmados por el MCU. La app independiente V8 config mantiene DMA y admite 8/10/12/14 bits y once períodos enteros de 32 a 1000 µs. Cambiar bits/tasa reinicia captura y cierra CSV; cambiar sólo salida conserva continuidad. Pasaron 99 pruebas locales, 20 perfiles físicos y cinco CSV sin huecos ni errores de escala. [Guía](../monitor/historico/v10/README.md) y [validación](../diagnosticos/ADQUISICION_V10.md).

## 2 de octubre de 2026: tasas SPI superiores en V10

Se agregan 40, 50 y 62,5 kHz por canal exclusivamente por SPI. 40 kHz mantiene la ventana ADC larga; las otras dos usan 68 ciclos (1,7 µs). UART sigue limitado a 31,25 kHz tanto en interfaz como en MCU. El barrido a 100 kHz falló integridad y esa opción se retiró. [Ensayo físico y límites analógicos](../diagnosticos/TASAS_SPI_V10.md).

## 2 de octubre de 2026: zoom y render de V10

Se amplía el horizontal a 250.000 muestras (4 s a 62,5 kHz). Historial NumPy por lotes, reducción visual antes de escalones, preservación de extremos/cortes y transferencia de objetos Python entre hilos. Mediciones completas a 10 Hz. Ensayos físicos con CSV: 58,5 FPS de render a 9.000 muestras y 48,2 a 250.000, con Qt offscreen. [Evidencia y alcance](../diagnosticos/RENDER_V10.md).
# 4 de octubre de 2026 · Monitor V12 y firmware V11 P992

Promoción del candidato P992 a una pareja independiente: `monitor/historico/v12`,
`arduino/historico/v11_p992`, receptor propio y relay SCP1 V3/992. Hasta 125 kHz SPI
por canal; se conservan V11/100 kHz y V10. [Guía](../monitor/historico/v12/README.md)
y [evidencia del candidato](../experimentos/tasas_spi/opt125/README.md).

## 6 de octubre de 2026 · Monitor y audio

[Monitor V13](../monitor/historico/v13/README.md), PyQt6/Python 3.13, con grabación WAV
estéreo de A2/A3 y filtro DC opcional. [Q V12 Audio](../arduino/v12_audio/README.md)
añade reproducción L/R/Mix por A0 con remuestreo 20/40/50 ksps y amplitud en vivo.
Conectar recupera app y relay instalados; Preparar Q instala/actualiza el conjunto.
SINGLE conserva la FFT próxima al trigger de mayor energía y restaura el trigger
al volver a RUN. Chirp: corregido fin prematuro y 24 disparos físicos completos.
Portada organizada por funciones; versiones enlazadas al final. Respaldos `.bak`
agrupados en `respaldos/historico/`, sin modificar su contenido.
