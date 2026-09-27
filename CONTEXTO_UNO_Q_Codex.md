# CONTEXTO DEL PROYECTO — UNO Q → UNO R4 → PC

> Documento de transferencia a Codex / VS Code. Estado confirmado en la conversación hasta el 26/09/2026. **Leé también el código actual del repositorio**: algunas modificaciones confirmadas durante las pruebas son posteriores al sketch compartido y pueden no estar reflejadas en aquella copia.

## 1. Objetivo y problema actual

Adquirir en tiempo real dos canales analógicos en el microcontrolador STM32U585 del Arduino UNO Q, con disparo por hardware, transferencia GPDMA en doble búfer, marca temporal por muestra y salida binaria por UART directa. Un Arduino UNO R4 WiFi hace de puente UART → USB hacia una PC; Python recibe, grafica y puede guardar la captura en columnas.

**Estado:** el sistema funciona a 10 kHz, 14 bits, UART Q→R4 a 1 Mbaud y bloques seriales de 512 muestras. Se solucionó una congelación al subir de 256 a 512 muestras moviendo el búfer `Sample tx[512]` fuera de la pila del hilo serial. **Problema pendiente:** aparecen puntos basura/anomalías con un aparente patrón periódico. Hay que establecer si coinciden con bordes de bloque serial (512 muestras), de nodo DMA (2048 pares), o si el origen está en timestamps, sincronización de nodos, puente R4, recepción o parser Python. No dar por identificado el origen sin mediciones.

## 2. Hardware y conexiones

- **Arduino UNO Q:** microcontrolador STM32U585, Arduino Core Zephyr 0.90.0.
- A0 = PA4 = ADC1_IN9: `ADC_IN`.
- A1 = PA5 = ADC1_IN10: `ADC_OUT`.
- A2 = PA6: salida digital que alterna ON/OFF cada 200 ms; físicamente conectada a A1.
- UART directa del UNO Q: `Serial1` en USART1: **D1/PB6 = TX**, D0/PB7 = RX. No usar el `Serial` del Q, que atraviesa RouterBridge/Linux, para este enlace.
- UNO Q **D1/TX → UNO R4 RX** y **GND común**; R4 `Serial1` recibe la UART y `Serial` reenvía por USB a PC.
- Frecuencias de transporte confirmadas: Q→R4 a **1 000 000 baudios**; R4→PC `Serial.begin(2000000)`.

## 3. Parámetros validados y constantes

```cpp
#define WRITE_PIN            A2
#define ADC_IN_PIN           A0
#define ADC_OUT_PIN          A1
#define SAMPLE_RATE_HZ       10000U
#define SAMPLE_PERIOD_US     100U
#define TOGGLE_PERIOD_MS     200U
#define SERIAL_BAUD          1000000U
#define DMA_NODE_PAIRS       2048U
#define DMA_NODE_RESULTS     (DMA_NODE_PAIRS * 2U)
#define DMA_NODE_BYTES       (DMA_NODE_RESULTS * sizeof(uint16_t))
#define DMA_NODE_COUNT       2U
#define DMA_BUFFER_RESULTS   (DMA_NODE_RESULTS * DMA_NODE_COUNT)
#define SERIAL_BLOCK_PAIRS   512U
#define TIM2_PRESCALER       159U
#define TIM2_AUTORELOAD      99U
#define PRIORITY_TOGGLE      6
#define PRIORITY_SERIAL      7
```

TIM2 parte de un reloj de timer supuesto de 160 MHz: /160 → 1 MHz y ARR 99 → 10 kHz; TIM5 también usa prescaler 159 y cuenta nominalmente en microsegundos. El tamaño de nodo es **2048 pares A0/A1 = 204,8 ms a 10 kHz**, y se envía en **4 bloques seriales de 512 pares**. Hay dos nodos ping-pong. Los comentarios antiguos de código que mencionen 5 kHz/409,6 ms o «Serial 2 Mbps» pueden estar desactualizados: comprobar los `#define` y las llamadas reales.

## 4. Adquisición y estructura de datos

- ADC1: resolución **14 bits** (se cambió desde 12 bits y se comprobó que funcionó), `uint16_t` por conversión. Dos ranks: canal 9/A0 primero, canal 10/A1 segundo. Trigger externo TIM2 TRGO por flanco ascendente; una secuencia de dos conversiones por trigger. Modo ADC DMA unlimited; sampling time 391,5 ciclos por canal.
- GPDMA1 **canal 1**: ADC1 DR → `dmaBuffer[]` en ping-pong por nodos de 2048 pares; cada par tiene dos `uint16_t` intercalados (`A0`, `A1`).
- GPDMA1 **canal 0**: petición TIM2 update → lectura de `TIM5->CNT` → `timestampBuffer[]`; ping-pong con nodos de 2048 marcas de 32 bits. `LL_TIM_EnableDMAReq_UPDATE(TIM2)` es indispensable y fue agregado durante el desarrollo.
- Ambos canales usan listas enlazadas circulares, sin ISR DMA: el hilo serial consulta las banderas TC de ambos canales, invalida D-cache del nodo completado, lo empaqueta y transmite. `dmaErrorCount` contabiliza errores DTE, pero su valor no se transmite ni se presenta automáticamente.
- Importante: copiar `TIM5->CNT` por DMA **NO equivale a un hardware input capture** en el instante exacto de TIM2. Puede haber latencia y anomalías si la petición DMA se demora o se desincroniza. No interpretar una marca temporal adelantada como prueba definitiva de una causa particular.

```cpp
struct __attribute__((packed)) Sample {
    uint32_t timestamp; // TIM5, nominalmente microsegundos
    uint16_t adc_in;    // A0, 14 bits dentro de uint16_t
    uint16_t adc_out;   // A1, 14 bits dentro de uint16_t
}; // 8 bytes exactos
```

Búferes principales típicos:

```cpp
static uint16_t dmaBuffer[DMA_BUFFER_RESULTS]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
static uint32_t timestampBuffer[DMA_NODE_PAIRS * DMA_NODE_COUNT]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
static LL_DMA_LinkNodeTypeDef dmaNode[DMA_NODE_COUNT]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
static LL_DMA_LinkNodeTypeDef timestampNode[DMA_NODE_COUNT]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
```

El sketch compartido contiene implementaciones `weak` específicas de compatibilidad con Core Zephyr 0.90.0: funciones LL ADC/TIM/DMA y mantenimiento D-cache Cortex-M33. **No reemplazar indiscriminadamente por llamadas HAL/LL que no enlacen en este core.** La limpieza/invalidez de caché y la accesibilidad DMA de los descriptores merecen inspección al analizar los bordes de nodo.

## 5. Protocolo binario Q → R4 → PC

Cada paquete transmitido por `Serial1` del Q:

| Campo | Tamaño | Detalle |
|---|---:|---|
| Magic | 4 bytes | ASCII `DATA` |
| Estado | 1 byte | actualmente **el código compartido lo fija en `1`**, no refleja la alternancia real; revisar si se quiere telemetría ON/OFF |
| Cantidad | 2 bytes | `uint16_t` little-endian, normalmente 512 |
| Payload | `cantidad * 8` bytes | cada muestra: `uint32_t timestamp` + `uint16_t adc_in` + `uint16_t adc_out`, little-endian, packed |

Tamaño actual por paquete: **7 + 512×8 = 4103 bytes**. Cuatro paquetes por nodo de 2048 muestras. A 10 kHz: 80 000 bytes/s de carga útil más ~137 bytes/s de cabeceras; la UART a 1 Mbaud (8N1) tiene ~100 000 bytes/s nominales, por lo que existe margen, aunque hay que verificar los buffers reales de UART/USB y bloqueos de `write`.

**No asumir que cada lectura del puerto serial en R4 o Python corresponde a un paquete entero**: es un stream arbitrariamente fragmentado. Python debe acumular bytes, buscar `DATA`, leer cabecera completa, esperar exactamente `count*8` y resincronizar si hay corrupción. Validar límites de `count` antes de consumir paquetes para no desalinear el stream.

### Código probado del R4 como puente transparente

```cpp
#include <Arduino.h>
constexpr uint32_t BAUD = 1000000;
uint8_t buf[512];

void setup() {
    Serial.begin(2000000);
    Serial1.begin(BAUD);
}

void loop() {
    int n = Serial1.available();
    if (n > 0) {
        if (n > (int)sizeof(buf)) n = sizeof(buf);
        for (int i = 0; i < n; ++i) buf[i] = Serial1.read();
        Serial.write(buf, n);
    }
}
```

El R4 no debería interpretar ni alterar el protocolo. No obstante, podría perder bytes por desbordamiento del buffer RX o bloqueos del USB; no está descartado sin pruebas.

## 6. Corrección crítica ya realizada: bloque de 512 congelaba el sistema

En una versión enviada del Q, el hilo serial creaba:

```cpp
K_THREAD_STACK_DEFINE(serial_stack, 4096);
// ...
static void serial_thread(void *, void *, void *) {
    Sample tx[SERIAL_BLOCK_PAIRS]; // 512 * 8 = 4096 bytes
    // ...
}
```

Con 256 pares (~2048 bytes) funcionaba; con 512 pares `tx` solo ya ocupaba los 4096 bytes de stack, y se detenían la transmisión **y también la alternancia ON/OFF**. El usuario confirmó que se solucionó moviendo `tx` a memoria estática/global:

```cpp
static Sample tx[SERIAL_BLOCK_PAIRS];

static void serial_thread(void *, void *, void *) {
    uint32_t completedNode = 0;
    // ...
}
```

**Esto ya está corregido en la versión funcional, aunque el sketch de 922 líneas compartido antes de la corrección todavía mostraba `Sample tx[]` local.** No volver a introducir buffers grandes en stacks limitados de Zephyr.

## 7. Historial de pruebas relevantes

- **5 kHz**: funcionando.
- **10 kHz, 12 bits, 1 Mbaud**: funcionando.
- **10 kHz, 14 bits**: se cambió solo `LL_ADC_SetResolution(ADC1, LL_ADC_RESOLUTION_14B)` y funcionó; no hubo aumento de bytes/muestra.
- **Bloques 128 → 256 → 512**: 256 funcionó. 512 congelaba por desbordamiento de stack; con `tx` estático volvió a funcionar perfectamente.
- **20 kHz / 1 Mbaud**: pérdida de bloques previsible por exceso de caudal: ~160 kB/s solo de payload frente a ~100 kB/s máximos nominales de UART 1 Mbaud 8N1. Se volvió a 10 kHz.
- **1,2 Mbaud** probado en Q y R4: no funcionó. Una prueba anterior a **2 Mbaud en el enlace Q→R4** tampoco funcionó; **causa no determinada**. No presentarlo como capacidad confirmada. El R4→USB sí usa `Serial.begin(2000000)` en la configuración actual.
- Prueba sintética previa Q→R4→Python a 10 kHz con bloques de **1000** muestras validó el protocolo, sin bloques corruptos (`bad=0`); esa prueba no demuestra que el parser actual soporte 512, ni que el DMA real esté bien.

## 8. Anomalía de timestamp observada antes

En capturas anteriores aparecían muestras aisladas con timestamp **adelantado mucho más de los 100 µs esperados**, y luego la serie regresaba a su secuencia temporal normal. La anomalía afecta el timestamp común a ambos ADC. Ejemplo conceptual:

```text
... 400, 600, 500, 600, ...
```

No se afirmó que todas las anomalías actuales sean de ese tipo: registrar valores reales antes de vincular ambos fenómenos. Posibles pistas a evaluar sin asumirlas como hecho: demora de servicio del DMA de timestamp, sincronización de banderas TC de ambos canales, transición de nodos, coherencia de D-cache, corrupción/pérdida de bytes en la cadena serial o error de resincronización en Python. Una solución a largo plazo para timestamps precisos sería hardware capture por timer, no DMA leyendo directamente un contador libre.

## 9. Problema actual: patrón de puntos basura

El usuario observa puntos basura con aparente periodicidad en el gráfico, sin haber establecido todavía el intervalo ni si afectan ambos ADC, timestamp o los tres. Se sospecha de los bordes de bloques/buffers; el objetivo inmediato es **medir y localizar**, no aplicar cambios especulativos.

Captura exportable desde Python: texto tabulado, 6 columnas, por ejemplo:

```text
indice  timestamp_us  adc_in  volts_in  adc_out  volts_out
0       1923585855    327     0.07      65       0.01
1       1923585955    424     0.09       0       0
2       1923586055    427     0.09      34       0.01
```

El índice de la primera columna puede ser generado por el receptor al guardar: **un índice continuo en el archivo no prueba que Q no haya perdido muestras**. Para cuantificar pérdidas verdaderas, comparar secuencia temporal, un contador de muestra transmitido explícitamente, u otro indicador de continuidad. El contador TIM5 de 32 bits eventualmente hace wrap-around; tratarlo explícitamente si la captura es lo suficientemente larga.

Ya se generó un script aparte, `analizar_captura.py`, que lee las seis columnas e informa saltos de índice, distribución de diferencias entre timestamps (`dt`, esperado ~100 µs), timestamps atrasados/adelantados/duplicados, supuestos outliers ADC y posiciones respecto a múltiplos de 512 y 2048. **Es diagnóstico inicial, no prueba definitiva**: los umbrales robustos del ADC pueden marcar transiciones reales A2→A1 como outliers, y las posiciones modulares podrían estar desfasadas si el archivo comenzó a mitad de un bloque/nodo. Evaluar proporciones y concentración frente al comportamiento basal, no solo presencia cerca de una frontera.

## 10. Plan recomendado de diagnóstico en Codex

1. Leer el código **actual** Q, R4, Python y `analizar_captura.py` si está en el repositorio. Verificar qué cambios están realmente implementados, en especial el `tx` estático y el `count=512` del parser.
2. Analizar una captura larga y reportar **tabla de anomalías con contexto**: índice, timestamp anterior/actual/siguiente, `dt` anterior/siguiente, A0/A1, offsets `idx % 512` y `idx % 2048`, número de eventos y distribución por offset. Distinguir un timestamp aislado «futuro» de pérdida permanente de muestras.
3. Comprobar alineación: el inicio de un archivo exportado puede no coincidir con un bloque del Q. Preferir anotar la frontera desde el parser real (`DATA`, `count`) al guardar, y/o añadir temporalmente a Q un número de bloque/nodo/contador de muestra para diagnóstico **mediante una versión explícita del protocolo** (actualizar ambos extremos a la vez).
4. Antes de atribuir los errores al DMA, registrar bytes brutos en PC (captura `.bin`) y hacer un parser offline que cuantifique encabezados válidos, `count`, longitudes incompletas, bytes descartados al resincronizar y posiciones de corrupción. Si el stream bruto está sano y ADC/timestamp muestran errores regulares, enfocar el Q.
5. En Q, estudiar especialmente **la espera simultánea de banderas TC de dos canales**, la paridad del nodo `completedNode`, la limpieza de banderas, si se pierde alguna transición de nodo durante un `Serial1.write()` bloqueante, y coherencia de descriptores/buffers DMA ante D-cache. **No asumir que dos banderas TC verdaderas significan necesariamente el mismo número de nodo si alguna finalización se omitió.**
6. Evaluar el margen temporal: un nodo de 2048 pares tarda 204,8 ms en llenarse. Enviar un nodo ~16 412 bytes ×10 bits /1 Mbaud ≈164 ms nominales, más bloqueo y overhead. Si el hilo se retrasa por encima de un período de nodo, el DMA podría volver a escribir un búfer que se está leyendo. Medir duración real de procesamiento/escritura y contar overruns.
7. Si persiste duda Q vs R4, usar temporalmente un adaptador USB-UART compatible a 1 Mbaud conectado directamente a D1 TX/GND del Q para aislar el R4; o ejecutar una transmisión sintética determinista **sin ADC/DMA** y comprobar integridad de extremo a extremo. Evitar diagnósticos que agreguen bytes de debug al mismo flujo binario sin adaptar el parser.
8. Una vez localizado el mecanismo, proponer el **cambio mínimo verificable**, ejecutar prueba A/B y conservar la versión funcional para poder regresar.

## 11. Advertencias específicas del sketch compartido

- El byte `state` del encabezado está fijado a `uint8_t state = 1` en ese código. El hilo `toggle_thread` sí alterna A2 cada 200 ms. No usar el campo `state` como evidencia de alternancia real a menos que se haya cambiado después.
- `Serial1.write` se llama tres/cuatro veces por paquete (magic, state, count, payload). Fragmentación de escrituras o lecturas **no** constituye corrupción mientras el receptor ensamble correctamente el stream.
- La lógica del hilo de consumo es aproximadamente:

```cpp
while (!(LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_1) &&
         LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_0))) {
    // revisar flags DTE; k_sleep(K_USEC(50))
}
LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_1);
LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_0);
// src = dmaBuffer[completedNode], tsrc = timestampBuffer[completedNode]
// invalidar caché, convertir bloques de 512 y enviar
completedNode ^= 1U;
```

  La correspondencia entre TC, nodo realmente completado y buffers es **hipótesis central a verificar**, en particular si el UART bloquea.
- Los datos exportados de ejemplo muestran escalas de voltaje redondeadas, p. ej. `327 → 0.07 V`, aparentemente hay conversión fuera del sketch; inspeccionar el código Python antes de inferir que un ADC «bajo» es corrupción.

## 12. Encargo inicial para Codex

> Leé este contexto y los archivos actuales del proyecto UNO Q, R4 y Python. No modifiques el código todavía. Primero identificá posibles mecanismos de puntos basura y diseñá instrumentación para ubicar exactamente las anomalías respecto de los paquetes seriales de 512 muestras y los nodos GPDMA de 2048 pares. Separá claramente hechos comprobados, hipótesis y pruebas sugeridas. Prestá especial atención a desbordamientos de UART, sincronización de ambos canales DMA, recuperación del stream binario y duración real de cada envío. Después proponé el cambio mínimo y una prueba de validación.
