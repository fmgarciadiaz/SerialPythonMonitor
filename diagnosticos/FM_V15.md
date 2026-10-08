# Síntesis FM y MIDI del monitor

Validación local del 7 de octubre de 2026. No se cargó ni modificó firmware del Q.

- 37 pruebas heredadas de FFT y nuevas de FM pasaron; una prueba adicional del
  sintetizador con el receptor y sus créditos también pasó (6 pruebas FM en total).
- Continuidad de fase y estado del filtro entre bloques de 480 muestras;
  diferencia de hasta un código DAC al comparar con un bloque largo.
- Verificación de portadora/bandas laterales, parámetros válidos, silencio tras
  Note Off, controles durante Play, Stop y retorno al panel normal.
- Protocolo existente: inicio con contador uint32 y generación perezosa de bloques,
  amplitud 2 Vpp y offset 1,65 V en el receptor. Memoria independiente de la duración.
- 1.000 bloques (12 s de audio) se generaron en 0,216 s en este Mac.
- Mido 1.3.3 y python-rtmidi 1.5.8 instalados en Python_3_13_DataScience.
  Creación y cierre de puerto CoreMIDI virtual temporal, envío y recepción de nota 69
  comprobados fuera del sandbox. El sandbox restringe el acceso al servicio CoreMIDI.
- Inspección visual de FM a tamaño inicial: controles dentro del ancho del panel.

Pendiente: reproducción física por A0, concurrencia con ADC a tasas altas,
estabilidad prolongada, latencia MIDI→DAC y escucha con teclado/aplicación musical.
Sesión limitada a 24 horas por los contadores del protocolo; inicio nuevo manual.

## Presets y revisión de los cortes

Se agregaron Manual, Flauta, Órgano y Piano, con envolventes de amplitud,
liberación de notas y evolución del índice; velocidad visible y aplicada a nivel
y brillo. Se mantiene monofonía. Pasaron 40 pruebas V15, incluyendo MIDI, seguimiento
de nota/ratio, registro agudo limitado en banda, decaimiento del piano y Note Off.
La interfaz de presets entra dentro del viewport del generador (316/338 píxeles).

La alimentación del DAC se adelanta al procesamiento ADC después de cada ACK.
Los mensajes FM a la GUI se limitan a 5 Hz con cambios de estado inmediatos;
antes se publicaba uno por bloque, aproximadamente 83 por segundo. Cada sesión
registra estado/créditos/intervalos de ACK en `diagnosticos/resultados_fm`.
Estas modificaciones reducen trabajo redundante y mejoran la prioridad del envío,
pero no prueban cuál fue la causa del corte observado: no se vio el mensaje ni
se conoce el muestreo ADC de ese episodio. La estabilidad física queda pendiente.

## Detección MIDI sin bloqueo de la interfaz

Las operaciones nativas de CoreMIDI se aislaron en un proceso Python gestionado
por QProcess, con límite de ocho segundos para enumerar/abrir y procesamiento
acotado de mensajes. Se mantiene la selección al actualizar, se liberan notas
ante errores y se corrige el cierre para no acceder a objetos Qt destruidos.
La salida de otro proceso incluye solo Note On, Note Off y Control Change.

El backend real encontró `Nord Stage 4 MIDI Output` y `Scarlett 4i4 4th Gen`.
La búsqueda asíncrona mantuvo el bucle Qt activo (170 eventos de un timer de 10 ms),
con cierre limpio del proceso. Pasaron 43 pruebas V15 antes del último ajuste de
cierre, y las 11 pruebas de MIDI/FM se repitieron tras ese ajuste, todas correctas.
No se reinició el servicio MIDI de macOS ni se modificó el Q.
