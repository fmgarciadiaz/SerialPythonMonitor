# Osciloscopio UNO Q · Monitor V10

La versión actual es **Python V10 + firmware UNO Q V8 config**. Permite elegir
Q de control, salida SPI o UART con R4, resolución, tasa, color de los canales
y detalle del gráfico desde la pantalla principal.

## Abrir la versión actual

```sh
python3 tools/usb_stream.py start
python monitor/v10/app.py
```

Las herramientas del Q seleccionan V8 config por defecto. Para compilar o
actualizar su aplicación:

```sh
python3 tools/unoq.py compile
python3 tools/unoq.py deploy
```

| Componente actual | Acceso |
|---|---|
| Monitor Python | [monitor/v10/app.py](monitor/v10/app.py) |
| Uso del monitor | [monitor/v10/README.md](monitor/v10/README.md) |
| Sketch UNO Q | [sketch.ino](arduino/v8_config/oscilloscope/sketch/sketch.ino) |
| Firmware y despliegue | [arduino/v8_config/README.md](arduino/v8_config/README.md) |
| Puente R4 para UART | [R4 V5](arduino/historico/v5/r4_bridge_v5/README.md) |

Pines actuales: **A0/DAC0 salida**, **A2/V_IN** y **A3/V_OUT** entradas.
El firmware debe actualizarse antes de usar este cableado.

ADC nativo de 8/10/12/14 bits, hasta 62,5 kHz por SPI. El modo 16 bits con
oversampling ×16 admite hasta 50 kHz SPI. UART admite hasta 31,25 kHz.
El selector FS muestra el período y la ventana de adquisición. Las ventanas
cortas requieren menor impedancia de fuente; la precisión analógica debe
validarse con el circuito real.

## Histórico y referencias

- [Monitores anteriores](monitor/historico/README.md): versiones hasta V9.
- [Firmwares anteriores](arduino/historico/README.md): incluye V6 ADC y V7 dual.
- [Plan de trabajo](Plan%20de%20trabajo.md).
- [Validación de oversampling y fallos conocidos](diagnosticos/OVERSAMPLING_V10.md).
- [Guía anterior completa](docs/historico/README_uart_v5_v7.md).

Las capturas, diagnósticos y respaldos conservan sus carpetas. Las versiones
históricas se mantienen con sus fuentes; sus identificadores siguen disponibles
mediante `tools/unoq.py --version VERSION`. VS Code muestra V10 como entrada
principal; las configuraciones anteriores están en `.vscode/historico/`.
