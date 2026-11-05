# Validación del monitor de escritorio

El monitor PySide6 y la pareja independiente Scope V19 están instalados en el Q.
El firmware y relay coinciden con el recibo aceptado; V17 y V18 se conservaron.
La aceptación de campo cubre la adquisición inicial y el smoke descritos abajo,
no todas las tasas, bits, modos de análisis ni la respuesta analógica. Estado y
respaldos en [Versiones](VERSIONES.md) y [Preparar Q V19](PREPARAR_Q_V19.md).

## Ejecución y dependencias

```sh
./tools/run_v19.sh
python -m monitor.v19 --gui
python -m monitor.v19 --self-test
```

Se utiliza Python 3.13, PySide6 6.11.2, pyqtgraph 0.14.0, NumPy 2.3.1,
SciPy 1.16.0, pyserial 3.5, Numba 0.62.1, mido 1.3.3 y python-rtmidi 1.5.8.
Las dependencias se declaran en [requirements](../monitor/v19/requirements.txt)
y [environment.yml](../monitor/v19/environment.yml). Cada binding Qt corre en
su propio proceso; no se importan PyQt y PySide juntos.

## Resultados disponibles

- La regresión automatizada completa pasó **354 pruebas** con Python 3.13
  (`python -m monitor.v19 --self-test`, con loopback local habilitado).
  Incluye dos regresiones nuevas para cursores sobre ventanas largas y para
  restaurar la cadencia de refresco al cambiar de vista.
- La comparación visual determinista cubre diez vistas: V(t), generador, FFT,
  heatmap, Bode, FILTER, WAV, Synth, Radio recortada y Generador Radio. Seis
  coinciden píxel por píxel; cuatro (V(t), generador, WAV y Synth) presentan
  2,17 % de píxeles distintos por encima de 20 niveles y MAE 1,07.
  El resultado global queda `ok: false`; no se debe anunciar identidad visual
  total. El comparador informa igualdad exacta y tolerancia por separado.
  La diferencia está en el área temporal: V18 aplica `padding=0.02` al eje X,
  y V19 usa `padding=0` para quitar los márgenes vacíos del 2 % que aparecían
  en V(t). Cambian la ubicación de ticks y la extensión horizontal del trazo;
  es una corrección deliberada, por eso las cuatro vistas que muestran V(t) no
  coinciden píxel por píxel. Los demás modos comparados sí coinciden.
- En la prueba física de la pareja normal V19, ADC8 CH1 a 1,860 MS/s sostuvo
  adquisición durante 120 s: 255.876 frames, cola pico 2, cero nodos perdidos,
  fatales o errores SPI. El BIN de firmware y el relay coincidieron con la
  pareja V18 aceptada; el perfil original se restauró y V17 quedó verificada
  por su primer frame. Esto valida sólo ese perfil de adquisición; no demuestra
  igualdad de FPS ni califica todos los modos de la GUI V19.
- La primera instalación `Scope V19` desde Preparar Q pasó verificación de
  fuentes, firmware, relay, entorno y recuperación durante 10,03 s (313.344
  muestras; cero pérdidas/fatales). Reporte:
  [prepare_q report](../diagnosticos/resultados_v19/prepare_q_20261027/report.json).
- El smoke de GUI mantuvo V19 expuesta mientras adquiría ADC8/1,860 MS/s y
  dibujaba FFT de 16.384 puntos: 46,15 millones de muestras, 744 eventos Paint,
  cola GUI pico 3, sin errores; A0 permaneció apagada y el cierre confirmó la
  restauración. Esto es una prueba acotada de interfaz, no aceptación visual
  manual de todos los paneles. [Evidencia](../diagnosticos/resultados_v19/prepare_q_20261027/gui_fft_smoke.json).
- RADIO/A0 en el mismo perfil: Scan normal completó con 64 candidatos; salida
  40 kHz reprodujo 1.014.240 muestras durante 25,36 s y un retune. Cero errores
  o underruns, buffer mínimo 10.274 muestras; parada/cierre confirmados.
- WAV por A0 confirmó Play, avance de 160.000 muestras, Stop y salida apagada.
  Synth FM con 20 voces confirmó Play y 242.400 muestras. En ambos recorridos
  no hubo errores de transporte y el receptor se liberó al cerrar. Son smoke
  acotados, no campañas prolongadas de audio.
- Scan US al máximo ADC8 (1,860 MS/s) terminó con 29 candidatos; FFT Radio de
  16K completó 782 actualizaciones en 75 s, sin error de flujo, con A0 apagada
  y cierre confirmado. La ventana estuvo expuesta durante el inicio y el scan;
  el último registro antes del cierre marcó exposición falsa, así que esta
  corrida no cuenta como exposición visible continua.
- Smoke de los paneles de análisis: V(t) 59 Paint fps en ADC8/1,860 MS/s, FFT
  16K 30 fps, Heatmap dual CH1/CH2 10 fps y Bode 12,6 fps con curva demo. V(t)
  a máximo tuvo una corrida de 24 s estable y otra de 18,9 s en que el relay
  registró `PC disconnected or too slow; close session (sent=-1)`, con retardo
  GUI máximo 604 ms; la recuperación posterior y un nuevo smoke de 24 s pasaron.
  Es un evento aislado aún sin causa confirmada, no una aceptación de estabilidad
  prolongada. El código actual no registra `errno` ni nivel de cola al cerrar;
  el diagnóstico pendiente está en [cierre de flujo V(t)](DIAGNOSTICO_CIERRE_FLUJO_VT_V19.md).
  [V(t) fallido](../diagnosticos/resultados_v19/prepare_q_20261027/gui_vt_smoke.json) ·
  [V(t) repetido](../diagnosticos/resultados_v19/prepare_q_20261027/gui_vt_repeat_smoke.json) ·
  [Heatmap dual](../diagnosticos/resultados_v19/prepare_q_20261027/gui_heatmap_dual_smoke.json) ·
  [Bode](../diagnosticos/resultados_v19/prepare_q_20261027/gui_bode_smoke.json).
- El sondeo inicial se corrigió para aceptar un paquete de estado nativo vacío
  y acotar la espera del primer frame. La primera interrupción fue un defecto
  del sondeo, no evidencia de fallo del firmware normal.
- Las pruebas simuladas de GUI, Bode, MIDI, WAV y procesos no sustituyen una
  aceptación física de A0, de RADIO/WAV, ni de todos los bits, tasas y paneles.

## Pruebas de regresión prioritarias

| Área | Prueba y aceptación |
|---|---|
| Inicio/cierre | Arranque por IDE, módulo y script con el Python 3.13 habitual; cierre con y sin reproducción, sin proceso Qt huérfano |
| Interfaz | Diez vistas deterministas comparadas; smokes físicos V(t), FFT, Heatmap y Bode hechos. Revisar manualmente todos los paneles |
| V(t) largo | Ventanas de millones de muestras, detalle Completo, gaps y cursores Seguir/Libre; el cursor debe leer datos originales |
| Cambio de vista | Pasar de ventana temporal larga a FFT/heatmap/Bode y cambiar Fs; sólo V(t) largo usa cadencia reducida |
| Canales | CH1, CH2 y dual en V(t), FFT, heatmap y cursores; los bancos de cursor se conservan por análisis |
| RADIO/FILTER/A0 | Normal Scan y Radio/A0 smoke completados; falta FILTER, escucha/clics y campaña prolongada |
| WAV/Synth | WAV y FM 20 voces smoke completados; faltan campaña larga, MIDI físico y modos restantes |
| Preparar Q | Primera instalación en Q vacío completada; validar conexión y controles manuales en la GUI |

## Revisión de mejoras con Astra

La revisión detectó dos problemas concretos ya corregidos en este cierre:

1. La envolvente de V(t) largo podía alimentar los cursores con puntos reducidos.
   La optimización queda desactivada mientras cualquier cursor está encendido y
   cuando se elige Completo; hay regresión específica.
2. La cadencia de refresco de ventanas grandes podía permanecer en FFT/heatmap.
   Cada cambio de modo restablece la cadencia normal y vuelve a aplicar la
   cadencia lenta únicamente en V(t) largo; hay regresión específica.

La revisión no recomienda cambiar las tasas ni el firmware en esta transición.
Como mejora posterior, medir el recorrido de plugins Qt en el arranque; no se
debe mezclar esa optimización con la aceptación del cambio de binding.

## Evidencia de campañas previas

La comparación congela el extremo de Roll y usa una misma definición de demo
en ambos procesos. La corrida de promoción, sus imágenes y
[comparison.json](../diagnosticos/resultados_v19/visual_promotion/comparison.json)
se conservan en `diagnosticos/resultados_v19/visual_promotion/`. Los reportes
previos siguen en [`diagnosticos/resultados_v19Pyside`](../diagnosticos/resultados_v19Pyside/);
las carpetas mantienen sus nombres por trazabilidad histórica.
