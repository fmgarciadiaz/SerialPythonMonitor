# Firmware O2 privado: carga e integridad · 28/10/2026

Continúa el [A/B estático GCC14.3](PREPARE_COMPILADOR_V19_20261028.md).
El candidato cambia únicamente Os→O2 de `prepare_batch_half`. No se edita el
recibo aceptado ni las fuentes locales de firmware/monitor. V17/V18 congeladas.

## Contrato privado

`private_firmware_v19.py` comprueba la comparación aislada con restauración,
control BIN idéntico al aceptado, fuentes originales sin cambios, diff exacto
de un carácter y hashes de BIN/ELF de ambos builds.

Identidad privada: firmware `4e56c37b…` y relay aceptado `27da0bc4…`, app
`scope-v19-main-1` y serial seleccionado. El manifiesto debe estar activo,
sin error ni restauración en curso; una vez restaurado no habilita conexión.
Se comprueba identidad instalada exacta. La conexión habitual sigue exigiendo
firmware aceptado `37f049fa…`; no se generaliza el binding privado del relay.

## Rebuild verificado, no inyección de caché

`probe_prepare_firmware_v19.py` reutiliza owner/capture/backup/rollback completos.
Antes de mutar marca incertidumbre; detiene relay, conserva su contenedor por
ID y detiene app. Copia sólo el ino privado al Q y verifica el manifiesto remoto
completo. La copia local permanece aceptada.

Usa el launcher normal y su política de rebuild. No copia artefactos de `/tmp`
a caché ni fabrica fingerprints. Exige BIN y ELF iguales al candidato comparado
antes de iniciar una copia exacta del relay aceptado bajo el contenedor temporal
propio. Cualquier discrepancia aborta y restaura fuentes/caché completas.

Primero verifica10s con el snapshot original; después establece explícitamente
ADC8/CH1/1.860.465 S/s (86ticks/3488) y mide10s. El controlador administrativo
mantiene el lock durante toda esta primera prueba; no hay GUI ni audio. El
binding privado se comprueba antes de abrir el receptor interno.

Al salir, incluso por error, detiene app/relay propios, restaura material exacto,
arranca la pareja original y verifica snapshot/identidad/CPU e integridad10s.
No promueve automáticamente el firmware si la carga funciona.

## Verificaciones previas

17 tests dirigidosPASS: identidad/serial/app/relay, manifiesto inactivo, fuente
inesperada, BIN/ELF inesperados antes de relay, fallo después de copiar fuente
privada con rollback y contratos de conexión/actualización existentes.
El control ELF también coincide exactamente con el respaldo aceptado.

Esta etapa sólo puede acreditar carga e integridad breve. No califica pilas en
ejecución, máxima carga GUI/audio, otros bits ni mejora de rendimiento.

## Resultado de carga privada

`diagnosticos/resultados_v19/prepare_o2_load_20261028/report.json`: carga verificada,
10,005 s a 1.860.465 S/s sin pérdidas ni errores fatales; margen medio 19,15 %,
cola pico 2. Restauración exacta de la pareja aceptada y adquisición de 10,022 s
sin errores. Son resultados breves sin GUI/audio: no habilitan promoción.

El adaptador GUI privado conserva identidad separada y rollback. Sus criterios
exigen plataforma Cocoa y avance FFT entre dos capturas ya válidas. La campaña
GUI/audio queda pendiente mientras se reproduce US con el firmware aceptado.


## Primera prueba GUI/audio · 29/10

`prepare_o2_gui_screen_20261029`: 20,041 s de PLAYING, 803.520 muestras DAC,
FFT visible con avance y 597 eventos de pintura. Cero errores funcionales;
margen medio de envío 11,4765 %, cola pico 3, slack mínimo 75.438 ticks.
Estos valores pertenecen al candidato O2 con el host ACK-refresh privado;
no atribuir toda la mejora exclusivamente al compilador ni incorporarlo al
runtime. GUI y restauración exacta PASS. Sigue la campaña 60 s + 3×120 s,
con la misma pareja privada y rollback completo en cada corrida.


## Campaña sostenida: detenida por holgura

`prepare_o2_gui_campaign_20261029/run_1_60s`: 60,053 s de PLAYING,
funcionalidad/FFT visible/restauración PASS. Margen medio 11,3204 %, slack
mínimo 76.891 ticks; pico acumulado MCU 4 (muestreo instantáneo máximo 3).
El criterio sigue siendo pico <4: holgura FAIL. El controlador detuvo la
campaña antes de los tres ensayos de 120 s. No se promovió el candidato ni
se reinterpretó el pico acumulado como si fuera el máximo muestreado.

La prueba independiente ADC10 requiere observador parametrizado para
118 ticks × 5.568 muestras = 657.024 ticks por nodo. El observador anterior
por defecto sólo medía ADC8/86/3.488: no sirve para atribuir márgenes ADC10.
Las herramientas ahora seleccionan el perfil nativo validado sin mezclar los
perfiles auxiliares de Scan. Se conservan los mismos criterios.
