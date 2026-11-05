# V20 reparada: campaña RADIO/A0 · 1/11/2026

Misma pareja V20 con el [mapa corregido y BSP fijado](V20_MEMORIA_20261101.md). ADC8/CH1 a1.860.465S/s, FFT16k, RADIO→A0 a40kHz. No se cambiaron fuentes, binario ni relay entre corridas. Cada repetición volvió a cargar el candidato y restauró V19 al terminar.

| Corrida | RADIO/A0 | Margen medio | Cola pico | Slack mínimo | Visible |
|---|---:|---:|---:|---:|---:|
|60s|60.057s|12.30%|4/16|74851ticks|100%|
|120s-1|120.036s|12.05%|5/16|69204ticks|100%|
|120s-2|120.016s|12.13%|4/16|70585ticks|100%|
|120s-3|120.089s|12.02%|4/16|67387ticks|100%|

Pasaron las cuatro corridas, incluyendo progreso/parada de RADIO, WAV sintético, Synth20voces, cierre y liberación del worker. WAV/Synth se prueban después con adquisición8bits/40kHz dual; no simultáneamente con el perfil alto. Scan, tanto normal como US, no fue solicitado en estas corridas: su aserción opcional verdadera no cuenta como prueba ejecutada.

Las tres corridas nuevas suman360s de RADIO/A0, con ventana visible100%. No hubo errores reportados de flujo/audio ni fallos de integridad. La exposición y los paint events se conservaron en cada informe; no se confunden callbacks del timer con FPS visibles.

## Reserva, restauración y alcance

Las cuatro corridas cumplen el screen privado de reserva: margen>=10%, pico<8/16 y slack positivo. El resultado legacy headroom_pass permanecefalse por su umbral absoluto<4; esto no es una aceptación pública ni prueba analógica/acústica. La cola mayor amortigua jitter; no garantiza inmunidad.

Todas las restauraciones confirmaron fuentes/caché/firmware/relay exactos, snapshot/configuración/CPU iguales y10s continuos sin pérdidas/fatales. Estado final: Q libre con V19 activa, V20 reparada detenida. No se modificaron V17/V18/V19.

Pendientes: Scan US y matriz completa de análisis/bits/tasas de audio.2MS/s conserva7,51% en el sondeo ADC corto anterior; necesita mejorar margen antes de promoción.

[Resumen y hashes de informes](../diagnosticos/resultados_v20/sram3_tail_fix_campaign_20261101.json).
