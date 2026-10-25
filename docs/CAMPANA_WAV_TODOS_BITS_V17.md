# WAV: matriz de estabilidad por bits · 21/10/2026

El usuario cerró V17 y se completó la matriz física de60s por caso,
selección Vivaldi conRADIO/1,6MHz y controlesSeek/Stop/EOF/replay.
[Resumen de evidencias](../diagnosticos/resultados_v17/wav_radio_validation_20261021_review.json).

La reproducción WAV pública limita la adquisición a100kHz. Se conserva esa
protección; los máximos de adquisición/RADIO no están calificados para WAV.

| Bits | Adquisición solicitada | Salida WAV |
|---|---:|---:|
| 8 | 100000Hz | 50000Hz |
| 10 | 100000Hz | 50000Hz |
| 12 | 100000Hz | 50000Hz |
| 14 | 100000Hz | 50000Hz |
| 16 | 76226Hz | 50000Hz |

Los cinco casos pasan la validación local de `Configuration`.100kHz es un
perfil legacy soportado por el firmware, oculto en el selector normal; se
expone sólo en la ventana diagnóstica con esa etiqueta. No es una nueva
opción pública ni una tasa promovida. Archivo inicial: `audios/vivaldi.wav`,229,785s. Su duración permite
ensayos de60/120s sin confundir EOF legítimo con un corte.

## Runner preparado

`diagnosticos/probar_wav_playback_v17.py` admite `--stability-matrix` y
`--case BITS ADC_HZ AUDIO_HZ`. Valida la matriz y metadatos antes de acceder
al Q; rechaza casos de reproducción que omiten el límite público.

- Detiene la campaña al primer caso fallido y devuelve un código de salida
  distinto de cero; conserva el informe también si falla la restauración.
- Los callbacks capturan su ventana, worker y caso, evitando atribuir señales
  tardías a la siguiente combinación.
- La traza WAV incorpora RID de envío y ACK; el callback de selección registra
  su duración, junto con pausas GUI y diagnóstico de entrega.
- `--analysis-audit` cuenta Paint/exposición reales durante reproducción;
  `--keep-visible` mantiene arriba sólo la ventana de diagnóstico.
- El ensayo Seek/EOF usa la duración real del archivo y el cabezal actual,
  en vez del salto fijo175s que no alcanzaba el final de Vivaldi.
- Restauración: identidad comprobada a baja carga, luego ajustes originales
  y10s de recuperación. Ninguna consulta administrativa posterior a restaurar
  una configuración alta. Si el worker sigue activo, no abre otra conexión.

## Secuencia ejecutada

Un solo propietario del Q, V17 cerrado. Usar el Python3.13/Cocoa habitual.

1. Selección sin Play a8bits/1,6MHz, Vivaldi/50kHz y RADIO encendida, para
   comprobar el caso reportado de carga del archivo.
2. Matriz de cinco casos a60s; detenerse ante el primer fallo real.
3. Ampliar sólo los casos que requieran evidencia adicional; una pasada corta
   no constituye calificación sostenida ni prueba de holgura.

```sh
QT_QPA_PLATFORM=cocoa python diagnosticos/probar_wav_playback_v17.py --select-only --source audios/vivaldi.wav --radio --trace --keep-visible
QT_QPA_PLATFORM=cocoa python diagnosticos/probar_wav_playback_v17.py --stability-matrix --seconds 60 --source audios/vivaldi.wav --trace --analysis-audit --keep-visible
```

## Verificación offline

14tests WAV pasan en Python3.13: contratos PCM/seek, capacidad, grabación,
matriz y auditoría visual. Pycompile y revisión de whitespace pasan.
La inspección de cabecera local tardó aproximadamente0,5ms en Imperial
y0,4ms en Vivaldi. Eso no reproduce ni descarta una pausa de GUI bajo carga.

No se modificaron firmware, relay ni lógica de reproducción de producción.

## Resultados físicos

Selección Vivaldi sinPlay,8bits/1,6MHz conRADIO: pasa, callback1,684ms,
sin errores ni pérdidas; máximo retrasoGUI290,213ms. No reproduce el fallo
original y no lo descarta.

La primera matriz tuvo cinco reproducciones sin cortes, pero su informe
global falló por excepciones GUI: el runner seleccionaba índice−1 al buscar
100kHz en el combo normal. Se conservó ese intento, se corrigió sólo el
selector del diagnóstico y se agregó un test con los widgets reales. Los
errores globales ahora detienen también la campaña.

[La matriz corregida](../diagnosticos/resultados_v17/wav_playback_20261021_122907/report.json)
completó los cinco casos y salió con código0, sin errores globales ni ADC.
Todos tuvieron gráfico100%visible.

| Bits | Paint/s | Reserva DAC mínima observada |
|---|---:|---:|
| 8 | 55,67 | 240ms |
| 10 | 53,02 | 192ms |
| 12 | 54,50 | 211,2ms |
| 14 | 52,62 | 163,2ms |
| 16 | 57,59 | 153,6ms |

Son mínimos de snapshots deACK, no garantía de reserva continua ni aprobación
de holgura de transporte.60s es un screening, no calificación prolongada.

[Controles conVivaldi](../diagnosticos/resultados_v17/wav_playback_20261021_123525/report.json):
avanzar, retroceder,Stop,replay,salto próximoalEOF,EOF,reinicio yStopfinal
pasan a16bits/76226 yWAV50kHz. Gráfico100%visible durante reproducción.

Restauraciones verificadas: configuración previaADC8/1,6MHz, generadorOFF,
identidad96685… igual antes/después y10s finales sin dropped/fatal. No se
observó el falloQt/SIP al finalizar estas corridas; sigue siendo una incidencia
intermitente abierta. La lógica de reproducción de producción no cambió.
