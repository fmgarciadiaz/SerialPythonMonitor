# ADC8 CH1: SPI DMA BYTE frente a WORD — 15/10/2026

Autorización: usuario pide aumentar tasa ADC8, confirma Q libre y solicita
revisión de internet con Astra. Un único coordinador opera hardware.

Se clona el motor aislado de maxfreq_optimized_v17. No se modifican fuentes,
perfiles ni selectores productivos. Cada variante usa CRCSIZE=7 según ES0499,
CRCEN=0, DSIZE=8 bits, tramas SCP1 de 992 bytes y CRC32 íntegro.

- BYTE: DMA de 1 byte y FIFO threshold 1 frame.
- WORD: DMA origen/destino de 4 bytes, burst1 y threshold 4 frames;
  TSIZE sigue siendo 992 frames de 8 bits, BNDT sigue siendo 992 bytes.
- Se conservan puertos, reloj SPI solicitado38MHz, READY, pipeline por
  referencias, ACK final, timestamps por muestra y validadores.

Antes de tocar la placa: dueño exclusivo, snapshot ADC/generador/WAV,
identidad de firmware, relay montado, permisos/entorno del contenedor y backup.
Comparación física de 10 s por punto: ticks114/113/112, nodo3456, ADC8 CH1.
Primer fallo se repite desde arranque independiente. Un fallo corta el
ascenso de esa variante. Se detiene adquisición/relay antes de recompilar.

Si WORD pasa por encima del máximo actual, el finalista más rápido intenta
60 s + tres arranques independientes de 120 s. Sin 600 s. Si falla se prueba
el siguiente finalista ya sondeado. Integridad y holgura se reportan aparte:
holgura requiere margen medio>=10%, cola pico<4 y slack positivo.

Finally restaura app V17, relay, ADC/generador exactos e identidad, y valida
10 s de continuidad. No acepta precisión analógica, GUI/RADIO concurrente ni
incorpora nuevos perfiles a producción.


## Continuación: WORD corregido (15/10/2026)

El header DMA instalado en el Q documenta source/dest_burst_length en bytes.
WORD usaba width4/burst1 y el driver Zephyr rechaza esa combinación. Corregir
el burst a4bytes mantiene un único beat; BYTE sigue usando1byte.
Se guarda la evidencia original sin modificarla. Fuentes sólo experimentales.
Nuevo runner probe_word_fixed.py: sondeo10s ticks114/112/110/108/106/104,
N3456, corte al primer fallo y repetición independiente. Si el relay no
inicia, conservar log y repetir arranque una vez; no deducir límite ADC.
Hasta tres finalistas con60+3×120s: mayor tasa sondeada íntegra primero;
si no cumple holgura, candidato más lento con reserva medida. No es barrido
exhaustivo de máximo con margen. Snapshot/backup fresco y restauración exacta.
