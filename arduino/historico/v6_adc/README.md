# V6 ADC → SPI → Linux

Subpaso del **paso uno** del [Plan de trabajo](../../../Plan%20de%20trabajo.md):
llevar la adquisición al MPU del Q conservando dos canales, 14 bits,
31.250 pares/s, timestamps hardware y A2 conmutando cada 200 ms.
Esta carpeta conserva la prueba aislada ADC → Linux. La ruta completa hacia
el PC se utiliza desde el [monitor V8](../../../monitor/historico/v8/README.md) con un relay
Linux independiente, sin cambiar este firmware.

Prueba física de 120 s: **3.745.898 pares**, 71.333 bloques válidos,
cero pérdidas o errores. También se verificó la detección de cola llena
al detener y reanudar el receptor.

La aplicación independiente `Scope ADC SPI V6` reutiliza el ADC/TIM2/TIM5
por registros de V5 y SPI DMA con callbacks + READY de V6 IRQ.
GPDMA1 0/1 adquiere timestamps/ADC; 2/3 transmite/recibe SPI.
No se deshabilitan globalmente las IRQ durante una transferencia.

## Buffers y errores

Dos nodos DMA de 2.048 pares alternan cada 65,536 ms. Un productor copia
cada nodo terminado a una cola de cuatro nodos (64 KiB de muestras), con
semáforos de espacios libres y ocupados. El consumidor conserva la propiedad
de su nodo hasta transmitir todos sus fragmentos. SPI nunca lee RAM que el
ADC esté escribiendo. No hay un segundo buffer SPI precargado: por ahora el
solapamiento es entre adquisición y transporte, usando la cola.

Cuando se llena la cola se descarta el nodo nuevo completo, se incrementa
`dropped_nodes` y el índice de muestras conserva el salto. No se sobrescribe
un nodo que Linux todavía está consumiendo. Los cuatro nodos incluyen el
que tiene prestado el consumidor; el margen disponible depende de la ocupación.

El productor comprueba propiedad DMA antes/después de copiar, período de
32 µs, rango ADC, banderas de error y tiempo entre observaciones. Ante una
lectura ambigua o error hardware detiene TIM2 y comunica un error fatal;
no intenta reconstruir muestras. El productor sigue sondeando cada 1 ms;
las IRQ de finalización por bloque corresponden al transporte SPI.

La adquisición empieza cuando Linux toma READY. Si el receptor se cierra,
el ADC continúa y eventualmente la cola se llena: **reiniciar esta variante
antes de cada medición limpia**. El verificador rechaza contadores de
adquisición no nulos, incluso anteriores al comienzo de la medición.

## Contrato experimental

SCP1/v2 conserva bloques de 512 bytes y PING tipo 2. Los datos ADC usan
**tipo 3** para distinguirlos de los datos sintéticos tipo 1. CRC-32 cubre
los primeros 508 bytes; todos los enteros son little-endian.

| Offset absoluto | Contenido |
|---|---|
| 0–15 | Cabecera SCP1: versión, tipo, secuencia, payload de 492 bytes |
| 16–47 | Estado y ACK idénticos a V6 IRQ |
| 48 | Frecuencia de muestreo, uint32 |
| 52 | Índice del primer par, uint32 (wrap natural) |
| 56 | Nodos descartados por cola llena, uint32 |
| 60 | Errores fatales de adquisición, uint32 |
| 64 | Cantidad de pares, uint16, máximo 53 |
| 66–67 | Resolución 14 y cantidad de canales 2, uint8 cada uno |
| 68 | Período 32 µs, uint32 |
| 72 | Índice de nodo adquirido, uint32 |
| 76 | Flags: bit 0 indica adquisición detenida |
| 80–503 | Hasta 53 registros `uint32 timestamp, uint16 A0, uint16 A1` |
| Resto hasta 507 | Ceros |
| 508–511 | CRC-32 |

Cada nodo produce 38 fragmentos de 53 pares y uno de 34. En error fatal
pueden emitirse bloques de cero pares. Los registros mantienen los mismos
8 bytes de V5; la futura salida al PC podrá agruparlos en paquetes DATA.
Los metadatos describen la configuración fija, no habilitan aún controles.

## Prueba aislada

```sh
python3 tools/unoq.py compile --version v6_adc
python3 tools/unoq.py create --version v6_adc  # primera instalación
python3 tools/unoq.py stop --version v6_irq   # si ésta es la activa
python3 tools/unoq.py start --version v6_adc
python3 tools/spi_benchmark.py --firmware v6_adc --build-native
python3 tools/spi_benchmark.py --firmware v6_adc --implementation c --hz 20000000 --seconds 120
```

READY conserva el [procedimiento de arranque de V6 IRQ](../v6_irq/README.md).
El verificador agrega `--adc`: comprueba CRC, secuencias, ACK, índices,
período y rango, sin exigir el patrón sintético. El umbral de caudal de esta
prueba es 240.000 bytes/s de muestras (objetivo nominal 250.000); no es una
nueva medición del techo del enlace de 750.000 bytes/s sintéticos.

[Resultados de esta etapa](../../../diagnosticos/ADC_SPI_V6.md).
