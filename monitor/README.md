# Monitor Python

Interfaz de osciloscopio, generador, FFT, heatmap, Bode y grabación CSV/WAV.
El receptor de cada aplicación corre en el PC; el relay corre en Linux del Q.

```sh
conda activate Python_3_13_DataScience
python monitor/v15/app.py
```

[Controles y uso](v15/README.md) · [Arquitectura](../docs/MONITOR_TECNICO.md)

[Wav y Synth](../README.md#wav--grabación-y-reproducción) · [Motor Synth](../docs/SYNTH.md)

## Versiones

- [V15 / Synth](v15/README.md): FM, tres osciladores, MIDI y modelos físicos de guitarra/piano; 40 kHz experimental.
- [V14 / PyQt6](historico/v14/README.md): archivada con Spectrum, Power, Distortion y Transfer en FFT.
- [V13 / PyQt6](historico/v13/README.md): archivada; audio con firmware Q V12 Audio.
- [V12 / PyQt5](historico/v12/README.md): archivada con Q V11 P992.
- [Histórico](historico/README.md): versiones anteriores archivadas.
- [Historia completa](../docs/HISTORIA.md).
