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

ADC8 CH1 alcanza 1,818 MS/s con IPC compacto automático. La pareja instalada
pasó tres recorridos de 120 s con RADIO/A0, Scan, WAV y Synth20, y recuperación
de 10 s por cierre. Los cortes anteriores se conservan para seguimiento;
no implica estabilidad universal, FPS garantizados ni aceptación analógica.

[Uso y límites](../../docs/GUIA_V18.md) ·
[Arquitectura](../../docs/ARQUITECTURA_V18.md) ·
[Validación](../../docs/VALIDACION_V18.md).
