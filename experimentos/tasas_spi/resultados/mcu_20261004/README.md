# Medición MCU válida · 4 de octubre de 2026

Dos repeticiones de 125 kHz / 14 bits, SPI 32 MHz y receptor sin interfaz:

- [Generador activo](generador_activo_125.json): cuadrada de 2,5 Hz, A0 DAC.
- [Generador apagado](generador_apagado_125.json).
- [Recepción activa](ensayo_on.json) y [apagada](ensayo_off.json).
- Los logs homónimos guardan la trama original de 512 bytes, CRC incluido.
- [Fuentes verificadas](fuentes_verificadas.json): las herramientas, V9 Fast y
  el relay diagnóstico permanecieron iguales durante la repetición controlada.

| Métrica MCU | Generador activo | Apagado |
|---|---:|---:|
| Preparación trama | 55,34 µs | 55,46 µs |
| Armado DMA/SPI | 19,98 µs | 19,76 µs |
| READY → interrupción final | 245,42 µs | 240,59 µs |
| Interrupción → retorno/limpieza | 15,23 µs | 12,73 µs |
| Verificación recibida | 73,50 µs | 75,14 µs |
| Fragmento completo y handoff | 470,24 µs | 465,58 µs |
| Envío completo de nodo | 18,365 ms | 18,171 ms |
| Intervalo sondeo productor | 1123,79 µs | 1124,09 µs |
| Validación/copia ADC por nodo | 433,90 µs | 432,24 µs |
| Máximo de cola | 4/4 | 4/4 |
| dropped / fatal | 1 / 0 | 1 / 0 |

El presupuesto por nodo a 125 kHz es 16,384 ms. La duración de envío lo supera
12,09 % con generador y 10,91 % sin él. Los fragmentos y nodos en curso al
congelar la captura no contribuyen como observaciones completas a esas dos
métricas; se conservan los conteos explícitos en las instantáneas.

La copia ADC no es el costo dominante en estas repeticiones. El déficit sigue
al deshabilitar esta cuadrada; no se extrapola este resultado a otras formas o
frecuencias del generador. READY → IRQ incluye espera al maestro, transferencia
física e interrupciones. IRQ → retorno incluye planificación y limpieza.
Las métricas inclusivas de fragmento/nodo se superponen con el resto: no sumar
las filas como si fueran costos independientes.

La suma de las cinco etapas SPI medidas promedia ~409 µs con generador y
~404 µs sin él. El handoff promedia ~470/466 µs, por lo que aún quedan ~61 µs
por fragmento fuera de esas cinco ventanas (coordinación y trabajo entre ellas).
No es una medición exclusiva de tiempo de CPU. Cada registro agrega costo.

## Interrupciones anteriores

El primer contenedor compartía nombre con las herramientas comunes y fue
parado/eliminado tras iniciarse; Docker no permitió atribuir quién lo solicitó.
Otro intento obtuvo 512 bytes FF a 100 kHz y se descartó por CRC inválido.
No hay prueba suficiente para atribuir ese FF a otra sesión ni al déficit de
caudal. No se encontró otro proceso de ensayo activo ni un timer pertinente.

Se repitió con el nombre exclusivo `serialmonitor-mcu-diagnostic`: las dos
instantáneas anteriores se recuperaron correctamente y las fuentes comprobadas
no cambiaron. Esto permite usar las mediciones; no demuestra la causa de la
parada inicial. No se borró ni modificó V10 diagnóstico, encontrado en el workspace.

## Siguiente prueba propuesta

Comparar en otra variante aislada la validación/preparación de PING y CRC, y
la coordinación por fragmento. Después medir transacciones de mayor tamaño:
512 bytes a 32 MHz requieren idealmente 128 µs de reloj, pero el ciclo completo
observado es ~466–470 µs. Eliminar tráfico USB al PC o apagar esta cuadrada no
alcanza. No ampliar sólo la cola como solución de un déficit sostenido.

## Restauración

Se retiró el contenedor exclusivo y se detuvo Scope SPI Timing Diagnostic.
Se reinició el relay normal con V9 Fast. El perfil restaurado y la recepción
posterior se registran en [restauracion.json](restauracion.json). La comprobación
breve confirma funcionamiento tras restaurar; no descarta pérdidas esporádicas
como la que se encontró previamente a 100 kHz.
