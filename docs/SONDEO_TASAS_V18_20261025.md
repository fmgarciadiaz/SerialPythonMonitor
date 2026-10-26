## Segunda tanda incorporada · 25/10

Máximos CH1 actuales: 8 bits 1.860.465,116 S/s; 10 bits 1.355.932,203 S/s;
12 bits 1.103.448,276 S/s; 14 bits 1.000.000 S/s; 16 bits 150.943,396 S/s.
Los métodos, tasas anteriores y perfiles duales se conservan.

Los cuatro candidatos privados pasaron 60 + 3×120 s y GUI/audio privada.
8 bits/85 ticks falló después en GUI instalada por UNDERRUN: se retiró del
selector y del permiso A0. Ese fallo permanece en el informe, sin reintentos
para declararlo aceptado. Control 8 bits/86 ticks instalado pasó 120 s.
10/118, 12/145 y 14/160 pasaron GUI instalada de 120 s con RADIO/A0, Scan US,
WAV, Synth20, exposición, dibujo y cierre. Regresión restante 9/9 aprobada,
incluidos 16 bits simple y dual. 145 selecciones Scan previas sin cambios.
El margen aislado mínimo fue 13,63 %, 12,08 % y 15,97 % respectivamente;
no se interpreta como margen bajo carga conjunta ni certificación analógica.

Evidencia:
- Calificación: `experimentos/fs_max_v18/resultados/20261025_181349/report.json`.
- Fallo instalado 8/85: `diagnosticos/resultados_v18/rateonly2_installed_20261025_190204/new8.json`.
- Regresión aceptada: `diagnosticos/resultados_v18/rateonly2_installed_remainder_20261025_191207/report.json`.
- Actualización: `diagnosticos/resultados_v18/rateonly2_production_update_20261025.json`.
- Stage/prebuild: `experimentos/fs_max_v18/release_rateonly2_20261025_184722/`.
- Rollback: `experimentos/fs_max_v18/resultados/same_app_restore_20261025_184745_0b4426/report.json`.

La pareja instalada es MCU 540c1674… / relay ecccdbcd… . El firmware contiene
períodos privados adicionales, pero solo se exponen los perfiles aceptados.
V17 permanece congelada. La landing conserva sus imágenes y badges.

---

Historial de la primera tanda:

# Tasas V18 con métodos constantes · 25/10/2026

## Resultado actual

Tres perfiles incorporados en Monitor V18 y Scope V18, después de calificación
física, rollback, prebuild y regresión instalada. V17 permanece congelada.

| Bits CH1 | Máximo público (S/s) | Margen medio mínimo | Cola pico |
|---|---:|---:|---:|
| 8 | 1.860.465,116 | 18,38 % | 3 |
| 10 | 1.333.333,333 | 15,39 % | 2 |
| 14 | 941.176,471 | 20,92 % | 2 |

Cada perfil pasó 60 + 3×120 s con reinicios independientes, dropped=fatal=0,
slack positivo y margen medio >=10%. Además pasó GUI visible, RADIO/A0 a 40 kHz
por 120 s, Scan US, WAV, Synth de 20 voces, cierre confirmado y restauración exacta.
El margen indicado corresponde a adquisición aislada; la prueba combinada
valida funcionalidad y dibujo, no certifica ese mismo margen bajo carga conjunta.
No se certifica ENOB ni calidad analógica con esta campaña.

Las restauraciones verifican identidad, relay, política CPU y 10 s de adquisición
original. El Q quedó restaurado y libre. Los 175 archivos de la pareja V17
coinciden con el manifiesto congelado. Producción conserva su lista pública.

## Métodos conservados

Se copió la pareja V18 aceptada a Scope V18 Rate Probe RateOnly. Solo se
ampliaron listas y condiciones explícitas privadas de perfiles rápidos y CPU.
Los perfiles existentes conservan sus condiciones. Sin cambios de reloj ADC/SPI,
ventana ADC, resolución, sobremuestreo, packing, CRC, validación ni arena DMA.
8 bits conserva bloque 3488, cola 8 e IPC compacto; 10/12/14 bits conservan bloques
5568/7488/5952 y cola 4. El bootstrap GUI selecciona exclusivamente un perfil
privado y hereda los auxiliares rápidos ya validados para Scan US.

## Escalones descartados para uso combinado

- 8 bits / 84 ticks (1,905 MS/s): pasó aislado, pero RADIO/A0 dio UNDERRUN.
- 10 bits / 116 ticks (1,379 MS/s): pasó aislado, pero el Q cerró el flujo al iniciar audio.
- 12 bits / 144 ticks (1,111 MS/s): pasó aislado y más de 100 s de audio; terminó en UNDERRUN.

Los tres informes conservan resultado fallido, con restauración externa
verificada. No se ocultan ni se reinterpretan como aceptación. En 12 bits se
conserva 1.095.890,411 S/s; 16 bits mantiene sobremuestreo x16 y su tasa actual.

## Evidencia

Consolidado verificable: `experimentos/fs_max_v18/rateonly/qualified_candidates.json`.
Incluye hashes de identidad de candidatos y enlaces a cada informe.

- Sondeos: `resultados/20261025_121157`, `121731`, `122126` bajo `experimentos/fs_max_v18/`.
- Primera calificación aislada 16/16: `experimentos/fs_max_v18/resultados/20261025_122824/report.json`.
- Primera GUI: `diagnosticos/resultados_v18/rateonly_gui_campaign_20261025_130208/report.json` (global false por tres fallos).
- GUI escalones menores: `diagnosticos/resultados_v18/rateonly_gui_fallback_20261025_152933/report.json` (true).
- Calificación aislada 8/86 y 10/120: `experimentos/fs_max_v18/resultados/20261025_153648/report.json` (true).

## Incorporación en producción

Pareja instalada: MCU `545c240499a65b67a526ea8aae6fc0c7a9a671419955175f5f32a387e5388f23`
y relay `3c663944e85229549935d3064f6ffbf2c7d709aace4484e6de8b7a0d6255ae7f`.

- Rollback same-app: `experimentos/fs_max_v18/resultados/same_app_restore_20261025_170343_9be146/report.json`.
- Prebuild exacto: `experimentos/fs_max_v18/release_rateonly_20261025_170513/prebuild_report.json`.
- Respaldo anterior: `respaldos/parejas/v18_antes_rateonly_20261025_171017/manifest.json`.
- Actualización: `diagnosticos/resultados_v18/rateonly_production_update_20261025.json`.
- Regresión instalada: `diagnosticos/resultados_v18/rateonly_installed_20261025_171653/report.json`.

Regresión instalada 9/9: 120 s RADIO/A0 por tasa nueva (8/10/14), Scan US,
WAV, Synth20, GUI visible y cierre. Además, recorridos de 20 s de audio para
las tasas anteriores de 8/10/12/14 y 16 bits simple/dual, con Scan, WAV,
Synth y cierre. Los recorridos breves de regresión no reemplazan una nueva
calificación sostenida de esas tasas anteriores.

Se preservaron todas las entradas anteriores de native_profiles.json y las
selecciones de auxiliares de Scan US para las 142 configuraciones existentes.
Los nuevos objetivos heredan los auxiliares exactos usados en la calificación;
ningún objetivo nuevo se usa como auxiliar de los perfiles anteriores.
Los relojes, DMA, colas, packing y métodos existentes permanecen.
La landing conserva sus 16 imágenes/badges y actualiza solo las cifras actuales.

## Cierre final

334 pruebas offline aprobadas. Preparar Q verificó la pareja actual, fuentes
y 10 s de adquisición: `diagnosticos/resultados_v18/rateonly_final_prepare_20261025.json`.
Respaldo final pareado: `respaldos/parejas/v18_tasas_rateonly_20261025_173359/manifest.json`.
Se verificaron los 175 archivos congelados de V17 y la identidad de los archivos
centrales app.py, processing.py, numeric_batch.py, radio_am.py, radio_stream.py
y digital_filter.py respecto del respaldo anterior. No hay campañas activas;
Q disponible para uso normal.

Cierre de segunda tanda:342 pruebas offline aprobadas;PrepararQfinalverificado.
Respaldo `respaldos/parejas/v18_tasas_rateonly2_20261025_193958/manifest.json`. Qlibre y175archivosV17 intactos.
