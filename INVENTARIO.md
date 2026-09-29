# Inventario y versiones del proyecto

Actualizado: 28 de septiembre de 2026.

## Qué usar actualmente

- **Firmware Q para desarrollo y despliegue:** `arduino/oscilloscope/sketch/sketch.ino`, copiado de la aplicación `Osciloscopio DMA_TXRX V2` por USB; conserva la sincronización DMA corregida y usa 1.100.000 baudios. La copia anterior se conserva en `respaldos/sketch_pre_applab.ino.bak`.
- **Monitor PC para probar:** `SerialMonitorAppQt_V6.py`, con desplazamiento suavizado y objetivo de unos 60 FPS. Validación visual con hardware pendiente.
- **Monitor PC estable anterior:** `SerialMonitorAppQt_V5.py`, conservado sin cambios.
- **Capturas normales:** `capturas/`.
- **Herramientas de diagnóstico:** `diagnosticos/`.
- **Resultados de diagnóstico:** `capturas/diagnosticos/`.

Los números V2–V6 son los nombres históricos de los programas, no versiones
publicadas con un esquema semántico. Las versiones anteriores se conservan en la
raíz. No ejecutar varias aplicaciones sobre el mismo puerto serial.

## Archivos y carpetas

| Ruta | Contenido y estado |
|---|---|
| `arduino/` | Fuentes de App Lab, configuración USB e instrucciones del entorno de desarrollo; ver `arduino/README.md`. |
| `tools/unoq.py` | Estado, compilación sin carga, respaldo, despliegue y logs del Q mediante ADB. |
| `respaldos/sketch_pre_applab.ino.bak` | Copia anterior del firmware normal UNO Q. ADC dual de 14 bits a 10 kHz; UART a 1 Mbaud; paquetes de 512 pares; dos nodos DMA de 2048 pares. Espera la transición real nodo 0 → nodo 1 antes de la primera entrega. Sin parada de diagnóstico. |
| `SerialMonitorAppQt_V6.py` | Basado en V5: temporizador preciso de 16 ms y posición visual suavizada en Roll en vivo (H-Pos = 0), con constante de 100 ms. Bordes suavizados, reducción visual por píxel conservando extremos y cortes, y barra superior en grilla con botones iguales. Conserva la adquisición; las capturas CSV nuevas usan comas y punto decimal. |
| `tests/test_v6_roll.py` | Pruebas sin Qt del desplazamiento, límites del buffer y conservación de adquisición, grabación y preparación de trazos respecto de V5. |
| `tests/test_v6_display.py` | Pruebas con NumPy de conservación de picos, orden, escalones y cortes durante la reducción visual. |
| `SerialMonitorAppQt_V5.py` | Monitor estable anterior PyQt5/PyQtGraph. Parser binario dinámico, dos canales, trigger, ejes muestras/tiempo y grabación tabulada de hasta 30 segundos. Crea `capturas/` automáticamente y guarda allí. |
| `SerialMonitorAppQt_V4.py` | Versión anterior con parser binario y control de trazo. Conservada como referencia; usar V5 para las capturas actuales. |
| `SerialMonitorAppQt_V3.py` | Versión histórica con recepción textual/CSV y columnas dinámicas. No usar para el flujo binario actual. |
| `SerialMonitorAppQt_V2.py` | Versión histórica de dos canales sobre texto/CSV. |
| `SerialMonitorAppQt.py` | Versión Qt base, monocanal y protocolo textual. |
| `SerialMonitorApp.py` | Monitor histórico con Tkinter y Matplotlib, recepción textual. |
| `SerialMonitor.py` | Script histórico por celdas para adquisición, análisis y exportación con pandas. No es el receptor binario vigente. |
| `SerialMonitor.ipynb` | Notebook histórico de adquisición y análisis interactivo. |
| `diagnosticos/analizar_captura.py` | Analiza seis columnas separadas por comas, tabs o espacios: índices, timestamps y posibles outliers ADC. Ver limitaciones debajo. Recibe la ruta del archivo por argumento. |
| `diagnosticos/recibir_diagnostico.py` | Recibe el stream del R4, guarda `.bin` y extrae el informe `.txt` del sketch de diagnóstico. Crea `capturas/diagnosticos/` automáticamente. |
| `diagnosticos/DebugRTRXread.py` | Receptor experimental histórico, fijado en 1000 muestras por paquete y ADC de 12 bits. No sirve tal cual para la configuración actual de 512 muestras y 14 bits. |
| `diagnosticos/diagnostico_dma/diagnostico_dma.ino` | Firmware instrumentado `startup_sync_v2`. Registra destinos/contadores DMA y tiempos de copia/envío; detiene adquisición ante anomalía temporal, escritura corta o plazo de unos 15 segundos. |
| `diagnosticos/diagnostico_dma/LEEME.md` | Pasos de la prueba e interpretación de campos del diagnóstico. |
| `capturas/` | CSV normales y subcarpeta de resultados de diagnóstico. Detalle de las capturas existentes debajo. |
| `respaldos/sketch_antes_sync.ino.bak` | Copia del firmware anterior a la corrección de sincronización inicial. Conservar para comparación; no cargar como versión actual. |
| `CONTEXTO_UNO_Q_Codex.md` | Transferencia histórica de las conversaciones y estado previo a esta investigación. Sus rutas y conclusiones pendientes reflejan aquel momento; consultar este inventario para el estado actual. Incluye el código del puente R4; no hay un sketch R4 separado en el proyecto. |
| `README.md` | Presentación, instalación y documentación histórica de la aplicación; enlaza a este inventario. |
| `requirements.txt` | Dependencias Python declaradas para el monitor. Los scripts históricos pueden requerir dependencias adicionales. |
| `assets/demo_screenshot.png` | Imagen de demostración usada en el README. |
| `.vscode/settings.json` | Configuración local de VS Code. |
| `.conda/` | Entorno Python local. No contiene código fuente del proyecto; su existencia no garantiza que estén instaladas todas las dependencias. |
| `__pycache__/` | Cachés generadas por Python para algunos programas. |
| `.git/` | Metadatos e historial del repositorio. |

## Capturas conservadas y resultados

| Archivo, relativo a `capturas/` | Resultado comprobado |
|---|---|
| `log_20260926_200237_001.csv` | Antes de corregir: 45.056 muestras; 22 timestamps adelantados exactamente 409.600 µs en 16 eventos. Dos picos aislados en ADC_IN con el criterio indicado debajo. |
| `diagnosticos/diagnostico_20260926_205200_626110.txt` y `.bin` | Primera prueba, sin sincronización corregida. Se leyó el nodo 0 cuando los DMA solo habían adquirido una muestra. Informe detenido por `1859 → 0`. |
| `diagnosticos/diagnostico_20260926_205816_557534.txt` y `.bin` | Prueba `startup_sync_v2`: primera entrega a 206.704 µs de TIM5; 290 paquetes, 148.480 muestras, todos los intervalos de 100 µs. Finalización por plazo sin anomalía temporal. |
| `log_20260926_210546_001.csv` | Firmware normal corregido: 48.640 muestras, 4,8639 segundos entre primera y última; todos los intervalos de 100 µs, sin picos aislados según el criterio indicado. Mejoría visual confirmada por el usuario. |

El criterio de pico aislado usado para comparar estas capturas fue: vecinos que
difieren como máximo 200 cuentas y muestra central desviada más de 500 cuentas
de su promedio. No demuestra ausencia de toda posible anomalía analógica.

El diagnóstico respaldó que las TC iniciales se interpretaban como un nodo
completado, desfasando el consumidor. La corrección espera observar ambos DMA
en nodo 0, limpia las TC iniciales y espera ambos en nodo 1 con nuevas TC antes
de entregar nodo 0. Se mantuvieron el protocolo, los tamaños, las funciones de
caché y el consumo posterior para aislar el cambio.

Pendiente: validar una captura normal de 30 segundos y repetir tras reinicios.
La corrección de arranque no agrega detección ni recuperación general de
sobrescrituras si el consumidor se demora durante una ejecución prolongada.

## Versiones de herramientas

- Hardware de adquisición: Arduino UNO Q / STM32U585; puente Arduino UNO R4.
- Core usado por el usuario: Arduino Zephyr **0.90.0**.
- Compilación local verificada: Arduino Zephyr **1.0.0**.
- Ambos sketches adaptan la firma de `LL_DMA_CreateLinkNode` a la declaración
  del header instalado: mutable en 0.90.0 y `const` en 1.0.0.
- Dependencias declaradas: pyserial ≥ 3.5, PyQt5 ≥ 5.15.0, pyqtgraph ≥ 0.12.0,
  numpy ≥ 1.20.0 y pandas ≥ 1.3.0. Son mínimos declarados, no versiones fijadas.

## Comandos habituales

Desde la raíz del proyecto, con el entorno Python correspondiente activado:

```bash
python3 SerialMonitorAppQt_V5.py
python3 diagnosticos/analizar_captura.py capturas/log_20260926_210546_001.csv
python3 diagnosticos/recibir_diagnostico.py
python3 diagnosticos/recibir_diagnostico.py /dev/cu.usbmodemXXXX
```

V5 y el receptor resuelven sus carpetas de salida respecto de la ubicación de
los scripts, incluso cuando se ejecutan desde otra carpeta. Los scripts
históricos conservan su comportamiento de exportación original.

Los CSV de V5 usan tabulaciones, aunque su extensión sea `.csv`. `Muestra` se
reinicia de 0 a 511 en cada paquete: no es un contador global del Q. El analizador
histórico usa esa columna para sus cálculos modulares, por lo que su informe de
fronteras de nodo puede ser engañoso. Tampoco sus outliers estadísticos distinguen
automáticamente transiciones reales de la señal cuadrada. No inferir pérdidas
ni corrupción solo de esas dos secciones.

Para cargar el firmware normal en el Q, usar `python3 tools/unoq.py deploy`;
el código vigente está en `arduino/oscilloscope/sketch/sketch.ino`. Para el diagnóstico, usar la carpeta `diagnosticos/diagnostico_dma/`.
No poner los dos sketches en una misma carpeta Arduino: sus funciones se duplican.
