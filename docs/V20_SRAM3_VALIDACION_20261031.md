# V20 SRAM3: revisión y sondeos privados

Se retoma la pareja independiente creada por Gemini. V19 es el control y destino
de restauración; no se modifican sus fuentes ni su aceptación. V20 todavía no
está promovida ni tiene un recibo de aceptación física propio.

## Estado encontrado

Scope V19 y su relay estaban activos, sin cliente TCP; V20 estaba detenida.
No había benchmark en ejecución. El BIN V19 instalado coincide con el aceptado
`37f049fa029ad62a10767c56dc586b2c3697f8d250a0b8a7396570ce8e0c7060`.
La app candidata importada es `/home/arduino/ArduinoApps/scope-v20-20261031-225916`.

## Correcciones para medir sin confundir versiones

- Las rutas copiadas de preparación/board/backend/identidad apuntaban todavía a
  Arduino V19, relay V19 y recibo aceptado V19. En los módulos V20 se separaron
  esos destinos. El recibo copiado se marca explícitamente como referencia no
  aceptada: no puede autorizar una preparación V20 con binarios V19.
- Perfiles cuyo firmware ahora usa16slots seguían declarando8 en el receptor.
  Se alineó su capacidad de decodificación. Las tasas nuevas de2/2,05MS/s se
  marcan privadas, con aceptación pendiente; no se publicitan como calificadas.
- El script inicial reutilizaba el ID de configuración, no verificaba CRC/ACK y
  consideraba suficiente cola<16. Se deshabilitó su entrada antigua. El nuevo
  `tools/probe_v20_sram3.py` usa el receptor real V20, confirma APPLIED y conserva
  CRC, secuencia, índices, timestamps y contadores de adquisición.
- El nuevo ensayo se ejecuta dentro de la transacción V19 ya calificada: propietario
  único, captura, respaldo de fuentes/caché/BIN/ELF/relay, parada y restauración
  exacta verificada durante10s. V20 compila su relay con la adquisición detenida.
  No se eliminan apps de la biblioteca ni contenedores ajenos; el relay del ensayo
  queda detenido como evidencia con nombre único.

## Qué significa la RAM libre

SRAM3 tiene512KiB según el [datasheet de ST](https://www.st.com/resource/en/datasheet/stm32u585vi.pdf).
El código de V20 coloca Storage mediante referencia a0x20040000, fuera del área
que contabiliza el linker. Por eso disminuye su .bss reportado; los buffers siguen
ocupando RAM física. Falta todavía reservar/auditar formalmente esa región contra
otras asignaciones, revisar ECC/atributos y comprobar comportamiento sostenido.
La compilación normal observada reportó94.552bytes globales y167.592libres en la
región principal, sin advertencia de memoria baja. Esto no garantiza estabilidad.

16nodos de3.488muestras son55.808muestras:29,997ms a1.860.465S/s,
27,904ms a2MS/s y27,206ms a2.051.282S/s. Es capacidad nominal, no inmunidad
al jitter ni una medición del margen real. Se conservan por separado integridad,
pico de cola, margen/slack y aceptación GUI/audio/analógica.

## Primer intento preservado

`sram3_initial_20261031`: el script no detectó sincronización porque buscaba el
mensaje en stdout y el relay lo escribe en stderr. El log sí contiene primer
frame verificado y2432frames/622.592pares sin pérdidas. No se ejecutó la matriz
de tasas, por lo que ese log no prueba las tasas nuevas. Lectura corregida para
el siguiente intento. Restauración V19 verificada.

Cuatro tests locales pasaron: aislamiento de preparación, rechazo de recibo
copiado, candidatos privados, capacidad16, rechazo de CRC y exceso de capacidad.

## Resultados físicos

| Relay | Tasa | Duración | Margen medio | Pico |
|---|---:|---:|---:|---:|
|Gemini original|1,86MS/s|10s|17,79%|2/16|
|Gemini original|2,00MS/s|10s|7,11%|3/16|
|Gemini original|2,051282MS/s|10s|2,45%|3/16|
|Privado sin sched_yield|1,86MS/s|10s|18,02%|2/16|
|Privado sin sched_yield|2,00MS/s|10s|7,41%|2/16|
|Privado sin sched_yield|2,051282MS/s|10s|2,44%|2/16|
|Gemini original|2,00MS/s|60s|7,16%|6/16|
|Gemini original|2,051282MS/s|60s|2,57%|5/16|

Todos los casos sin pérdidas/fatales ni errores de protocolo. Los60s validaron
119.930.520 y123.001.704muestras respectivamente; slack mínimo64.359 y56.183ticks.
La captura comienza después del ACK: muestras/tiempo host no se usa para calibrar
el reloj. La comparación sin yield es breve, no una mejora causal demostrada.

La cola ampliada permite más backlog; las tasas nuevas no cumplen el objetivo
10% de margen. Los60s verifican integridad sostenida, no aceptación de holgura.
No3×120s ni promoción pública. Falta GUI visible,RADIO/A0,WAV,Synth y analógico.
Las calificaciones heredadas de V19 en perfiles antiguos son referencias.

El firmware SRAM3 de Gemini no se modificó. La variante de relay alteró sólo
una copia privada; se conservan hashes/BIN/containers detenidos de evidencia,
sin borrar apps de la biblioteca. El destino estable scope-v20 todavía no está
aceptado: la candidata con fecha sólo se usa por el harness.

Todas las restauraciones pasaron. Última10,024s/313.344muestras,0pérdidas/fatales;
fuentes,caché,firmware,relay,snapshot,CPU yconfiguración originales iguales.
V19 activa y libre; V20 detenida.

[Resumen conjunto](../diagnosticos/resultados_v20/sram3_summary_20261031.json).

Siguiente: revisar reserva/inicio de vida/atributos/ECC de Storage SRAM3, preparar
binding de la pareja V20 para el monitor y medir GUI/RADIO/A0 primero1,86MS/s.
El ACK/RF anterior sigue como prototipo offline pendiente, sin mezclar aquí.
