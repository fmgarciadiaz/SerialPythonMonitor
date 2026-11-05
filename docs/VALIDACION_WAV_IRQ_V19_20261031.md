# V19: validación PCM antes de bloquear interrupciones

Candidato privado diseñado con las observaciones de Astra: mover únicamente el
recorrido de validación de códigos DAC (0–4095) antes de `irq_lock` en
`wav::submit`. El buffer recibido permanece estable hasta que retorna la llamada.
El recorrido conserva todas sus iteraciones; no cambia CRC, protocolo, deduplicado,
prioridad de BUSY/UNSUPPORTED, tamaño de reserva ni atributos de compilación.
`poll`, copia, caché, descriptores DMA y publicación de cola siguen protegidos.

La transformación exacta está en `tools/wav_validation_candidate_v19.py`.
El constructor `tools/compare_wav_validation_q_v19.py` compila control y candidato
en una carpeta privada del Q, con la pareja detenida y recuperación del
procedimiento de compilación existente. No modifica el sketch local aceptado.
El binding privado reconoce únicamente esta transformación o el experimento
Os/O2 anterior; no permite reemplazar un archivo arbitrario.

## Pruebas locales

Se ejecutaron ambas máquinas de estado C++ reales de V19 con la misma traza:
BUSY por sesión/cola/cantidad, muestra 4096, duplicados y conflicto de ID,
30 bloques, vuelta del buffer, fragmento final, DONE, UNDERRUN y STOP.
Respuestas y estado coinciden; la publicación al DMA exige bloqueo activo.
La cantidad inválida 481 con puntero nulo no se lee. Esto verifica semántica,
no rendimiento físico, propiedad DMA real ni duración de interrupciones.

## Fallo previo encontrado durante el preflight

Antes de cargar un candidato, el relay aceptado estaba detenido. Su registro
conservado informa un bloque con CRC correcto, `dropped_nodes=1`,
`fatal_errors=0`, cola actual 7 y pico 8, ADC8/CH1, ticks 86
(1.860.465 muestras/s), secuencia 8.542.356 y nodo 478.236.
Es una pérdida real reportada por MCU; no prueba su causa ni la configuración
RADIO/A0 del instante. Reiniciar sólo el relay no la borra: el MCU conserva el
contador y el relay vuelve a rechazar el flujo. Se verificaron hashes y fuentes
y se reinició la pareja V19 mediante su launcher normal.

Evidencia: `diagnosticos/resultados_v19/wav_validation_relay_preflight_20261031/`.
Los intentos previos de compilación abortaron antes de instalar firmware:
uno por restricciones de ADB y dos por relay inactivo. Se conservan esos informes.

## Criterio para incorporar

Compilación control idéntica al BIN aceptado, carga privada exacta, sondeo corto,
60 s y tres corridas independientes de 120 s sólo si los anteriores pasan.
Exigir integridad, audio, dibujo realmente visible, margen medio >=10%, pico de
cola <4, slack positivo y restauración verificada. No hay promoción de tasas
ni afirmación de mejora hasta contar con esas medidas.

## Compilación física

El control recompilado coincide exactamente con el firmware aceptado:
`37f049fa029ad62a10767c56dc586b2c3697f8d250a0b8a7396570ce8e0c7060`.
Candidato: `03f9e1a9425dc287ae4ffd8402f7dc1f00e878985f7aa16e1824584ec22fc6e6`.
GCC14.3.0 aceptado, atributos originales sin cambios. La compilación aislada
terminó con restauración verificada (`ok=true`, `restoration.ok=true`).
Informe: `diagnosticos/resultados_v19/wav_validation_build_live_20261031/report.json`.
39 tests locales PASS, incluidos rechazos por alterar encabezado, sketch o BIN.

## Sondeo físico: no pasa holgura

RADIO/A0 a 40 kHz con RF ADC8/1.860.465 S/s y FFT16k: 20,043 s,
802.080 muestras reproducidas, ventana expuesta el 100%, 610 paint events.
Pasaron progreso y parada RADIO, WAV, FM y cierre. Sin errores del ensayo.
Margen medio PLAY **10,69%**, slack mínimo 79.875 ticks, cola pico **4**:
FAIL de holgura. El pico creció 2→3→4 en PREPARING; no aumentó durante PLAY.
No se hicieron 60/120 s ni se incorporó el candidato. Una corrida corta tampoco
prueba que su margen mejore frente al control previo.

Restauración exacta de fuentes/caché/firmware/relay/configuración/CPU y snapshot.
Verificación final 10,025 s, 313.344 muestras, cero pérdidas y fatales.
Pareja aceptada activa; V17/V18 y tasas públicas intactas.

[Resumen del sondeo](../diagnosticos/resultados_v19/wav_validation_gui20_20261031/summary.json).

Siguiente experimento posible: combinar este cambio aislado con prellenado
uniforme 1 bloque/8 ms, que antes evitó picos de preparación, manteniendo PLAY
8 bloques/6 ms. Sería un candidato nuevo, no una aceptación de ninguno de los
dos cambios. Medir también duración real de IRQ por un canal diagnóstico
explícito; `check_us` sigue incluyendo más trabajo que el bloqueo.
