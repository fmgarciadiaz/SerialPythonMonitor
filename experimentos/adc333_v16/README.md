# ADC333 V16 aislado

Perfil de adquisición de dos canales a un par cada 3 µs: 333333,333… pares/s (333333 en el campo entero de frecuencia del protocolo). Conserva ADC14, SPI a 32 MHz, cuatro slots, DMA TIM5 de timestamps y la validación original por muestra. No agrega esta tasa al monitor habitual.

Las fuentes MCU/relay se copiaron desde V16. Los únicos cambios MCU son el nombre de aplicación y la admisión del período 3 µs. El relay admite ese período. `acquisition.py` admite la tasa nominal 333333 y valida la correspondencia período/tasa por retorno, en lugar de exigir divisibilidad exacta de un segundo. La ventana ADC sigue en 36 ciclos / 0,72 µs, como a 250 kHz.

`run.py` compila e importa Scope V16 ADC333 Experimental como aplicación independiente, respalda la aplicación estable y toma la configuración de `prior_profile.json`. Ejecuta ADC250 durante 30 s, ADC333 durante 10 y 120 s, y ADC250 durante 30 s. Ante éxito o fallo recarga la aplicación y relay estables, restaura el perfil y comprueba otros 10 s. El ensayo requiere monitor cerrado y salidas previamente apagadas. No debe ejecutarse con una configuración previa desactualizada; guardar de nuevo el perfil del Q antes de otro ensayo.

Ejecutar desde la raíz del repositorio:

```sh
python -m unittest experimentos.adc333_v16.test_contract
python experimentos/adc333_v16/run.py
```

`results.json` contiene integridad, tasa observada, estado y restauración. Los contadores `prepare_us`/`check_us` no representan ocupación ni margen mínimo de la cola. Este ensayo no certifica precisión analógica, impedancia de entrada, funcionamiento con GUI ni synth simultáneo.

## Resultado físico del 10 de octubre de 2026

333,3 kHz rechazado en dos arranques independientes. El primer ensayo sostuvo ADC250 durante 30,000 s (7.493.632 pares); ADC333 cerró el flujo a los 0,113 s tras 28.658 pares recibidos. La repetición sostuvo ADC250 durante 10,000 s (2.496.512 pares); ADC333 volvió a cerrar el flujo a los 0,114 s tras 28.672 pares.

La trama rechazada de la repetición (`rejected_frame.json`, bytes originales en `relay_trial.log`) tiene CRC correcto, ADC14, período 3 µs, índice 28672, `dropped=1`, `fatal=0`. El contador dropped aumenta cuando el productor no consigue reservar un slot libre de la cola. Por lo tanto, el ensayo demuestra una pérdida por cola llena; no identifica todavía cuál parte del consumidor/transferencia limita el vaciado. No se deshabilitaron controles ni se aumentó la cola para ocultar la pérdida.

En ambos ensayos se restauró el MCU/relay anterior y el perfil ADC14/250 kHz con A0/WAV apagados. Las verificaciones posteriores de 10 s pasaron sin pérdidas ni errores fatales. La aplicación experimental quedó detenida. `results_first.json` conserva el primer ensayo y `results.json` la repetición. Pasaron 3 pruebas específicas del contrato y 16 pruebas del protocolo estable. La tasa nueva sigue fuera del menú habitual.

Antes de aumentar la frecuencia hay que medir y mejorar el tiempo de vaciado por nodo: a 333,3 kHz hay 6,144 ms por nodo de 2048 pares, frente a 8,192 ms a 250 kHz. Hace falta medir ocupación y tiempos de transferencia; el éxito de integridad a 250 kHz no certifica margen a largo plazo.
