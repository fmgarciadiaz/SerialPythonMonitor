#include <Arduino.h>
#include <Arduino_RouterBridge.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>
#include <string.h>
#include "scope_config.h"
#include "scope_protocol.h"

extern "C" {
#include "stm32u5xx.h"
#include "stm32u5xx_ll_adc.h"
#include "stm32u5xx_ll_dma.h"
#include "stm32u5xx_ll_dcache.h"
#include "stm32u5xx_ll_tim.h"
#include "stm32u5xx_ll_gpio.h"
#include "stm32u5xx_ll_pwr.h"
}

// ============================================================
// Arduino UNO Q / STM32U585
//
// A0 = PA4 = ADC1_IN9
// A1 = PA5 = ADC1_IN10
// A2 = PA6 = digital output; externally connected A2 -> A1
//
// Acquisition path (entirely hardware timed):
//
//   TIM2 TRGO 31.25 kHz (32 us, experimental)
//          |
//          v
//       ADC1 sequence
//       rank 1 = A0
//       rank 2 = A1
//          |
//          v
//        GPDMA1
//     ping-pong linked list
//          |
//          v
//          RAM
//          |
//       UART 3 Mbps (polling TX)
//
// The CPU never calls analogRead() while acquiring.
// ============================================================

// Configuración y contrato binario: scope_config.h / scope_protocol.h.
// Versión limpia para Arduino Core Zephyr 1.0.0 (no es Zephyr RTOS 1.0).

// ------------------------------------------------------------
// DMA RAM
// ------------------------------------------------------------

static uint16_t dmaBuffer[DMA_BUFFER_RESULTS]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));

// Hardware timestamps captured on every TIM2 update.
// TIM5 is a free-running 1 MHz counter, so one tick = 1 us.
static uint32_t timestampBuffer[DMA_NODE_PAIRS * DMA_NODE_COUNT]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));

static LL_DMA_LinkNodeTypeDef dmaNode[DMA_NODE_COUNT]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));

static LL_DMA_LinkNodeTypeDef timestampNode[DMA_NODE_COUNT]
    __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));

static struct k_thread toggle_thread_data;
static struct k_thread serial_thread_data;

K_THREAD_STACK_DEFINE(toggle_stack, 1024);
K_THREAD_STACK_DEFINE(serial_stack, 4096);

static volatile uint32_t dmaErrorCount = 0;

// Core 1.0.0 no exporta cache_data_* en syms-dynamic.ld (App Lab).
// Usar el controlador DCACHE1 del STM32U585 mediante LL inline. La sección
// crítica impide que otro hilo/ISR reprograme el controlador en este MCU mononúcleo.
// Todos los buffers y nodos tienen dirección/tamaño alineados a la línea del core.
static void cache_maintain(void *addr, size_t len, uint32_t command)
{
    if (len == 0U) {
        return;
    }
    const unsigned int key = irq_lock();
    __DSB();
    if (LL_DCACHE_IsEnabled(DCACHE1)) {
        while (LL_DCACHE_IsActiveFlag_BUSY(DCACHE1) ||
               LL_DCACHE_IsActiveFlag_BUSYCMD(DCACHE1)) {
        }
        const uint32_t start = reinterpret_cast<uint32_t>(addr);
        LL_DCACHE_SetStartAddress(DCACHE1, start);
        LL_DCACHE_SetEndAddress(DCACHE1, start + len - 1U);
        LL_DCACHE_SetCommand(DCACHE1, command);
        LL_DCACHE_StartCommand(DCACHE1);
        while (LL_DCACHE_IsActiveFlag_BUSYCMD(DCACHE1)) {
        }
        LL_DCACHE_ClearFlag_CMDEND(DCACHE1);
    }
    __DSB();
    __ISB();
    irq_unlock(key);
}

static inline void cache_flush_invalidate(void *addr, size_t len)
{
    cache_maintain(addr, len, LL_DCACHE_COMMAND_CLEAN_INVALIDATE_BY_ADDR);
}

static inline void cache_invalidate(void *addr, size_t len)
{
    cache_maintain(addr, len, LL_DCACHE_COMMAND_INVALIDATE_BY_ADDR);
}

// ------------------------------------------------------------
// ADC1
// ------------------------------------------------------------

static void adc_init(void)
{
    // These are the actual STM32U585 RCC gates. The LL clock aliases
    // used by the STM32 bare-metal examples are not exposed by the
    // Arduino UNO Q Zephyr build, so use the CMSIS register definitions.
    RCC->AHB2ENR1 |= RCC_AHB2ENR1_GPIOAEN;
    RCC->AHB2ENR1 |= RCC_AHB2ENR1_ADC12EN;
    (void)RCC->AHB2ENR1;

    LL_PWR_EnableVDDA();

    // A0 = PA4 = ADC1_IN9
    LL_GPIO_SetPinMode(GPIOA, LL_GPIO_PIN_4, LL_GPIO_MODE_ANALOG);
    LL_GPIO_SetPinPull(GPIOA, LL_GPIO_PIN_4, LL_GPIO_PULL_NO);

    // A1 = PA5 = ADC1_IN10
    LL_GPIO_SetPinMode(GPIOA, LL_GPIO_PIN_5, LL_GPIO_MODE_ANALOG);
    LL_GPIO_SetPinPull(GPIOA, LL_GPIO_PIN_5, LL_GPIO_PULL_NO);

    // ADC clock = existing ADC kernel clock divided by 4.
    LL_ADC_SetCommonClock(__LL_ADC_COMMON_INSTANCE(ADC1), LL_ADC_CLOCK_ASYNC_DIV4);
    LL_ADC_SetResolution(ADC1, LL_ADC_RESOLUTION_14B);
    LL_ADC_SetLowPowerMode(ADC1, LL_ADC_LP_MODE_NONE);
    MODIFY_REG(ADC1->CFGR2, ADC_CFGR2_LSHIFT, LL_ADC_LEFT_BIT_SHIFT_NONE);

    LL_ADC_SetGainCompensation(ADC1, 0);
    LL_ADC_SetTriggerFrequencyMode(ADC1, LL_ADC_TRIGGER_FREQ_HIGH);

    // One TIM2 trigger starts exactly one two-channel conversion sequence.
    LL_ADC_REG_SetTriggerSource(ADC1, LL_ADC_REG_TRIG_EXT_TIM2_TRGO);
    LL_ADC_REG_SetSequencerLength(ADC1, LL_ADC_REG_SEQ_SCAN_ENABLE_2RANKS);
    LL_ADC_REG_SetSequencerDiscont(ADC1, LL_ADC_REG_SEQ_DISCONT_DISABLE);
    LL_ADC_REG_SetContinuousMode(ADC1, LL_ADC_REG_CONV_SINGLE);
    LL_ADC_REG_SetOverrun(ADC1, LL_ADC_REG_OVR_DATA_OVERWRITTEN);
    LL_ADC_REG_SetDataTransferMode(ADC1, LL_ADC_REG_DMA_TRANSFER_UNLIMITED);

    LL_ADC_REG_SetTriggerEdge(ADC1, LL_ADC_REG_TRIG_EXT_RISING);
    LL_ADC_SetOverSamplingScope(ADC1, LL_ADC_OVS_DISABLE);

    LL_ADC_SetChannelSingleDiff(ADC1, LL_ADC_CHANNEL_9, LL_ADC_SINGLE_ENDED);
    LL_ADC_SetChannelSingleDiff(ADC1, LL_ADC_CHANNEL_10, LL_ADC_SINGLE_ENDED);

    LL_ADC_REG_SetSequencerRanks(
        ADC1, LL_ADC_REG_RANK_1, LL_ADC_CHANNEL_9);
    LL_ADC_REG_SetSequencerRanks(
        ADC1, LL_ADC_REG_RANK_2, LL_ADC_CHANNEL_10);

    // Conservar el tiempo de adquisición de V4/V5 a 25 kHz.
    // Core 1.0.0: ADC kernel HCLK=160 MHz /4 =40 MHz.
    // Validar amplitud y continuidad físicamente al subir a 31.25 kHz.
    LL_ADC_SetChannelSamplingTime(
        ADC1, LL_ADC_CHANNEL_9, LL_ADC_SAMPLINGTIME_391CYCLES_5);
    LL_ADC_SetChannelSamplingTime(
        ADC1, LL_ADC_CHANNEL_10, LL_ADC_SAMPLINGTIME_391CYCLES_5);

    LL_ADC_SetChannelPreselection(ADC1, LL_ADC_CHANNEL_9);
    LL_ADC_SetChannelPreselection(ADC1, LL_ADC_CHANNEL_10);

    // STM32U5 ADC activation procedure.
    LL_ADC_DisableDeepPowerDown(ADC1);
    LL_ADC_EnableInternalRegulator(ADC1);
    k_busy_wait(100);

    LL_ADC_StartCalibration(ADC1, LL_ADC_SINGLE_ENDED);
    while (LL_ADC_IsCalibrationOnGoing(ADC1))
    {
    }

    k_busy_wait(100);

    LL_ADC_Enable(ADC1);
    while (!LL_ADC_IsActiveFlag_ADRDY(ADC1))
    {
    }
    LL_ADC_ClearFlag_ADRDY(ADC1);
}

// ------------------------------------------------------------
// GPDMA1
//
// Two linked-list nodes form a ping-pong buffer:
//
//   node 0 -> node 1 -> node 0 -> ...
//
// Every node completes after DMA_NODE_PAIRS ADC trigger frames.
// The TC event is generated for EACH linked-list item.
//
// No DMA interrupt is used. The serial thread polls the TC flag.
// This avoids IRQ_CONNECT entirely inside the Arduino sketch.
// ------------------------------------------------------------

static void timestamp_timer_init(void)
{
    // TIM5 conserva 1 MHz, independiente de TIM2: protocolo en microsegundos.
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM5EN;
    (void)RCC->APB1ENR1;

    TIM5->CR1 = 0;
    TIM5->PSC = TIM5_PRESCALER;
    TIM5->ARR = 0xFFFFFFFFU;
    TIM5->CNT = 0;
    TIM5->EGR = TIM_EGR_UG;
    TIM5->SR = 0;
    TIM5->CR1 = TIM_CR1_CEN;
}

// Nodos lineales STM32U5: CTR1, CTR2, CBR1, CSAR, CDAR, CLLR.
// El core no exporta las funciones LL no-inline de construcción de listas.
// Construimos sólo el formato fijo requerido, sin reemplazar símbolos de ST.
static constexpr uint32_t DMA_UPDATES =
    LL_DMA_UPDATE_CTR1 | LL_DMA_UPDATE_CTR2 | LL_DMA_UPDATE_CBR1 |
    LL_DMA_UPDATE_CSAR | LL_DMA_UPDATE_CDAR | LL_DMA_UPDATE_CLLR;

static void configure_dma_ring(uint32_t channel, LL_DMA_LinkNodeTypeDef *nodes,
                               uint32_t request, uint32_t source, void *buffer,
                               uint32_t nodeBytes, uint32_t sourceBytes,
                               uint32_t destWidth)
{
    for (uint32_t n = 0; n < DMA_NODE_COUNT; ++n) {
        auto &r = nodes[n].LinkRegisters;
        r[0] = LL_DMA_DEST_ALLOCATED_PORT1 | LL_DMA_DEST_INCREMENT | destWidth |
               LL_DMA_SRC_ALLOCATED_PORT0 | LL_DMA_SRC_FIXED | LL_DMA_SRC_DATAWIDTH_WORD;
        // Single transfers, burst length 1, zero padding, no byte exchange.
        r[1] = LL_DMA_DIRECTION_PERIPH_TO_MEMORY | LL_DMA_HWREQUEST_SINGLEBURST |
               LL_DMA_TRIG_POLARITY_MASKED | (request & DMA_CTR2_REQSEL);
        r[2] = sourceBytes;
        r[3] = source;
        r[4] = reinterpret_cast<uint32_t>(buffer) + n * nodeBytes;
        r[5] = DMA_UPDATES |
               (reinterpret_cast<uint32_t>(&nodes[(n + 1U) % DMA_NODE_COUNT]) & DMA_CLLR_LA);
        r[6] = r[7] = 0;
    }

    LL_DMA_ConfigControl(GPDMA1, channel,
        LL_DMA_HIGH_PRIORITY | LL_DMA_LINK_ALLOCATED_PORT1 | LL_DMA_LSM_FULL_EXECUTION);
    LL_DMA_SetTransferEventMode(GPDMA1, channel, LL_DMA_TCEM_EACH_LLITEM_TRANSFER);
    LL_DMA_SetLinkedListBaseAddr(GPDMA1, channel, reinterpret_cast<uint32_t>(nodes));
    LL_DMA_ConfigLinkUpdate(GPDMA1, channel, DMA_UPDATES, reinterpret_cast<uint32_t>(nodes));
    LL_DMA_ClearFlag_TC(GPDMA1, channel);
    LL_DMA_ClearFlag_DTE(GPDMA1, channel);
    cache_flush_invalidate(nodes, sizeof(LL_DMA_LinkNodeTypeDef) * DMA_NODE_COUNT);
}

static void dma_init(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPDMA1EN;
    (void)RCC->AHB1ENR;

    memset(dmaBuffer, 0, sizeof(dmaBuffer));
    memset(timestampBuffer, 0, sizeof(timestampBuffer));
    cache_flush_invalidate(dmaBuffer, sizeof(dmaBuffer));
    cache_flush_invalidate(timestampBuffer, sizeof(timestampBuffer));

    // Conservar la longitud de origen de 32 bits del ADC (aunque destino sea 16 bits).
    configure_dma_ring(LL_DMA_CHANNEL_1, dmaNode, LL_GPDMA1_REQUEST_ADC1,
        LL_ADC_DMA_GetRegAddr(ADC1, LL_ADC_DMA_REG_REGULAR_DATA), dmaBuffer,
        DMA_NODE_BYTES, DMA_NODE_RESULTS * sizeof(uint32_t), LL_DMA_DEST_DATAWIDTH_HALFWORD);
    configure_dma_ring(LL_DMA_CHANNEL_0, timestampNode, LL_GPDMA1_REQUEST_TIM2_UP,
        reinterpret_cast<uint32_t>(&TIM5->CNT), timestampBuffer,
        DMA_TIMESTAMP_NODE_BYTES, DMA_TIMESTAMP_NODE_BYTES, LL_DMA_DEST_DATAWIDTH_WORD);
}

// ------------------------------------------------------------
// TIM2 -> TRGO @ 31.25 kHz, 32 ticks de 1 us
// ------------------------------------------------------------

static void timer_init(void)
{
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM2EN;
    (void)RCC->APB1ENR1;

    LL_TIM_SetCounterMode(TIM2, LL_TIM_COUNTERMODE_UP);
    LL_TIM_SetClockDivision(TIM2, LL_TIM_CLOCKDIVISION_DIV1);
    LL_TIM_SetPrescaler(TIM2, TIM2_PRESCALER);
    LL_TIM_SetAutoReload(TIM2, TIM2_AUTORELOAD);
    LL_TIM_GenerateEvent_UPDATE(TIM2);
    LL_TIM_DisableARRPreload(TIM2);
    LL_TIM_SetClockSource(TIM2, LL_TIM_CLOCKSOURCE_INTERNAL);
    LL_TIM_SetTriggerOutput(TIM2, LL_TIM_TRGO_UPDATE);
    LL_TIM_DisableMasterSlaveMode(TIM2);

    // TIM2 UPDATE must also generate a GPDMA request for the hardware
    // timestamp channel.  Without UDE, the timestamp DMA never advances.
    LL_TIM_EnableDMAReq_UPDATE(TIM2);

    LL_TIM_SetCounter(TIM2, 0);
}

// ------------------------------------------------------------
// Toggle thread
// ------------------------------------------------------------

static void toggle_thread(void *, void *, void *)
{
    bool state = false;

    while (1)
    {
        state = !state;
        digitalWrite(WRITE_PIN, state ? HIGH : LOW);
        k_sleep(K_MSEC(TOGGLE_PERIOD_MS));
    }
}

// ------------------------------------------------------------
// Serial consumer
//
// IMPORTANT: this thread is completely outside the acquisition timing path.
// TX por polling desde este hilo; ADC + TIM2 + GPDMA continúan en hardware.
// No mezclar con Serial1.write(): evita la cola y las ISR TX del core.
// ------------------------------------------------------------

static Packet tx = {{'D', 'A', 'T', 'A'}, 1U, SERIAL_BLOCK_PAIRS, {}};

// El mismo dispositivo que usa Serial1 en el core UNO Q 1.0.0.
static const struct device *const scope_uart =
    DEVICE_DT_GET(DT_PHANDLE_BY_IDX(DT_PATH(zephyr_user), serials, 0));

static void write_packet()
{
    // Un único productor TX; sin cola ni ISR por byte. Las interrupciones siguen
    // habilitadas y el hilo cede al esperar el siguiente nodo DMA.
    const auto *data = reinterpret_cast<const uint8_t *>(&tx);
    for (size_t i = 0; i < sizeof(tx); ++i) {
        uart_poll_out(scope_uart, data[i]);
    }
}

// Validar el destino y el contador, no solo las banderas TC de arranque.
static bool dma_in_node(uint32_t channel, uint32_t bufferStart,
                        uint32_t node, uint32_t nodeBytes, uint32_t maxSourceBytes)
{
    uint32_t dest = LL_DMA_GetDestAddress(GPDMA1, channel);
    uint32_t remaining = LL_DMA_GetBlkDataLength(GPDMA1, channel);
    uint32_t start = bufferStart + node * nodeBytes;
    return dest >= start && dest < start + nodeBytes &&
           remaining > 0U && remaining <= maxSourceBytes;
}

static bool both_dma_in_node(uint32_t node)
{
    return dma_in_node(LL_DMA_CHANNEL_1, (uint32_t)dmaBuffer,
                       node, DMA_NODE_BYTES, DMA_NODE_RESULTS * sizeof(uint32_t)) &&
           dma_in_node(LL_DMA_CHANNEL_0, (uint32_t)timestampBuffer,
                       node, DMA_TIMESTAMP_NODE_BYTES, DMA_TIMESTAMP_NODE_BYTES);
}

static void serial_thread(void *, void *, void *)
{
    uint32_t completedNode = 0;

    // Primero observar ambos canales adquiriendo el nodo 0. Las TC iniciales
    // pueden estar activas antes de haber adquirido un nodo completo.
    while (!both_dma_in_node(0U)) {
        k_sleep(K_MSEC(DMA_POLL_MS));
    }
    LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_1);
    LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_0);

    // La primera entrega solo es valida cuando ambos DMA pasaron al nodo 1.
    // Dejar las nuevas TC pendientes para el consumidor normal.
    while (!(both_dma_in_node(1U) &&
             LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_1) &&
             LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_0))) {
        k_sleep(K_MSEC(DMA_POLL_MS));
    }

    while (1)
    {
        // Wait until BOTH DMA streams have completed the same ping-pong node:
        // ADC data + hardware timestamps.
        while (!(LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_1) &&
                 LL_DMA_IsActiveFlag_TC(GPDMA1, LL_DMA_CHANNEL_0)))
        {
            if (LL_DMA_IsActiveFlag_DTE(GPDMA1, LL_DMA_CHANNEL_1))
            {
                LL_DMA_ClearFlag_DTE(GPDMA1, LL_DMA_CHANNEL_1);
                dmaErrorCount++;
            }
            if (LL_DMA_IsActiveFlag_DTE(GPDMA1, LL_DMA_CHANNEL_0))
            {
                LL_DMA_ClearFlag_DTE(GPDMA1, LL_DMA_CHANNEL_0);
                dmaErrorCount++;
            }

            k_sleep(K_MSEC(DMA_POLL_MS));
        }

        LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_1);
        LL_DMA_ClearFlag_TC(GPDMA1, LL_DMA_CHANNEL_0);

        uint16_t *src =
            &dmaBuffer[completedNode * DMA_NODE_RESULTS];
        uint32_t *tsrc =
            &timestampBuffer[completedNode * DMA_NODE_PAIRS];

        // These nodes are complete and the DMA is now filling the other nodes.
        cache_invalidate(src, DMA_NODE_BYTES);
        cache_invalidate(tsrc, DMA_TIMESTAMP_NODE_BYTES);

        for (uint32_t base = 0;
             base < DMA_NODE_PAIRS;
             base += SERIAL_BLOCK_PAIRS)
        {
            for (uint32_t i = 0; i < SERIAL_BLOCK_PAIRS; i++)
            {
                const uint32_t pair = base + i;

                // REAL acquisition timestamp: copied by GPDMA from TIM5->CNT
                // on the same TIM2 update that triggered this ADC sample.
                tx.samples[i].timestamp = tsrc[pair];

                tx.samples[i].adc_in = src[2U * pair];
                tx.samples[i].adc_out = src[2U * pair + 1U];
            }

            // DATA + estado + uint16 LE + 512 muestras de 8 bytes.
            write_packet();
        }

        completedNode ^= 1U;
    }
}

// ------------------------------------------------------------
// Arduino setup / loop
// ------------------------------------------------------------

void setup()
{
    pinMode(ADC_IN_PIN, INPUT);
    pinMode(ADC_OUT_PIN, INPUT);

    pinMode(WRITE_PIN, OUTPUT);
    digitalWrite(WRITE_PIN, LOW);

    Serial1.begin(SERIAL_BAUD);
    uart_irq_tx_disable(scope_uart);
    uart_irq_rx_disable(scope_uart); // Enlace unidireccional Q -> R4.

    // Configure the hardware path before starting the trigger.
    timer_init();
    timestamp_timer_init();
    adc_init();
    dma_init();

    k_thread_create(
        &serial_thread_data,
        serial_stack,
        K_THREAD_STACK_SIZEOF(serial_stack),
        serial_thread,
        NULL, NULL, NULL,
        PRIORITY_SERIAL,
        0,
        K_NO_WAIT);

    k_thread_create(
        &toggle_thread_data,
        toggle_stack,
        K_THREAD_STACK_SIZEOF(toggle_stack),
        toggle_thread,
        NULL, NULL, NULL,
        PRIORITY_TOGGLE,
        0,
        K_NO_WAIT);

    // TIM5 timestamp counter is already running. Start both DMAs, then ADC and TIM2.
    LL_DMA_EnableChannel(GPDMA1, LL_DMA_CHANNEL_0);
    LL_DMA_EnableChannel(GPDMA1, LL_DMA_CHANNEL_1);
    LL_ADC_REG_StartConversion(ADC1);
    LL_TIM_EnableCounter(TIM2);
}

void loop()
{
    k_sleep(K_SECONDS(1));
}
