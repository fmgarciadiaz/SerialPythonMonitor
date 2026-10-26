# Revisión general de procesos y tasas V18 · 26/10/2026

Revisión de código, binarios y evidencia con Astra. No se operó el Q ni se
modificaron fuentes de producción durante esta revisión. V17 queda congelada.

## Estado comprobado

La cadena tiene propietarios y límites explícitos: adquisición MCU, relay,
receptor separado, procesamiento serial, entrega GUI y alimentación PCM/A0.
Las generaciones y créditos evitan mezclar configuraciones y acumular trabajo
sin límite. FILTER OFF evita el trabajo de filtro. El audio libera su crédito
sin esperar a que la GUI consuma toda la historia, sujeto al callback de DSP.
El relay usa envíos TCP no bloqueantes y conserva las tramas parciales.

Las 32 tasas nuevas pasaron el barrido RADIO/A0 de al menos 30 s por perfil;
los cinco máximos anteriores pasaron al menos 120 s cada uno. Todas las
restauraciones e identidades fueron verificadas. Sólo 6 de 37 casos cumplieron
el criterio de GUI visible; ADC8 máximo no está entre ellos. El usuario había
indicado dejar la aplicación en segundo plano.

Evidencia: `diagnosticos/resultados_v18/radio_rates_review_20261026_130257/`.
Las etiquetas del catálogo no tienen colisiones entre tasas distintas del
mismo formato en su vista recomendada: 17 opciones en 8–14 bits, 15 en 16 bits.
Esto no implica ausencia de colisiones al mostrar todos los perfiles históricos.

## Hallazgos

### 1. Prioridad alta: separar aceptación histórica y pareja actual

Los máximos conservan `headroom` y `combined_qualified` junto con evidencia de
parejas anteriores. Las pruebas recientes de la pareja catálogo no volvieron
a medir holgura, y ADC8 máximo todavía carece de aceptación de dibujo visible
sobre esa pareja. El tooltip presenta margen validado sin distinguir identidad.

Referencias: `monitor/v18/receiver/native_profiles.json`,
`monitor/v18/app.py:5489–5501`, `monitor/v18/radio_output.py:8–17`.

Acción propuesta: describir evidencia por hashes firmware/relay, geometría,
carga, duración y alcance. Distinguir integridad, funcionalidad RADIO/A0,
holgura, GUI visible y precisión analógica. Conservar los resultados históricos;
no convertir un PASS funcional en una aceptación completa ni borrar tasas.

### 2. Prioridad alta: localizar la pausa que saturó el ADC8 máximo

El fallo original está confirmado: un nodo perdido, cola MCU 8/8, CRC y
secuencia correctos; el relay detectó la pérdida y terminó. La reproducción
posterior no elimina esa evidencia. No está demostrado si la pausa provino
de scheduling, servicio SPI, carga simultánea o cambio temporal de binarios.

Referencias: `arduino/v18/relay/config_relay_protocol.h:24`,
`arduino/v18/relay/unoq_config_stream.c:94–107`,
[diagnóstico del incidente](DIAGNOSTICO_ADC8_MAX_20261026.md).

Acción propuesta: registrar picos de tiempos SPI/READY y huecos de servicio,
cola ADC y backlog TCP en una ventana acotada, evitando logs por cada trama.
La instrumentación del relay requiere candidato aislado, medición de su coste,
respaldo y restauración. Repetir ADC8 máximo con dibujo visible cuando sea
posible. Si reproduce diferencia, comparar las parejas completas bajo igual carga.

### 3. Prioridad media: correlación pasiva en el camino serial de DSP

El callback alimenta A0 y luego ejecuta el detector de realimentación antes de
liberar el crédito IPC y permitir el siguiente trabajo del executor. El detector
puede realizar cuatro correlaciones FFT. Los registros anteriores observaron
episodios de 20–40 ms, pero no prueban que causaran la pérdida MCU.

Referencias: `monitor/v18/app.py:690–728`,
`monitor/v18/radio_loop_guard.py:54–76`.

Acción propuesta: medir distribución de latencias y frecuencia real del detector.
Si domina el camino, evaluar su optimización aislada preservando detección,
parada automática, orden de sesiones/generaciones y tiempo de reacción. No
quitarlo ni saltar observaciones sin evaluar el efecto sobre la protección.

### 4. Prioridad media: identificar exactamente el presupuesto host agotado

La GUI limita tiempo, muestras, memoria y lotes. El receptor tiene además
límites propios de créditos y RF pendiente. Son protecciones válidas, pero un
mensaje genérico impide identificar qué recurso se agotó primero. El tope de
1,6 millones de muestras equivale a unos 860 ms a 1,86 MS/s, frente al límite
adicional de un segundo; la memoria también puede dominar según los canales.

Referencias: `monitor/v18/radio_delivery_budget.py:6–22`,
`monitor/v18/io/receiver_process.py:279–307`.

Acción propuesta: registrar límite responsable, valor actual y pico, junto con
bits/tasa/canales y generaciones, reutilizando el diagnóstico de fallo existente.
No aumentar presupuestos como supuesto arreglo de un consumidor atrasado.

### 5. Prioridad media: medir backlog TCP y distinguir cierres

La cola de envío tiene 64 tramas y no bloquea. Si se llena, el relay cierra el
cliente; esto es distinto del cierre por pérdida de un nodo ADC, que termina
el relay. La congestión del host no demuestra por sí sola la causa del fallo MCU.

Referencias: `arduino/v18/relay/frame_send_queue.h:3–28`,
`arduino/v18/relay/unoq_config_stream.c:176–190`.

Acción propuesta: contar pico de backlog, EAGAIN, envíos parciales y cierres por
ENOBUFS. Mostrar razones distintas para cierre del cliente, fallo de integridad
y parada del relay. Mantener los criterios de rechazo.

## Cambios temporales confirmados, sin causalidad demostrada

Los predicados del catálogo agregan tres comparaciones/ramas en las rutas ADC8/86.
`scope_high_rate` pasó de 268 a 328 bytes y `scope_spi40` de 60 a 72 bytes en los
ELF revisados. El coste es por nodo/batch, no por muestra. La búsqueda native
encuentra ADC8/86 en la misma posición: las entradas nuevas están al final.
`scope_cpu_runtime` retorna inmediatamente mientras no cambia la política;
no lee ni escribe el governor en cada trama.

Estos hechos justifican medir, pero no atribuirles la pausa registrada ni
reordenar rutas críticas sin una comparación física.

## Orden de trabajo propuesto

1. Separar alcances e identidad en evidencia y mensajes de validación.
2. Precisar el diagnóstico host sin alterar límites, créditos o muestras.
3. Preparar instrumentación mínima del relay en un candidato aislado.
4. Repetir el máximo ADC8 con carga visible y comparar parejas si falla.
5. Optimizar la correlación o los predicados sólo si las mediciones lo justifican.

Conservar tasas, relojes, sobremuestreo, SPI, prioridades y capacidades actuales
hasta disponer de una causa medida. La siguiente incorporación recomendable es
la mejora de diagnóstico y trazabilidad, no otra modificación de las tasas.
