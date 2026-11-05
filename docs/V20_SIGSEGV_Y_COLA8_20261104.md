# V20: caída nativa de GUI y candidato local de cola 8 · 4/11/2026

## Incorporación experimental de ADC8/2 MS/s en V20

El selector V20 muestra **2,00 MHz · CH1 · EXPERIMENTAL** sólo en SPI con
ADC8. La geometría permitida es exactamente 80 ticks, 3.488 pares por nodo y
cola 16 del firmware V20 ya instalado. No se cambió el predeterminado de
40 kHz ni las tasas anteriores. El resumen y el estado de adquisición
conservan la marca experimental; el tooltip explica el SIGSEGV GUI pendiente y
la holgura reducida. RADIO/A0 acepta sólo esa geometría; Scan US mantiene las
dos tasas auxiliares 1,6 y 1,403508 MS/s. La marca no concede aceptación a
2,051282 MS/s ni a otros bits o tamaños de nodo. No se activó el priming
privado ni se alteraron recibos, identidad, CRC o límites de flujo.

Es una opción de exploración, no una tasa calificada como estable. El control
60 s con ventana expuesta pasó, pero el ensayo 120 s terminó en SIGSEGV; la
reproducción 80 s pasó funcionalmente con 76,19 % de exposición. Durante A0
el margen medio de envío fue 0,53 % en esa reproducción, lejos de una reserva
de 10 %. La causa de la caída nativa sigue sin localizarse. Antes del cambio
se respaldaron cinco fuentes de host con SHA en
[`respaldos/host/v20_before_experimental_2m_20261104`](../respaldos/host/v20_before_experimental_2m_20261104/manifest.json).
Los 13 tests focalizados con Python 3.13 pasaron, incluido el selector Qt
offscreen, la guarda exacta de A0 y los auxiliares US. Es validación local del
cambio de catálogo y presentación, no una nueva aceptación física.

El [smoke físico de la ruta normal](../diagnosticos/resultados_v20/experimental_2m_normal_smoke20_r2_20261104/report.json)
aplicó ADC8/2 MS/s sin activador de tasa ni excepción privada de A0. El estado
mostró `EXPERIMENTAL`; RADIO/A0 confirmó PLAY, sostuvo 20,033 s, reprodujo
802.080 muestras y confirmó STOP. Las seis observaciones periódicas de ventana
estuvieron expuestas, y el cierre no informó errores. La sesión del receptor
restauró el snapshot; una verificación independiente lo mantuvo 10,025 s con
313.344 muestras, cero pérdidas/fatales y SHA de MCU/relay intactos. Q quedó
sin dueño de prueba. Un intento anterior, conservado aparte, no llegó a
conectar por un lock duplicado en el wrapper del ensayo; no operó el Q.
El smoke no resuelve la caída nativa de 120 s ni acredita reserva de envío o
estabilidad sostenida.

## Recuperación tras la caída

El control de 60 s sin priming privado
[`installed_2000_visible_native_us60_20261104`](../diagnosticos/resultados_v20/installed_2000_visible_native_us60_20261104/report.json)
pasó con exposición completa y restauración V20, pero con margen medio de
envío **durante reproducción** 0,66 % (ciclo completo 1,54 %) y cola pico
12/16. Ese pase no califica la reserva de transporte.

La GUI visible ADC8/2 MS/s, US durante A0 y reinicio de A0 de
[`installed_2000_visible_native_us120_20261104`](../diagnosticos/resultados_v20/installed_2000_visible_native_us120_20261104/report.json)
terminó con `child_returncode=-11` antes de escribir `gui.json`. El progreso
había llegado a 65,86 s de escenario y unos 43,9 s de audio tras US. Por ello
esa corrida **falló**; no acredita 120 s ni exposición final. El informe padre
registró `v20_snapshot_restore.ok=false` e identidad posterior no disponible
porque consultó mientras el receptor hijo aún poseía el Q.

El archivo de sesión del hijo se cerró después de ese informe: restauración
confirmada durante 10,011 s, 313.344 muestras, cero `dropped/fatal`. Se abrió
una conexión nueva sin reset ni despliegue y se confirmó en vivo la misma app
`scope-v20-20261031-225916-main-1`, MCU `52f933bd…` y relay `bf6893f5…`.
La observación coincidió con el snapshot: ADC14/32 ticks dual, generador OFF,
WAV IDLE y SPI. [Informe de recuperación](../diagnosticos/resultados_v20/recover_gui_sigsegv_20261104/report.json).

El `.ips` de macOS del 4/11 muestra `EXC_BAD_ACCESS` en la reducción booleana
de NumPy (`logical_or`) dentro de un callback de `QTimer` del hilo principal.
La caída anterior en `PySide::SignalManager::retrieveMetaObject` al construir
un `QTimer` tenía otra pila nativa. Ninguna de las dos demuestra una causa en
ADC, el relay o una rutina Python concreta.

## Reproducción acotada con traza privada

Se añadió `--trace-numpy-any` sólo al lanzador privado. Registra entrada,
salida, archivo, línea, forma y tipo de cada `np.any` del hilo GUI, y se retira
al terminar. El runner ahora espera el cierre del receptor tras una caída GUI
antes de recopilar la restauración. La prueba local del trazador y 14 pruebas
del lanzador pasaron con Python 3.13.

La reproducción de 80 s
[`installed_2000_native_any_trace80_20261104`](../diagnosticos/resultados_v20/installed_2000_native_any_trace80_20261104/report.json)
terminó funcionalmente bien: US capturó tres perfiles y restauró la tasa
original; Scan encontró dos candidatos; A0 sostuvo 80,09 s y completó las
transiciones. No se activó el priming privado de 12 ms. El proceso salió con
código 0, restauró el snapshot durante 10,022 s sin pérdidas/fatales, y
conservó identidad, recibo e informe de activación exactos.

La ventana estuvo expuesta en 16/21 observaciones (76,19 %), por debajo del
umbral visual de 90 %. El margen medio de envío fue 0,53 % durante reproducción
(1,27 % en todo el ciclo), cola pico 10/16:
no hay reserva de 10 %. Las 2.476 llamadas `np.any` registradas tienen pareja
entrada/salida; la caída no se reprodujo ni quedó identificada. No se toma
esta pasada como arreglo causal, aceptación visual o promoción de 2 MS/s.

## Candidato de cola 8

[`experiments/v20/queue8_candidates`](../experiments/v20/queue8_candidates/manifest.json)
contiene sólo overlays locales con SHA de las fuentes base. La capacidad 8 se
selecciona únicamente para ADC10 CH1/116 ticks/5.568 pares, ADC12 CH1/140
ticks/7.488 pares y ADC14 CH1/158 ticks/5.952 pares. Este último perfil se
añadió sólo a los catálogos y `high_rate` experimentales MCU/relay. Los
perfiles anteriores conservan capacidad 4, salvo el camino rápido ADC8 de 16.

El arreglo compacto plano contiene 59.904 muestras; los ocho descriptores de
cola son externos. `bind` valida antes de cambiar la unión y usa el stride
real en 8, 8.192 en 4 y la ruta rápida existente en 16. El límite estático
usa la cola real de SRAM3 de 384 KiB. Las cinco pruebas del candidato pasaron,
incluido el arnés C++ local de transiciones 4↔8↔16↔dual4, rechazos sin
mutación y punteros finales. **Faltan tamaño/mapa ARM y vínculo privado propio
MCU/relay/host** antes de instalar; tampoco existe aceptación física de cola 8.

## Próximo bloque

La caída nativa GUI sigue abierta. La próxima repetición debe buscar un
callsite concreto o una reproducción local acotada; una nueva campaña larga
sin hipótesis no resolvería esa incertidumbre. Mantener separados el ensayo
de cola 8, la estabilidad de RADIO/A0 y el margen de envío. Q queda con V20
restaurada y las versiones anteriores intactas.
