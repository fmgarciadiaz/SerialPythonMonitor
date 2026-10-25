# READY: flanco aceptado, retorno y SPI posterior

Segundo experimento aislado, copiado de `adc8_relay_timing_v17`. No modifica
la copia anterior, el relay certificado ni el MCU cc46. Mantiene ADC-only,
nodo3456/cola8/SPI40/WORD, CPU2/performance/FIFO10, spin50µs, frecuencia de
accept y heartbeat original. El runner mide 60s por tasa (1.600.000 y 1.632.653),
sin reintentos, con backup y restauración exacta al finalizar.

`Ready.accepted_edge_ns` sólo se asigna al aceptar un flanco después de
validar secuencia y timestamp posterior al SPI previo. Se borra al iniciar
cada espera y al entrar en `ready_initial`; un crédito inicial por nivel alto
sin flanco aceptado conserva cero. Los eventos GPIO usan el reloj monotónico
del kernel y no se solicita EVENT_CLOCK_REALTIME.

Además de los histogramas originales, por ticks100/98 se guardan:

- `ready_edge_age`: retorno de la espera menos timestamp del flanco válido.
- `edge_before_wait`: inicio de espera menos flanco, cuando ya existía.
- `edge_after_wait`: flanco menos inicio de espera, cuando llegó después.
- Contadores válidos, ausentes, anteriores al SPI previo y futuros.
- Contadores preexistente/nuevo e igualdad: la igualdad pertenece a ambos.
- Hasta ocho esperas >1ms, conservando las mayores: inicio, flanco, retorno,
  ticks y secuencia anterior al SPI. Después de validar el paquete siguiente
  se añaden `rx_kind`, `rx_sequence` y, si kind20, nodo, cola, pico, `produced`,
  cantidad de muestras y epoch. `rx_valid`/`has_adc_metrics` distinguen datos
  disponibles de ceros iniciales, incluso si el SPI falla.
- Duración separada de `recv`, `accept` y camino acotado de envío; se conserva
  también el intervalo global `socket_control_send`.

Las regiones temporales se superponen: no son causas mutuamente excluyentes
ni deben sumarse como diagnósticos causales. El timestamp del kernel no es una
medición de osciloscopio del pin; la latencia anterior a su timestamp, incluida
la atención de IRQ, queda sin resolver. El paquete posterior correlaciona la
espera con el estado observado, sin demostrar por sí mismo que faltaran nodos.

Almacenamiento fijo, sin I/O por frame. JSON `SPM_RELAY_TIMING` versión2 sólo
en baja o al salir. Se conserva la calibración inicial y los contadores de
segmentos/iteraciones completas; un error puede dejar segmentos incompletos.
El runner comprueba las fuentes certificadas y sólo permite diferencias en
`base_verifier.c`, `unoq_config_stream.c` y el nuevo `relay_timing.h`.

Prueba offline, sin Q:

```sh
.venv-v13/bin/python -m unittest experimentos.adc8_relay_edge_v17.test_timing -v
```

Ejecución física reservada al coordinador tras revisar y compilar la rama Linux:

```sh
.venv-v13/bin/python experimentos/adc8_relay_edge_v17/run.py
```
