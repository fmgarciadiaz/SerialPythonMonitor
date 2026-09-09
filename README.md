# ⚡ Serial Python Monitor & Digital Oscilloscope

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GUI PyQt5](https://img.shields.io/badge/GUI-PyQt5%20%2B%20PyQtGraph-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Un osciloscopio digital y monitor serial de alto rendimiento en tiempo real desarrollado en **Python**, **PyQt5** y **PyQtGraph**. Diseñado para adquirir, visualizar y analizar señales analógicas y digitales provenientes de microcontroladores (**Arduino, ESP32, STM32, Raspberry Pi Pico**) a velocidades de hasta **921.600+ baudios** sin pérdida de paquetes ni retraso de acumulación.

---

## 🌟 Características Principales

- 🚀 **Adquisición Serial de Cero Latencia**:
  - Lectura en bloques binarios directos (`read(in_waiting)`) desacoplada en un hilo de trabajo (`QThread`).
  - Capaz de procesar más de **500.000 líneas por segundo** sin congelar la interfaz ni acumular retardo en el buffer del sistema operativo.

- 🎛️ **Panel Frontal de Osciloscopio Digital**:
  - **Controles Rotativos (`QDial`)**:
    - **Horizontal**: Escala de tiempo / muestras visibles (50 a 20.000 muestras, por defecto 9.000 smp) y desplazamiento de posición ($H\text{-}Pos$).
    - **Vertical**: Escala de amplitud de tensión ($V/div$) y desplazamiento de offset ($V\text{-}Pos$).
    - **Trigger**: Nivel de disparo con perilla y arrastre directo de la línea indicadora en el gráfico.
  - **Botón Auto-Set**: Restablece instantáneamente las escalas a los valores estándar de visualización.

- 🔒 **Motor de Trigger de Precisión**:
  - **Modos de Adquisición**: `Auto`, `Normal` y `⚡ SINGLE SHOT` (captura única con parada automática `STOP`).
  - **Tipos de Flanco**: Ascendente (↑) y Descendente (↓) con histéresis anti-ruido (*Schmitt Trigger*).
  - **Fase Fija y Estable ($T=0$)**: La señal se ancla en el punto de disparo relativo para mantener la onda completamente estática y congelada en pantalla como un osciloscopio de laboratorio.
  - **Botón `50% (Auto)`**: Calcula en tiempo real el punto medio de la señal ($V_{mid} = \frac{V_{max} + V_{min}}{2}$) y sitúa el nivel de disparo con un solo clic.

- 📊 **Barra de Mediciones en Vivo**:
  - Cálculo automático en tiempo real sobre la ventana visible:
    - **$V_{\text{MAX}}$**: Tensión máxima observada.
    - **$V_{\text{MIN}}$**: Tensión mínima observada.
    - **$V_{\text{P-P}}$**: Tensión pico a pico ($V_{max} - V_{min}$).
    - **$V_{\text{RMS}}$**: Valor eficaz cuadrático medio real ($V_{rms} = \sqrt{\frac{1}{N} \sum V_i^2}$).
    - **$V_{\text{MEDIA}}$**: Valor medio / componente continua ($V_{avg} = \frac{1}{N} \sum V_i$).
    - **$\text{FRECUENCIA}$**: Estimación física de frecuencia en $\text{Hz}$ / $\text{kHz}$ utilizando timestamps reales en microsegundos o cruces por cero.

- 🔌 **Conectividad Inteligente**:
  - Detección y filtrado automático de puertos seriales USB (`Arduino Uno WiFi R4`, `CH340`, `FTDI`, `CP210x`, etc.).
  - Soporte de baudrates configurables (`9600`, `115200`, `921600`, etc.).

- 🧪 **Modo Demo Integrado**:
  - Generador de señal de carga y descarga $RC$ incorporado para probar todas las funciones (escalas, trigger, mediciones) sin necesidad de conectar hardware físico.

---

## 📁 Estructura del Repositorio

```text
.
├── SerialMonitorAppQt.py   # Aplicación principal GUI (Osciloscopio PyQt5 + PyQtGraph)
├── SerialMonitorApp.py     # Versión alternativa liviana con Tkinter / Matplotlib
├── SerialMonitor.py        # Script en consola para captura y exportación a pandas
├── SerialMonitor.ipynb     # Jupyter Notebook interactivo para análisis de datos
├── requirements.txt        # Dependencias de Python necesarias
└── README.md               # Documentación del proyecto
```

---

## 🛠️ Instalación y Requisitos

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/SerialPythonMonitor.git
cd SerialPythonMonitor
```

### 2. Crear entorno virtual (Recomendado)
```bash
python3 -m venv venv
source venv/bin/activate  # En Linux/macOS
# venv\Scripts\activate   # En Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## 🚀 Uso Rápido

Para iniciar la aplicación de osciloscopio:
```bash
python SerialMonitorAppQt.py
```

### Pasos dentro de la interfaz:
1. **Conexión**: Selecciona el puerto serial detectado y el baudrate (por defecto `921600`).
2. **Adquisición**: Haz clic en **"Conectar"** (o en **"Demo"** para simulación).
3. **Escala**: Gira las perillas **ESCALA H** y **ESCALA V** para ajustar la ventana visible.
4. **Trigger**:
   - Marca la casilla **"ACTIVAR TRIGGER"**.
   - Haz clic en **"50% (Auto)"** para anclar la señal de forma inmediata.
   - Utiliza **"⚡ SINGLE"** para capturar eventos transitorios únicos.
5. **Mediciones**: Observa las tarjetas inferiores para verificar $V_{max}, V_{min}, V_{rms}$ y frecuencia instantánea.

---

## 📡 Formatos de Datos Serial Compatibles

El parser interpreta automáticamente flujos CSV con diferentes estructuras:

1. **4 Columnas (Estándar de Laboratorio con Estado y Tiempo)**:
   ```text
   estado,muestra,tiempo_us,adc
   ON,1,1024,3100
   ON,2,1540,3250
   OFF,3,2050,1200
   ```
2. **3 Columnas (Muestra, Tiempo, ADC)**:
   ```text
   100,50200,2048
   101,50700,2080
   ```
3. **1 Columna (Valor directo de ADC o Tensión)**:
   ```text
   2048
   2100
   1950
   ```
4. **N Columnas (Multi-canal)**:
   Cualquier cantidad de columnas numéricas separadas por coma son asignadas dinámicamente como canales activables en la interfaz.

---

## 💻 Ejemplo de Código para Arduino (921600 Baudios)

```cpp
// Ejemplo de transmisión serial ultrarrápida para Arduino / ESP32
void setup() {
  Serial.begin(921600);
  analogReadResolution(12); // Para placas de 12 bits (ADC 0-4095)
}

unsigned long sample = 0;

void loop() {
  sample++;
  unsigned long t_us = micros();
  int adc_val = analogRead(A0);
  
  // Enviar en formato: muestra,tiempo_us,adc
  Serial.print(sample);
  Serial.print(",");
  Serial.print(t_us);
  Serial.print(",");
  Serial.println(adc_val);
  
  delayMicroseconds(400); // Tasa ~2.5 kHz
}
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más detalles.

