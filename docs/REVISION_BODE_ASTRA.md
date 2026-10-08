# Revisión de Bode por Astra · 2026-10-06

Revisión del estado de trabajo de V13, solicitada por el usuario. Alcance:
Tonos, Pulso, Sweep/Chirp, integración de UI, protocolo del generador y
calibración. Se ejecutaron pruebas locales con `.venv-v13/bin/python` y Qt
offscreen. No se operó el Q ni se modificó la implementación. El repositorio
ya contenía cambios del usuario; este informe describe esos archivos actuales.

**Resultado:** la base matemática es coherente, pero hay seis correcciones
concretas recomendadas. Dos afectan la confiabilidad de los valores medidos;
las otras afectan inicio, cancelación, timeout y recuperación de resultados.

## Hallazgos confirmados

### 1. P1 · La referencia antigua puede corregir un perfil instrumental distinto

Ubicación: `monitor/historico/v13/bode_calibration.py:24–33`,
`monitor/historico/v13/bode.py:105–108`,
`monitor/historico/v13/calibraciones/bode_v10.json`.

La compatibilidad sólo comprueba `bits` y `rate`; la casilla de corrección se
activa por defecto si existe el JSON. La referencia es ADC16/50 kHz creada el
3 de octubre, mientras que la documentación actual indica que fue medida con
reloj ADC de 40 MHz y que después se cambió a 50 MHz. El firmware actual local
configura PLL2 HSE/2 ×25 /4 en
`arduino/v13_pulse/oscilloscope/sketch/acquisition.h:62`. El mismo cambio figura
en V11 P992. Volver a ADC16/50 kHz hace que la referencia antigua se aplique
automáticamente aunque cambió el tiempo de conversión entre canales.

**Impacto:** se presenta como corregida una fase cuya calibración no está
validada para el hardware actual. Es especialmente relevante a alta frecuencia:
el JSON resta aproximadamente 31,9° a 10 kHz y 63,5° a 20 kHz. No se midió en
esta revisión cuánto error residual introduce ahora.

**Corrección:** conservar la referencia histórica, pero no habilitarla como
válida para la cadena actual; agregar identidad de firmware/reloj y parámetros
de adquisición que afecten el desfase. Una nueva referencia requiere un ensayo
de conexión directa explícito. No sustituir sus valores por una regla teórica
ni extrapolar la antigua calibración a otras tasas.

### 2. P1 · El descarte de muestras en Tonos introduce aliasing en el ajuste

Ubicación: `monitor/historico/v13/bode.py:201`, `monitor/historico/v13/bode.py:237–248`.

Para ahorrar muestras se conserva una cada `stride`, sin filtro previo. La
validación de ruido también se hace después del descarte, cuando una señal
ajena ya puede ser indistinguible del tono buscado.

**Reproducción numérica:** Fs=40.000 Hz, tono=20 Hz, 6.001 muestras,
`V_IN=cos(2π20t)` y
`V_OUT=V_IN+0,2*cos(2π*(40000/62-20)*t)`.
El `stride` seleccionado por el código es 62. `tone_transfer()` con todas las
muestras devuelve −0,00550 dB y 0,00106°. Con las muestras que conservaría
`batch()` devuelve **+1,57743 dB y 0,96682°**, sin rechazar el bloque.
La interferencia de aproximadamente 625,16 Hz se pliega sobre 20 Hz.

**Corrección:** ajustar usando todas las muestras. Para limitar memoria, es
posible acumular por bloques los productos del ajuste senoidal y estadísticas
del residuo. Otra opción es filtrar antes de diezmar, contabilizando los
transitorios del filtro y aplicando el mismo procesamiento a ambos canales.
La prueba anterior debe convertirse en regresión.

### 3. P2 · Las consultas periódicas impiden que venza el timeout de captura

Ubicación: `monitor/historico/v13/bode.py:216–220`,
`monitor/historico/v13/bode_pulse.py:119–121`, `monitor/historico/v13/app.py:508–509`.

El worker consulta el estado del generador cada segundo. Una respuesta
`APPLIED` con la configuración activa vuelve a establecer `deadline` aunque
`waiting` ya sea falso. Esas respuestas también se envían a los paneles.

**Reproducción local:** con `active=True`, `waiting=False`, `deadline=1` y
reloj simulado en 100, una respuesta `APPLIED` coincidente deja el límite en
110,35 para Tonos y 110,5 para Pulso. Sweep/Chirp hereda el segundo caso.
Repitiendo la consulta cada segundo, el vencimiento siempre queda por delante.

**Impacto:** si dejan de llegar muestras pero el canal de control sigue
respondiendo, Bode puede permanecer activo indefinidamente. Además se vuelve a
escribir el estado de medición sin una transición real.

**Corrección:** consumir la confirmación sólo cuando se espera el ACK de esa
etapa. Las consultas periódicas no deben renovar el límite de captura.
Separar plazo de confirmación y plazo de adquisición, y probar el caso de
control vivo con datos detenidos.

### 4. P2 · Tonos ignora el rechazo real de una orden

Ubicación: `monitor/historico/v13/bode.py:212`,
`monitor/historico/v13/receiver/unoq_generator.py:67–68`.

El decodificador devuelve `requested=None` cuando la respuesta es `REJECTED`,
para admitir campos inválidos que el MCU puede devolver literalmente. Tonos
compara ese `None` con su configuración y retorna antes de mostrar el rechazo.

**Reproducción local:** `GeneratorReply(..., Phase.REJECTED, Reason.BUSY,
..., requested=None)` pasado a `BodeSweep.confirmed()` no llama a `cancel()`.

**Impacto:** un rechazo concreto queda oculto tras la espera y posterior
mensaje genérico de falta de confirmación. Si las consultas devuelven después
`APPLIED` para la misma configuración, también pueden confundirse estados.

**Corrección:** correlacionar solicitud y respuesta sin depender de que el
payload rechazado sea decodificable. El receptor ya filtra los rechazos por
`generator_pending.request_id`
(`unoq_config_receiver.py:225–233`); se puede conservar esa información al
notificar al panel. No copiar el filtro actual de Tonos a Pulso.

**Comprobación adicional:** no se confirmó un fallo por rechazo ajeno en Pulso
en el flujo normal: el receptor filtra esos rechazos antes de emitirlos.

### 5. P2 · Volver a Bode borra visualmente la curva actual

Ubicación: `monitor/historico/v13/spectrum.py:202–220`,
`monitor/historico/v13/bode_pulse.py:261–267`.

Al seleccionar otro método, `changed()` dibuja sus datos; después
`select_bode()` llama a `set_mode(3)`, cuyo `reset()` vacía la curva compartida.
No se llama a `draw()` después del reset. También ocurre en Bode → FFT → Bode.

**Reproducción con Qt offscreen:** asignar dos puntos a `panel.result`, llamar
a `draw()`, cambiar Tonos → Pulso → Tonos. Los dos puntos siguen en `result`,
pero `curve_sets[0][0].xData` queda en `None`.

**Impacto:** se pierde de vista la medición actual sin haberse borrado sus
datos. Las curvas de historial extra sí vuelven a ser visibles, por lo que
una comparación puede mostrarse incompleta. No se confirmó el supuesto fallo
de que las curvas extra nunca volvieran a mostrarse: `configure_plots()` sí
las vuelve a habilitar para el panel seleccionado.

**Corrección:** redibujar el panel seleccionado después de resetear y configurar
los gráficos al entrar en modo Bode; preservar un estado informativo acorde al
resultado. Probar retorno entre los tres métodos y entre FFT/temporal/Bode,
con una y varias curvas.

### 6. P2 · Pulso y Sweep/Chirp pueden comenzar con un cambio de ADC pendiente

Ubicación: `monitor/historico/v13/bode_pulse.py:79–80`, frente a
`monitor/historico/v13/bode.py:154`; `monitor/historico/v13/app.py:3351–3380`.

Tonos rechaza el inicio si `_auto_apply_timer` está activo. Pulso y Sweep/Chirp
omiten esa condición. Durante los 50 ms previos a aplicar una selección de
adquisición, el combo aún puede estar habilitado; bloquearlo no cancela el
temporizador.

**Reproducción con Qt offscreen y worker simulado:** activar el temporizador,
llamar a `BodePulse.begin()` con generador conocido y controles habilitados.
El resultado es `active=True`, estado «Preparando nivel previo…» y el
temporizador de adquisición todavía activo.

**Impacto:** se puede aplicar un cambio de tasa/transporte durante la captura,
después de haber guardado `result_profile`, o interrumpirla inmediatamente.

**Corrección:** compartir las comprobaciones de adquisición pendiente entre
los tres métodos; rechazar el inicio hasta recibir la confirmación de la
configuración elegida. Agregar regresión para el temporizador activo.

## Matemática y límites revisados

- Tonos calcula correctamente el cociente complejo de los coeficientes seno
  y coseno, con offset independiente por canal. La convención de fase es
  coherente con `V_OUT / V_IN`.
- Pulso y Sweep/Chirp comparten `FFT(V_OUT)/FFT(V_IN)`, con la misma captura
  rectangular y resta del nivel previo. Para un sistema lineal e invariante
  y una respuesta completamente contenida, el procedimiento es adecuado.
  Aplicar Hann a ambos registros no garantiza conservar ese cociente y no
  es una corrección automática aconsejable.
- La guarda previa de 1 ms evita contaminar la estimación de ruido con el
  flanco adelantado de A3. El FFT conserva las muestras y el desfase observado.
- Los huecos de referencia espectral se conservan como NaN. Una salida débil
  conserva ganancia estimada y omite fase bajo el umbral de ruido. Esto es
  intencional y está probado: la ganancia bajo ruido no acredita la atenuación
  real del circuito.
- El chequeo de cola y el asentamiento fijo son criterios de aceptación,
  no una prueba universal de que un circuito haya llegado al régimen. No se
  demostró aquí un defecto adicional concreto que justifique cambiar ventanas,
  umbrales o la fórmula de transferencia.
- La referencia de conexión directa podría ser utilizable entre métodos
  para una cadena estable y una banda válida; no se debe asumir su validez
  para pulsos submuestreados ni usarla para ocultar variaciones entre capturas.

## Pruebas y evidencia física disponible

Comando ejecutado:

```sh
QT_QPA_PLATFORM=offscreen .venv-v13/bin/python -m unittest tests.v13.test_bode_transient -v
```

Resultado: **6 pruebas aprobadas**, incluyendo filtro RC sintético con pulso,
barrido lineal y logarítmico, referencia insuficiente, discontinuidad, cola
incompleta, salida atenuada/ruidosa y flanco adelantado. La prueba de paneles
comprueba su independencia e inicio manual, pero no cubre los seis casos
anteriores. Las reproducciones adicionales de esta revisión se ejecutaron
como scripts temporales sin modificar tests del proyecto.

La evidencia física se consultó en los informes existentes; no se repitió:

- `diagnosticos/resultados_bode/20261006_barridos.json`: Sweep/Chirp con
  conexión A0 → A2/A3, ADC14/40 kHz. La documentación de esa prueba fija
  rango 20–2.000 Hz. No acredita todo el rango predeterminado actual
  20–5.000 Hz ni un circuito bajo prueba.
- `diagnosticos/resultados_bode/20261006_pulso_corregido_100k.json`:
  seis capturas válidas de pulso de 100 µs, ganancias medianas aproximadamente
  −0,04 a +0,07 dB; **fases medianas** entre −0,26 y +0,28°. Estos JSON
  resumidos no permiten afirmar que todos los bins estén dentro de ±0,3°.
- `diagnosticos/resultados_bode/20261006_pulso_corregido_40k.json`:
  seis capturas completadas, cobertura aproximada 93–97 % y fases medianas
  de hasta **9,116°**. Es una limitación física ya observada, no un error de
  signo del cociente FFT demostrado en esta revisión. Una muestra de 25 µs
  equivale a 9° a 1 kHz, pero el mecanismo físico exacto requiere medirlo.

Después de corregir los fallos locales, la aceptación física debería separar
integridad de captura, exactitud de ganancia y exactitud/repetibilidad de fase;
comparar los métodos con una conexión directa y un filtro conocido; cubrir
expresamente 2–5 kHz antes de ampliar lo que se considera validado.


## Correcciones implementadas · 2026-10-06

Los seis hallazgos anteriores quedan corregidos en V13:

- Calibración: cargar o aplicar una referencia exige identidad instrumental
  explícita y coincidente, además de bits/tasa. Como el monitor no dispone
  todavía de una identidad verificada del Q para calibración, la corrección
  permanece deshabilitada. El JSON histórico se conserva intacto.
- Tonos: se elimina el descarte periódico de muestras; el ajuste utiliza todas
  las muestras del bloque, conservando el límite de dos millones de muestras.
- ACK: sólo una etapa que espera confirmación puede actualizar su plazo;
  las consultas periódicas no prorrogan la adquisición.
- Rechazos: Tonos acepta el rechazo correlacionado por el receptor aunque
  el payload solicitado sea None y muestra su motivo.
- Gráficos: al entrar a Bode se redibuja el resultado seleccionado después
  del reset; el estado de una medición previa no se sustituye por «Listo».
- ADC pendiente: Pulso/Sweep/Chirp esperan también al temporizador de aplicación.

Regresiones: tests/v13/test_bode_review.py. No se operó el hardware durante
estas correcciones; la validación física hasta 5 kHz y con un filtro conocido
sigue pendiente. No se modificaron la fórmula FFT ni los umbrales de ruido.


### 2026-10-06 — Nuevas referencias instrumentales Bode

A0 conectado directamente a A2 y A3. Tres capturas por método y perfil,
20–5000 Hz, ADC14/40 y 100 kHz; dos capturas para referencia y tercera
independiente para aceptación. Se aceptaron Tonos y Sweep a ambas tasas,
y Chirp a 100 kHz. Pulso 100 µs a ambas tasas y Chirp a 40 kHz no pasaron
la repetibilidad exigida para toda la banda; no se guardan como calibración.
El monitor identifica serie/app activa/hash del binario instalado por App Lab
y exige perfil/método compatible; resultados e historiales retienen identidad.
La identidad no lee flash MCU: una programación externa obliga a invalidar
la referencia. Dos nuevos barridos físicos de Tonos verificaron carga y
aplicación automática: error máximo 0,044 dB/0,40° a 40 kHz y
0,042 dB/0,16° a 100 kHz. 40 pruebas locales aprobadas.
Evidencia: diagnosticos/resultados_bode/20261006_referencias_validacion.json
y 20261006_referencia_tonos_validacion_monitor.json.
Estado final ADC14/40 kHz, salida apagada; firmware experimental sin cambios.
