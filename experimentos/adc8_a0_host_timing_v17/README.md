# Host: tiempo de pared, CPU y observación de ACK

Un caso visible de120s por defecto (`--runs 1`, hasta3 si se solicita),
RADIO+FFT65536 CH1/RADIO y A0/40k con la fuente ordinaria burst8. Reutiliza
sin copiar ni modificar las fuentes C de `adc8_a0_command_tails_v17` y exige
su binario exacto `28b11747e564474bcbf752b0353aedd622ee4777f8db6ac95db13e470e50a135`.
MCU cc46 y N8 se conservan. El runner mantiene cache por hash, identidad,
backup, captura de reportes incluso al fallar, logs antes de borrar el
contenedor y restauración exacta. Termina al primer fallo real sin reintentar.

El helper `diagnosticos/validar_generador_radio_v17.py` sólo activa esta
instrumentación con `--host-cpu-trace`. Un deque rolling de3000 registros
habilita los relojes de CPU que el receptor ya ofrece: tiempo de pared,
CPU del thread lector y CPU del proceso, por read/decode. No cambia producción.
No se escribe JSON por frame. Las estadísticas sum/count/max y top8 se
publican al finalizar, junto con el ring acotado.

Los ocho ACK de mayor latencia se enlazan por RID con el envío pendiente,
el último read completado y la última invocación del decoder. El campo
`read_containing_completion` no representa la llegada del primer byte del
ACK: un frame fragmentado puede haber empezado en un read anterior. No se
dispone del offset del decoder por este callback. La separación entre fin
del read y observación del ACK conserva procesamiento y pausas intermedias.
Sólo se construyen registros ACK detallados cuando entran en el top8.

`wall_minus_thread_cpu_seconds` incluye bloqueo, scheduling y otras causas;
no prueba espera de GIL. La CPU del proceso incluye otros threads locales y
excluye procesos DSP hijos. Los tiempos absolutos del host y Q no comparten
origen: correlacionar RID y comparar duraciones dentro de cada reloj.
Los contadores abarcan el lifecycle completo, incluida preparación/restauración;
los timestamps permiten distinguir esas etapas de la reproducción.

```sh
.venv-v13/bin/python -m unittest experimentos.adc8_a0_host_timing_v17.test_host_trace -v
```

Ejecución reservada al coordinador tras revisar el código:

```sh
QT_QPA_PLATFORM=cocoa .venv-v13/bin/python experimentos/adc8_a0_host_timing_v17/run.py --runs 1
```

Comparación aislada opcional: `--switch-interval-ms 1` o `5`. Sólo el proceso
hijo modifica el intervalo de Python; registra valor original/efectivo y
restauración en finally. Sin flag conserva el valor del intérprete. No cambia
producción. Resultados iniciales y límites en
`host_timing_20261021_082241/comparison.json`; no equivalen a calificación.

`--qualify --switch-interval-ms 1`:60s+3×120s con reinicio por sesión y
parada ante primer fallo. La campaña `host_timing_20261021_094100` falló
UNDERRUN en la primera sesión larga: candidato no aceptado; ver
`failure_review.json`. No continuar automáticamente las sesiones restantes.
