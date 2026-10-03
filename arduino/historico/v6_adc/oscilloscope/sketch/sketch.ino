#include <Arduino.h>
#include <Arduino_RouterBridge.h> // Dependencia del core, sin transporte RPC.
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <zephyr/irq.h>
#include <zephyr/drivers/dma.h>
#include <stm32u5xx.h>
#include <stm32u5xx_ll_dma.h>
#include <stm32u5xx_ll_dcache.h>
#include "benchmark_protocol.h"

#if !defined(CONFIG_SOC_STM32U585XX)
#error "Sólo UNO Q STM32U585"
#endif

using namespace scope_bench;
#define SPI_NODE DT_NODELABEL(spi3)
static const device *const spi_device = DEVICE_DT_GET(SPI_NODE);
static const device *const dma_device = DEVICE_DT_GET(DT_NODELABEL(gpdma1));
static_assert(DT_REG_ADDR(SPI_NODE) == SPI3_BASE, "Revisar mapa SPI3");
static_assert(BLOCK_BYTES <= 1023, "SPI3 tiene TSIZE limitado a 10 bits");
static constexpr uint32_t ERROR_FLAGS = SPI_SR_UDR | SPI_SR_OVR | SPI_SR_CRCE |
                                        SPI_SR_TIFRE | SPI_SR_MODF;
static constexpr uint32_t CLEAR_FLAGS = SPI_IFCR_EOTC | SPI_IFCR_TXTFC |
    SPI_IFCR_UDRC | SPI_IFCR_OVRC | SPI_IFCR_CRCEC | SPI_IFCR_TIFREC |
    SPI_IFCR_MODFC | SPI_IFCR_SUSPC;
static constexpr uint32_t ACTIVE_TIMEOUT_US = 50000;
static_assert(BLOCK_BYTES % CONFIG_DCACHE_LINE_SIZE == 0, "DMA cache alignment");
static uint8_t tx[BLOCK_BYTES] __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
static uint8_t rx[BLOCK_BYTES] __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
static DMA_Channel_TypeDef *const tx_dma = GPDMA1_Channel2;
static DMA_Channel_TypeDef *const rx_dma = GPDMA1_Channel3;
static constexpr uint32_t DMA_ERRORS = DMA_CSR_DTEF | DMA_CSR_ULEF | DMA_CSR_USEF | DMA_CSR_TOF;
static volatile uint32_t fault_dma = 0;
static uint32_t sequence = 0, last_ping = 0xffffffffU;
static uint32_t spi_errors = 0, bad_ping = 0, short_transfers = 0;
static int32_t last_result = 0, last_error = 0;
static uint32_t prepare_us = 0, check_us = 0;
static volatile uint32_t fault_sr = 0;
static bool ready = false;
static struct k_sem transfer_done;
static volatile bool completed = false;
static constexpr uint32_t DMA_IRQS = DMA_CCR_TCIE | DMA_CCR_DTEIE |
    DMA_CCR_ULEIE | DMA_CCR_USEIE | DMA_CCR_TOIE;
static volatile uint32_t done_channels = 0;
static inline void publish_ready(bool value) {
    GPIOG->BSRR = value ? (1U << 13) : (1U << (13 + 16));
    __DSB();
}
// El core tiene CONFIG_SHARED_INTERRUPTS: registrar otra ISR NO reemplaza
// el driver DMA, que limpia TC antes de llamarnos. Usar sus callbacks por bloque.
static void dma_done(const device *, void *, uint32_t channel, int status) {
    if (status == DMA_STATUS_HALF_COMPLETE) return;
    publish_ready(false);
    const uint32_t sr = SPI3->SR;
    if (sr & ERROR_FLAGS) fault_sr = sr;
    if (status < 0) fault_dma = (uint32_t(-status) & 0xffffU) << (channel == 2 ? 0 : 16);
    else done_channels |= channel == 2 ? 1U : 2U;
    if (!completed && (fault_sr || fault_dma || done_channels == 3U)) {
        completed = true;
        k_sem_give(&transfer_done);
    }
}

// PG12 es el NSS físico de SPI3 en el UNO Q; pinctrl lo configura en AF.
static inline bool selected() { return (GPIOG->IDR & (1U << 12)) == 0; }
static inline uint32_t elapsed_us(uint32_t start) {
    return k_cyc_to_us_floor32(uint32_t(k_cycle_get_32() - start));
}
static void stop_spi() {
    SPI3->CR1 &= ~SPI_CR1_SPE;
    __DSB();
    SPI3->IFCR = CLEAR_FLAGS;
}

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

// Canales 2/3 dedicados al ensayo; 0/1 quedan libres para futura adquisición.
// DMA mueve los bytes; IRQ de fin/error despierta al hilo mediante semáforo.
static bool reset_dma(DMA_Channel_TypeDef *channel) {
    if (channel->CCR & DMA_CCR_EN) {
        channel->CCR |= DMA_CCR_SUSP;
        const uint32_t started = k_cycle_get_32();
        while (!(channel->CSR & (DMA_CSR_SUSPF | DMA_CSR_IDLEF))) {
            if (elapsed_us(started) >= ACTIVE_TIMEOUT_US) return false;
        }
    }
    channel->CCR = DMA_CCR_RESET;
    __DSB();
    const uint32_t started = k_cycle_get_32();
    while (channel->CCR & (DMA_CCR_RESET | DMA_CCR_EN)) {
        if (elapsed_us(started) >= ACTIVE_TIMEOUT_US) return false;
    }
    channel->CFCR = DMA_CFCR_TCF | DMA_CFCR_HTF | DMA_CFCR_DTEF |
        DMA_CFCR_ULEF | DMA_CFCR_USEF | DMA_CFCR_SUSPF | DMA_CFCR_TOF;
    return true;
}

static int configure_dma(DMA_Channel_TypeDef *channel, bool transmit) {
    struct dma_block_config block = {};
    block.block_size = BLOCK_BYTES;
    block.source_address = transmit ? reinterpret_cast<uint32_t>(tx)
                                    : reinterpret_cast<uint32_t>(&SPI3->RXDR);
    block.dest_address = transmit ? reinterpret_cast<uint32_t>(&SPI3->TXDR)
                                  : reinterpret_cast<uint32_t>(rx);
    block.source_addr_adj = transmit ? DMA_ADDR_ADJ_INCREMENT : DMA_ADDR_ADJ_NO_CHANGE;
    block.dest_addr_adj = transmit ? DMA_ADDR_ADJ_NO_CHANGE : DMA_ADDR_ADJ_INCREMENT;
    struct dma_config config = {};
    config.dma_slot = transmit ? LL_GPDMA1_REQUEST_SPI3_TX : LL_GPDMA1_REQUEST_SPI3_RX;
    config.channel_direction = transmit ? MEMORY_TO_PERIPHERAL : PERIPHERAL_TO_MEMORY;
    config.source_data_size = config.dest_data_size = 1;
    config.source_burst_length = config.dest_burst_length = 1;
    config.channel_priority = 3;
    config.block_count = 1;
    config.head_block = &block;
    config.dma_callback = dma_done;
    int result = dma_config(dma_device, transmit ? 2 : 3, &config);
    if (result < 0) return result;
    // Mantener los puertos RAM/SPI del ensayo anterior, transferencias de byte.
    channel->CTR1 = transmit ? (DMA_CTR1_SINC | DMA_CTR1_SAP)
                             : (DMA_CTR1_DINC | DMA_CTR1_DAP);
    return 0;
}

static int exchange() {
    publish_ready(false);
    fault_sr = fault_dma = 0;
    completed = false;
    done_channels = 0;
    k_sem_reset(&transfer_done);
    uint32_t started = k_cycle_get_32();
    while (selected()) {
        if (elapsed_us(started) >= ACTIVE_TIMEOUT_US) return -EBUSY;
    }
    if (!reset_dma(tx_dma) || !reset_dma(rx_dma)) {
        ready = false; // No reutilizar RAM mientras un DMA no se detuvo.
        return -ETIMEDOUT;
    }
    cache_flush_invalidate(tx, sizeof(tx));
    cache_flush_invalidate(rx, sizeof(rx));
    if (configure_dma(rx_dma, false) < 0 || configure_dma(tx_dma, true) < 0) {
        ready = false;
        return -EIO;
    }
    SPI3->CR2 = BLOCK_BYTES;
    SPI3->IFCR = CLEAR_FLAGS;
    SPI3->CFG1 = 7U | SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN;
    __DSB();
    if (dma_start(dma_device, 3) < 0 || dma_start(dma_device, 2) < 0) {
        dma_stop(dma_device, 3);
        dma_stop(dma_device, 2);
        ready = false;
        return -EIO;
    }
    SPI3->CR1 = SPI_CR1_SPE;
    __DSB();
    publish_ready(true);
    int result = -EIO;
    // Idle ilimitado sin consumir CPU. La espera temporizada detecta bloques
    // truncados sin necesitar EXTI en NSS; el margen de detección es 50–100 ms.
    bool partial = false;
    for (;;) {
        if (k_sem_take(&transfer_done, K_MSEC(50)) == 0) {
            result = (fault_sr || fault_dma) ? -EIO :
                ((SPI3->SR & SPI_SR_EOT) && tx_dma->CBR1 == 0 && rx_dma->CBR1 == 0
                 ? int(BLOCK_BYTES) : -EMSGSIZE);
            break;
        }
        if (partial) { result = -ETIMEDOUT; break; }
        partial = selected() || rx_dma->CBR1 != BLOCK_BYTES;
    }
    publish_ready(false);
    SPI3->IER = 0;
    tx_dma->CCR &= ~DMA_IRQS;
    rx_dma->CCR &= ~DMA_IRQS;
    stop_spi();
    SPI3->CFG1 &= ~(SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN);
    // Detener ambos canales antes de leer o volver a escribir los buffers.
    dma_stop(dma_device, 2);
    dma_stop(dma_device, 3);
    const bool tx_stopped = reset_dma(tx_dma);
    const bool rx_stopped = reset_dma(rx_dma);
    if (!tx_stopped || !rx_stopped) { ready = false; return -ETIMEDOUT; }
    cache_invalidate(rx, sizeof(rx));
    return result;
}

#include "acquisition.h"

void setup() {
    // El core sólo aplica clocks y pinctrl; ninguna transferencia pasa por él.
    const int result = device_init(spi_device);
    ready = (result == 0 || result == -EALREADY) && device_is_ready(spi_device);
    ready = ready && device_is_ready(dma_device);
    if (!ready) return;
    irq_disable(DT_IRQN(SPI_NODE));
    SPI3->IER = 0;
    stop_spi();
    SPI3->CR1 = 0;
    SPI3->CFG1 = 7U; // DSIZE=8 bits, FTHLV=1 byte, CRC y DMA deshabilitados.
    SPI3->CFG2 = 0;  // Peripheral, full duplex, modo 0, MSB, NSS físico activo bajo.
    SPI3->UDRDR = 0;
    RCC->AHB1ENR |= RCC_AHB1ENR_GPDMA1EN;
    (void)RCC->AHB1ENR;
    // No apropiarse de un canal que el core ya esté utilizando.
    if ((tx_dma->CCR | rx_dma->CCR) & DMA_CCR_EN) { ready = false; return; }
    irq_disable(GPDMA1_Channel2_IRQn);
    irq_disable(GPDMA1_Channel3_IRQn);
    k_sem_init(&transfer_done, 0, 1);
    NVIC_ClearPendingIRQ(GPDMA1_Channel2_IRQn);
    NVIC_ClearPendingIRQ(GPDMA1_Channel3_IRQn);
    // PG13 también habilita el loader: Linux conserva GPIO70 alto al arrancar.
    // Sólo tomar la salida cuando el receptor solicite INPUT + pull-down.
    // La espera de arranque cede CPU y no toca el loader ni Arduino Router.
    GPIOG->MODER &= ~(3U << 26);
    GPIOG->PUPDR &= ~(3U << 26);
    while (GPIOG->IDR & (1U << 13)) k_sleep(K_MSEC(1));
    publish_ready(false);
    GPIOG->OTYPER &= ~(1U << 13);
    GPIOG->PUPDR &= ~(3U << 26);
    GPIOG->OSPEEDR = (GPIOG->OSPEEDR & ~(3U << 26)) | (2U << 26);
    GPIOG->MODER = (GPIOG->MODER & ~(3U << 26)) | (1U << 26);
    irq_enable(GPDMA1_Channel2_IRQn);
    irq_enable(GPDMA1_Channel3_IRQn);
    ready = acquisition::start();
}

void loop() {
    if (!ready) { k_sleep(K_MSEC(100)); return; }
    static acquisition::Node *node = nullptr;
    static unsigned offset = 0;
    if (!node) { node = acquisition::take(); offset = 0; }
    if (!node && !acquisition::fatal_errors) return;
    const unsigned count = node ? min(unsigned(53), unsigned(DMA_NODE_PAIRS - offset)) : 0;
    uint32_t started = k_cycle_get_32();
    data_frame(tx, sequence, last_ping, spi_errors, bad_ping, short_transfers,
               last_result, last_error, prepare_us, check_us);
    // SCP1/v2 type 3: status32 + metadata32 + up to 53 legacy Sample records.
    put16(tx + 6, 3);
    memset(tx + 48, 0, BLOCK_BYTES - 48 - CRC_BYTES);
    put32(tx + 48, SAMPLE_RATE_HZ);
    put32(tx + 52, node ? node->index * DMA_NODE_PAIRS + offset : 0);
    put32(tx + 56, acquisition::dropped_nodes);
    put32(tx + 60, acquisition::fatal_errors);
    put16(tx + 64, count); tx[66] = 14; tx[67] = 2;
    put32(tx + 68, SAMPLE_PERIOD_US);
    put32(tx + 72, node ? node->index : 0);
    put32(tx + 76, acquisition::fatal_errors ? 1 : 0);
    if (count) memcpy(tx + 80, node->samples + offset, count * sizeof(Sample));
    seal(tx);
    prepare_us = elapsed_us(started);
    last_result = exchange();
    started = k_cycle_get_32();
    if (last_result < 0) {
        ++spi_errors;
        // Extensión diagnóstica sin cambiar el formato SCP1/v2:
        // DMA usa 0x02000000; SPI usa 0x10000 + SR[15:0]; resto errno.
        last_error = fault_dma ? -int32_t(0x2000000U | fault_dma) :
            (fault_sr ? -int32_t(0x10000U | (fault_sr & 0xffffU)) : last_result);
        if (last_result == -EMSGSIZE) ++short_transfers;
    } else if (last_result != int(BLOCK_BYTES)) ++short_transfers;
    else if (valid_ping(rx)) last_ping = get32(rx + 8);
    else ++bad_ping;
    check_us = elapsed_us(started);
    ++sequence;
    if (node) {
        offset += count;
        if (offset == DMA_NODE_PAIRS) { acquisition::release(); node = nullptr; }
    }
}
