# V20: FPS de pintura, indicadores WAV y dial Radio (4/11)

El contador anterior sólo avanzaba al final de una rama RF de V(t). Las
salidas tempranas de la vista mixta, RADIO y espectros conservaban el último
número, y el contador medía callbacks de render en lugar de cuadros pintados.
Ahora un filtro de eventos cuenta pinturas Qt precedidas por actualización de
curvas, imágenes o raster; varias actualizaciones coalescidas cuentan una vez.
Repintados de título sin datos no suman. Un timer independiente actualiza cada
segundo la vista activa y devuelve cero si no hubo cuadros nuevos. El pequeño
indicador junto al logo sirve también en FFT/heatmap/Bode. No mide muestras/s
ni demuestra una mejora de rendimiento.

WAV reutiliza exactamente RadioLedSpectrum (10 bandas, marco y colores).
Un memmap de sólo lectura sobre el .npy ya utilizado por el transporte permite
leer hasta 2048 códigos alrededor de la posición played confirmada, sin retener
otra copia completa del WAV ni acceder al Q. La posición incluye seek; no se
confunde accepted relativo con played absoluto. El volumen efectivo es la
amplitud solicitada / 3,3 Vpp. El aro exterior usa el mismo InstrumentDial,
gradiente e interpolación de nivel. FFT visual acotada a 2048 puntos/~13 Hz,
interpolación ~30 Hz; no depende de activar FFT de análisis. Stop, error o
cambio de modo liberan el memmap y detienen el timer. Los polls IDLE anteriores
al BEGIN no borran una previsualización en preparación. No cambia el audio.

Radio: dial de 82x78 con referencia cero, centro y máximo kHz en texto de 8 px,
marcas finas y estaciones como pequeños trazos exteriores. Los trazos próximos
se agrupan visualmente; el listado de candidatos y la sintonía conservan todas
las estaciones. La banda extendida US mantiene su color y los límites reales
de sintonía no cambiaron.

Synth: se leyó el journal del ensayo físico normal anterior. prepare_ready
ocurrió a 2,935 s y PLAY a 2,990 s después del clic: casi toda la espera fue
preparar el proceso dedicado y los kernels antes de BEGIN. prepare_audio calienta
los kernels para evitar compilación durante audio. En este bloque no se alteró
esa preparación ni se afirma haber acelerado Synth.

Validación: 16 pruebas focalizadas PASS (FPS real/coalescido, cero sin datos,
imágenes, título Fs, WAV/memmap/seek/volumen/Stop, cuadrados y Synth).
Prueba física normal ADC14/40 kHz dual + WAV20 kHz: 120960 muestras reproducidas,
nivel exterior máximo 0,61, banda máxima 0,875 y máximo de FPS medido 16,01.
Es un smoke breve, no un benchmark comparativo ni calificación de tasas altas.
Restauración del snapshot durante al menos 10 s, identidad MCU/relay exacta,
sin errores ni procesos de prueba residuales.

[Informe, pruebas y captura](../diagnosticos/resultados_v20/wav_meters_20261104/).
Respaldo previo en `respaldos/host/v20_before_meters_fps_dial_20261104/`.
La corrección posterior del texto Fs se verificó por prueba unitaria; no se
repitió el smoke físico por un cambio de formato de título.

Control final de desconexión: la limpieza de entrada también libera el
medidor WAV si no llega otro ACK. Siete pruebas de medidores/reintento PASS
tras esa línea (19 pruebas distintas en total con el grupo anterior).
