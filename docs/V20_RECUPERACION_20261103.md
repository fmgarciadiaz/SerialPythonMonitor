# V20: recuperar Synth y dibujo frente a V19

El usuario pidió retirar el modo envelope, revisar las regresiones frente a
V19 y corregir Synth antes de volver a aumentar tasas. V19 permanece intacta.
Astra hizo una lectura inicial; Astra y Sol agotaron cuota antes de completar
su trabajo. El coordinador implementó y validó los cambios.

## Hallazgos y cambios

- **Regresión concreta en V(t):** se había deshabilitado la reducción de detalle
  de V19 y activado el raster completo incluso con detalle menor al 100 %.
  Se retiraron el modo envelope y su indicador, y se restauró el raster de V19
  adaptando sólo su namespace. La reducción habitual del control Detalle vuelve
  a trabajar directamente sobre la historia circular. Los cursores y el detalle
  completo mantienen su recorrido original; no se sustituye la adquisición.
- **Play de Synth:** el panel descartaba el clic si aún se estaba aplicando la
  adquisición de hasta 40 kHz; ese comportamiento también existía en V19.
  Ahora conserva una petición, espera la confirmación y continúa una vez.
  Durante la preparación, los avisos de reposo anteriores no borran la fuente.
  Un segundo clic cancela; desconectar o cambiar de modo también cancela.
- **Vista mixta CH1+RADIO:** copiaba la ventana RF completa antes de reducir
  los puntos de dibujo. Ahora aplica la misma política de detalle sobre el
  buffer circular antes de copiar. Si hay cursores, huecos o disparo, conserva
  el recorrido completo. La medición sigue usando todas las muestras originales,
  con vistas síncronas y su propia cadencia, sin retenerlas en procesos.
- **Revisión de versiones:** se corrigió el CLI V20 que anunciaba versión 19
  y ejecutaba tests V19, y las rutas de diagnósticos que escribían bajo V19.
  Los identificadores de variables de entorno compatibles no se renombraron.

La comparación de fuentes Python, descontando namespaces, está en
`diagnosticos/resultados_v20/recovery_review_20261103/host_diff.json`.
FFT/heatmap y el procesamiento DSP no muestran diferencias funcionales respecto
a V19. El motor Synth sólo añadía una caché de coeficientes DX estáticos, cuya
equivalencia numérica ya tenía tests; no se encontró evidencia para retirarla.
Se conservan las correcciones de EOF del receptor, ACK de apagado correlacionado
y la identidad/memoria de la pareja V20 instalada. El arranque por spawn que
reimporta la GUI queda como coste adicional por investigar, no como causa probada
de los cortes anteriores. La revisión de diferencias no acredita cada función
de la aplicación en hardware.

## Evidencia

- Suite V20 tras retirar envelope y corregir Play: **154 tests PASS**.
  Después del ajuste de vista mixta: **38 tests focalizados PASS**, incluidos
  picos, muestras completas para medición/cursores, huecos y cancelación.
- Comparación local, misma ventana sintética de 3.720.930 muestras y detalle50:
  mediana V19 **10,47 ms**, V20 **10,60 ms**, mismos puntos dibujados.
  Es Qt offscreen, no FPS físicos ni comparación con otro firmware cargado.
  Informe `recovery_review_20261103/temporal_comparison.json`.
- `recovery_synth_singleclick_20261103`: **PASS**, clic único mientras la
  configuración estaba pendiente, nuevo PLAY unos **1,69 s** después,
  **30,06 s** de reproducción confirmada a DAC40k, STOP y restauración.
  DX Piano recibió 20 notas; voces observadas0–20 por su envolvente percusiva,
  no 20 voces sostenidas. Adquisición de este ensayo: ADC8/40k dual.
- Vista mixta física, ADC8/1.860.465, RADIO/A040k, ventana2s, detalle50,
  ventana expuesta100 %, sostén20s y restauración: ambos ensayos **PASS**.
  Medianas de eventos de pintura durante reproducción: **2,86/s** antes del
  ajuste mixto y **5,18/s** después. No son medidas de imágenes nuevas ni
  garantía universal de FPS. Informes `recovery_vt_detail50_20261103` y
  `recovery_mixed_detail50_20261103`.
- Confirmación posterior `recovery_mixed_detail50_60s_20261103`: **PASS**,
  RADIO/A0 **60,10 s**, ventana expuesta100 %, sin errores. Restauración
  **10,022 s**, 313.344 muestras, cero pérdidas/fatales, misma identidad V20.
- Tras cubrir también STOP anterior pendiente, otros **16 tests focalizados
  PASS**. `recovery_synth_audiohandoff_20261103`: **PASS funcional**, nuevo PLAY
  unos1,61 s después del clic único, reproducción5,09 s, STOP y restauración
 10,022 s/313.344 muestras/cero pérdidas-fatal. Exposición37,5 %: no acredita
  FPS visibles. En este ensayo la configuración ya estaba confirmada al
  registrar el clic; el caso con configuración pendiente sí quedó observado
  en el ensayo anterior de30 s, y el STOP anterior pendiente se prueba en unit.

## Pendientes y límites

La vista mixta larga todavía tiene FPS bajos. No se aumentaron límites de flujo,
prioridades, workers ni tasas, y no se cambió firmware/relay. Primero estabilizar
la carga existente; después retomar candidatos superiores con margen e integridad
medidos. El modo Completo sigue dibujando cada punto y puede ser lento con
millones de muestras. La implementación retirada quedó como archivo histórico
en `experiments/v20/retired_envelope_20261103/`, fuera del monitor activo.

## Cadencia equilibrada incorporada a baja tasa

La recuperación se limita a V(t) hasta40kHz y80.000 muestras visibles, sin RADIO, FILTER ni raster. Usa el coste medido para reservar tiempo de servicio; no impone16ms globalmente. Ensayo físico limpio:15,09 imágenes nuevas/s en control20s frente28,82 en candidata20s y29,14 en confirmación60,60s, con exposición100%. Cada ensayo restauró el snapshot V20 y verificó10s sin pérdidas/fatales. Evidencia en `diagnosticos/resultados_v20/rf40k_physical_*_20261103/`; el primer legacy20 quedó invalidado por error del arnés, usar legacy20_r2.

El usuario autorizó explorar estabilidad de2MS/s aunque no alcance10% de margen: la adquisición sola60s validó119.928.776 muestras,0 pérdidas/fatales,cola pico5/16 y7,57% de margen medio. No acredita audio, precisión analógica ni reserva10%. Se inicia validación independiente120s y luego RADIO/A0, conservando V20. La cola16 corresponde a ADC8 rápido; no atribuirla a los demás bits, cuyos perfiles actuales usan4 nodos mayores.
