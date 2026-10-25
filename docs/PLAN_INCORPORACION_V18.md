## Integración funcional validada · 22/10/2026

El alcance solicitado es V18 completa, conservando V17 intacta. Para mantener
WAV/seek, RADIO/FM, generadores y cambios de perfiles, Astra revisó la elección:
la primera GUI usa una copia propia del receptor maduro dentro de un hijo.
El prototipo asíncrono `io/process_audio.py` queda separado y conserva su
alcance simulado; sus garantías no se atribuyen automáticamente al backend GUI.

`io/receiver_process.py` posee el transporte. `OutputWorker` es el proxy Qt,
con DSP y fuentes mutables en el padre, RF numérico y confirmaciones FIFO,
créditos explícitos, WAV por mmap y PCM live acotado por sesión/offset.
`installed_connection` usa exclusivamente la app y relay ya activos, con lock
compatible con V17; no instala, compila, inicia ni reinicia programas del Q.
`ReceiverLifecycle` captura el estado real y exige restauración y diez segundos
de recepción continua. Pasaron recepción real, restauración, matriz de once casos y GUI con
RADIO/A0 durante 120 s, Scan, WAV y Synth/FM. Ver [validación y límites](VALIDACION_V18.md)
y [base GUI](BASE_GUI_V18.md). No se acredita holgura ni aceptación analógica global.

Los apartados siguientes conservan la historia del prototipo anterior.

# Incorporación del proceso dueño en V18

Decisión del usuario, 21/10/2026: «cuando incorpores, todo en una v18».
La integración del proceso dueño de adquisición/A0 y los cambios asociados
se realizará en `monitor/v18/`. V17 conserva su función de referencia y
comparación. V18 ya tiene núcleo headless propio; todavía no tiene GUI ni backend físico
habilitado. [Entrada y alcance](../monitor/v18/README.md).

[Revisión de código Astra/Sol y bloques locales](REVISION_V18_ASTRA_SOL.md):
consulta automática del generador antes de READY, referencia OFF obligatoria
antes de BEGIN, RF numérico, rechazo acotado de sesiones WAV ajenas y barrera RF
en GENERATOR_READBACK. La integración del consumidor/API/GUI y del watermark
DSP completado sigue pendiente. El lock local V18 ya contiende con V17;
su integración efectiva con lease y proceso dueño aún está pendiente. Astra
completó la revisión de código; no constituye aprobación del backend físico.
El último bloque local pasó 143 pruebas V18 y
conserva la auditoría de creación como evidencia histórica.

## Base disponible

El experimento `experimentos/radio_io_process_v17/` conserva su ruta histórica.
Prueba IPC acotado, control FIFO, barreras RF, créditos confirmados, journal
RID/sesión, cancelación, EOF local y muerte del padre. Simula desconexión del
backend con un chunk pendiente y fallo de restauración; conserva ambos
errores si coinciden. Restauración fallida nunca se declara exitosa.

[Última evidencia: cinco rondas de 119 pruebas](../experimentos/radio_io_process_v17/resultados/20261021_224010/report.json).
No valida SCP1 real, estabilidad de audio físico, GUI ni restauración del Q.

## Adaptación iniciada sin hardware

`wire_adapter.py` ya utiliza el decoder estricto y el encoder WAV públicos.
Entrega callbacks por trama, preservando servicio ACK antes de decodificar
ADC posterior incluso si ambos llegaron juntos. Los errores cierran el
adaptador y EOF parcial es fallo. PCM y correlación usan el rango real WAV
0x80000000–0xfffffffe. Nueve pruebas de protocolo añadidas, todas offline.
`audio_control.py` añade control asíncrono QUERY/BEGIN/CHUNK/PLAY/STOP,
capacidad negociada, créditos confirmados, ventana y timeout. Once pruebas
nuevas pasan. `audio_pump.py` añade el bucle de envío/recepción no bloqueante, consultas
periódicas y cola PCM acotada, probado con LocalTransport. Maneja escrituras
parciales y STOP sin romper framing. Diez pruebas nuevas pasan. ProcessAudio ya ejecuta ese bucle en un hijo spawn con peer simulado y
consumo DAC modelado a40kHz. Ocho pruebas nuevas cubren bloqueo GIL del padre,
parada/cierre, sesiones, EOF, offset, underrun y muerte real del padre. El
resultado se etiqueta model_only; no es restauración física. AcquisitionPath ya une RF/configuración al mismo hijo con rf_enabled=True:
publica barreras sólo tras APPLIED y permite reiniciar el índice ADC después
de drenar la generación anterior. Diez pruebas nuevas cubren coexistencia,
barreras, fallos, cierre y muerte del padre. El modelo RF sólo cubreADC14 dual
a40/125kS/s. SocketTransport ya adapta un socket conectado a I/O no bloqueante,
con ocho pruebas de socketpair/TCP127.0.0.1 y AudioPump con peer fragmentado.
ProcessSocketAudio ya transfiere el socket al hijo y cierra la copia del
padre. TcpModelServer es otro proceso independiente; seis pruebas verifican
GIL bloqueado, ADC/audio, CONFIG, cierre, EOF temprano y muerte del padre por
TCP. El servidor confirma IDLE/perfil original independientemente del hijo.
Sigue model_only=true y perfil inicial conocido por fixture. AdbTunnel añade
lease de forward con identidad/exclusividad/USB y liberación después de salida
del dueño, probada sólo con FakeAdb (diez pruebas). Falta unirla al hijo,
snapshot/restauración física y adaptadorGUIV18; no se ejecutó ADB real.
DeviceSnapshot ya preserva perfil ADC codificado, todos los parámetros del
generadorOFF e identidad MCU/relay. restore_contract exige readback y evidencia
de recuperación10s y nunca declara hardware_restored=true. Nueve pruebas con
backend simulado pasan; falta implementar esas lecturas/ACK en el dueño y
persistir la referencia de Q antes de modificar su estado.
GeneratorPath ya permite GEN_QUERY en el hijo, con respuesta SCP1tipo9 y
evento GENERATOR_READBACK, probado localmente y por TCP. Usa journal compartido
y serializa con ADC/audio; seis pruebas nuevas pasan. Es la última lectura
observada durante uso; en cierre, con referenciaOFF confirmada, ahora
restaura mediante GEN_SET y vuelve a consultar después deStop. Compara todos
los parámetros/running y marca generator_verified. Cuatro pruebas nuevas
incluyen modificación/restauración exactas e inspección independiente del
servidorTCP. Falta captura automática con identidad y recuperación reales,
unión DeviceSnapshot/lease y adaptadorGUIV18; no se conectóQ.
Sin conexión al Q ni aceptación de carga a1,6MS/s.
El recorrido de contrato original se mantiene como prueba independiente.
El prebuffer de pruebas no define la política de RADIO/WAV de V18.

## Secuencia de incorporación

1. Adaptar decoder estricto y control asíncrono existentes al contrato aislado.
   Revisar QUERY/ACK, sesiones, orden de muestras, EOF del transporte y límites
   efectivos. Evitar que la adaptación vuelva a depender del hilo GUI.
2. Completar V18 con la GUI desde V17 revisada; el núcleo/protocolo ya están
   separados y122pruebas locales pasan. Auditar imports,
   rutas, recursos, perfiles, identidad de versión, lanzadores, tareas del
   editor, pruebas y documentación. No trasladar variantes experimentales
   rechazadas ni hacer una sustitución global de nombres sin revisar.
3. Conectar GUI/DSP por el adaptador de barreras y mensajes acotados; mantener
   filtros OFF sin trabajo, perfiles y funcionalidades vigentes. Verificar
   RADIO, WAV, Scan/US, Bode, generador, cierre y cambios de configuración.
4. Validar con Q exclusivo, backup/configuración e identidad verificables;
   restaurar y verificar recuperación al cerrar cada campaña. Comparar V17
   y V18 con la misma carga. Separar integridad ADC, audio, holgura y dibujo
   realmente visible; no declarar resuelto el underrun por pruebas simuladas.
5. Incorporar sólo con evidencia física suficiente. Para nuevas calificaciones
   mantener 60 s y tres arranques de 120 s. No promover tasas ni cambiar
   firmware como consecuencia automática de esta reorganización del host.

El README raíz sigue siendo la presentación con badges, imágenes, módulos,
arquitectura y puesta en marcha. Estado y campañas quedan en documentos
como éste, enlazados desde la presentación cuando corresponda.

## Creación de V18 headless ·21/10/2026

35archivos de núcleo/protocolo/pruebas migrados con namespace propio y
manifiesto de hashes. No hay imports runtime deV17 o experimentos. Entradas
`python -m monitor.v18` y `--self-test`; esta última pasó122pruebas una vez,
no una nueva campaña física. VS Code añade diagnóstico/tarea V18 sin cambiar
las entradas existentes. [Auditoría](../monitor/v18/migration_audit.json).
GUI/identidad física/lease+snapshot integrados siguen pendientes. V17, firmware
y appsQ intactos. El experimento original conserva sus119pruebas como historial;
el trabajo siguiente del candidato se hace enV18.
