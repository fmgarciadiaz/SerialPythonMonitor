# fergd · Osciloscopio y generador Arduino UNO Q

Un instrumento para generar señales, observar circuitos y analizar su respuesta.
Combina adquisición y generación por hardware con un monitor Python de dos
canales, análisis espectral, respuesta en frecuencia y grabación de señales.

## Qué hace

- Osciloscopio V(t) con trigger, RUN/STOP y captura SINGLE.
- FFT, heatmap y Bode de ganancia y fase.
- Generador de seno, cuadrada, triángulo y rampa; modos Sweep, Chirp y Pulso.
- Grabación CSV o WAV estéreo de A2/A3, con eliminación de DC opcional.
- Reproducción de archivos WAV por A0: selección L/R/Mix, remuestreo,
  conversión a 12 bits y ajuste de amplitud/offset entre 0 y 3,3 V.
- Adquisición configurable: 8/10/12/14 bits o 16 bits por oversampling.
  SPI hasta 125 kHz por canal; 16 bits hasta 62,5 kHz.

## Empezar

Desde la raíz del repositorio:

```sh
conda env create -f monitor/v13/environment.yml
conda activate Python_3_13_DataScience
python monitor/v13/app.py
```

Si el entorno ya existe, omitir su creación. Demo permite probar la interfaz
sin placa. Conectar intenta usar el enlace existente y, si no responde,
comprueba la app instalada y el relay e inicia lo que falte.
Preparar Q instala o actualiza la app MCU y el relay desde las fuentes del
proyecto; requiere un UNO Q con Linux, ADB y las herramientas Arduino operativas.

Valores iniciales: ADC 14 bits/40 kHz, amplitud 2 Vpp, offset 1,65 V y salida
apagada. Sweep y Chirp: 20 Hz→2 kHz en 2 s; se lanzan con Disparar.
Wav usa 50 mil muestras/s por defecto si el firmware lo admite.
Durante Play se activa la adquisición y se bloquea el cambio de perfil ADC;
la amplitud se puede ajustar durante la reproducción. Desconectar apaga la salida.

[Guía del monitor](monitor/v13/README.md) · [Instalación del Q](arduino/v12_audio/README.md)

## Cómo se conectan los componentes

| Componente | Función |
|---|---|
| PC / Python | Interfaz, análisis, archivos CSV/WAV y preparación del audio |
| MPU / Linux del UNO Q | App de App Lab y relay nativo USB/ADB ↔ SPI |
| MCU / STM32 del UNO Q | ADC A2/A3 y DAC A0, temporizadores y DMA |
| UNO R4 opcional | Puente UART de adquisición; el Q conserva el control |

El MCU adquiere A2/A3 y entrega los bloques por SPI al relay del MPU.
El relay los lleva por USB/ADB al receptor Python. Los comandos y los códigos
WAV viajan en sentido inverso: PC→relay→SPI→MCU; TIM6 y DMA alimentan el DAC A0.
El pequeño Python de App Lab mantiene la app; el relay es un proceso separado.

| Pin | Uso |
|---|---|
| A0 / DAC0 | Salida de 12 bits, 0–3,3 V |
| A2 / V_IN | Primera entrada / canal izquierdo de grabación |
| A3 / V_OUT | Segunda entrada / canal derecho de grabación |
| GND | Masa común |

[MCU y cableado](docs/UNO_Q_TECNICO.md) · [Relay y protocolos](docs/TRANSPORTE_TECNICO.md)

## Carpetas

| Carpeta | Contenido |
|---|---|
| [monitor](monitor/README.md) | Aplicación Python y receptor del PC |
| [arduino](arduino/README.md) | Sketch MCU, app MPU y relay de cada pareja |
| [transport](transport/README.md) | Herramientas y contratos de transporte compartidos |
| tools | Instalación, compilación y administración del Q |
| [docs](docs/README.md) | Guías técnicas e historia |
| [diagnosticos](diagnosticos/README.md) | Ensayos, informes y resultados físicos |
| [capturas](capturas/README.md) | Grabaciones e inventario de limpieza |
| audios | Archivos de audio para reproducción |
| [respaldos](respaldos/README.md) | Copias de fuentes y aplicaciones del Q |
| experimentos | Variantes aisladas y evidencia de desarrollo |

Las fuentes históricas se conservan en las carpetas `historico` de cada módulo.
Los entornos locales y cachés no forman parte de las fuentes.

## Documentación y validación

[Índice técnico](docs/README.md) · [Plan de trabajo](Plan%20de%20trabajo.md) ·
[Continuación](%23%20Continuar%20desde%20donde%20quedaste.md)

WAV a 40/50 ksps pasó ensayos de 120 s; 50 ksps también con ADC14/100 kHz.
La combinación WAV50/ADC125 está bloqueada por fallos observados.
[Resultados y límites](docs/WAV_TASAS.md).
La referencia Bode histórica corresponde al reloj ADC anterior y requiere
comprobación con el perfil actual. Los ensayos locales y los físicos se
identifican por separado en los informes.

## Versiones y enlaces

| Conjunto | Estado y documentación |
|---|---|
| [Monitor V13 · PyQt6](monitor/v13/README.md) + [Q V12 Audio](arduino/v12_audio/README.md) | Conjunto usado actualmente, con grabación y reproducción WAV |
| [Monitor V12 · PyQt5](monitor/v12/README.md) + [Q V11 P992](arduino/v11_p992/README.md) | Pareja anterior conservada, sin reproducción WAV |
| [Monitores históricos](monitor/historico/README.md) | Versiones anteriores archivadas |
| [Firmware histórico](arduino/historico/README.md) | Sketches y puentes anteriores |
| [Historia completa](docs/HISTORIA.md) | Evolución y catálogo del proyecto |

Las herramientas de consola conservan V11 P992 como valor predeterminado.
Para el conjunto de audio usar explícitamente `--version v12_audio` o
`--firmware v12_audio`. El monitor detecta la app instalada al conectar.
