# V20: carga Synth sostenida y fallo observado a 40 kHz

## Evidencia conservada del preset DX Piano

La campaña `v20_synth60_rates_campaign_20261102_085748` usó el preset del panel **DX Piano**, con tres osciladores. A DAC20k completó60,0086s de PCM pero las599observaciones de voces tuvieron mínimo0/máximo20: no demuestra20voces sostenidas. A DAC40k hubo PLAY a34,2572s y estadoUNDERRUN a36,2545s, antes del cierre36,305s y deSIGINT posterior~41,91s. No fue sólo una cancelación del ensayo. Se observaron20voces durante ese tramo de unos2s. Ambos casos recuperaron V20≥10s/313.344muestras/0pérdidas-fatal, con identidad y recibos iguales.

La captura40k tiene generaciónPCM máxima32,25ms y una respuesta con render9,29ms más espera6,59ms e IPC. Un bloque480a40k dura12ms. Los máximos no son el coste medio ni prueban una causa exclusiva; no se declara arreglado el fallo. Los ACK no muestran en esa captura un pico comparable al retraso de230ms de otro ensayoRADIO.

- [DX Piano20k](../diagnosticos/resultados_v20/v20_synth60_rates_campaign_20261102_085748_dac20k/report.json).
- [DX Piano40k: fallo anterior a señal](../diagnosticos/resultados_v20/v20_synth60_rates_campaign_20261102_085748_dac40k/report.json).

## Perfil privado de control sostenido

Sol alcanzó cuota; el coordinador continuó con cambios **sólo en herramientas y tests**. `--synth-profile sustained-fm` usa20notas mantenidas, FM básico de un oscilador y ADSR con sustain0,7. No modifica presets del programa ni representa el coste de DX Piano. `panel` sigue siendo el valor por defecto. El ensayo rechaza un pase sostenido si sus observaciones durantePLAY no conservan las voces solicitadas.

23tests focalizados PASS, incluyendo motor real a20/40k, conservación de parámetros del panel y rechazo de observaciones con voces extinguidas. Medición local después de cuatro bloques de calentamiento,50bloques por tasa, excluyendo IPC/Q/analógica:

| DAC | Duración bloque480 | Generación media | Máxima | Voces mín/máx |
|---|---:|---:|---:|---:|
|20kHz|24ms|1,411ms|1,586ms|20/20|
|40kHz|12ms|1,121ms|1,274ms|20/20|

[Medición local](../diagnosticos/resultados_v20/synth_sustained_local_20261102/render_benchmark.json).

## Separación de fallos

El primer ensayo físico del perfil no llegó a Synth: al salir deRADIO ADC8/1,86MS/s excedió el presupuesto de entregaGUI (1.604.480/1.600.000muestras). V20 recuperada, identidad igual. No es un resultado de rendimiento Synth. Se conserva sin elevar límites para ocultarlo.

[Ensayo detenido en entregaGUI](../diagnosticos/resultados_v20/v20_sustained_fm_campaign_20261102_dac20k/report.json).

Se añadió `--radio-rate40000` opcional al helper, con sintonía10kHz dentro de banda, para aislar el Synth usandoADC40kdual desde el principio. El valor predeterminado del helper sigue1,86MS/s. Esto cambia las condiciones de control: sus resultados no califican carga de adquisición alta ni arreglan el falloGUI o DX Piano.

## Preparación y observación a baja adquisición

El primer lanzamiento aislado fue rechazado por la herramienta antes de abrir su conexión de datos: el observador exigía un perfil nativo. Se añadió soporte **explícito** para diagnóstico de ACK/servicio con perfiles no nativos en la ruta privada V20. Los valores por defecto del observador anterior no cambian. Para el objetivo40k el informe indica `native_counters_expected=false` y `performance_acceptance_eligible=false`: no inventa contadores de MCU. Tests del opt-in, restauración de hooks y exclusión de aceptación nativa PASS.

El segundo lanzamiento aislado alcanzó la preparación Synth, pero excedió el límite de RF pendiente1s antes de PLAY. La GUI registró pausa de1,923s y demora de entrega1,888s; el lector no registró una etapa lenta equivalente. V20 recuperada e identidad igual. Se detuvieron repeticiones simples y se activó el rastreo de pilas existente (`--stall-trace`) para el siguiente control.

- [Rechazo del observador antes de abrir datos](../diagnosticos/resultados_v20/v20_sustained_fm_isolated_20261102_dac20k/report.json).
- [Pausa de GUI durante preparación](../diagnosticos/resultados_v20/v20_sustained_fm_isolated_retry_20261102_dac20k/report.json).

La siguiente corrida con rastreo no reprodujo esa pausa: a DAC20k pasó60s con20voces en todas las observaciones dePLAY y recuperaciónV20 verificada. La preparación+PLAY tomó28,66s, dentro del límite del ensayo, manteniendo la GUI expuesta. El archivo de pilas no capturó pausas≥0,7s en esta corrida; no localiza la causa del fallo anterior. No se declara arreglado el problema de GUI/FlowLimitExceeded.

[Control sostenido20k](../diagnosticos/resultados_v20/v20_sustained_fm_stalltrace_20261102_dac20k/report.json).


## Cierre de controles físicos

- DAC20kHz: hold60.010s, 601observaciones de voces mín/máx20/20, exposición100.0%, ACK observados4543/4543. RecuperaciónV20≥10s/0pérdidas-fatal y hashes/recibos iguales. [Informe](../diagnosticos/resultados_v20/v20_sustained_fm_stalltrace_20261102_dac20k/report.json).
- DAC40kHz: hold60.094s, 602observaciones de voces mín/máx20/20, exposición100.0%, ACK observados7051/7050. RecuperaciónV20≥10s/0pérdidas-fatal y hashes/recibos iguales. [Informe](../diagnosticos/resultados_v20/v20_sustained_fm_stalltrace_20261102_dac40k/report.json).

El control usa ADC40kdual desde el inicio y FM básico de un oscilador con notas mantenidas; no es la carga DX Piano ni adquisición alta simultánea. La afirmación20voces corresponde a todas las observaciones del tramoPLAY, no a una medición analógica continua. Se mantuvo V20 activa, generadorOFF al recuperar y recibo de trabajo sin cambios. No se inicióV19. No se modificó el motor de audio ni se elevaron límites de flujo para lograr estos pases.

Los fallos DX Piano40k y GUI/RF anteriores siguen abiertos. La comparación ayuda a acotar condiciones, pero cambia perfil y carga inicial respecto del fallo original; no demuestra una causa exclusiva. [Resumen consolidado](../diagnosticos/resultados_v20/v20_sustained_fm_control_summary_20261102.json).

En el control40k quedó una correlación diagnóstica incompleta al cierre (7.051ACK leídos/7.050observados al entrar al manejo). Las confirmaciones dePLAY/STOP/hold y la recuperación sí pasaron. No se interpreta ese contador como pérdida de transporte ni se oculta como diagnóstico completo.
