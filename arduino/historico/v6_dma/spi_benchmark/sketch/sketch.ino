#include <Arduino.h>
#include <Arduino_RouterBridge.h> // Dependencia del core, sin transporte RPC.
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <zephyr/irq.h>
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
static uint32_t fault_dma = 0;
static uint32_t sequence = 0, last_ping = 0xffffffffU;
static uint32_t spi_errors = 0, bad_ping = 0, short_transfers = 0;
static int32_t last_result = 0, last_error = 0;
static uint32_t prepare_us = 0, check_us = 0, fault_sr = 0;
static bool ready = false;

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
// DMA mueve cada byte. Esta primera etapa todavía consulta fin/error por polling.
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

static void configure_dma(DMA_Channel_TypeDef *channel, bool transmit) {
    channel->CCR = LL_DMA_HIGH_PRIORITY; // Sin IRQ DMA en esta etapa.
    // Accesos de un byte, bursts de uno. RAM por puerto 1, SPI por puerto 0.
    channel->CTR1 = transmit ? (DMA_CTR1_SINC | DMA_CTR1_SAP)
                             : (DMA_CTR1_DINC | DMA_CTR1_DAP);
    channel->CTR2 = transmit ? (DMA_CTR2_DREQ | LL_GPDMA1_REQUEST_SPI3_TX)
                             : LL_GPDMA1_REQUEST_SPI3_RX;
    channel->CBR1 = BLOCK_BYTES;
    channel->CSAR = transmit ? reinterpret_cast<uint32_t>(tx)
                             : reinterpret_cast<uint32_t>(&SPI3->RXDR);
    channel->CDAR = transmit ? reinterpret_cast<uint32_t>(&SPI3->TXDR)
                             : reinterpret_cast<uint32_t>(rx);
    channel->CLLR = 0;
}

static int exchange() {
    fault_sr = fault_dma = 0;
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
    configure_dma(rx_dma, false);
    configure_dma(tx_dma, true);
    SPI3->CR2 = BLOCK_BYTES;
    SPI3->IFCR = CLEAR_FLAGS;
    SPI3->CFG1 = 7U | SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN;
    __DSB();
    rx_dma->CCR |= DMA_CCR_EN;
    tx_dma->CCR |= DMA_CCR_EN;
    SPI3->CR1 = SPI_CR1_SPE;
    __DSB();
    bool active = false;
    unsigned polls = 0;
    int result = -EIO;
    for (;;) {
        const uint32_t status = SPI3->SR;
        const uint32_t tx_status = tx_dma->CSR, rx_status = rx_dma->CSR;
        if (status & ERROR_FLAGS) { fault_sr = status; break; }
        if ((tx_status | rx_status) & DMA_ERRORS) {
            fault_dma = ((tx_status & DMA_ERRORS) >> 8) |
                        ((rx_status & DMA_ERRORS) << 8);
            break;
        }
        if ((status & SPI_SR_EOT) && (tx_status & DMA_CSR_TCF) &&
            (rx_status & DMA_CSR_TCF)) { result = BLOCK_BYTES; break; }
        if (!active && (selected() || rx_dma->CBR1 != BLOCK_BYTES)) {
            active = true;
            started = k_cycle_get_32();
        }
        if (active && (++polls & 255U) == 0 && elapsed_us(started) >= ACTIVE_TIMEOUT_US) {
            result = -ETIMEDOUT;
            break;
        }
    }
    stop_spi();
    SPI3->CFG1 &= ~(SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN);
    // Detener ambos canales antes de leer o volver a escribir los buffers.
    const bool tx_stopped = reset_dma(tx_dma);
    const bool rx_stopped = reset_dma(rx_dma);
    if (!tx_stopped || !rx_stopped) { ready = false; return -ETIMEDOUT; }
    cache_invalidate(rx, sizeof(rx));
    return result;
}

void setup() {
    // El core sólo aplica clocks y pinctrl; ninguna transferencia pasa por él.
    const int result = device_init(spi_device);
    ready = (result == 0 || result == -EALREADY) && device_is_ready(spi_device);
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
}

void loop() {
    if (!ready) { k_sleep(K_MSEC(100)); return; }
    uint32_t started = k_cycle_get_32();
    data_frame(tx, sequence, last_ping, spi_errors, bad_ping, short_transfers,
               last_result, last_error, prepare_us, check_us);
    prepare_us = elapsed_us(started);
    last_result = exchange();
    started = k_cycle_get_32();
    if (last_result < 0) {
        ++spi_errors;
        // Extensión diagnóstica sin cambiar el formato SCP1/v2:
        // <= -65536 codifica SR[15:0]; los demás valores son errno negativos.
        last_error = fault_dma ? -int32_t(0x2000000U | fault_dma) :
            (fault_sr ? -int32_t(0x10000U | (fault_sr & 0xffffU)) : last_result);
        if (last_result == -EMSGSIZE) ++short_transfers;
    } else if (last_result != int(BLOCK_BYTES)) ++short_transfers;
    else if (valid_ping(rx)) last_ping = get32(rx + 8);
    else ++bad_ping;
    check_us = elapsed_us(started);
    ++sequence;
}
