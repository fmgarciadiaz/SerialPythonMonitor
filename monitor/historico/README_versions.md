# SerialMonitor — características y uso

Osciloscopio de dos canales para PC, desarrollado con Python, PyQt5 y PyQtGraph.
Recibe las muestras del UNO Q a través del puente R4 (V6/V7) o directamente
por USB (V8) o con destino seleccionable (V9), permite visualizar señales,
medirlas y guardarlas en CSV.

![Vista del SerialMonitor en modo demo](../../assets/demo_screenshot.png)

Imagen de referencia del proyecto; la apariencia puede variar entre versiones.

El [README anterior completo](../../docs/historico/README_anterior.md) se conserva
como referencia de las versiones anteriores. Esta guía describe V6 y la base de V7.

## Versiones

- **V6 estable**: `v6/app.py`, compatible con firmware V4; baud USB 2 Mbps.
- **V7 experimental**: `v7/app.py`, punto de partida para firmware V5; baud USB 3 Mbps.
  Mantiene DATA; probada físicamente a 31,25 kHz con Q V5 y puente R4 V5.
- **[V8 experimental](v8/README.md)**: interfaz independiente con transporte directo del UNO Q
  por USB/ADB, CRC verificado en PC y capturas en `capturas/experimental_v8/`.
- **[V9: Q de control y SPI/R4](v9/README.md)**: paso dos, salida seleccionable
  sin desconectar el Q; cambios en vivo y CSV continuo. Capturas en
  `capturas/experimental_v9/`.
- **[V10: adquisición configurable](v10/README.md)**: bits, tasa, Q y salida dentro de un panel plegable; resumen confirmado en la vista principal. Capturas en `capturas/experimental_v10/`.
- `historico/`: archivos anteriores conservados, sin convertirlos ni modificar su contenido.

Cada versión se abre directamente desde la raíz: `python monitor/historico/v6/app.py`,
`python monitor/historico/v7/app.py`, `python monitor/historico/v8/app.py` o `python monitor/historico/v9/app.py`. Para adquisición configurable: `python monitor/historico/v10/app.py`.
V6 guarda en `capturas/`; V7 en `capturas/experimental_v7/`, independientemente
del directorio actual. La V7 es una copia de desarrollo separada: sus futuros
cambios no modifican V6.

## Características

### Adquisición y conexión

- Recepción serial binaria en un hilo separado de la interfaz.
- Dos canales simultáneos: V_IN y V_OUT, con sus valores ADC y timestamps de hardware.
- Selector de puerto con identificación USB del hardware y baudrate configurable.
- Visualización de la frecuencia de muestreo y del período entre muestras.
- Modo Demo de dos canales para explorar los controles sin conectar una placa.

La combinación estable Q V4 + R4 V4 + monitor V6 se probó a **20 kHz por canal**.
El monitor conecta al R4 a **2.000.000 baudios**. V5/V7 utiliza
3.000.000 hacia el PC y fue probada a 31,25 kHz por canal con TX directo en el Q.
Ver [resultados y alcance de la prueba](../../diagnosticos/VALIDACION_V5.md).

### Visualización

- Doble traza, selección de canales y canal activo para las mediciones.
- Escala y posición horizontal; eje en muestras o tiempo en microsegundos.
- Ventana horizontal ajustable de **50 a 50.000 muestras**: hasta 1,6 segundos
  a 31,25 kHz, o 2,5 segundos a 20 kHz. Apertura inicial: 9.000 muestras.
- Escala y posición vertical, con controles de ajuste y Auto-Set.
- Trazo **Step/ZOH** (retención de cada valor) o **Linear**.
- Corte automático por silencios para evitar unir datos separados por huecos.
- Desplazamiento continuo suavizado, con refresco objetivo cercano a 60 FPS.
- Antialiasing y reducción de puntos para señales densas: conserva extremos,
  orden y cortes; al ampliar, recupera el detalle de las muestras.
- Botones superiores alineados y controles de adquisición y grabación de igual altura.

El suavizado introduce un pequeño retraso visual de seguimiento. La reducción
de puntos afecta al dibujo; las mediciones y el CSV usan las muestras completas.
El antialiasing del trazo no elimina el aliasing de una señal ya muestreada.

V7 permite elegir el aspecto junto a **TRAZO**: **Rápido** (predeterminado,
1 píxel sin antialiasing), **Intenso** (2 píxeles sin antialiasing, mayor
visibilidad con mayor costo de dibujo) y **Suave** (1 píxel con antialiasing,
aspecto anterior). Se puede cambiar también en STOP sin mover la captura.
Estos ajustes afectan únicamente al dibujo.

V6 y V7 preparan los escalones, coordenadas y mediciones con operaciones NumPy
para reducir el costo de las ventanas grandes. En una prueba local con Qt fuera
de pantalla, dos trazas y una ventana de 50.000 muestras, el tiempo por cuadro
bajó de unos 66 ms a 16 ms. Es una comparación de renderizado con datos sintéticos;
los FPS durante adquisición dependen también de la carga del equipo. Se conservan
los vértices del trazado, los picos y los cortes, y no se reducen los datos del CSV.

### Trigger y controles de adquisición

- Modos Auto y Normal, y captura única **SINGLE**.
- Selección de flanco ascendente o descendente, con histéresis.
- Nivel de disparo ajustable y ajuste al **50 %** de la señal.
- Alineación temporal al disparo para comparar ciclos.
- RUN/STOP y desplazamiento por el historial adquirido.

### Mediciones

Para el canal seleccionado: máximo, mínimo, pico a pico, RMS, media y estimación
de frecuencia de la señal. La frecuencia de muestreo se calcula a partir de los
timestamps cuando están disponibles; la estimación de frecuencia por cruces
depende de la forma de onda y del tramo visible.

### Grabación CSV

- Botones RECORD y STOP REC, con contador de filas y tiempo de grabación.
- Parada automática de la grabación a los 30 segundos.
- Capturas separadas por **comas**, con **punto decimal** y encabezado.
- Columnas: `Muestra,Tiempo_us,ADC_IN,V_IN,ADC_OUT,V_OUT`.
- V6 guarda en `capturas/`; V7 en `capturas/experimental_v7/`.
- El analizador de capturas también admite archivos históricos con tabs o espacios.

`Muestra` es el índice dentro del paquete y se reinicia en cada bloque; para
comprobar continuidad de adquisición se deben revisar los timestamps.

## Inicio rápido

Desde la raíz del proyecto, usando el entorno Python con las dependencias:

```sh
python -m pip install -r requirements.txt
python monitor/historico/v6/app.py
```

1. Seleccionar el puerto del **R4** y dejar **2.000.000** baudios para V6/V4.
2. Conectar, o elegir Demo si se quiere explorar la interfaz sin hardware.
3. Ajustar escalas, posición y canal de medición.
4. Activar y ajustar el trigger según la señal; usar SINGLE para una captura única.
5. Usar RECORD y STOP REC para guardar las muestras en CSV.

Para abrir V7: `python monitor/historico/v7/app.py`.
No necesita modificar el código de V6: cada versión tiene su propia carpeta.

## Protocolo actual y documentación

V6/V7 reciben paquetes binarios `DATA`: cabecera de 7 bytes y muestras de 8 bytes
(timestamp uint32 en microsegundos y dos ADC uint16, little-endian).
El firmware actual envía 512 pares por paquete, con ADC de 14 bits.
Los formatos de entrada textual/CSV descritos en el README antiguo corresponden
a versiones históricas; el CSV actual es el formato de salida de las capturas.

- [Organización del proyecto](../../README.md).
- [Validación física a 20 kHz](../../diagnosticos/VALIDACION_V4.md).
- [Preparación experimental de 31,25 kHz](../../arduino/historico/v5/README.md).
- [README anterior con las características históricas](../../docs/historico/README_anterior.md).
