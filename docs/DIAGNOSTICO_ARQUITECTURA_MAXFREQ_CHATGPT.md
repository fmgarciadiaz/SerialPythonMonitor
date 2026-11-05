# Informe Técnico de Arquitectura y Límites de Frecuencia para ChatGPT / Codex

**Proyecto:** Arduscopio Q (Arduino UNO Q: STM32U585 MCU + Linux MPU)  
**Fecha:** 31 de Octubre de 2026  
**Autor:** Antigravity (Gemini)  
**Destinatario:** Equipo de Modelos (ChatGPT / Codex / Astra) y Usuario (`fmgarciadiaz`)  
**Estado de Versiones:** **Scope V19 permanece 100% congelada e intacta.** La nueva campaña y pruebas se trasladan a la pareja independiente **V20 (v20Gemini)**.

---

## 1. Resumen Ejecutivo y Diagnóstico

Tras la revisión exhaustiva de la base de código (`arduino/v19/`, `monitor/v19/`), los protocolos de transporte (`SCP1 V4`, `batch2`, `high_rate_profile`), el datasheet del STM32U585 (RM0456, DS13086), y los más de 300 registros de fallo documentados en `experimentos/maxfreq_v16/` (`failure_0000.log` a `failure_0326.log`), se determinó con precisión la causa por la cual las campañas de optimización de ChatGPT / Codex no lograron incrementar la tasa máxima de sampleo.

Las campañas previas estuvieron concentradas en **micro-optimizaciones a nivel de software** (reemplazo de bucles por `memcpy` que causó regresión, reordenamiento de validación PCM respecto a `irq_lock`, pacing de colas en el receptor Python con `Queue.get` y backoffs de 500 µs, y cadencia de paquetes WAV en A0). 

Ninguna de estas modificaciones pudo mover el techo de frecuencia porque **el sistema está operando al límite físico de dos barreras estructurales independientes**:
1. En **16 bits**, el convertidor analógico-digital (ADC1) está en el **99.4% de su límite físico de conversión por silicio**.
2. En **8 a 14 bits**, el cuello de botella es la **asincronía y el jitter del espacio de usuario de Linux (MPU)** combinados con la **falta de memoria RAM en el MCU para amortiguar transferencias SPI síncronas**.

---

## 2. Análisis del Cuello de Botella en 16 Bits: Límite de Silicio

* **Arquitectura del ADC:** El STM32U585 posee un convertidor SAR de 14 bits nativos. Para entregar 16 bits de resolución efectiva, el hardware del MCU utiliza **oversampling por hardware de 16x** con desplazamiento a la derecha de 2 bits (`LL_ADC_ConfigOverSamplingRatioShift(ADC1, 16U, LL_ADC_OVS_SHIFT_RIGHT_2)`).
* **Tiempo de conversión real:** Para generar **1 muestra de 16 bits**, el ADC debe ejecutar **16 ciclos completos de conversión SAR**. En modo dual (2 canales), son **32 conversiones SAR por pareja de muestras**.
* **Frecuencia del ADC:** El reloj del ADC fue optimizado a **54 MHz** mediante PLL2 (alimentado por HSE de 16 MHz). El datasheet de ST fija el límite absoluto de reloj del ADC en 55 MHz.
* **Cálculo de tiempos:**
  $$\text{Ciclos por conversión SAR} = 5\text{ (muestreo)} + 14\text{ (resolución)} + 3 = 22\text{ ciclos ADC}$$
  $$\text{Tiempo por pareja (32 conversiones)} = \frac{32 \times 22}{54\text{ MHz}} = 13.037\ \mu\text{s}$$
  $$\text{Tasa Teórica Absoluta Máxima (2 canales)} = \frac{1}{13.037\ \mu\text{s}} \approx \mathbf{76.705\text{ kSPS}}$$
* **Realidad del sistema actual:** V19 opera actualmente a **76.226 Hz** (ticks=2099) en modo dual y **150.943 Hz** (ticks=1060) en 1 canal.
* **Conclusión para ChatGPT:** **En 16 bits no hay margen de optimización en código.** La tasa actual está en el 99.4% del límite de la física del chip. La única manera de obtener más muestras por segundo en 16 bits es reducir el oversampling por hardware a $8\times$ o $4\times$ y realizar el filtrado / promediado digital en el Host (Python) o en el Relay (C).

---

## 3. Análisis del Cuello de Botella en 8 a 14 Bits: Jitter de Linux y Memoria MCU

Para tasas altas en 8, 10, 12 y 14 bits (donde el sistema ya alcanza entre **1.0 MSPS** y **1.86 MSPS** en 1 canal), el ADC no es el factor limitante. El cuello se produce en la interfaz MCU $\leftrightarrow$ Linux:

1. **La ventana de vaciado es ultracorta:**
   * A 1.86 MSPS (8 bits, 86 ticks TIM2), un nodo de adquisición de 3.488 muestras se llena completamente en **1.87 milisegundos**.
   * En ese lapso de 1.87 ms, el MCU debe validar y empaquetar, notificar por GPIO `READY`, el Linux MPU debe atender el evento en espacio de usuario, invocar `ioctl(fd, SPI_IOC_MESSAGE, ...)`, transferir 1.984 bytes por SPI (lo que toma ~450 µs de puro tiempo de bus a 32–40 MHz), y liberar el slot.
2. **Jitter inevitable en Linux no-RTOS:**
   * La CPU Linux del Uno Q corre un kernel estándar con scheduler CFS. Las operaciones de red TCP, interrupciones y cambios de contexto en userspace generan demoras esporádicas de entre 0.5 ms y 2 ms.
3. **El estrangulamiento de SRAM en el MCU:**
   * El sketch del MCU compila ocupando **~258 KiB de los ~262 KiB** asignados a la SRAM principal (SRAM1+SRAM2), dejando apenas **3.660 bytes libres**.
   * Debido a esto, la cola de nodos de DMA en el firmware está forzada a solo 4 u 8 slots (`QUEUE_SLOTS`).
   * Un amortiguador de 4 slots a 1.86 MSPS representa un margen de retención de apenas **~7.5 ms**. Si Linux sufre un hipo de apenas un par de milisegundos, la cola alcanza su pico máximo (`queue_peak >= 4`), el DMA circular sobreescribe la memoria (`slack <= 0`), y el firmware dispara la bandera fatal `acquisition::fail()`.
   * Esta es la causa directa de los más de 300 fallos registrados en las pruebas de barrido (`failure_0xxx.log`).

---

## 4. Plan de Acción Técnico y Arquitectónico para V20 (v20Gemini)

Para no poner en riesgo la estabilidad del sistema ni degradar la versión actual:
* **V19 queda totalmente congelada y operativa en el UNO Q.**
* Toda la investigación y pruebas se realizarán en una pareja de desarrollo independiente: **Scope V20 / v20Gemini** (`arduino/v20/` y `monitor/v20/`).

### Estrategia de Solución para V20:
1. **Desbloqueo de Memoria (SRAM3):**
   * El STM32U585 posee en hardware **786 KiB de SRAM total** (SRAM1: 192KB, SRAM2: 64KB, SRAM3: 512KB).
   * Por defecto, el linker script de Zephyr asigna únicamente SRAM1/SRAM2.
   * Ubicar los buffers circulares de adquisición en la región de **SRAM3 (512 KiB)** permitirá elevar `QUEUE_SLOTS` de 4/8 a **32 o 64 slots**.
   * Esto otorgará al sistema un colchón de **más de 60 milisegundos de absorción de jitter**, eliminando los fallos por pico de cola sin tocar los algoritmos de validación.
2. **Empaquetado y Transferencias SPI Agrupadas:**
   * Aumentar el tamaño de bloque físico SPI o transferir ráfagas continuas para reducir a la mitad las llamadas `ioctl` por segundo en Linux, bajando la utilización de CPU del relay.
3. **Oversampling Híbrido para 16 bits:**
   * Evaluar modo de 14 bits con oversampling $4\times$ por hardware en el ADC + filtro digital CIC/FIR en el Host para tasas superiores a 150 kSPS en modo dual.

---

Este reporte queda incorporado en la documentación técnica del repositorio para coordinar las próximas fases de desarrollo con los asistentes de IA y el usuario.

