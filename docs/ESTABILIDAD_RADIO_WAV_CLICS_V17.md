# RADIO/WAV: muestras perdidas y clics · 19/10/2026

## Presentación del proyecto

Se recuperó el README raíz como landing: siete badges, imágenes y explicación de cada función, módulos PC/MPU/MCU, arquitectura y puesta en marcha. La versión y límites se actualizaron a V17 sin reemplazar la presentación por un índice técnico. RADIO y FILTER tienen capturas nuevas de demostración; su procedencia está en `assets/README.md`. Se verificaron 71 destinos locales sin faltantes. La preferencia quedó en `AGENTS.md` y se guardó por petición explícita del usuario en memoria.

## Clic al cambiar de emisora

La fuente A0 descartaba la reserva de la estación anterior y la reemplazaba por ceros. Eso podía saltar desde el último nivel emitido al offset y, después, desde el offset a la nueva señal.

Ahora conserva la misma cantidad de muestras de reserva y el orden de entrega, con transición del último código DAC a neutral en 5 ms y entrada gradual de la nueva emisora en 20 ms. Si la reserva es corta, interpola directamente desde el último nivel a la nueva señal. No se reproducen bloques antiguos de la estación anterior; sólo se usa el último nivel como punto de partida de la rampa. La transición continúa entre chunks, no vuelve a empezar en cada bloque.

Regresión antes/después con niveles opuestos, con y sin reserva: el primer código posterior a resintonía coincide con el último anterior; el salto máximo pasa de 1489 a 2 códigos sin reserva y de 745 a 4 con reserva en este caso controlado. [Datos](../diagnosticos/resultados_v17/radio_retune_20261019/report.json) y [gráfico](../diagnosticos/resultados_v17/radio_retune_20261019/transicion.png). Son códigos generados offline, no una medición acústica. Pasaron 25 pruebas locales de fuente, transiciones, auto gain, créditos y protección de lazo. Escucha y medición A0 pendientes.

## WAV: fallo reproducido y combinación candidata

`diagnosticos/resultados_v17/wav_playback_20261019_200658/report.json`: ADC16/76226, A0 50 kHz, imperial.wav, candidato con sólo servicio por tramas. Underrun DAC a 135360 muestras (~2,71 s). ADC sin dropped/fatal; GUI máxima 32,85 ms. Al último ACK PLAYING sólo quedaban 1920 muestras aceptadas sin reproducir (38,4 ms). No incorporar esta variante por sí sola.

En su traza acotada: lectura máxima 22,20 ms, envío 3,75 ms, decodificación 4,13 ms, generación de bloque 0,07 ms. Estas cifras no identifican una causa única ni bastan para culpar a la GUI. El déficit de alimentación es real y se mantiene como evidencia.

Se ensaya de forma aislada la combinación completa: dos chunks PCM en vuelo durante reproducción, capacidad anunciada de hasta 30 bloques y procesamiento de ACK entre tramas de 992 bytes. BEGIN/PLAY/QUERY/STOP siguen serializados. La reserva cuenta los envíos pendientes para no exceder los créditos del Q. No cambia firmware ni protocolo.

## Vivaldi: aviso DSP/GUI antes de Play

El usuario reporta el aviso de atraso al elegir `audios/vivaldi.wav`, con salida WAV de 50 kHz, antes de reproducir. El archivo es PCM16 mono, 16 kHz y 229,785 s; tres lecturas de metadatos tardaron menos de 0,13 ms. No hay remuestreo ni envío al DAC en esta operación.

Selección con diálogo Qt real/Cocoa, adquisición ADC8/1,6 MHz y salida WAV seleccionada a 50 kHz, sin pulsar Play:

- RADIO apagada: `diagnosticos/resultados_v17/wav_playback_20261019_215022/report.json`, 21.736.512 muestras, sin errores, atraso GUI máximo 91,4 ms.
- RADIO encendida: `diagnosticos/resultados_v17/wav_playback_20261019_215059/report.json`, 21.750.336 muestras, sin errores, atraso GUI máximo 89,9 ms.

Ambas pruebas seleccionaron el archivo y cerraron el diálogo, sin dropped/fatal. Restauración e identidad de firmware verificadas. El caso del usuario no quedó reproducido; no se declara corregido. Estas pruebas no validan reproducción WAV con adquisición a 1,6 MHz.

El runner admite `--select-only --source audios/vivaldi.wav --trace` y opcionalmente `--radio`. Se añadió contexto WAV al informe de atraso GUI (ruta, tasa, preparación, reproducción y diálogo abierto), y temporización de apertura del selector/inspección cuando superan 20 ms. Ocho pruebas de entrega PCM/créditos pasaron, además de selección y cierre locales después de agregar esta instrumentación.

## Clics en Sweep: seguimiento

El usuario confirma el 19/10 que ocurre siempre al iniciar y luego aleatoriamente durante el recorrido. Falta precisar Generador/Bode, forma y rango de frecuencias. El generador comienza con el primer nivel de la tabla y, al terminar, mantiene `active.low`; eso permite saltos de nivel en los extremos. `set_timing` cambia divisores durante el barrido; su efecto físico debe medirse antes de modificarlo. No se atribuyen todos los clics a una sola causa ni se cambia el firmware basándose sólo en la lectura.

Runner de medición: `diagnosticos/medir_transiciones_sweep_v17.py`, A0→CH2/A3, seno Sweep y Chirp 100–2000 Hz/2 s, ADC8 dual. Guarda capturas y pasos de tensión en comienzo/interior/final, respalda configuración y verifica restauración. No usar simultáneamente con el monitor ni con otra campaña.

El runner admite `--repeat`, `--duration-ms`, `--start-hz` y `--end-hz` para repetir y conservar cada captura por separado. El máximo salto entre muestras durante el interior es una medida eléctrica; incluye pendiente normal, escalones del DAC y cuantización del ADC, y no demuestra por sí solo un clic audible.

Nueva campaña `diagnosticos/resultados_v17/sweep_transitions_20261019_213453/report.json`: cinco Sweep y cinco Chirp de seno 100–2000 Hz/2 s. Los diez terminaron sin dropped/fatal. Nueve capturas permitieron localizar el arranque con el umbral actual; en una el detector no lo localizó, lo que no demuestra ausencia de salida. En las nueve evaluables el máximo salto interior fue 0,052–0,065 V. No se reprodujo ni identificó un clic aleatorio audible con esta medición; siguen pendientes el caso exacto del usuario y una corrección de firmware validada. Configuración restaurada y firmware sin cambios.

## WAV incorporado y controles

La combinación completa pasó tres arranques independientes de 120 s a ADC16/76226 y A0 50 kHz, con imperial.wav, Python 3.13/Cocoa. Reservas DAC mínimas observadas: 201,6 / 172,8 / 163,2 ms. Sin underrun ni dropped/fatal ADC. Informe: `diagnosticos/resultados_v17/wav_playback_20261019_200749/report.json`; [resumen](../diagnosticos/resultados_v17/wav_pcm_delivery_20261019/qualification.json).

Se incorporó en el host: dos chunks PCM en vuelo sólo durante reproducción, cola limitada a la capacidad anunciada (hasta 30) y decodificación/servicio de ACK por tramas. Los controles siguen serializados; se cuenta lo pendiente para no exceder créditos. RADIO y Synth conservan sus políticas propias; no se modificó firmware ni se habilitó WAV a tasas ADC antes bloqueadas.

Con producción, `wav_playback_20261019_201524/report.json` pasó seek adelante/atrás, Stop, replay, final real de archivo y reinicio. `wav_playback_20261019_202000/report.json` completó además 60 s a ADC14/100000 y A0 50 kHz, sin underrun ni errores ADC, reserva mínima 268,8 ms y restauración verificada. Después de imprimir el informe, ese proceso terminó con SIGBUS: el crash de macOS sitúa el fallo en `sip_api_visit_wrappers` / `QtCore cleanup_on_exit` / `atexit_callfuncs`, al finalizar Python. No atribuir ese cierre a muestras perdidas durante la captura; tampoco declarar solucionado el cierre Qt. [Registro reducido](../diagnosticos/resultados_v17/wav_pcm_delivery_20261019/qt_exit_failure.json).

## Sweep/Chirp medido

`diagnosticos/resultados_v17/sweep_transitions_20261019_201623/report.json`, seno 100–2000 Hz durante 2 s, A0→CH2, ADC8 dual 632411 S/s:

| Recorrido | Paso observado al inicio | Paso al final | Paso máximo interior |
|---|---:|---:|---:|
| Sweep | 1,618 V | 0,194 V | 0,052 V |
| Chirp | 0,984 V | 0,738 V | 0,065 V |

Son diferencias entre muestras ADC8, con cuantización y respuesta analógica, no medición acústica ni prueba de todos los rangos. Ambos terminan en ~1,152 V, correspondiente al nivel bajo configurado. Los extremos dominan en esta prueba; la causa de clics interiores en otro ajuste no queda cerrada. No se cambió firmware. Configuración e identidad restauradas, recuperación sin dropped/fatal. Corregir el comportamiento de inicio/fin del generador requiere un candidato de firmware aislado y validar que preserve los estímulos de Bode y el rango de generación.

## RADIO: no consumir reserva al descartar una sintonía vieja

El control `generador_radio_20261019_201722/report.json` completó 120 s a ADC8/1,6 MS/s con 58 resintonías (cada 2 s). No hubo corte DAC ni errores ADC, pero el host llegó a cero de reserva; se rechazaron 12764 muestras de audio de generaciones anteriores. El rechazo evita reproducir la estación vieja, pero perdía su duración y debilitaba la reserva con cada edición.

Se conserva ahora esa duración como silencio de transición, con rampa y contador `transition_silence_samples`. Sólo se compensa dentro de la misma sesión de salida, con adquisición y tasa de audio iguales, RADIO activa y una fuente ya iniciada. No se rellenan discontinuidades RF ni errores de DSP; siguen provocando error. Cambios de sesión/reloj no aceptan padding de resultados antiguos. El audio rechazado no reingresa en gráficos ni en la salida.

## Comparación física de la reserva tras compensar

`diagnosticos/resultados_v17/generador_radio_20261019_202322/report.json` repitió 120 s ADC8/1,6 MS/s→A0 40 kHz y 58 resintonías cada 2 s: sin underrun ni dropped/fatal; reserva mínima host 7670 muestras (191,75 ms), frente a cero antes. Se registraron 14085 muestras neutrales de transición. En el ring final, mínimo DAC accepted−played 9600 muestras, frente a 8640 antes. [Comparación](../diagnosticos/resultados_v17/radio_retune_20261019/physical_comparison.json).

Es un control comparativo con restauración verificada, no aceptación global de todos los bits/escenarios ni una prueba acústica de ausencia absoluta de clics. La cola ADC pico fue 5/8; no declarar holgura universal. El firmware permaneció idéntico y el Q quedó restaurado ADC8/1,6 MS/s, generador OFF.
