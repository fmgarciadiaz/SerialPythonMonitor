# Monitor de osciloscopio y análisis espectral

Interfaz PyQt6 para dos entradas A2/V_IN y A3/V_OUT, generador A0,
trigger/SINGLE, FFT, heatmap, Bode y grabación/reproducción CSV/WAV.
Esta variante conserva los protocolos, perfiles ADC y firmware del monitor anterior.

## Inicio

```sh
conda activate Python_3_13_DataScience
python monitor/historico/v14/app.py
```

Para instalar el entorno en otra computadora:

```sh
conda env create -f monitor/historico/v14/environment.yml
```

VS Code incluye tareas y configuraciones de depuración para este monitor.
Conectar utiliza el enlace disponible y comprueba/inicia app y relay cuando hace falta.
Preparar Q instala o actualiza V13 Pulse, con audio y pulsos desde 100 µs,
incluyendo app, firmware MCU y relay. Al iniciar aplicaciones detenidas se prioriza
V13 Pulse; Conectar reutiliza una conexión activa sin cambiar su firmware.
Antes de preparar aparece un aviso: puede tardar varios minutos. El relay se
reutiliza si ya existe el binario correspondiente a las mismas fuentes; solo se
compila cuando falta. La validación y carga del MCU y el respaldo siguen activos.
La variable `MONITOR_V13_WAV_FIRMWARE=v12_audio`
se mantiene por compatibilidad con las herramientas de audio.

## Selección FFT

Elegir **FFT** en «Modo» y seleccionar a su derecha:

| Análisis | Qué muestra |
|---|---|
| Spectre | Magnitud, fase, picos y frecuencia dominante |
| Power | PSD, piso de ruido, potencia por bandas y SNR |
| Distort | Armónicos, THD, THD+N y SINAD |
| Transfer | Relación V_OUT/V_IN, ganancia y fase, coherencia y retardo de grupo |

El panel inferior «Medición» muestra las estadísticas del análisis elegido.
Su selector permite elegir V_IN o V_OUT, incluso si ese canal no está dibujado.
En Transfer indica OUT / IN y analiza ambas entradas juntas. Los detalles de
picos, armónicos y unidades están en los tooltips; las curvas quedan libres de
textos estadísticos. V(t) recupera sus mediciones y su selección de entrada.

La entrada de cada gráfico se elige en su encabezado, con V_IN, V_OUT o
Ninguno. Estos selectores también están en Heatmap; Transfer y Bode mantienen
la relación fija entre las entradas.

La cantidad de muestras se elige en los ajustes FFT. Heatmap mantiene su
selector de muestras. El análisis completo se conserva aunque el dibujo reduzca
los puntos para ajustarse al ancho de pantalla.

![Spectre con dos entradas sintéticas](../../../assets/monitor_fft_spectrum.png)

Capturas con datos sintéticos, sin placa:
[Power](../../../assets/monitor_fft_power.png) ·
[Distort](../../../assets/monitor_fft_distortion.png) ·
[Transfer](../../../assets/monitor_fft_transfer.png).

[Definiciones, algoritmos y límites](../../../docs/FFT_ANALISIS.md) ·
[Resultados de pruebas y tiempos](../../../diagnosticos/FFT_V14.md).

## Funciones conservadas

ADC 14 bits/40 kHz al iniciar; 16 bits por oversampling hasta 62,5 kHz.
SPI hasta 125 kHz por canal según perfil. Generador inicialmente apagado,
amplitud 2 Vpp y offset 1,65 V. Wav reproduce a 50 kHz por defecto cuando el
firmware instalado lo admite; cambiar el análisis no cambia el perfil del ADC.

Las capturas se guardan en `capturas/v14/`. Assets, receptor y referencias Bode
están en esta carpeta. Las referencias copiadas conservan identidad instrumental,
perfil y método originales; no son una nueva calibración física ni se aplican
automáticamente al modo FFT Transfer.

[Uso de los controles conservados](../v13/README.md) ·
[Arquitectura del monitor](../../../docs/MONITOR_TECNICO.md) ·
[Relay y MCU](../../../arduino/README.md).

## Verificación

```sh
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests/v14 -v
```

Las pruebas sintéticas comprueban cálculos y controles; no sustituyen la
validación del instrumento y de su ruido/distorsión con hardware.

## Versiones

- [Monitor V14](app.py): cuatro modos de análisis FFT.
- [Monitor V13](../v13/README.md): referencia conservada.
- [Histórico](../README.md).
