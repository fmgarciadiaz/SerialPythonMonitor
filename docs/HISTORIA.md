# Historia y evolución del proyecto

[Volver a la presentación del proyecto](../README.md).

Este documento reúne la evolución del osciloscopio y los detalles de versiones,
organización y operación que antes estaban en el README principal. Los documentos
originales se conservan como referencia; sus rutas, velocidades y estados pueden
corresponder a etapas anteriores.

## De monitor serial a osciloscopio de dos canales

Los primeros receptores incluían una consola Python, un notebook y una interfaz
Tkinter/Matplotlib. Las versiones Qt incorporaron visualización de dos canales,
lectura de formatos de texto/CSV, controles de osciloscopio, trigger y mediciones.
La adquisición actual utiliza paquetes binarios DATA con timestamps y dos ADC;
el CSV se genera en el receptor para guardar las capturas.

Se conservan los [programas anteriores](../monitor/historico/), el
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
La [guía de V5](../arduino/v5/README.md) describe configuración y restauración.

---

## Organización y operación del repositorio

Los siguientes apartados conservan la información del README principal anterior,
con enlaces ajustados y el estado de las placas actualizado al último ensayo.

[Características y uso del SerialMonitor](../monitor/README.md) ·
[README anterior completo](../docs/historico/README_anterior.md).

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
python iniciar_monitor.py                      # V6 estable
python iniciar_monitor.py --version v7         # V7 experimental
python iniciar_monitor.py --list               # ver versiones sin abrir ventanas
```

Seleccionar el puerto **R4**. La V6 usa 2.000.000 baudios; V7 usa 3.000.000.
Instalar dependencias en el entorno elegido con `python -m pip install -r requirements.txt`.
En VS Code también están las tareas **Monitor V6: Abrir estable** y
**Monitor V7: Abrir experimental**, y las mismas opciones para ejecutar con F5.

## Dónde está cada cosa

```text
iniciar_monitor.py              Entrada única para abrir el monitor
monitor/
  v6/app.py                   Monitor estable
  v7/app.py                   Monitor experimental
  historico/                  V1–V5, Tkinter, consola y notebook originales
arduino/
  v4/oscilloscope/            App Lab Q estable (sketch + Python + perfil)
  v4/r4_bridge_v4/            Sketch R4 estable
  v4/unoq.json                Destino de las tareas V4
  v5/oscilloscope/            App Lab Q experimental
  v5/r4_bridge_v5/            Sketch R4 experimental
  v5/unoq.json                Destino independiente V5
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
[Detalle V4 estable](../arduino/v4/oscilloscope/README.md) ·
[Configuración V5](../arduino/v5/README.md) ·
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
