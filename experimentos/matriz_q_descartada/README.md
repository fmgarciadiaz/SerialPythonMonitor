La función de iconos LED fue retirada a pedido del usuario el 2026-10-10, para priorizar captura y audio. No está integrada en V16. Los archivos `.txt` son evidencia del intento; no son fuentes activas ni una variante aceptada para desplegar.

El controlador de matriz del core Zephyr 1.0.0 genera una interrupción cada 10 us. La primera implementación pasó un minuto de ADC14 a 40/250 kHz con cambios de iconos, pero las dos pasadas de guitarra con matriz encendida necesitaron crecer de cinco a siete/nueve bloques; la pasada intermedia con matriz apagada mantuvo cinco bloques. No hubo cortes ni pérdidas ADC/IPC, pero esa diferencia motivó investigar el refresco. Estas tres pasadas no aíslan definitivamente la causa: también hubo esperas variables del host y del transporte.

Se empezó un controlador PWM de menor carga; el usuario solicitó quitar la función antes de compilarlo o instalarlo. No se valida ese código. Se restauraron las fuentes activas previas del monitor, firmware, relay, diagnóstico de audio y pruebas. Las fuentes MCU se compararon byte por byte con `respaldos/unoq/osciloscopio_20261010_223900_913474.zip` antes de volver a cargarlas, y se seleccionó el binario de relay correspondiente al hash previo.

Evidencia del intento:

- `diagnosticos/resultados_v16/20261010_224219_matriz.json`: 2.398.208/14.989.298 pares continuos a 40/250 kHz, 119/120 cambios confirmados, dropped/fatal=0.
- `diagnosticos/resultados_piano/eficiencia_v16/20261011_014500_audio_owner.json`: matriz encendida, crecimiento a siete bloques, generación máxima 56,784 ms.
- `diagnosticos/resultados_piano/eficiencia_v16/20261011_014635_audio_owner.json`: matriz apagada, cinco bloques, generación máxima 19,056 ms.
- `diagnosticos/resultados_piano/eficiencia_v16/20261011_014751_audio_owner.json`: matriz encendida, crecimiento a nueve bloques, envío-a-ACK máximo 61,326 ms.

El flujo anterior a esta función ya se había detenido por un nodo perdido a ADC14/250 kHz. Se guardó `respaldos/synth/20261010_led_modes/prior_relay_failure.json`. Tras recuperar el Q se dejó ADC14/250 kHz con generador deshabilitado y WAV IDLE; no se afirma haber identificado la causa de aquella pérdida ni preservado parámetros de generador que no pudieron consultarse con el flujo detenido.

Restauración completada: firmware y relay previos en ejecución, capacidades WAV=7 (sin función de matriz). `diagnosticos/resultados_v16/20261010_matriz_retirada_restauracion.json` registra 10,003 s/2.496.738 pares ADC14 a 250 kHz, dropped=0/fatal=0 y período/índices estrictamente continuos. Generador deshabilitado, WAV IDLE. Pasaron 88 pruebas FM, latencia, protocolo compacto, WAV, créditos y dueño de audio. Los seis archivos principales coinciden byte por byte con sus respaldos anteriores a esta función; no se retiraron las optimizaciones previas del synth y MIDI.
