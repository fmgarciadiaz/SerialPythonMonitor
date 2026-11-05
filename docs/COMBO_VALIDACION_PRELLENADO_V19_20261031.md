# Validación PCM y prellenado uniforme · V19

La comparación previa RF/FFT, RADIO en PC y RADIO→A0 señala que añadir la
ruta A0 reduce el margen observado de aproximadamente18% a10%. No identifica
una causa única: incluye PCM del host, CHUNK/ACK, transferencia SPI, validación,
copia/caché y servicio WAV/DAC. A0 ya usa TIM6 y DMA con descriptores enlazados.

Este candidato combina dos cambios privados ya ensayados por separado:

- Firmware: recorrido de validación PCM antes de `irq_lock`; publicación y
  propiedad DMA siguen protegidas. Mismo BIN privado exacto del ensayo anterior.
- Host: prellenado de1 bloque cada8ms, vuelve a ráfaga8/6ms durante PLAY.

No combina O2, espera READY, backoff IPC ni intervalos QUERY nuevos.
No cambia reservas, perfiles, tasas públicas, V17 ni V18. Se usa el launcher
normal, respaldo pareado y restauración comprobada en cada ensayo.

El cambio de validación solo llegó a pico4 durante PREPARING; el prellenado
uniforme solo antes pasó20s pero llegó a pico4 en PLAY durante60s. Combinarlos
es una hipótesis nueva, sin garantía de éxito ni aceptación por asociación.

Los resultados crudos se conservan en
`diagnosticos/resultados_v19/wav_validation_prefill20_20261031/`.

## Primera combinación: PLAY8

20,026s,800.640muestras DAC,100% exposición,578paint events; RADIO/WAV/FM,
paradas y cierre funcionales, cero errores. PLAY margen10,58%,slack80.627ticks,
pico4: FAIL de holgura. PREPARING mantuvo pico2. PLAY subió a3 y luego4:
el segundo aumento fue5,549s después del primero, no sólo una transición
instantánea. El registro de los8CHUNK recientes muestra varias peticiones
separadas por~50µs cerca del aumento, sin probar causalidad de una en particular.

No60/120s. Restauración10,024s,313.344muestras,0pérdidas/fatales; materiales,
snapshot,CPU/configuración e identidad originales verificados.

La siguiente combinación mantiene el mismo firmware y prellenado, con PLAY
limitado a2bloques/6ms (herramienta privada existente). Esta cadencia ya tuvo
pruebas anteriores con otros candidatos: no se acepta automáticamente en ésta.

## Segunda combinación: PLAY2

20,094s,803.520muestras DAC,100% exposición,629paint events. RADIO/WAV/FM,
paradas y cierre funcionales, cero errores. Margen9,28%,slack84.079ticks,
pico4: FAIL de holgura por margen y pico. PREPARING mantuvo pico2, PLAY
subió a3 y a4; ambos aumentos separados15,380s. No60/120s ni promoción.

| Combinación con el mismo firmware privado | Margen PLAY | Pico acumulado | Estado vacío durante PLAY |
|---|---:|---:|---:|
| Prellenado1/8ms, PLAY8/6ms |10,58%|4|710|
| Prellenado1/8ms, PLAY2/6ms |9,28%|4|1.420|

Los tiempos PLAY son aproximadamente20s en ambos casos. En PLAY2 aumentaron
las tandas físicas observadas (23.106 frente a22.737) y las mitades/estados vacíos;
prepare/check medios también fueron ligeramente mayores. Son ventanas cortas
sin repetición estadística: muestran que este cambio no resolvió el problema,
no establecen una ley general ni una causa única. `check_us` no mide sólo IRQ.

Ambas restauraciones exactas pasaron. Consultar el resumen para la duración y
muestras de cada verificación. No cambió ningún runtime ni tasa pública.

[Resumen conjunto](../diagnosticos/resultados_v19/wav_validation_combinations_20261031/summary.json).

## Próximo paso con fundamento

No continuar reduciendo ráfagas a ciegas: este ensayo empeoró el aprovechamiento
de las transferencias. Separar el costo de validar/copiar/caché y el tiempo real
con IRQ bloqueadas mediante un diagnóstico privado con contrato explícito.
Mantener intactas validación CRC, propiedad de nodos hasta EOT y reservas DMA.
El DMA del DAC ya existe; poner «más DMA» sin identificar ese costo no resuelve
el tráfico ni el servicio por bloque.
