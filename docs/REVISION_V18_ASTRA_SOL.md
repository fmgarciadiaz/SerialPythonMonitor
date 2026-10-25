# Revisión de código V18 Astra/Sol y bloques locales

Fecha: 21/10/2026. La primera revisión de Astra se interrumpió por cuota;
posteriormente completó la revisión a nivel código. Esto no aprueba la
integración física. Sol ejecutó los bloques locales de arranque y RF numérico
que se describen aquí, sin Q, ADB real, firmware, GUI, cambios de V17 ni cambios
del experimento histórico.

## Hallazgos y límite de la revisión

`ProcessAudio` todavía combina el dueño con detalles de `LocalTransport` y
`SocketModelPeer`, incluidos `peer.original_config` y sus contadores. El perfil
ADC inicial de esos fixtures es conocido por el modelo; no constituye una
captura del Q. CONFIG sólo admite el modelo ADC14 dual a 40/125 kS/s.

El arranque publicaba READY después del descubrimiento WAV/RF sin consultar el
generador. BEGIN rechazaba un generador observado activo, pero admitía
`observed=None`. La ausencia de una lectura no prueba OFF y tampoco permite
afirmar restauración exacta. Se reprodujo antes de editar producción con dos
pruebas nuevas: fallaron cinco subcasos de descubrimiento ausente y de estado
activo/running/respuesta perdida.

## Plan acotado ejecutado

1. Consultar automáticamente el generador mediante el protocolo estricto y el
   journal compartido, después del descubrimiento WAV/RF y antes de READY.
   Mientras WAV está ready, `AudioPump` no agenda consultas periódicas WAV;
   la consulta del generador utiliza ese mismo canal ocioso.
2. Exigir APPLIED, referencia inicial OFF y `running=false` antes de READY y
   antes de cada BEGIN. ACCEPTED, timeout y consultas pendientes no habilitan
   el inicio. Los controles de sesión se rechazan antes de READY; SHUTDOWN
   permite completar el descubrimiento pendiente.
3. Si no se obtuvo referencia OFF, cerrar sin emitir STOP/GEN_SET/CONFIG para
   tomar control de una salida ajena. Mantener el error inicial y declarar
   `restored=false`. Con referencia confirmada, conservar STOP, restauración
   exacta del generador y consulta final independiente; `restored` ahora exige
   también `generator_verified`.
4. Conservar IPC acotado, barreras RF, secuencia FIFO, serialización ADC/audio/
   generador y cierre por muerte del padre. El manifiesto de migración conserva
   sus hashes y resultados históricos; no representa los archivos posteriores
   a esta corrección.

## Evidencia local

Python utilizado:
`/Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python`.

- Suite V18: `-m unittest discover -s tests/v18 -t . -v`, **126 pruebas OK**,
  una pasada de 12,042 s.
- Pruebas del generador: **14 pruebas OK** después de revisar también que los
  fixtures activo/running envían estados válidos del protocolo. Cubren
  lectura automática con/sin RF, rechazo de BEGIN pendiente, APPLIED frente
  a ACCEPTED, timeout, referencia ausente, restauración exacta y TCP local.
- Los fixtures de fallo inspeccionan el cable: ante activo/running/timeout
  sólo se envían QUERY WAV y GEN_QUERY; no BEGIN, STOP, GEN_SET ni CONFIG.
- La suite conserva casos de escrituras parciales, GIL del padre bloqueado,
  muerte real del padre, EOF y barreras de configuración. Los sockets TCP
  usados son exclusivamente de loopback y requirieron permiso del sandbox.

Estos resultados son simulación y protocolo local. No prueban restauración
del Q, audio físico, holgura a 1,6 MS/s, latencia de GUI ni FPS visibles.

## Primer bloque tras la revisión completa: RF numérico

La decisión de Astra es conservar el control asíncrono V18 y reutilizar el
decoder/desempaquetado numérico ya existente. No trasladar `OutputReceiver`
entero: contiene `sendall`, esperas de hasta 3 s y apagado a cero al cerrar,
que no satisfacen automáticamente el contrato de un dueño no bloqueante y
restauración exacta.

`ProtocolIngress` ahora activa `decoder.numeric`. `AcquisitionPath` publica
directamente el array `uint32` de forma `(count, 4)` con columnas timestamp,
CH1, CH2 e índice. Se elimina `tuple(value)` y se conserva un mensaje por
trama, generación, ordinal, barrera y límite de cola. El productor marca su
array como sólo lectura y el decoder crea arrays separados por trama; no
reutiliza ni modifica un buffer publicado. Pickle puede entregar al consumidor
un array escribible: no se promete inmutabilidad entre procesos ni memoria
compartida. `RfBarrier` valida tipo numérico, dimensiones e índice inicial.

Las tres pruebas nuevas se reprodujeron antes del cambio. Ahora verifican
igualdad exacta de las cuatro columnas, los nueve perfiles bits/canales
disponibles (8/10/12/14 CH1 y dual, 16 dual), extremos, wrap uint32, secuencia
SCP1, fragmentación y conservación del primer array después de decodificar
otra trama. La suite autorizada pasó **129 pruebas en 13,445 s**, incluidos
ACK antes de RF, CONFIG, sobrecarga, shutdown, sockets locales y muerte del
padre. La lista explícita de `--self-test` incluye el módulo nuevo. No se
añadieron batching ni barreras de generador.

### Medición local decoder → Queue spawn → consumo

Script: [benchmark_rf_ipc_v18.py](../diagnosticos/benchmark_rf_ipc_v18.py).
Evidencia final con fuentes/SHA-256, Python/NumPy/plataforma y métricas por
caso: [rf_numeric_20261021.json](../diagnosticos/resultados_v18/rf_numeric_20261021.json).
La ejecución informada tiene 1.500 tramas por caso y compara el comportamiento
anterior con tuplas frente a arrays, en Queue de 16 y de 2 mensajes; esta
última agrega una pausa inicial de 50 ms al consumidor. Se verificaron todas
las columnas de 1.296.000 filas CH1 o 372.000 filas dual por caso, sin pérdidas.

Resultados de Queue 16 sin pausa, una ejecución local informada:

| Perfil del vector | CPU total tuplas → numérico | Tiempo tuplas → numérico | Ejemplo pickle por trama tuplas → numérico |
| --- | --- | --- | --- |
| ADC8 CH1, 872 filas | 0,979 → 0,350 s | 0,530 → 0,236 s | 11.789 → 14.206 bytes |
| ADC14 dual, 248 filas | 0,468 → 0,262 s | 0,287 → 0,244 s | 3.782 → 4.220 bytes |

El CPU total suma productor y consumidor. `process_time` del productor se
mide hasta terminar el feeder de Queue y lo incluye; no se midió el CPU del
feeder por separado. Generación de entrada, spawn y sondas de tamaño pickle
quedan fuera del intervalo. El consumidor convierte las tuplas a array y
comprueba exactamente las cuatro columnas, el trabajo numérico esperado.
Los tamaños son ejemplos por longitud de fragmento; en tuplas también dependen
de los valores de los enteros. Es una reducción de objetos/CPU, no compresión.

Con Queue 2, los eventos `queue.Full` fueron 702 → 386 para CH1 y 758 → 747
para dual. El tiempo dual apenas varió, 1,166 → 1,122 s, con 0,996 → 0,976 s
de espera acumulada al publicar. La cola pequeña y su presión siguen siendo
un límite. Se registra presión observada y espera; no se infiere un pico con
`qsize`. Estos tiempos no son un umbral de test ni una calificación a 1,6 MS/s.
La simulación no incluye transporte del Q, DSP, GUI o audio físico.

## Segundo bloque: rechazo acotado de sesiones WAV ajenas

Antes de corregir, los tres estados iniciales BUFFERING, PLAYING y DONE
dejaban al dueño esperando READY sin resultado terminal. Como no existía
referencia del generador, SHUTDOWN tampoco podía enviar STOP y `close`
terminaba agotando su espera y usando terminación forzada. Se reprodujeron
los tres casos en fixtures locales antes del cambio.

Ahora el dueño rechaza `occupied` inmediatamente después de procesar la
respuesta discovery, con un error `Startup occupied` que identifica estado
WAV y sesión. El terminal conserva `wav_readback` (sesión, estado/nombre,
aceptadas/reproducidas/total y capacidades). No publica READY, no consulta el
generador ni emite BEGIN, STOP, GEN_SET o CONFIG para tomar la salida ajena.
El proceso libera su transporte y sale por sí mismo; reporta fallo,
`restored=false`, `generator_verified=false` y `model_only=true`.

DONE conserva el rechazo inicial existente. `DeviceSnapshot` admite IDLE o
DONE como audio detenido, pero ese contrato todavía no está integrado con el
dueño y no demuestra que una sesión terminada ajena sea adoptable. Este bloque
mantiene la admisión inicial del dueño en el subconjunto IDLE; no redefine
DONE ni cambia cómo termina una sesión creada por el propio dueño.

Se añadieron cuatro pruebas: BUFFERING/PLAYING/DONE locales, PLAYING por TCP
independiente, SHUTDOWN con discovery demorado y SHUTDOWN con QUERY perdido.
Verifican resultado terminal, `join` con salida natural y código 0 antes de
usar el cierre de la API, además de una sola trama QUERY y estado/counters
ajenos conservados. La consulta perdida conserva su timeout de ACK y también
sale sin STOP. Los fixtures usan consumo congelado para comparar exactamente
el estado; no representan la evolución temporal de un DAC real.

Validación con el Python del proyecto: 15 pruebas puntuales OK en 1,891 s y
una pasada final de **133 pruebas V18 OK en 15,272 s**. `--self-test` incluye
el módulo nuevo. No se repitió el benchmark RF: su informe conserva hashes y
resultados del bloque anterior. Estos resultados validan el rechazo local y
por loopback, sin aceptación física del Q ni afirmación de restauración real.

## Trabajo posterior pendiente

Continuar con la integración del consumidor/API/GUI de las barreras y su
watermark de DSP completado. Después, resolver exclusividad/lock, lease, identidad y captura persistida
DeviceSnapshot antes de permitir operaciones sobre Q. Ninguno se arregló
como parte de las barreras RF. También siguen pendientes la separación del
backend físico respecto de los fixtures, recuperación observada y adaptador
GUI V18. No conectar el backend físico como consecuencia automática de estas
pruebas locales. La auditoría de migración conserva sus hashes históricos.

## Tercer bloque: barrera RF de GENERATOR_READBACK

La regresión contractual se reprodujo antes del cambio: el evento no contenía
`rf_barrier`. Un fixture determinista entrega ADC → ACK de generador → ADC,
con ACK y el segundo ADC en una misma lectura. El dueño ahora captura en ese
callback síncrono `rf_barrier=path.emitted`, `rf_generation=path.generation`
y epoch/sesión de control. La barrera cuenta sólo tramas RF admitidas antes
del ACK; sin RF, barrera y generación valen cero. No hay batching ni reinicio
de generación o índice ADC por una confirmación del generador.

`GeneratorReadbackGate.release(event, rf_gate.consumed)` aporta un gate de
memoria constante y sin cola interna. Devuelve False mientras falte consumir
RF previo y True cuando se puede liberar esa confirmación según ese watermark.
El consumidor futuro debe invocarlo, retener los ACK pendientes en FIFO con
capacidad explícita y fallar ante sobrecarga; debe continuar atendiendo CONFIG
mientras espera, sin acumular una lista ilimitada ni bloquear los eventos que
permiten consumir RF. El gate todavía no está conectado a una API pública o
GUI que haga esta retención automáticamente.

El esquema y tipos del evento son estrictos. Se aceptan saltos entre RIDs y
varios ACK en un mismo ordinal; duplicados ya liberados, RIDs reordenados y
regresiones de barrera/watermark fallan explícitamente. Una confirmación
pendiente puede consultarse de nuevo. La generación RF es contexto histórico:
CONFIG puede avanzar en el mismo ordinal sin invalidar un ACK anterior, y el
gate nunca llama a `configure` ni modifica épocas de muestras.

Las seis pruebas nuevas cubren la frontera exacta del callback, ambos órdenes
entre colas, ACK al mismo ordinal, CONFIG intermedio, duplicados y eventos
malformados. Validación: **20 pruebas puntuales OK en 3,172 s** y una pasada
final de **139 pruebas V18 OK en 16,634 s**. El módulo nuevo está en `--self-test`.
No hubo benchmark nuevo, hardware ni cambios de hashes históricos.

RF consumido no implica DSP terminado. La GUI futura necesita además un
watermark de DSP completado antes de mostrar el ACK público como aplicado a
todos los datos anteriores; este bloque sólo implementa y prueba la frontera
de admisión/consumo RF local.

## Cuarto bloque: lock local compatible con V17

`monitor/v18/board_owner.py` incorpora una copia propia del algoritmo V17:
SHA-256 del serial truncado a 20 caracteres, mismo archivo
`serialmonitor-q-{uid}-{key}.lock` en `tempfile.gettempdir()`, `flock`
exclusivo no bloqueante y conservación del inode al salir. No importa V17 ni
modifica su implementación. Es un lock advisory local: sólo protege procesos
cooperantes que usen el mismo serial, usuario y directorio temporal; no es
exclusividad entre hosts ni una prueba de estado del Q.

Cuatro pruebas con procesos spawn reales verifican contención V17/V18 en ambos
sentidos, serial distinto independiente, liberación tras excepción/salida
natural y SIGTERM, y persistencia del inode. Pasaron **4 pruebas puntuales en
0,366 s** y una pasada de **143 pruebas V18 en 16,448 s**. El módulo está en
`--self-test`. No se ejecutaron ADB real ni operaciones del Q.

La integración con `AdbTunnel` queda explícitamente pendiente. Hoy la lease
recibe `exclusive()` y `confirm_owner_exit(bool)`: esos callbacks no adquieren
el lock ni observan por sí mismos la vida de otro proceso. Este bloque no
afirma que una lease ocupada evite ADB ni que una transferencia mantenga el
lock. Un contexto abierto sólo por el coordinador podría liberarlo al morir
éste mientras sigue vivo el hijo; no se añadió ese contexto inseguro.

Secuencia requerida para el backend siguiente: el proceso dueño adquiere
`with board_owner(serial, purpose)` antes de cualquier identidad/ADB/lease o
I/O del Q; mantiene el contexto durante la sesión, restauración/cierre del I/O
y liberación del forward. El coordinador no abre primero el Q ni confunde un
booleano con ownership efectivo. La integración de ese ciclo de vida, la
observación de salida y la validación física todavía deben implementarse.
