## 14/10/2026 — Eficiencia física: host y visualización

Revisión posterior e implementación host con Astra:
[optimizaciones y evidencia local](OPTIMIZACIONES_ASTRA_V17.md).
Los ensayos físicos siguientes corresponden a fuentes anteriores a ese incremento.

**Vista temporal con trigger: ensayo físico de 120 s completado.**
Informe: `diagnosticos/resultados_v17/radio_live_20261014_113834.json`.
ADC8/CH1 a 1,4035 MHz, RADIO40 y FILTER RADIO: 168448896 muestras RF,
4800760 de audio, sin errores ni dropped/fatal. La ventana estuvo expuesta
el 100% del ensayo y registró 62,41 FPS reales; DSP medio 2,319 ms por lote,
cola admitida y transporte pico 3. Margen medio de envío 8,83% y slack
mínimo 1028,03 µs: no acredita holgura conjunta >=10%.
Restauración confirmada a ADC10/909090 SPI y generador apagado, identidad
de firmware idéntica antes/después, y 9089104 muestras de recuperación
durante 10 s sin pérdidas. El generador estuvo apagado durante el ensayo:
estos FPS no acreditan estabilidad visual del trigger sobre una señal AM
conocida ni aceptación analógica.

**FFT visible aceptada durante 120 s:**
`diagnosticos/resultados_v17/radio_live_20261014_113600.json`.
168395328 muestras RF, 4799234 audio, 5339 lotes, sin errores; cola admitida
pico 3 y ventana expuesta el 100% del ensayo. FFT65536 dibujó 9,88 FPS reales.

| Etapa | Tiempo medio medido |
|---|---:|
| Decoder | 0,109 ms por lectura decodificada |
| Demodulación | 1,529 ms por lote |
| Remuestreo | 0,367 ms por lote |
| FILTER audio | 0,126 ms por lote |
| DSP total | 2,459 ms por lote |
| Entrega e historiales GUI | 0,485 ms por lote |
| Análisis/preparación FFT | 12,272 ms por actualización |
| Paint FFT real | 11,638 ms por pintura |

Latencia publicación→consumo: media 8,07 ms, máximo 104,40 ms. Buffer RF
pico 183168 muestras; no fue necesario agrupar por presión de cola en esta
ejecución. Integridad Q/relay intacta, cola transporte pico 3, slack mínimo
1125,48 µs. Margen medio de envío 8,69%: **no acredita holgura conjunta >=10%**.
Q restaurado a ADC10/909090 SPI y generador apagado; firmware instalado
con identidad idéntica antes/después y recuperación de 10 s sin errores.
Los tiempos son de etapas distintas y concurrentes; no se suman como CPU
total. La captura con ventana cubierta indicada más abajo queda histórica.

La integración CH1 está completada: [perfiles y evidencia](INCORPORACION_CH1_V17.md).
RADIO permanece a 40 kHz. Con ventana expuesta, el trabajador por hilos
acumuló ocho lotes durante FFT65536 y se detuvo explícitamente. Transporte
mantuvo dropped=fatal=0; esto no es un límite nuevo del ADC.

El DSP ahora tiene un único dueño en un proceso separado, con el mismo
límite de ocho lotes, generaciones y ACK ordenados por el coordinador.
FILTER OFF no crea proceso ni ejecuta DSP. Se envían los bloques RF una
vez y sólo vuelven audio/FILTER/metadatos, evitando copiar RF de regreso.
Activar DSP después de OFF muestra “Preparando DSP…” mientras nace su
dueño; RF continúa, audio/FILTER empiezan cuando el proceso está listo.
El arranque confirma una sola configuración y espera a que GUI instale
sus historiales antes de publicar bloques.

Una prueba posterior con ventana al frente detectó una pausa de entrega
de 578 ms y agotó los ocho lotes aunque DSP sólo necesitaba 2,49 ms/lote:
`diagnosticos/resultados_v17/radio_live_20261014_113115.json`.
Se añadió agrupamiento RF cuando hay cuatro lotes admitidos pendientes:
el lector sigue validando y conserva los bloques en orden, luego publica
un lote mayor. La cola admitida sigue limitada a ocho; el buffer previo
tiene un límite de un segundo de muestras por configuración, más el
último bloque de entrada que dispara el límite. Si se supera, se detiene
explícitamente. En ADC8/1,4035MHz esto requiere hasta unos 22,5 MB de RF
uint32; la conversión/IPC genera además sus arrays temporales.
Las pruebas verifican unión sin huecos, FILTER NaN durante preparación,
OFF sin proceso, continuidad del dueño DSP, reinicio de generación,
orden de ACK y conservación del error primario ante fallo de apagado.
109 pruebas amplias pasaron; después del agrupamiento pasaron las 20
pruebas actuales de procesamiento.

FFT/heatmap grandes (>=16384) con adquisición física actualizan hasta
10 Hz y ceden si hay más de un lote pendiente. Conservan resolución FFT
y todos los lotes adquiridos; SINGLE sigue ejecutándose explícitamente.
FFT menores mantienen sus intervalos anteriores.

Primera captura de 120 s con IPC reducido pasó adquisición/DSP:
`diagnosticos/resultados_v17/radio_live_20261014_112718.json`.
170943264 RF, 4871850 audio, sin errores; DSP medio 3,657 ms/lote.
**No valida FPS visibles:** exposición sólo 5,73%; la ventana estaba cubierta.
La prueba exige ahora exposición >99% y mantiene la ventana al frente.
Los informes fallidos anteriores se conservan; algunos errores secundarios
de apagado ocultaron la sobrecarga original. El error primario ahora se
preserva y no se reenvía el bloque que ya avanzó su reloj.

Generador apagado: estas mediciones no validan recepción AM analógica,
DAC/THRU, Scan concurrente ni estabilidad del tono demodulado con señal real.

# Revisión V17 — 2026-10-14

Continuación del hilo 01a13842-4882-73c1-b67b-ec8a3bc7463c.
Revisión de Astra de toda la cadena, sólo lectura; sin operación del Q.
FS RADIO permanece en 40 kHz.

## Estabilidad del audio

`diagnosticos/resultados_v17/radio_stability_synthetic.json` contiene una
medición offline con RF 160 MHz/114, portadora 20525 Hz, AM 50%, tono 1 kHz,
duración 0,6 s y bloques de 3456 muestras. Tras descartar 100 ms de arranque,
se ajusta seno/coseno/DC en ventanas de 20 ms. Semilla de ruido: 17.

| Entrada | Amplitud pico a pico relativa | Residuo RMS relativo a amplitud |
|---|---:|---:|
| Ideal | 0,0000091% | 0,000581% |
| Cuantizada ADC8 | 0,0293% | 0,114% |
| ADC8 con ruido RMS 1 LSB | 0,208% | 0,426% |

Esto acredita estabilidad sintética del DSP en este caso, no del DAC,
señal analógica, dos portadoras simultáneas ni dibujo visible.
El trigger audio en `monitor/v17/app.py` elige un cruce a muestra entera:
a 40 kHz queda una incertidumbre temporal inferior a 25 µs, equivalente
a 9 grados a 1 kHz. Es una hipótesis de variación visual, aún no verificada.

## Auditoría de eficiencia

- ADC/DMA y relay tienen métricas de integridad/cola/holgura. Falta campaña
  conjunta sostenida con RADIO, FILTER y FFT; no inferir margen del host.
- Decoder valida CRC/secuencia y usa NumPy, pero convierte payload ADC8
  a cuatro columnas uint64, concatena y convierte a float64. Medir coste
  y tráfico de memoria antes de modificar; conservar validaciones.
- Qt limita a ocho lotes pendientes con ACK. DSP y FFT siguen en GUI;
  el límite evita acumulación ilimitada pero no garantiza latencia visible.
- RADIO ya fusiona heterodino y FIR polifásico. El remuestreo precalcula
  fases, pero aún materializa matrices de 800 por 128 en bloques de 20 ms.
- FILTER usa SOS y coeficientes cacheados. Historial circular correcto,
  con columnas/ejes redundantes en CH1/RADIO que conviene medir.
- FFT en GUI reconstruye ventana y segmentos de promedio; evaluar caché
  e incremento por hops nuevos tras medir. Trigger/dibujo necesita prueba
  de alineación fraccional y paintEvent con ventana expuesta.
- Scan corre bajo demanda en worker. Mejora localizada con muchas imágenes,
  no prioridad para coste continuo.

El informe actual `radio_gui_offline_15s.json` registra 750/750 lotes,
media 4,698 ms, pico 40,400 ms, atraso máximo 85,100 ms y cola máxima 5.
Inyecta NumericBatch directamente y usa offscreen: no mide decoder,
transporte físico ni FPS visibles. Las cifras anteriores en documentación
corresponden a otra ejecución.

## Próximas pruebas propuestas

1. Seno ideal a FS40 con trigger: comparar cruce entero/fraccional y frames
   para separar variación numérica de movimiento visual.
2. Medir por etapa p50/p95/p99, máximos, bytes/lote y antigüedad de cola;
   medir paintEvent y exposición por separado.
3. Según resultados, separar DSP continuo de GUI con dueño único del estado,
   cola acotada y reinicio por generación/discontinuidad. Coalescer sólo dibujo.
4. Optimizar remuestreo/copias y FFT según costes; validar equivalencia.
5. Ensayo físico sostenido: integridad, margen, estabilidad y FPS separados.

La revisión inicial no modificó procesamiento. El incremento siguiente,
autorizado en el hilo 01a13897-85ea-7632-af80-4ae935c34b40, se detalla abajo.

## Implementación y continuidad del 14/10/2026

FILTER incorpora OFF como fuente inicial: no ejecuta el filtro ni acumula
su historial. Sus controles quedan deshabilitados hasta elegir una fuente.
La adquisición RF continúa normalmente. RADIO conserva FS40 predeterminada.

`processing.py` concentra demodulación, remuestreo y FILTER en un executor
de un único trabajador, separado de GUI. El límite de ocho lotes comprende
DSP y entrega a GUI; los ACK de adquisición esperan los lotes anteriores.
Las generaciones de configuración impiden publicar audio/filtro antiguos
después de cambiar o apagar la fuente. FFT y dibujo todavía corren en GUI.
El trigger audio calcula el cruce fraccional y desplaza sólo el eje X;
conserva las muestras Y originales. Pruebas a 1/4 kHz, ambos flancos y
distintas fases verifican nivel y continuidad del eje, sin aceptación visual.

Remuestreo: ventanas contiguas de 128 muestras y producto vectorizado;
límites racionales exactos evitan publicar una muestra antes de que exista
su lookahead. Decoder: registros uint32 de 16 bytes/muestra, frente a los
32 previos, conservando valores/índices/timestamps incluso al envolver uint32.
Espectro: coeficientes/ventanas reutilizados; comparación numérica y costes
en `diagnosticos/resultados_v17/dsp_efficiency_before_after.json`.

La cadena completa offline pasó 120 s con RADIO40, FILTER RADIO, trigger y
FFT65536: 6092/6092 lotes, 168431616 muestras RF, 4800243 audio,
sin errores, pico cinco lotes pendientes. DSP medio 3,67 ms/lote,
entrega GUI 0,46 ms y antigüedad máxima 90,20 ms. Informe:
`diagnosticos/resultados_v17/processing_gui_offline_120s.json`.
Estos números no acreditan transporte físico, paintEvent visible, estabilidad
analógica ni holgura del Q con RADIO/FILTER/FFT.

Al retomar se verificaron 92 pruebas locales de DSP, FILTER/UI, trigger,
espectro, colas, decoder/continuidad, Scan y contrato C/C++ del barrido.
Campaña física CH1 ADC10/12/14 aislada en `experimentos/maxfreq_optimized_v17`;
duraciones autorizadas: 60 s + tres arranques independientes de 120 s,
sin etapa de 600 s. La reanudación conserva el reporte original y comprueba
los hashes locales y desplegados antes de completar la última etapa pendiente.
