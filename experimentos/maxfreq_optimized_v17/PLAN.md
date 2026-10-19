# Máximo CH1 ADC10/12/14 con envío optimizado — 2026-10-14

Usuario autoriza búsqueda física aplicando la optimización ADC8 y limita
cada ensayo a 120 s. Aceptación: 60 s + tres repeticiones independientes
de 120 s. Se elimina la etapa de 600 s por instrucción expresa.

Fuentes aisladas derivadas del ensayo8 en `send1400_v16`: SPI solicitado
38 MHz, FIFO10, espera READY acotada 50 µs, tres buffers por referencia,
último ACK físico antes de liberar nodo, sin compresión adicional.
Se conserva validación de CRC, secuencia, epoch, índices, timestamps,
DMA, dropped y fatal. Se agrega empaquetado ADC12 real, capacidad576.
No se modifican firmware V16/V17 ni selectores de producción.

| Bits | Tamaños de nodo probados |
|---|---|
| 10 | 2784, 5568, 8192 |
| 12 | 2304, 4608, 8192 |
| 14 | 1984, 3968, 7936 |

Sólo CH1, reloj160MHz; ticks78–640. Pantallas10s más1s asentamiento,
búsqueda binaria de ticks enteros con hipótesis monotónica; cada fallo
se repite desde arranque independiente. Se registra frontera por nodo.
Finalistas se reinician independientemente antes de cada etapa; si fallan,
se retrocede a ticks más lentos. El máximo reportado queda limitado a
esta matriz de nodos y esta duración, no demuestra ausencia de otras
geometrías mejores ni aceptación analógica.

Integridad y holgura se buscan por separado: holgura exige envío medio
con margen>=10%, cola pico<4 (incluido arranque) y slack mínimo>0.
Los fallos de arranque y discontinuidad del reloj host se conservan y
no se atribuyen a límites ADC. Un único coordinador opera el Q.

El runner toma snapshot V17 vivo, identifica relay montado, capacidades
y variables SCOPE, obtiene respaldo antes de cambiar app, detiene
adquisición durante construcción y conserva fuentes/hashes por campaña.
Finalmente restaura app V17, relay anterior, ADC/generador exactos,
identidad de firmware y10s de continuidad. Resultados por caso persistidos
en `probe_1400_*/report.json`, con logs de fallos y relay final.

Prueba local `test_contract.py`: código C++ real para pack8/10/12/14,
colas y extremos, wraps32bit y validadores Python/C con padding corrupto.
