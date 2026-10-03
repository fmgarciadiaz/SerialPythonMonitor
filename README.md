# fergd · Osciloscopio y generador Arduino UNO Q

[![GitHub](https://img.shields.io/badge/GitHub-SerialPythonMonitor-181717?logo=github)](https://github.com/fmgarciadiaz/SerialPythonMonitor)
[![Último commit](https://img.shields.io/github/last-commit/fmgarciadiaz/SerialPythonMonitor?logo=github)](https://github.com/fmgarciadiaz/SerialPythonMonitor/commits)
[![Stars](https://img.shields.io/github/stars/fmgarciadiaz/SerialPythonMonitor?style=flat&logo=github)](https://github.com/fmgarciadiaz/SerialPythonMonitor/stargazers)
![Python](https://img.shields.io/badge/Python-PyQt5%20%7C%20NumPy-3776AB?logo=python&logoColor=white)
![Arduino](https://img.shields.io/badge/Arduino-UNO%20Q-00979D?logo=arduino&logoColor=white)

**Un instrumento para generar señales, observar circuitos y analizar su respuesta.**
El proyecto combina la adquisición y generación por hardware de Arduino UNO Q
con un monitor Python que funciona como osciloscopio de dos canales, analizador
de espectro y medidor de respuesta en frecuencia.

![Interfaz del monitor: demostración de dos canales](assets/monitor_v10_actual.png)

## Qué hace

- **Observa señales:** dos canales, trigger, RUN/STOP y SINGLE, escalas editables
  y colores independientes.
- **Genera estímulos:** seno, cuadrada, triángulo, rampa, pulso, sweep y chirp,
  con amplitud, frecuencia y duración configurables; de 0,1 Hz a 20 kHz.
- **Analiza frecuencias:** FFT instantánea, heatmap temporal y Bode de ganancia
  y fase, con ejes logarítmicos y comparación de hasta cinco barridos.
- **Configura la adquisición:** 8/10/12/14 bits nativos o 16 bits por oversampling;
  hasta 62,5 kHz por SPI, 50 kHz en 16 bits y 31,25 kHz por UART.
- **Guarda mediciones:** CSV con muestras y timestamps originales, independiente
  del nivel de detalle usado para dibujar.

## Módulo monitor · Python

El monitor reúne los controles y la visualización del instrumento. La columna
izquierda contiene el generador y los modos V/t, FFT, heatmap y Bode. En el
centro están conexión, configuración y gráfica; a la derecha, adquisición,
escalas y trigger. Las selecciones se aplican automáticamente al recibir la
confirmación del Q. El modo Demo permite explorar la interfaz sin placas.

FFT y Bode muestran un relleno translúcido bajo cada curva. Bode permite añadir
mediciones de distintos colores y aplicar una referencia instrumental compatible
con el perfil ADC. Los huecos sin lectura interrumpen el área rellenada.

[Uso y controles](monitor/v10/README.md) ·
[Funcionamiento técnico y esquemas](docs/MONITOR_TECNICO.md) ·
[FFT, heatmap y Bode](docs/FFT_V10.md)

## Módulo Arduino UNO Q · adquisición y generación

El MCU del UNO Q adquiere las dos entradas mediante temporizadores y DMA,
y genera la señal del DAC con un temporizador y DMA independientes. El Linux
del Q ejecuta un relay que transporta muestras y comandos hasta el PC por USB.
Puede enviarse la adquisición por SPI directo o por UART a un UNO R4 que actúa
como puente; el Q permanece conectado para controlar el instrumento.

| Conexión | Función |
|---|---|
| **A0 / DAC0** | Salida del generador de 12 bits |
| **A2 / V_IN** | Entrada de referencia del circuito |
| **A3 / V_OUT** | Lectura de la salida del circuito |
| **GND** | Masa común |

[Instalación del firmware](arduino/v8_config/README.md) ·
[Cableado, temporizadores y DMA](docs/UNO_Q_TECNICO.md) ·
[Relay y protocolos](docs/TRANSPORTE_TECNICO.md)

## Probar el proyecto

Versión actual: **monitor V10 + firmware UNO Q V8 config**. Con el firmware y
relay instalados, ejecutar desde la raíz:

```sh
python -m pip install -r requirements.txt
python3 tools/usb_stream.py start
python monitor/v10/app.py
```

Elegir CONTROL Q, ENLACE y Conectar, o pulsar Demo (2 CH) para usar señales
sintéticas. La captura de portada muestra esa demostración.

## Versiones, historia y documentación

| Recurso | Contenido |
|---|---|
| [Historia completa](docs/HISTORIA.md) | Evolución y catálogo de versiones Python y firmware |
| [Monitores históricos](monitor/historico/README.md) | Programas iniciales y versiones anteriores a V10 |
| [Arduino histórico](arduino/historico/README.md) | Firmwares y puentes anteriores a V8 config |
| [Documentación técnica](docs/README.md) | Guías de cada componente, esquemas y protocolos |
| [Validación Bode](diagnosticos/BODE_V10.md) | Ensayos físicos, referencia vigente y límites |
| [Plan de trabajo](Plan%20de%20trabajo.md) | Estado del proyecto y próximos pasos |

La referencia vigente cubre 20 Hz–20 kHz con ADC de 16 bits / 50 kHz.
Las ventanas ADC cortas requieren menor impedancia de fuente; la salida de
16 bits por oversampling no cambia la resolución de 12 bits del DAC.
[Detalles de adquisición](docs/CONFIGURACION_ADQUISICION.md) y
[límites del generador](docs/GENERADOR_PASO4.md).

La grabación y reproducción WAV es el próximo paso del plan y todavía no está
implementada. Fuentes históricas, capturas y diagnósticos se conservan separados
de los módulos activos.
