# Monitor de osciloscopio, generador y audio

Interfaz Python con PyQt6 para adquisición de dos canales, trigger/SINGLE,
FFT, heatmap, Bode, grabación CSV/WAV y reproducción de audio por A0.
El receptor corre en el PC y se comunica con el relay Linux y el MCU del Q.
Para audio se usa el firmware y relay V12 Audio; el conjunto anterior P992
permite adquisición y generador sin reproducción WAV.

## Entorno e inicio

Entorno recomendado: `Python_3_13_DataScience`, con Python 3.13.5, NumPy
2.3.1, pandas, SciPy, Matplotlib, IPykernel, PyQt6 6.11.0 y pyqtgraph 0.14.0.
Desde la raíz del repositorio:

```sh
# Para reproducir la instalación en otra máquina:
conda env create -f monitor/v13/environment.yml
# Para usar el entorno ya instalado:
conda activate Python_3_13_DataScience
python monitor/v13/app.py
```

En VS Code seleccionar `Python: Select Interpreter` →
`Python_3_13_DataScience`. La configuración de depuración V13 y su tarea
usan explícitamente ese entorno; V12 conserva `Python_3_10_DataScience`.
Si VS Code recuerda una selección anterior, elegir el intérprete una vez.
`requirements.txt` contiene las dependencias del monitor para Python 3.13.

El entorno anterior `.venv-v13` y `requirements-python310.txt` corresponden
al ensayo comparativo con Python 3.10, NumPy 1.23.3 y pyqtgraph 0.13.7.
Sus mediciones no representan el nuevo entorno Conda.
No cargar ambos monitores en un mismo proceso: V13 selecciona explícitamente
el backend PyQt6 de pyqtgraph. `app.py` funciona desde cualquier directorio.
Conectar prueba el enlace existente; si falla, comprueba la app y el relay
e inicia lo que falte. Preparar Q instala/actualiza MCU y relay desde las fuentes.
Inicio manual del conjunto de audio: `python tools/usb_stream.py start --firmware v12_audio`.

CSV separado en `capturas/v13/`. Assets, receptor y calibraciones pertenecen
a V13. Las calibraciones copiadas mantienen el perfil medido original;
no implican calibración nueva para ADC a 50 MHz.

## Perfiles y presentación

SPI admite 8/10/12/14 bits hasta 125 kHz por canal y 16 bits con oversampling
×16 hasta 62,5 kHz; UART/R4 conserva su límite de 31,25 kHz. La migración Qt conserva los perfiles ADC; audio requiere el firmware
y relay propios. Cableado: A0 salida, A2/V_IN y A3/V_OUT.

Se mantienen tema oscuro, Fusion, controles de 34 px, colores de trazas y
antialias desactivado. Los diales recuperan 25 marcas uniformes, con graduaciones principales; el deslizador usa una pista fina y un indicador circular con hover. En modo tiempo, escala horizontal editable en ms
con un decimal, convertida internamente a muestras. FFT8192 conserva análisis
completo y reducción de dibujo por ancho de pantalla.

## Verificación y comparación

Las pruebas Qt6 se ejecutan en un proceso separado de las pruebas Qt5:

```sh
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests/v13 -v
```

La comparación sintética utiliza el mismo tamaño, estilo, versiones de
NumPy/pyqtgraph y señales; mide cálculo/dibujo y eventos de pintura por
separado. Ejecutar cada variante en su intérprete correspondiente:

```sh
QT_QPA_PLATFORM=offscreen python diagnosticos/comparar_qt_v12_v13.py --version v12 --output /tmp/v12_qt.json
QT_QPA_PLATFORM=offscreen .venv-v13/bin/python diagnosticos/comparar_qt_v12_v13.py --version v13 --output /tmp/v13_qt.json
```

Estos resultados offscreen excluyen la adquisición real y no certifican
FPS visibles ni reducción del rezago USB. Migrar a Qt6 permite evaluar una
base moderna; su velocidad y aspecto deben compararse en la pantalla real.

## Plugins de Qt6 en macOS

En el entorno local se observó que los plugins de plataforma recibían la
marca Finder `hidden`, y Qt dejaba de encontrarlos aunque estaban instalados.
V13 retira únicamente esa marca de los archivos y carpetas de plugins de su
propio Qt6 antes de crear la aplicación. No modifica
permisos, firmas, otras marcas ni la selección de plataforma. Si la carpeta
no es modificable, el error identifica el archivo que requiere corrección.

[Resultados de comparación local Qt5/Qt6](../../diagnosticos/QT6_V13.md).

[Resultados de la evaluación](../../diagnosticos/QT6_V13.md): 24 pruebas Qt6
aprobadas. En el ensayo offscreen Qt6 fue más lento en todos los escenarios
medidos; V12 sigue disponible para comparar la fluidez real.

## Amplitud y offset del generador

La configuración inicial preparada usa 2 Vpp, offset 1,65 V y salida apagada.
Al conectar en modo Continuo se aplica esa configuración preparada y se espera
la confirmación del Q. Los modos finitos conservan el disparo manual.
El offset se ajusta por número o slider de 1 mV, entre Vpp/2 y
3,3−Vpp/2. Al aumentar amplitud, un offset fuera del nuevo rango se ajusta
al extremo permitido. El aviso cerca de los extremos aparece si la señal
sale del margen conservador 0,2–3,1 V; no garantiza ausencia de distorsión
ni limita automáticamente la amplitud solicitada. El cambio es del monitor,
sin modificar los valores predeterminados del firmware.

Inicio de V13: 14 bits y 40 kHz (SPI). El selector abrevia 16 bits como
`16 bits · (OS)`. Doble clic izquierdo en el slider de offset centra
la señal en 1,65 V dentro del rango permitido por la amplitud.

Salida R4: puente [V5](../../arduino/historico/v5/r4_bridge_v5/README.md)
recargado y probado el 2026-10-05: UART a 14 bits/31,25 kHz y
16 bits/25 kHz; retorno a SPI confirmado. Son pruebas breves de 4 segundos.
[Evidencia](../../diagnosticos/resultados_r4/20261005_puente_v5.json).

Seleccionar Bode prepara el panel; el barrido comienza únicamente con
los botones Repetir o Agregar.


## Grabación CSV o WAV

En adquisición, elegir CSV (predeterminado) o WAV y pulsar RECORD; STOP REC
cierra el archivo. Ambos formatos usan `capturas/v13/` y nombres
`log_AAAAMMDD_HHMMSS_14bit_40kHz`, con extensión correspondiente.
Sólo se añade sufijo si ya existe el nombre. Máximo 30 segundos; el selector queda bloqueado al grabar.

WAV estéreo PCM de 16 bits: A2/ADC_IN a izquierda y A3/ADC_OUT a derecha.
Usa todas las muestras recibidas y la tasa confirmada del Q, sin remuestreo,
ajuste automático de amplitud. El rango ADC completo se convierte
a −32768…32767 con centro fijo en mitad de escala. El filtro DC opcional
se aplica después de esa conversión.
No se graba el trazado reducido de pantalla. Demo sólo permite CSV porque
su tasa simulada difiere de la configuración de adquisición.

Un salto de índice o timestamp detiene WAV con un error explícito y cierra
el archivo anterior al lote inválido; no rellena ni comprime huecos. El
wrap de contadores de 32 bits se admite. STOP de pantalla conserva la
adquisición y la grabación, igual que CSV. Cambio de bits/tasa, desconexión,
cierre de ventana, error y límite temporal cierran el archivo y finalizan
la cabecera WAV. La reproducción por A0 requiere V12 Audio.
Implementación verificada localmente; grabación WAV física pendiente.

### Eliminación DC opcional en WAV

«Eliminar DC · WAV» está activado inicialmente y se fija al iniciar RECORD.
Aplica un pasaaltos continuo de primer orden a 5 Hz, independiente por
canal, con estado conservado entre lotes. Se inicializa desde la primera
muestra para evitar un salto grande debido al offset de entrada. No resta
medias por ventanas ni normaliza volumen. Atenúa señales muy lentas; puede
haber un transitorio inicial de la señal y saturación ante saltos grandes.
Desactivarlo conserva la conversión con centro fijo de 1,65 V. CSV siempre
conserva datos originales.

Nombres compactos: `log_AAAAMMDD_HHMMSS_14bit_40kHz.wav` (o `.csv`).
Sin sufijo numérico inicial; `_2`, `_3`, etc. se agregan únicamente si
ya existe una grabación con el mismo nombre en ese segundo.

El eje horizontal inicia en tiempo; etiqueta y selector están centrados
verticalmente en la misma fila.

## Reproducción Wav por A0

Elegir modo Wav, abrir un archivo PCM o float mono/estéreo y seleccionar
L, R o Mix (promedio de ambos canales). El botón Play/Stop inicia una pasada o la interrumpe. Python elimina la media, remuestrea con filtro
antialias a la tasa seleccionada (20/40/50 ksps) y normaliza al Vpp y offset seleccionados,
cuantizando a 12 bits.
La tasa de salida es la cantidad de muestras por segundo, no la frecuencia del tono.
El selector de salida ofrece únicamente tasas anunciadas por la MCU.
A 20 ksps la banda queda por debajo de 10 kHz; a 40, de 20 kHz; a 50, de 25 kHz.
El archivo completo se prepara en memoria del host. No admite WAV comprimido.

A0 alimenta A2/A3 mediante el cableado externo; la adquisición continúa
con su propio perfil. El firmware usa créditos y una reserva de 384/192/153,6 ms según la tasa;
si faltan datos, detiene la salida en el centro y muestra el error.
El generador previo se restaura al terminar normalmente o pulsar Detener.

Requiere el [firmware y relay V12 Audio](../../arduino/v12_audio/README.md)
V13 detecta automáticamente la aplicación V12 Audio activa en el Q y consulta
su capacidad. También se puede seleccionar con `MONITOR_V13_WAV_FIRMWARE=v12_audio`.
Los comandos nuevos quedan bloqueados sin detección/selección y sin
confirmación del firmware. V11 P992 continúa como valor predeterminado.
Pruebas locales y ensayo físico inicial L/R/Mix/Detener aprobados.
Ensayos sostenidos a 40/50 ksps completados: ver tasas probadas más abajo. En VS Code elegir «Monitor V13 — WAV A0 (V12 Audio)».

Al elegir un WAV se valida la cabecera y se muestran frecuencia de muestreo,
bits y canales originales. Un único botón Play/Stop usa iconos propios; permite
consultar el motivo cuando falta conexión o confirmación del Q.

Durante la preparación y reproducción WAV quedan bloqueados bits, tasa y
destino de adquisición. Se habilitan al finalizar o confirmar Detener.
Play activa RUN y cancela SINGLE armado para mostrar la adquisición en vivo.

### Tasas WAV probadas

El selector «Salida» ofrece 20, 40 y 50 kHz. 40 y 50 ksps completaron 120 s
con ADC14/40 kHz; 50 ksps completó además 120 s con ADC14/100 kHz.
Play se bloquea con ADC125: esa combinación falló dos veces. Bits/tasa/destino
siguen bloqueados mientras se reproduce, y Play activa RUN. Ver
[cálculos, límites y evidencia](../../docs/WAV_TASAS.md).

Al seleccionar Chirp o Sweep: 20→2000 Hz en 2 s. Las confirmaciones del firmware conservan sus valores reales.

### Inicio desde el monitor

Pulsar **Conectar**: intenta abrir primero el transporte existente por USB/ADB.
Si no está disponible, comprueba la aplicación instalada (V12 Audio preferida
si ambas están detenidas, o V11 P992) y el relay, y los inicia si hace falta.
No instala fuentes ni compila el relay; **Preparar Q** realiza la instalación.
App CLI puede compilar/iniciar su sketch instalado durante el arranque.

El único botón muestra un icono de plug desconectado, conectándose o conectado.
Mientras conecta, pulsarlo cancela; conectado, pulsarlo desconecta el lector.
El trabajo corre en segundo plano. Otra aplicación activa se informa como
conflicto y no se detiene. Si falta el relay compilado, usar **Preparar Q**.
No hay casilla de autoinicio: este comportamiento se aplica siempre al conectar.

Sweep, Chirp y Pulso se preparan al seleccionar el modo o modificar sus
parámetros. Sólo «Disparar» envía la configuración e inicia la salida;
las consultas periódicas de estado no disparan ni sobrescriben lo preparado.

Después de encender, el relay permite hasta 10 s para el primer READY.
El arranque sólo se confirma cuando recibe una trama SPI válida; las
transferencias posteriores mantienen el plazo original de 1 s.

### Preparar un UNO Q desde el monitor

Seleccionar el Q por USB y pulsar **Preparar Q**. Se valida y compila el
firmware MCU de V12 Audio, se importa la app en un Q nuevo (o se respalda y
actualiza la existente), se compila el relay en el MPU y se inicia la app.
El arranque termina únicamente cuando el relay confirma una trama SPI válida.
Luego pulsar **Conectar**.
El lector Python corre en la computadora y se conecta en ese último paso.

La placa debe tener el sistema UNO Q con ADB autorizado, Arduino App CLI,
Arduino CLI y Docker; la compilación puede requerir Internet en el Q para
obtener dependencias e imágenes. Se usa siempre el dispositivo seleccionado,
aunque su número de serie sea distinto del Q original. Si otra app está activa,
la preparación se detiene antes de modificar la placa.

Los logs quedan en `diagnosticos/resultados_autoload/preparar_q_*.log` y los
respaldos en `respaldos/unoq/`. Durante la carga se bloquean los controles de
conexión y el cierre de la ventana para evitar interrumpir la carga del MCU.
También se puede ejecutar `python tools/prepare_q.py --serial NUMERO_DE_SERIE`.
La instalación nueva y la actualización están verificadas con pruebas locales;
falta validar el proceso completo en una placa nueva o recién encendida.

Corrección de arranque (2026-10-06): READY puede estar alto antes de comenzar
la espera de eventos del relay. El primer intercambio admite ese único crédito
inicial, drena los eventos pendientes antes del SPI y exige validación completa
de la trama. Los intercambios posteriores siguen exigiendo flancos nuevos.
El aumento previo del timeout a 10 s no resolvía este caso. Los errores del
autoinicio ahora conservan el log en `diagnosticos/resultados_autoload/`.


La salida Wav se selecciona inicialmente a 50 kHz; si el firmware conectado
no la admite, se conserva la reducción a 20 kHz tras consultar capacidades.

En Wav, la amplitud se ajusta con un dial de 0–3,3 Vpp (inicio 2 Vpp).
El WAV se prepara una vez a escala completa y los bloques se adaptan a la
amplitud/offset actuales antes de enviarlos. El dial funciona durante Play,
incluso al volver desde amplitud cero, sin detener ni remuestrear el archivo.
Los cambios incluyen una rampa de un bloque; el audio ya encolado en el MCU
conserva sus niveles anteriores, por lo que la respuesta tiene el retardo de
esa cola. No se modifica el protocolo ni se requiere cargar nuevo firmware.

El dial Wav mide 64 px. Si Wav queda en error o sin muestras, Stop sigue
 disponible para liberar A0. Al conectar se consulta y detiene la sesión Wav
anterior antes de configurar el generador. Al cerrar, Stop se confirma con
el enlace todavía abierto; así Wav no deja bloqueados los otros modos.

Desconectar y cerrar V13 detienen Wav y apagan el generador (DAC a 0 V),
esperando confirmación mientras el enlace USB permanece abierto.

Reconexión después de desenchufar: se verifica que el túnel ADB entregue datos,
sin consumirlos, antes de considerar abierto el enlace. Si el túnel abre pero
el puerto remoto está cerrado o no entrega datos, se comprueba/inicia la app y
el relay. El estado indica «Sin datos del Q; comprobando app y relay…».

Corrección de inicio de Sweep/Chirp (2026-10-06): el firmware V12 Audio detiene
el DMA manteniendo el primer valor de la nueva onda, en vez de llevar A0 a cero
antes de preparar la tabla. Salida deshabilitada conserva 0 V. Compilación MCU
y siete pruebas locales OK; tres arranques de Sweep y tres de Chirp medidos en
A2 a 40 kHz, sin valores inferiores a 0,5 V con señal de 2 Vpp/offset 1,65 V.
Esto verifica la captura ADC; los transitorios más cortos que su intervalo de
muestreo requieren comprobarse con osciloscopio externo.

Amplitud y offset: pasos de 0,01 V. En el dial Wav y el slider de offset, usar
Shift + arrastrar para mover 0,01 V por píxel; rueda: 0,01 V por paso. Arrastre
normal conserva recorrido completo y doble clic en offset conserva centrado.

Amplitud y offset muestran dos decimales, con pasos de 0,01 V. SINGLE en FFT/heatmap captura un bloque del tamaño FFT seleccionado,
eligiendo cerca del trigger el de mayor energía AC ponderada por la ventana FFT,
entre bloques que contienen el disparo. Espera las muestras posteriores
necesarias, pero calcula el espectro sobre ese bloque, no sobre el final del
buffer. La captura queda fija mientras está en STOP; RUN retoma el flujo en vivo.

La captura SINGLE muestra un indicador naranja dentro del gráfico. Desaparece
al volver a RUN o armar otra captura. El cálculo en vivo conserva su conducta.

V(t) también muestra SINGLE en naranja al capturar. SINGLE habilita el trigger
para la captura; al salir con RUN/STOP restaura el estado previo del trigger,
incluso si se rearmó varias veces. Las confirmaciones iguales del generador no
reconstruyen repetidamente los controles. Medición Sweep 14 bits/40 kHz:
intervalo de interfaz máximo ~35 ms y cola máxima ~12 ms en prueba de 6 s.

### 2026-10-06 — Chirp intermitente: fin prematuro

Reproducido antes de la corrección: el octavo Chirp de 20→2000 Hz/2 s
quedó detenido a los 0,1 s, con confirmación OK. generator::tick convertía
la diferencia de ticks directamente a uint64_t: una diferencia negativa
terminaba inmediatamente el barrido. Ahora conserva la diferencia signed
y descarta callbacks con tiempo anterior al arranque. Prueba nativa reproduce
ese caso y verifica también la finalización normal; siete pruebas locales OK.
La relación exacta entre el callback y el fallo físico es una hipótesis;
no se instrumentaron los ticks del MCU durante el fallo.

Firmware compilado y cargado, con respaldo
respaldos/unoq/osciloscopio_20261006_123319_510143.zip. Después: 24 Chirps
consecutivos, seno 2 Vpp/offset 1,65 V, ADC 14 bits/40 kHz; todos activos
a los 0,1/0,6/1,2/1,8 s y finalizados a los 2,1 s, sin errores de estado.
Salida apagada al terminar. Informes:
diagnosticos/resultados_autoload/20261006_chirp_repeticiones.json (antes) y
20261006_chirp_timer_corregido.json (después). La repetición sin fallos
no descarta otros problemas intermitentes.

## Versiones y enlaces

- [Monitor V13](app.py): PyQt6; [firmware Q V12 Audio](../../arduino/v12_audio/README.md).
- [Monitor V12](../v12/README.md): PyQt5; [firmware Q V11 P992](../../arduino/v11_p992/README.md).
- [Histórico](../historico/README.md) · [Historia completa](../../docs/HISTORIA.md).
