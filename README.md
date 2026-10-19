# SerialPythonMonitor · UNO Q · V17

Osciloscopio, generador y receptor AM para Arduino UNO Q. Adquiere CH1/A2 y CH2/A3, genera por A0 y ofrece vista temporal, FFT, heatmap, Bode, filtros y audio WAV. El monitor Python se conecta por USB/ADB con el relay Linux y el firmware STM32.

**[Estado vigente, límites y pendientes](docs/ESTADO_ACTUAL_V17.md)** · [Documentación](docs/README.md) · [Plan](Plan%20de%20trabajo.md)

## Iniciar

Desde la raíz del proyecto:

```sh
conda env create -f monitor/v17/environment.yml
conda activate Python_3_13_DataScience
python monitor/v17/app.py
```

Si el entorno ya existe, omitir su creación. Demo permite explorar la interfaz sin placa. V17 usa su pareja MCU/app/relay V17; Conectar comprueba el enlace. Preparar Q instala fuentes y firmware y modifica la placa; no hace falta para un cambio de documentación.

Las herramientas de consola todavía usan V16 por defecto. Seleccionar V17 explícitamente:

```sh
python tools/unoq.py status --version v17
python tools/usb_stream.py start --firmware v17
```

## Capacidades actuales

| Área | Alcance |
|---|---|
| Entradas | CH1/A2 y CH2/A3, rango nominal 0–3,3 V; ADC 8/10/12/14 bits y 16 por oversampling |
| Muestreo | Perfiles CH1 y dual según bits; ADC8 CH1 hasta 1,6 MS/s |
| Generador | A0: seno hasta 150 kHz, cuadrada hasta 200 kHz, triángulo/rampa hasta 50 kHz; frecuencias intermedias |
| RADIO AM | Sintonía según Fs, Scan, US/alias, bandas RF, gain manual/auto hasta ×80 |
| Salida Radio | RADIO o FILTER hacia A0, con volumen y offset |
| FILTER | Selector de entrada, rechazo de banda y presets; OFF sin procesamiento de filtro |
| Análisis | Temporal, FFT, heatmap y Bode con referencia/respuesta seleccionables |
| WAV | Lectura y grabación; salida A0 a 20/40/50 kHz bajo restricciones del perfil |

Las tasas de muestras no certifican ancho de banda analógico. La integridad del transporte, la holgura, la calidad analógica y el comportamiento con RADIO/WAV simultáneos se validan por separado. Persisten incidencias de GUI atrasada y cortes de audio: ver el estado vigente antes de elegir un perfil exigente.

Para Bode, CH1 debe medir el estímulo en la entrada del circuito y CH2 su salida, con masa común. Una antena en CH1 no proporciona esa referencia. Tonos y Sweep/Chirp permiten hasta 150 kHz; Pulso hasta 200 kHz, siempre por debajo de 0,45 × Fs. La ampliación de Bode aún necesita validación física a esas frecuencias.

## Archivos del proyecto

| Carpeta | Uso |
|---|---|
| `monitor/v17`, `arduino/v17`, `tests/v17` | Implementación activa y sus pruebas |
| `monitor/v16`, `arduino/v16` | Respaldo local anterior |
| `monitor/historico`, `arduino/historico` | Versiones anteriores |
| `docs` | Guías actuales e informes fechados; historia en `docs/historico` |
| `diagnosticos` | Herramientas de ensayo y resultados |
| `experimentos` | Candidatos aislados y evidencia; no equivalen a producción |
| `respaldos` | Exportaciones recuperables y fuentes de referencia |
| `audios`, `capturas`, `calibraciones`, `assets` | Recursos y datos conservados |

En el Q sólo queda Scope V17 como app de usuario. Las anteriores se exportaron antes de eliminarlas; los ejemplos Arduino se conservan. [Inventario y restauración](arduino/APPS_APPLAB.md).

[Monitor](monitor/v17/README.md) · [Firmware](arduino/v17/README.md) · [Arquitectura](docs/ARQUITECTURA.md) · [Organización](docs/ORGANIZACION.md) · [Generador ampliado](docs/GENERADOR_200K_V17.md)

La presentación anterior, incluidas imágenes y secciones Synth/V16, se conserva en el [README histórico](docs/historico/README_v16_20261019.md).
