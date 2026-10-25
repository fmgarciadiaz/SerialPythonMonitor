# Synth de 20 voces en V18

`MAX_VOICES=20` controla asignación, notasMIDI, robo de voces y etiqueta de
salida. No se modificó V17. Tres pruebas cubren20notas, rechazo de más de20
en un paquete, robo de voz y reciclado con sustain.

Se midieron frases iguales de1,2s con11y20voces, bloques480muestras, seno,
DX Piano de tres osciladores y Piano Virtual. [DatosCPU](../diagnosticos/resultados_v18/synth20_cpu.json).
Usar el entorno Anaconda del proyecto conNumba; el venv alternativo sinNumba
no ejecuta los presets confeedback y no sirve para calificarlos.

Con20voces a20kHz, P95 de render: seno0,71ms,DX6,54ms,PianoVirtual4,24ms,
frente a24ms disponibles. A40kHz: seno0,61ms,DX4,98ms,PianoVirtual6,67ms,
frente a12ms. PianoVirtual tuvo1bloque por encima de12ms (máximo16,52ms).
Por eso40kHz sigue experimental. El benchmark usa feedback4,0 en DX como
el preset real. Los números sonCPU aislada, no latencia MIDI ni aceptación
física. El primer ensayo físico de20voces DX detectó UNDERRUN; se conserva
`gui_synth20_20261022.json`. Se corrigió el servicio PCM para enviar un bloque
ya recibido antes de esperar otra lectura del socket; validación posterior
registrada por separado, sin ocultar el intento fallido.

## Renderer independiente

El segundo intento con servicioPCM adelantado también cortó; se conserva
`gui_synth20_refill_20261022.json`. Se separó el render de Synth en un proceso
persistente (`synth_process.py`). Sus parámetros se envían como datos; locks,
controles Qt y fuentes RADIO permanecen en el host. La preparación ocurre
antes deBEGIN y Stop invalida pedidos pendientes. El mismo proceso conserva
fases, voces, envolventes y filtros entre bloques.

La prueba local compara códigos DAC idénticos entre renderer local y proceso,
con20notas y actualización de acorde. [Prueba física posterior](../diagnosticos/resultados_v18/gui_synth20_process_20261022.json):
DX Piano20voces,20kHz,PLAYING/progreso/Stop confirmados,256320muestras
reproducidas y259200aceptadas. Sin errores, cierre/restauración confirmados.
Es una prueba corta, no calificación sostenida de todos los instrumentos.
