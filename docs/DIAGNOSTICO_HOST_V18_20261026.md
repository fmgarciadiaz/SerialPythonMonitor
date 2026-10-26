# Diagnóstico host y trazabilidad de tasas · 26/10/2026

Primer bloque implementado tras la revisión con Astra. No cambia tasas,
firmware, relay, prioridades, capacidades, criterios de corte ni permisos A0.

## Límites host

`FlowLimitExceeded` sigue siendo RuntimeError, pero conserva un objeto
`details` con recurso agotado, valores previos/proyectados, límites, picos y
contexto de adquisición. DeliveryBudget registra picos de muestras, tiempo,
memoria y lotes durante la sesión; un rechazo no reserva ni elimina datos.
El receptor añade detalles al snapshot antes de finalizar el ciclo de lectura.
El valor RF previo incluye los chunks anteriores, además de lotes retenidos.

Los límites siguen siendo 1 s, 1,6 millones de muestras, 64 MiB y 256 lotes en
la entrega GUI, junto con los límites originales del receptor. Las capturas de
fallo del worker incluyen límites/picos y, cuando existe, el motivo estructurado.

## Evidencia visible en el selector

`rate_evidence.json` es un resumen de sólo lectura derivado de informes
verificados. `tools/build_rate_evidence_v18.py` lo reconstruye sin tocar el Q.
Incluye 37 geometrías, identificadas por bits, canales, ticks y tamaño de nodo.
El loader exige hashes de firmware y relay iguales a la pareja aceptada;
si cambian o faltan datos, el tooltip informa que no hay medición registrada.

Se distingue ADC sin audio, holgura ADC sin audio, prueba funcional RADIO/A0,
visibilidad y ausencia de medición de holgura conjunta. Se conserva la evidencia
histórica en los perfiles, sin atribuirla a otra pareja. En los anclajes de audio,
el informe con la pareja integrada duró 15 s; por eso no se presenta como 60 s.
Los 60 s del primer binario y el resto del historial siguen en sus informes.
La identidad descrita es la pareja aceptada localmente, no una lectura en vivo.

## Validación

Pruebas de fronteras exactas y cada recurso, rechazo sin mutación, picos tras
liberación, snapshot del worker, sobrecarga en proceso real y lectura completada
antes del cierre. Se cubre acumulación en dos bloques para verificar el valor
RF previo. Pruebas de evidencia: hash distinto, geometría distinta, archivos
inválidos, reconstrucción exacta, duración real y tooltip del máximo ADC8 sin
heredar holgura histórica.

Revisión de Astra aprobó el enfoque y detectó la omisión de chunks previos en
el primer diagnóstico RF; se corrigió antes del cierre. Una corrida completa
posterior tuvo un timeout aislado de arranque en test_acquisition_process;
la familia de 10 pruebas pasó al repetir. Se conserva el informe fallido.

## Siguiente bloque: relay aislado

Preparar candidato sólo de relay, manteniendo firmware exacto, con contadores
acumulados de tiempo SPI/READY, máximo intervalo de servicio, pico de backlog,
EAGAIN y envíos parciales. Emitir resumen de baja frecuencia y captura de fallo;
no escribir por cada trama. Medir el coste frente al relay sin instrumentar.
No añadir consultas administrativas durante un ensayo ni reiniciar el Q mientras
la GUI sea propietaria. Antes de desplegar: respaldo de fuentes/binarios/estado,
comparación aislada y restauración verificada de la pareja aceptada.

El fallo ADC8 original no se considera resuelto por estos cambios de diagnóstico.

Cierre: regresión completa 247/247 y selector 5/5 aprobados.
Evidencia: `diagnosticos/resultados_v18/host_diagnostics_20261026/`.
175 archivos V17 y47 fuentes Arduino V18 verificados sin cambios.
