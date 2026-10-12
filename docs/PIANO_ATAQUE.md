# Ataque y resonancias del piano virtual

El motor modal usa dos planos de vibración y un unísono de una, dos o tres cuerdas según registro, con desafinación leve, rigidez y relajación de tensión después del golpe. El puente disipa el movimiento común y conserva diferencias entre cuerdas. Al repetir una nota se conserva el estado vibratorio: el siguiente martillo encuentra una cuerda que aún se mueve. La velocidad entrante se aproxima constante durante el contacto; su conversión desde el estado modal es empírica, no una magnitud mecánica calibrada.

## Inicio de la nota

Se ajustaron fases acústicas por parcial contra cinco notas/velocidades de Salamander Grand Piano V3, grabaciones de Alexander Holm de un Yamaha C5, CC BY 3.0. El diagnóstico prueba cuatro intensidades de corrección y conserva solamente la que reduce el error de envolvente RMS de los primeros 150 ms. Para Do4 a velocidad MIDI 60, el error pasó de 0,521 a 0,301 dB; en Do5 no se aceptó un cambio de fase.

Una segunda identificación aproxima el residuo no armónico del contacto con ruido filtrado en seis bandas, limitado a 120 ms y moldeado por la fuerza del martillo. Su ajuste combina el error de energía por bandas con el de envolvente. No reproduce fragmentos de la grabación ni identifica de manera única el martillo o la tabla. Los parámetros se interpolan; fuera del registro medido se usan los extremos.

Los archivos reproducibles están en [ajuste de fase](../diagnosticos/ajustar_ataque_piano.py) y [residuo de contacto](../diagnosticos/ajustar_ruido_ataque.py). Los resultados y WAV de comparación están en [ataque](../diagnosticos/resultados_piano/ataque/). El archivo `perfil_antes.json` conserva el ajuste anterior. Las comparaciones usan la misma RMS y sala apagada.

## Tabla, teclas y sala

La radiación agrega reflexiones tempranas breves. La resonancia simpática contiene fundamentales y segundos parciales: las teclas sostenidas y el pedal prolongan la respuesta; el registro agudo sin apagadores conserva una cola natural. Es un banco excitado por el puente, no un acoplamiento mecánico bidireccional completo entre todas las cuerdas.

En Virtual, **Sala** controla una reverberación separada con cuatro líneas de retardo y mezcla ortogonal estable; **Cola** controla su tiempo nominal de caída. Piano Virtual inicia en 6 % y 1,2 s. La sala se aplica una sola vez después de sumar las voces. Las pruebas secas no incluyen esta etapa.

Esta aproximación sigue lejos de un piano físico comercial: falta identificar la impedancia y radiación de una tabla real, acoplamiento completo entre notas y variaciones mecánicas medidas. Mejorar métricas de ataque no garantiza similitud perceptual. Reiniciar V15 y volver a elegir Piano Virtual permite cargar el nuevo perfil.

## Verificación de esta revisión

Pasaron 142 pruebas de V15 y seis pruebas específicas del perfil/ataque tras el último cambio de caché. La prueba offline de nueve voces durante tres segundos costó 287 ms a 20 kHz y 748 ms a 40 kHz; P95 por bloque de 480 muestras: 2,30 y 3,02 ms. El primer bloque costó 23,7 y 26,4 ms respectivamente: la preparación del ataque sigue pudiendo producir un pico, especialmente a 40 kHz (presupuesto de bloque 12 ms). Estos datos no prueban estabilidad del transporte ni latencia física; esta revisión no operó el Q. Los WAV del diagnóstico usan sala apagada, mientras que el preset inicia con sala suave.
