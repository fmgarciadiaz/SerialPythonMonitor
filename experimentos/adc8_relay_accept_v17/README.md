# Accept N1/N8, comparación pareada a 1.632.653 muestras/s

Experimento nuevo desde `adc8_relay_edge_v17`, conservando instrumentación
READY/SPI, colas y timings. No modifica experimentos anteriores ni producción.
El primer bloque compara **una tasa**, ADC8 CH1/1.632.653, durante 60s con
N1 y 60s con N8. Ambos casos usan el mismo binario de relay instrumentado y
el mismo MCU cc46. Cada caso arranca MCU/relay a baja carga; no se reutiliza
un resultado anterior como control ni se reintenta un fallo.

`SCOPE_ADC8_ACCEPT_EVERY` se lee una vez al arrancar: sólo admite `1` o `8`,
con valor por defecto `1`. La nueva política actúa únicamente con un cliente
activo y el perfil exacto ADC8 CH1 ticks100/98 nodo3456. N8 ejecuta `accept`
cada ocho frames válidos. Con ningún cliente o cualquier otro perfil, el
contador se reinicia y `accept` sigue ocurriendo en cada iteración permitida
por las guardas existentes contra ACK antiguos. `recv` y `send` no se omiten.
Una nueva conexión aceptada mientras otro cliente sigue activo se cierra;
el cliente existente conserva ownership. Ocho frames representan unos 4,2ms
nominales en este perfil; no constituyen un límite de latencia por reloj.

Se conservan SPI40/WORD, nodo3456/cola8, CPU2/performance/FIFO10, spin50µs,
heartbeat de 10s y cadencia de los demás caminos. Los histogramas y tails
READY conservan las limitaciones descritas en el experimento EDGE: timestamp
del kernel, no osciloscopio; regiones superpuestas y correlación sin causalidad.

El JSON de baja/salida añade `accept_every`, frames que alcanzaron la política,
llamadas y omisiones. El reporte calcula llamadas por frame y tiempo de pared
de `accept` por frame; ese tiempo no es tiempo de CPU. Conservar la integridad,
los máximos y el comportamiento de cola además del ahorro de llamadas.

El runner deriva del lifecycle A/B anterior. Inyecta la variable sólo al relay
experimental; al restaurar recupera exactamente el entorno, mounts, cpuset,
relay, firmware, ADC y generador previos. Los logs se leen después de volver
a baja. La identidad del MCU debe seguir siendo
`cc46e4f798a39edfb8e5bd2db8ecd510dd40fee3f10e89c69978de4191156223`.

Pruebas offline:

```sh
.venv-v13/bin/python -m unittest experimentos.adc8_relay_accept_v17.test_accept experimentos.adc8_relay_accept_v17.test_timing -v
```

Ejecución reservada al coordinador después de revisión y compilación Linux:

```sh
.venv-v13/bin/python experimentos/adc8_relay_accept_v17/run.py
```
