# Pausas del receptor y envíos lentos · 30/10/2026

Se instrumentaron campos existentes del MCU en el observador privado:
ocho mayores envíos de nodo y contexto de cada aumento del pico de cola.
No se modificaron firmware, relay, cadencias, buffers ni tasas públicas.

## Resultados físicos

ADC8/1.860.465 S/s, FFT16k, RADIO/A0 a 40 kHz; pareja aceptada.

| Corrida | Audio | ACK hasta lectura completa | Etapas receptor ≥100 ms | Margen MCU / pico |
|---|---|---:|---|---|
| Primera, actividad user | 92,31 s; harness FAIL por opciones mezcladas | 37,99 ms | Ninguna | 10,12 % / 5 |
| Repetición user | UNDERRUN; 408.960 muestras reproducidas | 414,05 ms | pump 115/248 ms; tick 105 ms | 10,52 % / 4 |
| Actividad critical | 60,078 s, sin errores | 38,22 ms | Ninguna | 10,26 % / 5 |

La primera orden mezcló `--analysis-mode fft`, cuyo contrato exige A0 apagado,
con una retención RADIO/A0. Se conserva su error `a0_remained_off`; no se
contabiliza como prueba funcional aprobada. La repetición correcta omitió
esa opción y reprodujo el UNDERRUN. No se alteraron informes históricos.

En el fallo, `pump_global` duró 248,94 ms con 32,14 ms de CPU del hilo;
`tick` duró 105,28 ms con sólo 0,35 ms de CPU. Esto muestra espera/desplanificación
en esas etapas, sin identificar si es IPC, bloqueo u otra causa. El ACK
es tiempo comando→lectura completa en espacio de usuario, no llegada al kernel.
El retraso máximo lectura→handler fue 15,33 ms.

La actividad crítica de macOS ya existía como opción del harness. La opción
`--macos-activity critical` de esta corrida se aplicó al proceso gráfico;
el receptor mantuvo su modo `user` (evidencia de sesión). Su corrida
sin pausas largas es sólo un contraste exploratorio: faltan repeticiones
independientes y control de carga. No se incorporó como nuevo valor por defecto.
La cola MCU siguió alcanzando 5, de modo que tampoco acredita holgura.

## Interpretación de los contadores

En la primera corrida, el envío de nodo más lento fue de 7,01 ms. Los
máximos acumulados de copia y sondeo DMA observados allí fueron 0,25 y
1,43 ms. Los campos de preparación y chequeo pertenecen al intercambio
físico anterior; copia/sondeo son máximos acumulados y el envío pertenece
al nodo anterior. Compartir una observación no implica simultaneidad.
No sumar ni atribuir causalidad entre esos contadores.

El observador guarda sólo ocho registros de envíos lentos, deduplicados por
inicio de nodo/época, y enriquece los eventos de pico existentes. No conserva
arrays RF. Dieciséis pruebas dirigidas PASS, incluidas CRC/perfiles,
deduplicación, límite de registros y significado de los campos.

## Continuación

1. Medir por separado las lecturas no bloqueantes de colas IPC dentro de
   `tick`, sin cambiar su política ni perder muestras. Una llamada no bloqueante
   puede incluir trabajo de recepción/deserialización; el origen sigue abierto.
2. Contrastar user/critical en corridas independientes con la misma carga.
3. Para MCU, correlacionar los peores envíos con tiempo de ciclo completo
   del relay, incluyendo huecos entre etapas; las medidas agregadas previas
   no cubren todos esos huecos. Mantener EOT y criterios de aceptación.

Cada sesión confirmó apagado/restauración. La verificación final independiente
se conserva en `node_tails_critical_20261030/final_verification.json` con 10 s,
snapshot original y hashes aceptados. V17/V18 permanecen intactas.

[Evidencia y resumen](../diagnosticos/resultados_v19/node_tails_critical_20261030/summary.json)
· [Combinaciones anteriores](COMBINACIONES_RADIO_V19_20261030.md).
