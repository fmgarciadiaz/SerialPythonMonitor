# Revisión e implementación con Astra — 14/10/2026

Revisión de toda la cadena V17, autorizada por el usuario, seguida de
implementación de mejoras host acotadas. Sin operación del Q.
Las pruebas físicas anteriores son baseline, no aceptación de estas fuentes.

## Implementado

Defaults posteriores solicitados por el usuario: RADIO Gain ×2 y Offset
1,65 V; generador/WAV/Radio Test y volumen Synth 2 Vpp. El DSP aplica
la escala digital sin normalizar la señal a 2 Vpp.

- Gain/Offset: cambiar sólo niveles conserva demodulador, remuestreador y
  estado de filtros. FILTER produce el transitorio natural del cambio.
  La GUI inicia historial con la escala nueva y conserva generaciones para
  rechazar resultados anteriores. Reinicios explícitos, configuración RF,
  sintonía, FS y FILTER siguen reconstruyendo el DSP. Cambios de niveles
  con generaciones saltadas también reinician conservadoramente.
- FFT: una lectura de historial y un análisis por canal dentro de cada
  actualización, aunque ambos paneles seleccionen el mismo canal.
  No cambia la posición de las ventanas, fase, PSD, promedios ni SINGLE.
- Pintura FFT: reutiliza pen/brush por panel y color; no reinstala el pen
  si ya coincide. Conserva actualización de rangos y respuesta a interacción.
- IPC: envía índices, timestamps y sólo los canales requeridos por RADIO
  y FILTER. Los historiales RF permanecen en el padre. El retorno sigue
  limitado a audio/FILTER/metadatos. No introduce memoria compartida.
- Runner offline: permite elegir `--backend thread` o `--backend process`
  y cierra el proceso al terminar.

## Evidencia local

83 pruebas de procesamiento, RADIO/UI, FFT/UI y análisis espectral pasaron.
Incluyen continuidad del dueño DSP al ajustar niveles, equivalencia de
salida, reinicio explícito, IPC por proceso, generaciones/ACK y análisis
único de un canal seleccionado en dos paneles.

Dos ensayos sintéticos de 15 s, ADC8/CH1 1,4035 MHz, RADIO40, FILTER RADIO,
trigger y FFT65536, pasaron con 762 lotes/21067776 muestras RF cada uno,
sin errores, cola pico cuatro:

- `diagnosticos/resultados_v17/processing_optimization_review_20261014.json`
  (thread): 600374 muestras audio, DSP medio 2,108 ms/lote.
- `diagnosticos/resultados_v17/processing_optimization_process_20261014.json`
  (process): 702 lotes DSP y 553096 muestras audio, DSP medio 2,064 ms/lote.
  Los 60 lotes iniciales entregaron RF mientras el proceso se preparaba,
  conforme al comportamiento de arranque. No son 15 s completos de audio.

Son ejecuciones separadas, no una comparación causal de rendimiento.
No acreditan transporte físico, FPS visibles ni estabilidad AM analógica.

Para un lote CH1 de 27648 muestras, serialización pickle protocolo 5:
774919 bytes antes y 553653 después, aproximadamente 29% menos.
Informe: `diagnosticos/resultados_v17/optimization_ipc_bytes_20261014.json`.
No equivale a medir reducción de latencia ni margen del relay.

## Oportunidades pendientes de medición

1. FFT incremental y reutilización de temporales: hoy las ventanas se
   anclan a la última muestra. Hops fijos cambian esa semántica; en RF a
   10 Hz hay poca reutilización potencial. Evaluar primero audio/bajas FS.
2. Pintura: medir coste del relleno y rangos con ventana expuesta, resize,
   escalas lineal/log y picos estrechos, sin ocultar detalles.
3. Representación de ejes/CH2 NaN y buffers: medir bytes y memoria antes
   de alterar wrap uint32, propiedad de muestras o capturas congeladas.
4. Remuestreo: reducir matrices temporales por fase sólo si el perfil lo
   justifica; conservar FIR, lookahead y límites racionales.
5. MCU/relay: instrumentar READY, SPI, CRC, packing y socket en campaña
   aislada. El margen previo 8,69–8,83% no mejora por optimizar la GUI.
6. Repetir aceptación física RADIO/FILTER/FFT, ventana visible y Scan
   concurrente; la señal AM conocida y su estabilidad siguen pendientes.

Ya existen caché de ventanas FFT y reducción de extremos por píxel.
RADIO FS40, controles de integridad, ocho lotes admitidos y buffer RF acotado
se conservan. Firmware y relay permanecen sin cambios.

## Segunda revisión Astra · 14/10/2026

Revisión de las fuentes actuales, incluyendo V(t) mixto RF/RADIO. Las prioridades 1–4 se implementaron después de esta revisión; el punto 5 requiere una campaña física independiente. La evidencia posterior se detalla abajo. Offline mixto previo: 762 lotes completos, render medio 2,90 ms con ruido / 3,29 ms con AM, decoder alrededor de 2,34 ms/lote y DSP alrededor de 2,0 ms/lote. El hash actual de app.py difiere del reporte de comparación.

| Prioridad | Cambio propuesto | Verificación necesaria |
|---|---|---|
| 1 | Vectorizar candidatos del trigger mixto conservando histéresis de diez muestras e interpolación. Un outlier aislado puede habilitar miles de cruces Python. | Comparar índice/fracción con referencia: ruido con outlier, ráfagas, AM, ambos flancos, Auto/Normal/SINGLE. |
| 2 | Compartir reloj, índices y X por dominio RF/audio en cada frame; después copiar sólo la ventana necesaria del historial circular. | Equivalencia X/Y, wrap, H-pos antigua, dos canales por dominio y SINGLE inmutable. |
| 3 | Cache exacta de Configuration por bits y encoded, preservando prioridad de perfiles y todas las validaciones. | Replay válido/corrupto, cambios APPLIED, contradicciones y benchmark decoder. |
| 4 | Mover distortion() de Power al trabajador acotado con snapshot y descarte por contexto/generación. | Power65536 tonal/armónicos, cambios de canal/banda, respuesta GUI y coincidencia numérica. |
| 5 | Instrumentar MCU/relay antes de intervenir READY/SPI/CRC/packing/socket. | Campaña física aislada y restauración; margen medido separado del rendimiento GUI. |

Ubicaciones: `_render_mixed_temporal` en app.py, `history.py`, `receiver/unoq_config_decoder.py`, `receiver/unoq_acquisition.py`, `receiver/unoq_native.py` y `spectrum.py`. No se prioriza otra intervención en FILTER/remuestreo ni Scan bajo demanda. Se mantiene RADIO40 y todas las comprobaciones de integridad.

## Segunda implementación y verificación · 14/10/2026

- Trigger mixto: selección vectorizada de cruces en el intervalo válido y misma histéresis sobre hasta diez muestras previas. Conserva el último cruce válido y su interpolación.
- Ventanas mixtas: búsqueda binaria en el reloj circular, copia sólo `[left,right]` y comparte índices/X por dominio RF/audio durante el frame. Las ventanas siguen siendo copias independientes de nuevas escrituras.
- Decoder: cache LRU de 128 perfiles exactos por `(bits, encoded)`. Configuration es frozen; CRC, geometría, rate, canales, época y continuidad siguen comprobándose en cada frame.
- Power: reutiliza el trabajador de distorsión, con una tarea pendiente, snapshots copiados y descarte por generación/contexto. SNR aparece N/A hasta tener un ajuste válido; SINGLE conserva ajuste síncrono. También recoge el resultado aunque no lleguen muestras nuevas.

106 pruebas de RADIO/UI, FFT/UI, historia circular, protocolo, procesamiento y perfiles pasaron. Dos comprobaciones posteriores de ventana antigua y reloj compartido también pasaron (una ya pertenecía a la suite): 107 pruebas distintas aprobadas. Incluyen ruido con outlier y ambos flancos comparados contra referencia, H-pos antigua, wrap/duplicados, snapshots independientes, rechazo de campos contradictorios incluso con perfil cacheado y Power pendiente/contexto.

Comparación controlada con historiales fijos y llamadas alternadas, 80 pares por caso; todos los ejes y valores coinciden exactamente con la referencia anterior:

| Caso | Mediana anterior | Mediana nueva |
|---|---:|---:|
| AM con trigger | 1,131 ms | 1,168 ms |
| H-pos hacia el pasado | 1,084 ms | 1,048 ms |
| Ruido pequeño con outlier aislado | 4,581 ms | 1,234 ms |

La mejora demostrada está en el caso patológico del trigger (aprox. 3,7×), no en una aceleración general de AM. Runner reproducible: `diagnosticos/benchmark_mixed_trigger_v17.py`; resultado `diagnosticos/resultados_v17/mixed_render_controlled_20261014.json`. Usa una referencia reconstruida del renderer anterior y Qt offscreen; no mide FPS visibles.

Dos ensayos completos offline de 15 s con ADC8/CH1 1,4035 MHz, RADIO40/FILTER y V(t) mixto entregaron 762 lotes/21.067.776 muestras RF cada uno, sin errores y a tasa completa. Resultados:
`mixed_temporal_second_optimization_20261014.json` y `mixed_temporal_second_optimization_isolated_20261014.json`, en `diagnosticos/resultados_v17/`. El segundo se ejecutó sin la suite completa en paralelo (hubo una comprobación breve de interfaz): decoder medio 2,094 ms/lote, render 3,849 ms, cola pico cinco. El primero dio decoder 1,868 ms y render 3,544 ms. La variación entre corridas no demuestra causalmente una mejora general frente al baseline. El runner completo ahora registra hashes de fuentes.

No se operó el Q ni se modificó firmware/relay. La aceptación física, FPS visibles, Power bajo carga real y el margen del transporte siguen siendo verificaciones independientes pendientes.
