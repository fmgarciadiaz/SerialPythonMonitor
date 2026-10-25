# Tiempos del relay ADC8, experimento aislado

Preparado sin ejecución física. Copia del relay certificado de
`fs_max_all_bits_v17`, con instrumentación y un runner ADC-only de 60s por
tasa: 1.600.000 y 1.632.653 muestras/s. El MCU debe conservar exactamente
`cc46e4f798a39edfb8e5bd2db8ecd510dd40fee3f10e89c69978de4191156223`.
Nodo3456, cola8, SPI40, WORD, CPU2/performance y FIFO10 se mantienen iguales.
El host privado normaliza ambas entradas mediante 14/40k → 8/1.428.571 →
espera conectada de 0,5s → objetivo. No se modifican fuentes certificadas,
perfiles guardados ni producción. No se propone optimización en este bloque.

`relay/relay_timing.h` guarda histogramas fijos en memoria para ticks100/98.
Por cada iteración cuya configuración al entrar coincide se observan:

| Campo | Intervalo |
| --- | --- |
| ready_wait | espera de READY |
| command_policy | política del comando previo al SPI |
| spi_ioctl | llamada SPI_IOC_MESSAGE |
| checker_policy | validación del paquete y transición de política |
| socket_control_send | control TCP, accept y envío |
| heartbeat | comprobación y log periódico original de 10s |
| frame_wall | iteración completa, incluyendo huecos entre segmentos |

Los tiempos son monotónicos; sumas y máximos están en ns, límites de bins
en µs, con último bin de overflow. El número de llamadas de cada segmento
se conserva separadamente de iteraciones iniciadas/completadas. Un `continue`
o error puede omitir segmentos: no afirmar que `frame_wall` es su suma.
El pico de cola TCP es una observación al final del envío, no un historial
de cada cambio interno. Las llamadas de reloj y actualización del histograma
añaden coste; un control inicial de 128 pares de reloj mide su coste local
antes del bucle, sin añadir llamadas de calibración por frame. No descuenta
ese coste de los resultados ni demuestra overhead físico bajo carga.

Sólo se emite una línea JSON `SPM_RELAY_TIMING` al terminar una iteración
en perfil legacy ≤40kHz, o al salir del proceso. No se emite al pasar entre
perfiles altos. Cada emisión reinicia contadores y conserva la calibración.
No hay asignación dinámica, logs por frame ni consultas administrativas nuevas
durante la adquisición alta. Se conserva el heartbeat original de 10s.

El runner `run.py` conserva ownership exclusivo, backup, caché del relay por
hash, verificación de MCU, vuelta a baja antes de leer logs y restauración
exacta de firmware/relay/configuración/generador con comprobación de 10s.
El nuevo relay tiene identidad distinta y queda registrada; no se compara su
hash con el binario original. Falla el primer caso → no se intenta el segundo
ni se repite el fallo. El promedio de envío del helper heredado no deduplica
`produced`: estos histogramas y picos se analizan aparte de ese promedio.

Validación offline:

```sh
.venv-v13/bin/python -m unittest experimentos.adc8_relay_timing_v17.test_timing -v
```

La ejecución física queda para el coordinador después de revisión:

```sh
.venv-v13/bin/python experimentos/adc8_relay_timing_v17/run.py
```

Leer los histogramas para localizar dónde aparecen los máximos; no inferir
pérdida de muestras a partir de una pausa del host ni extrapolarla directamente
a la capacidad temporal de las colas del MCU.
