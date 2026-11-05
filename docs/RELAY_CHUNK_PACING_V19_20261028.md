# Relay privado: admisión alternada de CHUNK · 28/10/2026

Continúa la [medición de intercalado SPI](RADIO_SPI_V19_20261028.md).
La pareja aceptada no se modifica. Las fuentes privadas se clonaron directamente
de `arduino/v19/relay/` a
`diagnosticos/resultados_v19/relay_chunk_pacing_sources_20261028/relay/`.
No se combina con el candidato anterior de FIFO/registro de errores.

## Única diferencia funcional

El relay admite un CHUNK como máximo en batches alternados exclusivamente
con perfil confirmado SPI/ADC8/CH1/86ticks/3488muestras. Se identifica mediante
`scope_native_find(checker.bits, checker.period)`: `period` está codificado y
no se compara directamente con86. Fuera de ese perfil conserva el comportamiento.

La primera mitad sigue llevando PING; la segunda lleva un comando completo
o PING si se posterga CHUNK. El comando pendiente conserva bytes/identificador,
no se lee otro comando TCP mientras esté retenido, y se confirma la admisión
únicamente después del intercambio y validación física completos.

STOP/QUERY/BEGIN/PLAY/configuración/generador no reciben postergación propia.
FIFO se conserva: STOP no salta CHUNK todavía delante en TCP. ConN bloques
delante puede haber hastaN batches adicionales, sin cota wall-clock dura.
El guard existente de reconexión conserva pending/previous_tx/respuestas
abandonadas. Un fallo físico sale sin reintento de efecto incierto.

El relay no distingue RADIO de WAV: afecta todo CHUNK bajo ese perfil ADC.
Para el contraste RADIO se mantiene fijo el candidato host ACK-refresh, con
burst8 y todos los demás límites originales. No cambia firmware, ADC, tasa,
buffers, propiedad de nodo, EOT ni política de CPU/SPI.

## Revisión y pruebas antes de hardware

Astra revisó el diff y no encontró bloqueante para un experimento privado:
un header nuevo y tres zonas de main (admisión, commit físico, recv condicionado).
No es aceptación física ni autorización para promover.

Harness C compilado con `-std=c11 -Wall -Wextra -Werror` pasó FIFO de30CHUNK
seguidos de STOP,29 diferimientos, CHUNK→STOP→CHUNK, alcance fuera de perfil y
commit sólo tras intercambio válido. Es una prueba de la máquina de estados,
no una simulación completa del transporte TCP/SPI.

40 tests Python dirigidos pasan, incluyendo respaldo/rollback, lease, identidad,
origen/hash de artefactos, callback privado y métricas. Las nuevas fuentes
se seleccionan con `build_relay_candidate_v19.py --sources`; el artefacto queda
ligado a directorio y hashes, sin invalidar ni sobrescribir la evidencia previa.
Se conserva compatibilidad de lectura del build privado anterior.

El observador correlaciona STOP enviado con su respuesta por request_id y
registra tiempo ida/vuelta, estado y reason. No agrega relojes al MCU/relay.

## Secuencia prevista y límites

Compilar con respaldo completo y pareja detenida, restaurar y verificar; luego
transporte breve, audio breve con STOP confirmado y sólo después60s comparables.
Registrar rachas WAV/RF, finales RF/idle, margen, excedencias de presupuesto,
pico por fase, audio y demora de parada. Abortan la hipótesis los errores de
integridad/audio/parada/restauración. No relajar margen≥10%,pico<4,slack>0.

Espaciar respuestas puede repartirlas entre más nodos y aumentar huecos.
Los1598 RF-final/idle previos sólo representaban unos317ms de mitades de cable
en60s (0,53 puntos del tiempo), no1598 batches completos ahorrables. No hay
ganancia garantizada ni motivo para promover sin medición.

## Build y transporte breve

Build `relay_chunk_pacing_build_20261028/report.json`: ELF64aarch64 de73.912bytes,
SHA256 `4548a5b35801bdbdc85f15c5f66bbff9aceaa06dd159d55fd0497564b09bce65`.
Se compiló con pareja detenida, contenedor compilador eliminado y restauración
exacta verificada. Sólo cambian `unoq_config_stream.c` y `chunk_pacing.h` frente
a fuentes aceptadas. El binario antiguo de otras campañas no se reutiliza.

Transporte `relay_chunk_pacing_transport_20261028/report.json`:10,005 s,
18.614.584 muestras a1.860.465 S/s, dropped=fatal=0; restauración exacta y
recuperación aceptada10,024 s/313.344 muestras sin errores. Esta prueba sin
audio no ejercita aún los diferimientos CHUNK ni demuestra holgura conjunta.

## Primer arranque GUI: fallo previo a adquisición

`relay_chunk_pacing_audio_screen_20261028` venció el plazo de arranque GUI;
`ok=false`, restauración exacta `true`, estado incierto `false`. No se generó
evidencia de reproducción. No contarlo como ensayo de audio ni fallo causal
del candidato. El muestreo nativo guardado en `gui_start_sample.txt` muestra
QIcon→QSvgRenderer→QFileDevice→read bloqueado; macOS marcaba los SVG como
`compressed,dataless`. El SIGINT de cancelación terminó la construcción de
la ventana antes de crear un receptor.

Se pidió descarga de assets y se leyeron/verificaron los61SVG del workspace
sin modificar contenido (`asset_hashes.json`). La comprobación posterior del
icono mostró los flags despejados. Se repite el ensayo en directorio nuevo,
preservando íntegramente este fallo ambiental y su restauración.

Segundo intento `relay_chunk_pacing_audio_retry_20261028`: GUI abrió, pero
RF pendiente excedió el límite de1s antes de PLAYING (`FlowLimitExceeded`).
Sólo88.072 muestras llegaron a GUI; no se envió ningún CHUNK. El MCU reportó
pico2 y no hubo observaciones RADIO PLAYING. El ensayo falla y no mide todavía
la política de admisión de audio; no demuestra la causa del atraso host.
Receptor y coordinador confirmaron restauración, con recuperación aceptada.

Para separar problemas del host se ejecutó el flujo sintético sinQ. Su primer
arranque quedó esperando un diálogo crítico offscreen; se canceló únicamente
ese proceso sin hardware. La prueba ahora captura diálogos críticos y exige
lista de errores vacía, evitando un bloqueo invisible. Reejecutada pasó GUI,
RADIO/A0, WAV, Synth y cierre en3,26s, además de los40tests dirigidos previos.
No se modifica runtime ni se amplían límites de atraso para forzar un PASS.

## Ensayo breve completado y decisión

`relay_chunk_pacing_audio_warm_20261028/`:20,025 s RADIO/A0,801.120 muestras
reproducidas, cero errores; GUI/FFT16K visible100% y593Paint. Reserva mínima
observada9.080 muestras. STOP confirmado en2,716ms (IDLE,reason0), cierre y
restauración exacta PASS. El MCU mantuvo firmware aceptado.

La política actuó: racha máxima WAV/RF=1 tanto en preparación como PLAYING.
Sin embargo, durante PLAYING hubo1.117 RF-final/idle en20s (55,8/s), frente
a1.598 en60s del diagnóstico anterior (26,6/s). No es un A/B controlado de
igual duración/carga visible, pero evidencia más fragmentación en esta corrida.

Margen8,792%,pico5,ocupación muestreada4,slack72.785ticks;1.561 de10.688 nodos
superaron el presupuesto de envío. **Holgura FAIL. No incorporar ni extender
esta variante a campaña de60s/120s**: el ensayo breve no justificó el cambio.
No demuestra que todo el cambio de margen se deba causalmente a esta política.

`report.json` dice `ok=true` para verificaciones funcionales GUI/audio y
restauración; **no significa aceptación de holgura**. `decision.json` explicita
ambos resultados y `promoted=false`, manteniendo los dos intentos fallidos
anteriores. Q queda con pareja aceptada y ningún candidato activo. Hashes
runtime de la revisión global sin cambios; V17/V18 intactos.
