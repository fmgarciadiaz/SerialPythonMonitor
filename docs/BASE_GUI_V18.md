# Base de interfaz V18

La interfaz en `monitor/v18/app.py` conserva las funciones de Scope, FFT,
Heatmap, Bode, filtro, RADIO, generador, WAV y FM de la base V17. Tiene identidad
visible V18 y dependencias de ejecución en `monitor.v18`, con los recursos SVG,
perfiles y configuración de entorno necesarios dentro de esa versión.

## Archivos y separación

`monitor/v18/gui_migration_manifest.json` enumera los 111 archivos copiados y
sus hashes de origen y de migración. Registra también los archivos preexistentes
que se preservaron. No reemplaza los manifiestos históricos de incorporación.

Se copiaron los módulos de interfaz, procesamiento y síntesis de la raíz de
V17, sus 54 recursos en `assets/`, `piano_identificado.json`, los requisitos de
Python y `environment.yml`. Se incorporaron únicamente los módulos faltantes
del receptor: autoinicio, control, receptor configurable y compatibilidad dual.
Se preservaron `io/`, `__main__.py`, los receptores y perfiles ya presentes, y
el módulo de propiedad del Q que se desarrolla por separado.

Los nuevos datos producidos por esta interfaz usan `capturas/v18`,
`diagnosticos/resultados_v18`, `diagnosticos/resultados_autoload_v18` y
`monitor/v18/calibraciones/bode_v18.json`. Las referencias de evidencia de los
perfiles conservan sus rutas originales: siguen identificando las campañas
reales que validaron esos perfiles.

## Pareja independiente del Q

La GUI V18 usa `CURRENT_FIRMWARE='v18'`, app Scope V18 y contenedor
`scope-v18-main-1`, con relay `serialmonitor-usb-stream-v18`. El protocolo
SCP1V4 continúa igual. Las fuentes están en `arduino/v18`; V17 permanece
congelada con su monitor y binarios en el respaldo pareado.

El hijo exige la app y relay V18 ya activos, comprueba identidad y toma el
lock exclusivo. No instala, inicia ni reinicia aplicaciones automáticamente.
Preparar Q sigue deshabilitado en la interfaz. La activación explícita está
en `tools/activate_v18_pair.py`. Ver [parejas](PAREJAS_V17_V18.md).

## Backend y proxy integrados

`OutputWorker` conserva su API Qt y el procesamiento DSP. La adquisición y los
comandos del receptor maduro se ejecutan en
`monitor/v18/io/receiver_process.py`, en un proceso hijo independiente. El host
recibe lotes RF NumPy aproximadamente cada 20 ms y devuelve el identificador de
crédito sólo después de que la GUI consume el lote. Ese crédito cubre juntos
IPC, DSP y GUI; los límites de muestras, tiempo, memoria y lotes no descartan
muestras silenciosamente. Las confirmaciones comparten FIFO con los lotes y
pasan por la barrera DSP; la cola de confirmaciones también tiene límite.

Las fuentes FM y RADIO mutables permanecen en el host, con sus locks y
controles en vivo. Un productor dedicado responde pedidos PCM acotados por
sesión y offset. La preparación nativa de FM ocurre en ese productor antes de
enviar BEGIN, mientras el proxy sigue recibiendo RF. Hay una preparación activa
y un último pedido retenido; Stop invalida el pedido aunque la preparación nativa
aún termine en segundo plano. Los niveles se aplican una vez en la fuente. RADIO recibe los
resultados DSP antes de su entrega a la GUI. Los WAV se transfieren mediante un
descriptor de archivo `.npy` temporal, leído con mmap; se borra después de
liberarlo el hijo o al confirmar su cierre. La identidad pública de Bode
conserva sus tres campos históricos; la identidad completa con hash del relay
se conserva en el snapshot de restauración.

La desconexión pide detener al hijo antes de esperar DSP, espera su restauración
y cierre y publica siempre el resultado final. Un fallo de restauración se
muestra también cuando la desconexión fue solicitada por el usuario.

Esto acredita integración funcional local. Las pruebas sintéticas no acreditan
integridad del transporte real, headroom, audio físico ni FPS visibles.

## Verificación sin hardware

Se construyó, mostró y cerró la ventana con Qt `offscreen`, anulando la
enumeración de dispositivos. La prueba comprobó filtro OFF inicial, icono local,
identidad V18 y ausencia de módulos `monitor.v17` cargados.

Las regresiones acotadas están en `tests/v18/gui/`: construcción y cierre sin
abrir transporte, cambios de modos, controles RADIO y Radio Test, trazado mixto
de RF/audio sintético, FFT y arranque Bode con FILTER OFF y origen inválido.
Se ejecutan con:

```sh
QT_QPA_PLATFORM=offscreen .venv-v13/bin/python -m unittest discover -s tests/v18/gui -v
```

La base inicial aprobó 11 pruebas. La integración añade regresiones de proxy y
un smoke de la ventana completa con backend sintético: conexión por QThread,
RF/DSP/GUI, créditos, dibujo, RADIO A0, FM, WAV y cierre. Se verifica que RADIO
alimente su fuente real en el host. La suite integrada aprobó **20 pruebas**
en 7,543 s (Qt offscreen, sin Q). La auditoría AST de
todos los módulos V18 no encontró imports a `monitor.v17`; los hashes de los 111
archivos de origen V17 copiados permanecieron sin cambios.

Las pruebas de esta sección no abren el Q ni instalan firmware. La validación
física posterior se registra por separado en `diagnosticos/resultados_v18/`.

## Smoke físico preparado

`tools/gui_live_smoke_v18.py` prepara una sesión acotada con ADC8/1,6 MHz,
RADIO, A0, resintonía, Stop y cierre. Con `--scan --wav` también ejecuta
Scan, cambia la adquisición a 40 kHz y reproduce un WAV temporal de 500 Hz. Recoge eventos `Paint` del viewport,
exposición de ventana, contadores RF/audio/DSP y resultado de restauración en
un JSON. No se ejecuta desde los tests offline; requiere un único propietario
del Q y autorización para la sesión física. Ejemplo:

```sh
.venv-v13/bin/python tools/gui_live_smoke_v18.py --serial SERIAL --output /tmp/gui_v18.json --scan --wav
```

Los eventos Paint sólo acreditan dibujo de la ventana si la evidencia también
registra exposición; este smoke no sustituye la aceptación de audio ni una
campaña de transporte sostenida.

El smoke admite `--hold-radio-seconds 120`: el tiempo se cuenta desde el primer
estado PLAYING confirmado de A0 a 40 kHz. Guarda estados por sesión de forma
acotada, muestras reproducidas/aceptadas y registros cada 10 s de exposición,
eventos Paint, ritmo de dibujo y pendientes IPC/DSP/GUI. Las assertions exigen
PLAYING, progreso y Stop; también Scan completado y WAV si se solicitaron.
`--fm` agrega adquisición de 40 kHz y Synth con confirmaciones PLAYING/progreso/Stop
para comprobar la preparación previa a BEGIN. No sustituye escucha física.
