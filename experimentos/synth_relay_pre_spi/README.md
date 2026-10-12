# Consulta de comandos PC antes de SPI

Candidato aislado: mueve recv no bloqueante después de READY y antes de SPI,
sin ampliar cola de comandos ni alterar CRC, secuencias o el crédito READY.
Compiló en Q con -O2 -Wall -Wextra -Werror.

Ensayo 30 s, Synth20kHz/ADC100k, 11 voces y pedal simulado: sin cortes ni
pérdidas, pero target5→7, cola mínima2, generación37,79ms, ACK55,49ms y
gap57,09ms. No demostró mejorar la cola; no se promovió. Relay estable y
ADC14/40k/generador deshabilitado/WAV IDLE restaurados y verificados.
La fuente estable coincide byte a byte con la del binario previo del Q.

Evidencia: `diagnosticos/resultados_piano/eficiencia_v16/20261010_045234_cola_fisica.json`
y `relay_trial_restoration.json` en la misma carpeta.
Candidato compilado aislado en Q:
`/home/arduino/.cache/serialmonitor/usb-stream-7156b2fe6d8224f14406/unoq_stream`.
El ensayo requiere Q libre y se ejecuta con
`diagnosticos/probar_relay_synth_v16.py --candidate-binary <ruta_Q>`;
conserva el contenedor previo y lo restaura al finalizar.

Comparaciones con ensayos anteriores no son A/B controlado. Tiempo envío→ACK
incluye pausas del host mientras genera otros bloques; no mide RTT puro ni
permite atribuir toda la demora al relay/Q. Latencia acústica no medida.
