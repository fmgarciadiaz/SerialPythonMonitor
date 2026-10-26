# Monitor V18

Osciloscopio, generador, RADIO/FILTER, FFT, heatmap, Bode, WAV y Synth20.

```sh
python -m monitor.v18 --gui
python -m monitor.v18 --self-test
```

No conecta al Q automáticamente. Seleccionar el dispositivo y usar Conectar;
«Preparar Q» verifica la pareja aceptada sin reinstalarla si ya coincide, o
actualiza una pareja existente con respaldo y recuperación. No sobrescribe
aplicaciones desconocidas ni ejecuta preparadores de otras versiones.

Código, receptor, DSP, utilidades y preparador están dentro de esta versión.
Las fuentes de su propia pareja del Q viven en `arduino/v18`. La verificación
AST de imports impide dependencias del proyecto fuera de `monitor.v18`.

ADC8 CH1 alcanza 1,860 MS/s con IPC compacto automático. Los nuevos perfiles
ADC8/10/14 pasaron 60 + 3×120 s aislados y GUI instalada de 120 s por formato
con RADIO/A0, Scan US, WAV y Synth20. Se conservan los métodos y tasas anteriores.
La aceptación de transporte y funcionalidad se distingue de la calidad analógica.

[Uso y límites](../../docs/GUIA_V18.md) ·
[Arquitectura](../../docs/ARQUITECTURA_V18.md) ·
[Validación](../../docs/VALIDACION_V18.md).

Tasas CH1 incorporadas: ADC10 1,355932 MS/s, ADC12 1,103448 MS/s,
ADC14 1000,000 kS/s y ADC16 (OS ×16) 150,943 kS/s. ADC16 dual conserva
76,227 kS/s por canal. Ver [campaña y límites](../../docs/SONDEO_TASAS_V18_20261025.md).

## Catálogo de tasas de adquisición

El selector ofrece una distribución compacta hasta el máximo de cada formato,
con anclajes de audio de aproximadamente 44,1/48/96/192 kHz. En 16 bits se
respetan los límites: 96 kHz sólo en CH1 y sin opción de 192 kHz.
El símbolo ≈ indica una tasa nominal; el tooltip muestra la tasa real del reloj.
La grabación WAV escribe la tasa real redondeada a Hz enteros.

Clic derecho en el selector → «Mostrar todas las tasas» recupera los perfiles
históricos. La tasa histórica seleccionada permanece visible al volver al
catálogo. No cambia el método de adquisición de esos perfiles.
[Evidencia y límites del catálogo](../../docs/CATALOGO_TASAS_V18_PLAN_20261025.md).
