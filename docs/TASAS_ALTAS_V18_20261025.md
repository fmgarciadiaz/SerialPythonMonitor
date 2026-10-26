# Tasas altas V18 · 25/10

Campaña cerrada: perfiles incorporados después de aceptación física, GUI y
restauración verificadas. V17 permanece congelada. Los pendientes de las
secciones históricas se resolvieron en las etapas posteriores.

## Sondeo sin reflashear

`experimentos/fs_max_v18/installed_campaign/20261025_014222/report.json`:
10 bits CH1 1.311.475 S/s, 12 bits CH1 1.095.890 S/s, 14 bits CH1 909.091 S/s
y 16 bits CH1 145.455 S/s pasaron 15 s sin dropped/fatal. Márgenes medios
17,24 / 12,82 / 23,65 / 72,20 %, colas pico 2/2/2/1.
El intento dual no se ejecutó por identificador nominal 76227 incorrecto en
el arnés (la clave es 76226; tasa real 76226,775). Restauración exacta e
identidad verificadas. El resultado global conserva `ok=false`.

## 16 bits

El ADC es nativo de 14 bits. La producción obtiene el formato 16 bits con
sobremuestreo hardware x16 y desplazamiento de 2 bits. Se conserva esa
configuración, la ventana de 5 ciclos y reloj de 54 MHz.

`prepare_adc16.py` crea una copia privada de V18, modificando únicamente
las listas de perfiles de MCU/relay: CH1 1080/1060/1048 ticks y dual
2090/2088/2086 ticks. No reduce sobremuestreo, no cambia buffers ni reloj.
Se ensaya con app independiente Scope V18 Rate Probe ADC16 y restauración
mediante el runner transaccional.

[Datasheet ST](https://www.st.com/resource/en/datasheet/stm32u585ri.pdf)
· [Manual RM0456](https://www.st.com/resource/en/reference_manual/rm0456-stm32u575585-armbased-32bit-mcus-stmicroelectronics.pdf).

Pendiente: aceptación sostenida y GUI/audio de nuevos perfiles; caracterización
analógica separada. Ninguna tasa nueva pública por este documento.

## Referencia física 16 bits · 60 s

`installed_campaign/20261025_014407/report.json`: simple145454,5 S/s y
dual76226,8 S/s/canal, dropped=fatal=0, cola1, margenmedio72,23%/84,41%.
Restauración exacta y misma identidad verificadas. Sondeo no califica GUI/audio.
13 tests del contrato/runner ADC16 pasaron. Escalera aislada iniciada en
`resultados/20261025_014633/report.json`, app Scope V18 Rate Probe ADC16.

## Escalera ADC16 a 54 MHz

`resultados/20261025_014633/report.json`: CH1 148148 y150943 S/s pasaron15s;
152672 S/s (1048ticks) cerró el flujo durante la estabilización, antes de la
medición útil. Restauración verificada con misma identidad/configuraciónrelay.
`resultados/20261025_015238/report.json`: dual76555 S/s/canal (2090ticks)
falló antes de medir; trama CRCválida con fatal=1. No se promueve. Restauración
exacta verificada; dual mantiene76226,8 S/s/canal.

Calificación CH1/1060ticks en `resultados/20261025_015536/report.json`: se
ejecutan60+3×120s independientes con reinicio de app/MCU entre corridas.
Los tres primeros ensayos pasaron. Relay reutilizado sólo tras comprobar hashes
de todas sus fuentes y SHA256 del binario de la prueba anterior; no se compila
mientras se adquiere.

## ADC16 CH1/1060 · aceptación aislada

`resultados/20261025_015536/report.json` terminó ok/restored:60+3×120s
independientes, dropped=fatal=0, cola pico1 en las cuatro y margenmedio
71,14/71,14/71,15/71,14%. Q y políticas CPU/restauración verificados.
Sigue prueba GUI con RADIO/A0, Scan, WAV y Synth20 a150943,396 S/s; no
habilita todavía perfil público.

## GUI ADC16 confirmada

`diagnosticos/resultados_v18/gui_private_20261025_020837/report.json`
terminó ok, con restauración de producción verificada. RADIO/A0 sostuvo
120,322 s; Scan, WAV, Synth20, apagado confirmado y liberación del worker
pasaron. El primer intento020431 conserva ok=false: el arnés confundía
ventana oculta con cierre completo. Se corrigió y el ensayo se repitió.

Campaña instalada10/12/14 en `installed_campaign/20261025_093116/report.json`,
60+3×120s por formato. Cada repetición reinicia adquisición (cambio a14/40k
y configuración objetivo); no reinicia/reflashea MCU. Reportar este alcance
por separado de los reinicios de app/MCU usados para ADC16.

## Calificación instalada: avance

En `installed_campaign/20261025_093116/report.json`,10 bits/122ticks
completó60+3×120s sin pérdidas, cola2 y márgenes17,24/17,25/17,24/17,22%.
12 bits/146ticks completó60+3×120s sin pérdidas, cola2 y márgenes
12,85/12,82/12,84/12,85%.14bits/176ticks pasó60s y sigue en120s.
Las repeticiones reinician adquisición/época; no el MCU. Aún falta cierre
y restauración del conjunto, más GUI/audio por perfil.

## Tres formatos: aceptación aislada completa

`installed_campaign/20261025_093116/report.json`:12/12 casos pasaron,
restauración exacta e identidad verificadas.10 bits1311475,4 S/s,
12 bits1095890,4 S/s y14 bits909090,9 S/s, cada uno60+3×120s.

## Scan US 10 bits: fallo y corrección de auxiliares

`gui_installed_private_20261025_095355` falló al pasar al auxiliar antiguo
10/176/N8192 (909090 S/s): CRCválido, dropped1, fatal0, ruta normalSPI32.
Se guardó `relay_failure.log`; no es un fallo del perfil principal122ticks.
La GUI diagnóstica además dejaba activo el Scan al recibir error; se corrigió
y se agregó reintento de cierre al finalizar la transacción de Scan.

La pareja aceptada se recuperó mediante Preparar Q y el snapshot inicial
14/31,25kHz se restauró explícitamente con10s de adquisición sin errores:
`gui_installed_private_20261025_095355/manual_recovery.json`. El primer
reporte conserva ok=false. Scan US de los grupos rápidos10/12/14 ahora usa
sólo auxiliares SPI38/40FIFO con geometrías explícitas.13 tests del planner,
cancelación/cierre y arnés pasaron. Repetición física activa en
`gui_installed_private_20261025_100543`.

## Incorporación y pareja instalada

10/12/14 incorporados con GUI120, Scan US y restauración en
`gui_installed_private_20261025_100543`, `100945` y `101315`, respectivamente.
La restricción de RADIO/A0 para ADC14 permite ahora únicamente el perfil
176/N5952 con `combined_qualified=true`; no libera otros candidatos.

ADC16: rollback same-app exacto en
`resultados/same_app_restore_20261025_101736_b4959b/report.json`. Prebuild de
Scope V18 coincide con BIN7f8de38c…; relayf43923b0…. Propuesta/artefactos en
`release_adc16_20261025_093436`. Respaldo pareado anterior en
`respaldos/parejas/v18_antes_adc16_20261025_102856`.

El primer actualizador abortó porque exigía tres archivos nuevos incluso
para actualizar archivos existentes. Su rollback verificó fuentes/caché,
identidad, configuración de relay/CPU y10s de adquisición. Reporte fallido
con rollbackPASS: `adc16_production_update_20261025.json`. El adaptador ahora
acepta cero altas o las tres altas originales, sin bajas y con los mismos
hashes/manifest exactos.20 tests del motor/adaptador/perfiles pasaron.

Actualización aplicada y verificada en
`diagnosticos/resultados_v18/adc16_production_update_existing_20261025.json`.
GUI instalada16/150943: `adc16_installed_public_gui120_20261025.json`:125,36s
RADIO/A0, Scan/WAV/Synth20, apagado confirmado y worker liberado, sin errores.
ADC16 CH1 se publica a150943,396 S/s; dual conserva76226,775 S/s/canal.
La precisión efectiva analógica no se certifica mediante estas campañas.

## 25/10 · Tasas incorporadas y regresión final aprobada

| Formato CH1 | Máximo público |
|---|---:|
| 8 bits | 1.818.181,818 S/s |
| 10 bits | 1.311.475,410 S/s |
| 12 bits | 1.095.890,411 S/s |
| 14 bits | 909.090,909 S/s |
| 16 bits (sobremuestreo x16) | 150.943,396 S/s |

16 bits dual conserva 76.226,775 S/s por canal: el siguiente candidato falló.
10/12/14/16 pasaron calificación física 60 + 3×120 s y GUI combinada de
120 s; integridad y margen se documentan por separado en la campaña.
La pareja Scope V18 instalada es MCU `7f8de38c…` / relay `f43923b0…`.
Regresión instalada final 8/10/12/14: RADIO/A0, Scan US, WAV, Synth 20 voces
y cierre aprobados, sin errores. 16 pasó su GUI pública de 120 s.
Evidencia: `diagnosticos/resultados_v18/installed_rates_regression_20261025_104120/report.json`
y `diagnosticos/resultados_v18/adc16_installed_public_gui120_20261025.json`.
No se certifica ENOB analógico con estas pruebas. V17 permanece congelada.
Detalle: [campaña de tasas](TASAS_ALTAS_V18_20261025.md).
No quedan procesos de campaña activos; continuar desde esta pareja aceptada.

Regresión offline final: 86 pruebas aprobadas (perfiles, Scan US, RADIO,
cursores, cierre, Preparar Q y restauración transaccional).

Cierre final: Preparar Q verificó la pareja aceptada y adquisición durante
10 s (`diagnosticos/resultados_v18/final_prepare_rates_20261025.json`).
Respaldo pareado: `respaldos/parejas/v18_tasas_aceptadas_20261025_104819/manifest.json`,
con exportación de Scope V18 y hashes. Los 175 archivos de la pareja V17
coinciden con su manifiesto congelado.
