# Controles visibles: RF, RADIO y A0 · 31/10/2026

Con la ventana visible se realizaron tres controles sobre la pareja aceptada,
sin O2, IPC500, READY250 ni pacing privados. Misma adquisición ADC8/1.860.465
S/s, FFT16k y actividad user de gráfico/receptor. Observador y temporizadores
privados iguales en los tres casos. No se modificó código de producción ni
tasas. V17/V18 intactas.

| Modo | Exposición periódica | Margen medio MCU | Pico acumulado | Resultado |
|---|---:|---:|---:|---|
| RF/FFT, RADIO y A0 apagados | 100% | 18,37% | 2 | Control breve PASS |
| RADIO en PC, A0 apagado | 100% | 18,23% | 2 | Control breve PASS |
| RADIO→A0, 60,023s de audio | 100% | 10,33% | 6 | Audio funcional; holgura FAIL |

Los dos primeros harness duraron45s y reunieron79.345.024/79.463.616 muestras
RF útiles (aproximadamente42,6/42,7s a esta tasa). Cumplieron las aserciones
de progreso FFT/RADIO y A0 apagado. El tercer caso tuvo sintonía fija710kHz
sin resintonía deliberada, con2.400.960muestras DAC reproducidas: el número
exacto debe consultarse en `gui.json` porque las observaciones de arranque/
Stop pueden desplazar un bloque en los extremos.

No hubo pérdidas/fatales ni errores de flujo/audio en estos controles. Eso
no convierte el pico6 en aceptación de holgura ni demuestra ausencia de
cortes intermitentes a mayor duración. No se extendió a3×120s.

## Alcance de la conclusión

En estas ventanas, encender la demodulación RADIO sin A0 no mostró un cambio
importante del margen/cola frente a FFT sola. Los conteos de comandos enviados
al Q fueron idénticos en los dos controles sin A0; no se trató de un enlace
sin ningún RPC (hubo consultas/control normales).

La degradación aparece al añadir la ruta completa RADIO→A0. Esa ruta incluye
peticiones/entrega PCM en el host, CHUNK/ACK, transferencias SPI y servicio
WAV/DAC en MCU. Los tres controles no separan todavía sus contribuciones;
no prueban que el cálculo DSP sea gratis ni identifican una causa única.
Además, los promedios sin A0 abarcan toda su adquisición objetivo y el valor
con A0 corresponde a PLAY: no es un ensayo estadístico apareado.

En el tercer control, el pico subió a3/4/5 durante PREPARING y a6 durante
PLAY (nodo27438). El criterio sigue incluyendo el arranque completo, sin
sustituirlo por ocupación muestreada ni bajar el umbral.

## Próximo diagnóstico acotado

Relacionar las duraciones `prepare_us/check_us` ya emitidas por el MCU con
ACK de CHUNK/QUERY y la mezcla de mitades físicas. Revisar su orden exacto
en el bucle antes de atribuir costo a una operación: acompañar un ACK no
significa por sí solo simultaneidad causal.

La inspección estática de `wav::submit` confirma validación y publicación de
muestras dentro de una región con IRQ bloqueadas. Es un punto para medir,
no una causa demostrada ni autorización para mover límites de IRQ/propiedad
sin revisión. Conservar CRC, reservas y EOT. No seguir ajustando cadencias
a ciegas ni subir tasas con la evidencia actual.

Cada sesión confirmó restauración; verificación final independiente10,025s,
313.344muestras, cero pérdidas/fatales, snapshot e identidades aceptadas iguales.
Q libre y pareja aceptada activa. Los únicos cambios de este bloque son
informes/continuidad; no hubo cambios de implementación ni tests nuevos.

[Consolidado](../diagnosticos/resultados_v19/visible_controls_20261031/summary.json)
· [Verificación final](../diagnosticos/resultados_v19/visible_controls_20261031/final_verification.json).
