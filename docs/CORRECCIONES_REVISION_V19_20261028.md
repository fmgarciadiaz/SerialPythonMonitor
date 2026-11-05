# Correcciones de la revisión V19 · 28/10/2026

**Seguimiento posterior:** se completaron el build ARM64 y la integridad privada
del relay (60 s + 3×120 s), con restauración física. Ver el
[informe del candidato](RELAY_CANDIDATO_V19_20261028.md); los apartados de esta
tanda conservan sus límites originales.

Se implementaron los pendientes de la [revisión global de Astra](REVISION_ASTRA_V19_20261027.md).
V17 y V18 conservan sus fuentes. Los cambios del monitor son de V19; la pareja
física aceptada conserva los hashes de su recibo.

## Preparar Q

El informe inicial decía que el backend de actualización estaba bloqueado por
preflight. Esa afirmación era incorrecta: `ProductionBackend` puede habilitarse
con el recibo aceptado. Se corrigió la ruta realmente ejecutable.

La secuencia ahora verifica el respaldo exacto, calcula los cambios de fuentes,
arma rollback, pausa adquisición, detiene y retiene el relay y detiene la app.
Recién después compila. Tanto preparación como recheck verifican que la pareja
original siga detenida. La primera instalación usa una comprobación explícita
de Q vacío y no requiere una pareja previa.

Un fallo desde la pausa, incluyendo compilación y recheck, intenta restaurar
fuentes, caché completo, app, relay, CPU y configuración originales. El reporte
expone `state_uncertain`: sólo queda falso después de verificar instalación o
restauración. Los tests inyectan fallos en cada etapa previa a instalación y
también un fallo de rollback. La actualización con build no se ejecutó en Q en
esta tanda; su restauración física sigue sujeta a la calificación de la ruta.

## Cierre y recursos

Las esperas a procesos DSP/Synth comprueban cancelación cada 50 ms y tienen
plazo. El cierre restaura primero el Q y luego recoge los procesos de cálculo;
puede terminar exclusivamente esos hijos si no responden. Un lock impide que
un warmup tardío cree un proceso nuevo después de iniciada la limpieza.

Los trabajos de cálculo ordenados (DSP, PCM, Scan y ajuste de distorsión) usan
un executor de un hilo daemon con `Future`, cancelación pendiente y orden FIFO.
Así el hook de salida de `ThreadPoolExecutor` ya no espera indefinidamente una
tarea nativa bloqueada. Estos hilos nunca son dueños del transporte del Q; las
entregas y señales tardías se descartan al cerrar. El receptor de hardware
conserva su cierre/restauración confirmado y su pipe terminal independiente.

La preparación WAV libera el `QThread` terminado y sus referencias. El servicio
PCM también tiene cierre acotado; su fallo se reporta sin saltar la restauración
del hardware. Tests incluyen un hijo de cálculo que nunca termina y un proceso
Python que debe salir aun con un hilo de cálculo bloqueado.

La prueba física detectó además una competencia entre `Process.join()` y el
gestor interno del pool al recoger los mismos hijos. La limpieza espera ahora
al gestor; sólo ese hilo hace la recolección. El adaptador está acotado al
Python 3.13 que exige la aplicación y sus detalles privados quedan encapsulados
en `worker_cleanup.py`.

## Identidad, arranque y herramientas

- La conexión normal compara firmware y relay con la identidad del recibo V19
  aceptado antes de abrir el socket. Administración y ensayos privados tienen
  vías explícitas de inspección; no se confunden con aceptación productiva.
- La reparación de flags Finder de plugins Qt se ejecuta una vez por proceso y
  sólo recorre las familias de plugins usadas por la aplicación. No se repite
  por cada import de Bode o Spectrum ni recorre todo el árbol de Qt.
- `run_stack_diag_v19.py` y `probe_v19_normal_pair.py` rechazan su entrada
  operativa porque restauraban V17. Se conservan helpers y código histórico.
  `validate_v19.py` ejecuta sólo V19. La comparación FPS puede leer un reporte
  V18 archivado, pero sólo opera la pareja V19.
  Ante timeout, ambas matrices piden cancelación y esperan restauración; no
  matan al wrapper que todavía podría ser dueño del Q.
- El smoke mide Paint en el viewport realmente visible, verifica progreso de
  muestras, configuración, duración y datos finitos del modo seleccionado.
  FFT/Heatmap requieren avance de su resultado. La configuración del harness
  conserva CH2 en Heatmap y Transfer. Bode demo sigue declarado sintético.

## Relay candidato

El candidato aislado intenta vaciar una FIFO llena antes de rechazar una trama
nueva. Conserva sus 64 posiciones, orden y bytes, y usa un máximo compartido de
dos sends no bloqueantes por trama. El harness C prueba recuperación tras
`EAGAIN`, cola todavía llena, escrituras parciales, `EINTR`, `EPIPE` y escritura
cero. Pasa con `-Wall -Wextra -Werror`.

El fuente candidato y sus hashes están en
`diagnosticos/resultados_v19/prepare_q_20261027/candidate/`. El binario ARM64 de
esa carpeta sigue obsoleto y marcado **no instalar**. La corrección no se
promovió a la pareja aceptada: requiere build aislado, ensayo/restauración y
evidencia física. Tampoco demuestra que FIFO llena haya causado `sent=-1`.

## Evidencia física de esta tanda

- V(t), ADC8/1.860.465 S/s, ventana 4 s: 75,60 s efectivos y 152.358.456
  muestras; 815 Paint events, cadencia estable cercana a 10 FPS después del
  arranque. Sin errores; cierre confirmado, identidad idéntica y recuperación
  10,025 s / 313.344 muestras sin pérdidas/fatales.
  Informe: `diagnosticos/resultados_v19/radio_rate_check_20261028_004720/`.
- RADIO/A0 40 kHz durante 60,03 s, luego WAV y Synth 20 voces: todas las
  confirmaciones de reproducción/progreso/Stop pasaron, sin underrun/error y
  con restauración verificada. El conteo Paint apuntaba al viewport temporal
  oculto; por eso el reporte global correctamente quedó falso y no se usa como
  aceptación visual. Informe conservado sin reescribir:
  `diagnosticos/resultados_v19/radio_rate_check_20261028_005059/`.
- Repetición con contador Paint corregido: 30,03 s RADIO/A0, WAV y Synth
  confirmados y 805 Paint, pero error en la limpieza del pool. Q restaurado;
  reporte global falso preservado en
  `diagnosticos/resultados_v19/radio_rate_check_20261028_005310/`.
- Después de corregir la recolección del pool: RADIO/A0 40 kHz durante 20,03 s
  a adquisición ADC8/1,860 MS/s, luego WAV 40 kHz y Synth 20 voces a 20 kHz con
  adquisición dual 8 bits/40 kHz. Reproducción, progreso, Stop, dibujo visible
  (851 Paint), cierre y restauración **PASS**, sin errores. Recuperación
  10,028 s / 313.344 muestras, sin pérdidas/fatales. Informe:
  `diagnosticos/resultados_v19/radio_rate_check_20261028_005711/`.

## Regresión final

**372 tests de la suite V19 y 3 tests suplementarios de herramientas PASS** con
Python 3.13. El log de suite, resumen, hashes de fuentes host e identidades Q
antes/después están en `diagnosticos/resultados_v19/revision_20261028/`.
La identidad final es idéntica a la inicial; las fuentes de V17/V18 no cambiaron.
El harness C del relay candidato también pasa. La landing mantiene sus imágenes,
badges y presentación.

Estas corridas son controles acotados. No cierran por sí solas el incidente
intermitente de transporte ni equivalen a calificar todos los bits/tasas.
