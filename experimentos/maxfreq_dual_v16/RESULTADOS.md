# Campaña dual cerrada · 12/10/2026

`sweep.json`: `ok=true`, `restored=true`, 478 ensayos registrados.
Nueve perfiles distintos superaron 60 + 3×120 + 600 segundos, con reinicios
independientes, host despierto, continuidad de índices/timestamps y cero
`dropped`/`fatal`. Todas las tasas siguientes son **por canal**, con dos valores
por disparo y TIM5 a 160 MHz. ADC16 conserva oversampling ×16.

| Bits | Mayor tasa aceptada (Hz/canal) | Ticks / nodo | Con margen en campaña aislada (Hz/canal) | Ticks / nodo |
| --- | ---: | --- | ---: | --- |
| 8 | 632411,067 | 253 / 3888 | 597014,925 | 268 / 3456 |
| 10 | 519480,519 | 308 / 4176 | 495356,037 | 323 / 4176 |
| 12 | 437158,470 | 366 / 4032 | 410256,410 | 390 / 4032 |
| 14 | 363636,364 | 440 / 3968 | 355555,556 | 450 / 1984 |
| 16 | 76226,775 | 2099 / 3456 | 76226,775 | 2099 / 3456 |

El criterio de margen exige ≥10% de tiempo medio disponible en envío,
cola máxima menor de cuatro y margen positivo antes de sobrescritura en cada
aceptación. Los cuatro máximos de 8/10/12/14 bits conservan integridad pero no
cumplen ese criterio en todas las repeticiones.

Estas son las mayores tasas aceptadas entre los candidatos ensayados, no una
demostración del máximo físico ni de todos los ticks intermedios en aceptación
larga. Por ejemplo, ADC14 descartó candidatos de 416–421 ticks y aceptó 440;
422–439 no tienen la secuencia completa de aceptación. Precisión analógica,
asentamiento y ENOB no se midieron.

## Interrupción y reanudación

El primer dueño del host desapareció durante la tercera repetición ADC14 a
420 ticks/N3968. La causa no quedó establecida y el ensayo incompleto no se
contó como aceptación ni fallo ADC. Se conservaron reporte y log completos en
`interruption_20261012T161655Z/`, y se restauró primero V16 integrado y sus campos
originales; véase `interruption_restore.log`.

`resume_finalists.py --resume`, bajo `caffeinate -i -s`, conservó sólo los seis
ganadores completos ADC8/10/12 que pasan el gate físico `accepted_profiles`.
Repitió desde cero las aceptaciones pendientes ADC14/16 y conservó exclusiones
por fallos largos controlados previos. Las fuentes originales de firmware,
contrato y barrido mantuvieron sus hashes; el runner registra su propio hash.
La ejecución reanudada terminó con código de salida cero; `resume_finalists.log`.

## Auditoría y restauración final

`acceptance_audit.json` contiene los nueve perfiles y sus 45 ensayos controlados
de aceptación, con hash del reporte completo. El gate físico pasó, se verificó
la igualdad de todos los hashes originales y cinco pruebas de aceptación,
contrato, empaquetado y tramas completas pasaron antes de reanudar.

El Q quedó con **V16 de producción integrado con CH1**, relay estable
`usb-stream-80706d1ec26cf81e535b/unoq_stream`, ADC8/333333 Hz, SPI y generador seno
de 50 kHz habilitado, con todos sus campos originales restaurados. La prueba
de integridad del perfil original volvió a cerrar el flujo (`restore_integrity_ok=false`),
igual que antes de la campaña: la restauración de campos no recertifica ese perfil.
El dueño y su `caffeinate` terminaron; no queda campaña host activa.

## Incorporación a producción completada

Los nueve perfiles dual están incorporados, junto con los cinco CH1 anteriores.
El selector muestra los nuevos como `(CH1+CH2)` y oculta tasas incompatibles con
resolución/salida/Synth. ADC16 incluye 76,23 kHz SPI. Los formatos anteriores,
UART, cuatro slots de cola, WAV de 16 bloques y validación temporal se conservan.

El primer diseño dejó 1364 bytes libres y falló READY dos veces; ambos intentos
restauraron firmware CH1 y conservan diagnóstico. `acquisition_storage.h` usa
arenas estáticas excluyentes para CH1 compacto y dual/legacy: ADC, timestamps y
cuatro slots completos para cada modo, sin heap. Los cambios de arena ocurren
con DMA/producer detenidos y sin nodos prestados. La compilación final ocupa
117908 bytes flash y 259132 bytes RAM, con 3012 libres; arrancó correctamente.

`production_integration.json`: `ok=true`, `restored=true`, 18 casos/transiciones,
120s para cada uno de los 14 perfiles nativos; ambos canales y timestamps
NumericBatch correctos, cero pérdidas/errores. También se midieron envío por
nodo, cola y margen de sobrescritura. Los casos completos anteriores al rechazo
del criterio de margen se preservaron con sus hashes; no se reutilizó el ensayo
interrumpido de `before_margin_*`. La reanudación conserva el origen en el reporte.

| Perfil dual candidato de margen | Margen medio integrado | Etiqueta de margen en producción |
| --- | ---: | --- |
| ADC8 / 597,01 kHz | 11,39% | Validado |
| ADC10 / 495,36 kHz | 9,03% | Retirada |
| ADC12 / 410,26 kHz | 9,39% | Retirada |
| ADC14 / 355,56 kHz | 10,09% | Validado |
| ADC16 / 76,23 kHz | 77,66% | Validado |

Los dos perfiles cuya etiqueta se retiró siguen aceptados por integridad; la
campaña aislada conserva sus resultados originales de margen. Los máximos
ADC8/10/12/14 no reciben etiqueta de margen por una prueba corta de integración.
Los tres perfiles CH1 de margen lo conservaron en producción.

279 pruebas V16, arenas/validadores con sanitizadores, constructor real en todos
los perfiles y colector de métricas pasaron. Tras reconciliar las etiquetas,
26 pruebas de perfiles/UI/constructor también pasaron.
Auditoría final: `production_acceptance.json`; carga: `production_deployment.json`.
Respaldo CH1 previo: `../../respaldos/unoq/osciloscopio_20261012_155653_138423.zip`.
Relay final: `usb-stream-046d2c12bc108dce30a0/unoq_stream`.

Firmware integrado instalado; parámetros originales ADC8/333333 SPI y seno50kHz
restaurados, incluyendo todos los campos del generador. Su prueba de integridad
volvió a fallar como antes (`restore_integrity_ok=false`). Dueños/caffeinate de
validación terminados. No Astra. Reiniciar el monitor para cargar la whitelist.
