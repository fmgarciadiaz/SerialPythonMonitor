# Revisión y plan de cierre · 8 de octubre de 2026

[Proyecto](../README.md) · [Arquitectura](ARQUITECTURA.md) · [Organización](ORGANIZACION.md)

Revisión de Astra y contraste con fuentes locales. Este documento es un
reporte y una propuesta: no implementa cambios, no carga firmware y no opera
el Q. Las 469 pruebas aprobadas corresponden a la consolidación anterior;
no se volvió a ejecutar esa suite para esta revisión.

## Aplicación del plan · estado actual

Correcciones de software aplicadas: V15 exige V13 Pulse también con un relay
ya activo; herramientas y Preparar Q usan esa variante por defecto. V11/V12
se conservan sólo para selección explícita desde herramientas/versiones anteriores.
La actualización prepara el relay antes de detener la app instalada, conserva
respaldo y reporta estado incompleto si falla una etapa tardía.

Desconexión/cierre son asíncronos y no eliminan hilos activos. La confirmación
de apagado tiene resultado separado; un fallo se conserva como salida sin
confirmar. Preparación tiene watchdog de 30 minutos y termina el grupo local
de procesos; no confirma el estado de operaciones remotas si agota el plazo.
La guía actual está separada del historial y las dependencias incluyen MIDI.

Verificación: 129 pruebas V15, 123 V13 y 208 anteriores aprobadas en procesos
separados. Pruebas nuevas cubren selección de firmware, fallo de apagado,
retención de hilos, watchdog y eliminación de un hijo local que ignora SIGTERM.
Enlaces locales verificados. Posteriormente se actualizó y probó el Q;
ver [validación física y respaldos](VALIDACION_CIERRE.md).

**Avance físico:** Wav 20/40 kHz con ADC100 durante dos minutos por tasa;
Synth20 con nueve notas durante diez minutos; los cuatro métodos Bode
produjeron curvas con loopback confirmado. Apagado confirmado y respaldos
anterior/posterior guardados. Pendientes concretos en el reporte de validación,
incluidos GUI bajo carga, MIDI real, desconexión física y Synth40.
Los hallazgos de abajo conservan el reporte previo a estas correcciones.

## Conclusión

El proyecto tiene las funciones necesarias para cerrar. Conviene priorizar
recuperación de conexiones, instalación reproducible y aceptación física del
perfil estable. No propongo nuevas funciones, cambiar TCP/ADB ni rehacer
`app.py` antes de la entrega. Synth a 20 kHz es candidato a perfil estable;
40 kHz debe seguir experimental hasta comprobar el flujo completo.

## Hallazgos comprobados en fuentes

| Prioridad | Hallazgo | Consecuencia y propuesta |
|---|---|---|
| Alta | V15 admite V11 P992 pero autoload busca sus fuentes en la ruta anterior | Con ese firmware seleccionado y recuperación del relay necesaria, la lectura de fuentes puede fallar. Usar resolución de carpetas activas/históricas común |
| Alta | Desconexión espera hasta 12 s y luego 1 s en GUI; después programa eliminación del hilo sin comprobar el resultado final | Puede bloquear la ventana y soltar referencias a un hilo aún activo. Finalización asíncrona con estado de cierre y propiedad conservada hasta `finished` |
| Alta | Preparación espera stdout y fin del subprocess sin watchdog global; cierre de preparación Wav tiene `wait()` sin plazo | Un hijo detenido o una operación que no termine puede dejar la interfaz esperando. Añadir plazos, progreso y gestión de cierre por etapa |
| Alta | Preparar detiene otra app compatible antes de terminar la preparación del relay; la actualización no tiene recuperación transaccional completa | Un error tardío puede dejar la app anterior detenida o fuentes parcialmente actualizadas. Preparar artefactos primero y conservar ruta de recuperación y estado final explícitos |
| Media | Pruebas autoload principales importan V13 histórico | Las pruebas anteriores no cubren esa ruta en V15. Aplicar escenarios al receptor activo y probar salida/cierre con fallos simulados |
| Media | `requirements.txt` raíz declara Qt5; el de V15 omite Mido/RtMidi, que sí están en su entorno Conda | Dos caminos de instalación ofrecen capacidades diferentes. Declarar un camino actual canónico y separar requisitos históricos/MIDI opcional claramente |
| Media | Synth40 tiene underruns documentados, con optimizaciones posteriores sin aceptación integral nueva | El margen de CPU de un benchmark no certifica continuidad con UI, ADC y transporte. Mantener experimental y ensayar por separado |
| Baja | “Experimental” está en tooltip del selector de 40 kHz, no en su etiqueta | Hacer visible la condición antes de elegir la tasa |
| Baja | La guía V15 mezcla uso actual con cientos de líneas de evolución y benchmarks de estados anteriores | Separar guía vigente y registro de cambios; dejar una sola tabla de capacidades y evidencia actual |

### Fuentes de los hallazgos

- [Selección y recuperación de apps/relay](../monitor/historico/v15/receiver/unoq_autoload.py):
  admite `v11_p992`; calcula la huella desde `arduino/{version}/relay`.
  El destino real es `arduino/historico/v11_p992/relay`.
  [Resolvedor de herramientas](../tools/unoq.py) ya contempla ambas ubicaciones.
- [app.py](../monitor/historico/v15/app.py): `QPreparationThread.run`, `stop_input` y
  `closeEvent` contienen las esperas descritas. El worker intenta apagar la
  salida en `finally`; no debe perderse esa finalización al cambiar el cierre.
- [prepare_q.py](../tools/prepare_q.py): orden de respaldo, detención,
  preparación del relay, actualización/importación e inicio.
- [requirements raíz](../requirements.txt), [requirements V15](../monitor/historico/v15/requirements.txt)
  y [entorno Conda](../monitor/historico/v15/environment.yml).
- [Pruebas autoload históricas](../tests/v13/test_unoq_autoload.py),
  [pruebas del receptor/Synth activo](../tests/v15/test_fm.py) y
  [pruebas de preparación UI](../tests/v15/test_fft_widgets.py).
  Sí existen pruebas de créditos, dos bloques Synth en tránsito, WAV y
  adaptación de cola en V15; el hueco es la cobertura de ciclo de vida completo.
- [Guía V15](../monitor/historico/v15/README.md) y [límites Synth](SYNTH.md):
  evidencia anterior de underruns y cola mínima de 120/192 ms a 20/40 kHz.

La espera y ausencia de rollback se comprobaron leyendo el código. En esta
revisión no se reprodujo un bloqueo físico nuevo. La ruta V11 tampoco afecta
por sí sola la conexión normal a V13 Pulse.

## Candidatos a medir, sin causa demostrada

1. Warmup Numba desde el constructor del panel: medir arranque con caché fría
   antes de moverlo a otro hilo. Si se nota, mostrar preparación y habilitar
   Play al terminar.
2. Escritura JSONL síncrona en recepción: medir su duración antes de atribuirle
   cortes o añadir otra cola/hilo.
3. Latencia: separar tiempo MIDI, síntesis, espera de cola, transporte y DAC.
   La cola mínima de 120/192 ms no es una medida total MIDI→A0. No recortarla
   otra vez sin demostrar margen y continuidad.
4. Piano/Guitarra Virtual: comparar por escucha y registro contra referencias.
   Los parámetros publicados del piano no convierten su caja sintética en
   un instrumento medido. El realismo adicional puede quedar para otra etapa;
   no es un bloqueo del cierre funcional.

## Plan propuesto, en orden

### 1. Correcciones pequeñas y contrato de entrega

- Resolver rutas activas/históricas de autoload sin cambiar apps remotas.
- Probar el receptor V15 con Q sin app, app compatible detenida, app ajena
  activa, relay ausente, selección de Q y cancelación.
- Unificar instalación y explicar requisitos MIDI/Numba.
- Marcar Synth40 como experimental en el selector.

**Aceptación:** arranque en entorno limpio, mensajes accionables y todas las
rutas declaradas válidas. Un Q sin instalación deriva a Preparar Q; una app
ajena no se sustituye automáticamente. Regresiones pertinentes aprobadas.

### 2. Robustez de preparar, desconectar y cerrar

- Finalización asíncrona de workers: mantener referencias hasta `finished`.
- Plazos y estado explícito para comandos externos, lectura/preparación Wav
  y pérdida de enlace. La interfaz debe seguir respondiendo.
- Validar/compilar artefactos antes de detener el conjunto instalado cuando
  sea posible; identificar respaldo y recuperación si falla una etapa tardía.
- No interrumpir a ciegas una carga de MCU. Distinguir cancelación segura de
  una etapa crítica en curso y explicar el estado resultante.

**Aceptación:** simular ACK ausente, socket interrumpido, hijo sin salida,
fallo de compilación y cierre mientras hay trabajo. Sin éxito falso, sin
borrar hilos activos, con timeout/error y estado final comprensibles. Mantener
apagado de salida confirmado cuando el enlace permita confirmarlo.

### 3. Aceptación física del perfil de entrega

Usar un único dueño del Q, identificar monitor/firmware/perfil ADC y conservar
la configuración inicial para restaurarla al acabar. No se ejecuta este plan
de pruebas hasta aprobar la implementación y coordinar el acceso a la placa.

| Escenario | Qué comprobar |
|---|---|
| Adquisición con V(t), FFT y heatmap | Secuencias/CRC, timestamps, épocas, nodos perdidos y fatal; UI responde |
| Generador y SINGLE | Seno, pulso, Sweep/Chirp; disparo manual y captura correctos |
| Bode | Tonos, pulso y Sweep/Chirp; repetir, cancelar, calibración compatible y restauración |
| Wav | Archivo completo, seek, cambio de nivel, EOF silencioso y Stop |
| Synth20 | Nueve notas, pedal sostenido/release, presets y controles; carga de ADC y gráfica activa |
| Ciclo de vida | Desconectar/reconectar, apagar/encender Q, cierre con salida activa y recuperación |

Propuesta de duración: 10 minutos de Synth20 bajo carga y al menos 2 minutos
por combinación Wav/ADC elegida para la entrega. Guardar los perfiles exactos,
mínimo de cola, render máximo/distribución, tiempos de ACK, underruns y errores.
Medir MIDI→A0 por separado con una referencia temporal identificada.

**Aceptación:** cero underruns en escenarios aceptados, cero pérdidas/errores
no explicados y parada/recuperación repetibles. Una tasa que falle queda
fuera del perfil estable; se conserva su diagnóstico y se restaura el perfil
inicial tras las pruebas. Un promedio de CPU favorable no sustituye esta evidencia.

### 4. Synth40, opcional para cerrar

Repetir el ensayo integral a 40 kHz. Optimizar sólo el cuello de botella
medido. Si no pasa, conservarlo experimental y cerrar con el perfil aceptado
a 20 kHz; no bloquear toda la entrega por esa tasa ni prometer baja latencia.

### 5. Congelar documentación y entrega

- Guía breve de operación, instalación y recuperación; evolución en historial.
- Tabla de perfiles aceptados, experimentales y pendientes, con enlaces a evidencia.
- Respaldo recuperable, inventario y versiones exactas de entorno/firmware.
- Verificar enlaces y ejecutar pruebas pertinentes tras los cambios.

**Aceptación:** otra persona puede instalar, conectar, operar y recuperar el
instrumento siguiendo la guía. Código, documentación y perfiles coinciden.
Crear commit/tag o publicar sólo cuando se autorice ese paso.

## Lo que dejaría después del cierre

Refactor amplio de `app.py`, migración de transporte USB, más osciladores,
nuevos instrumentos y una emulación física más profunda. Se pueden abordar
sobre una base congelada y validada, sin poner en riesgo las funciones actuales.
