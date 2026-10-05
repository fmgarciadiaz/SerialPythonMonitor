#include <Arduino.h>
#include <Arduino_RouterBridge.h> // Dependencia del core, sin transporte RPC.
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <zephyr/irq.h>
#include <zephyr/drivers/dma.h>
#include <zephyr/drivers/uart.h>
#include "control_protocol.h"
#include "acquisition_protocol.h"
#include <stm32u5xx.h>
#include <stm32u5xx_ll_dma.h>
#include <stm32u5xx_ll_dcache.h>
#include "benchmark_protocol.h"
#include "timing_diag.h"

#if !defined(CONFIG_SOC_STM32U585XX)
#error "Sólo UNO Q STM32U585"
#endif

namespace acquisition { struct Node; }
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
        timing_diag::irq_cycle=k_cycle_get_32();
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
static bool reset_dma(DMA_Channel_TypeDef *channel, uint32_t timeout_us = ACTIVE_TIMEOUT_US) {
    if (channel->CCR & DMA_CCR_EN) {
        channel->CCR |= DMA_CCR_SUSP;
        const uint32_t started = k_cycle_get_32();
        while (!(channel->CSR & (DMA_CSR_SUSPF | DMA_CSR_IDLEF))) {
            if (elapsed_us(started) >= timeout_us) return false;
        }
    }
    channel->CCR = DMA_CCR_RESET;
    __DSB();
    const uint32_t started = k_cycle_get_32();
    while (channel->CCR & (DMA_CCR_RESET | DMA_CCR_EN)) {
        if (elapsed_us(started) >= timeout_us) return false;
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
    const uint32_t diag_arm=k_cycle_get_32();
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
    const uint32_t diag_ready=k_cycle_get_32();
    timing_diag::record(timing_diag::ARM,diag_arm,diag_ready);
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
    timing_diag::record(timing_diag::READY_TO_IRQ,diag_ready,timing_diag::irq_cycle);
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
    timing_diag::record(timing_diag::IRQ_TO_RETURN,timing_diag::irq_cycle);
    return result;
}

#include "acquisition.h"

// SPI owns tx/rx exclusively. Output worker owns acquisition::take/release.
// A one-frame handoff keeps borrowed ADC RAM alive until SPI has sent it.
static k_mutex output_lock;
static k_sem frame_available, frame_sent;
static uint8_t sample_frame[BLOCK_BYTES];
K_MSGQ_DEFINE(control_replies, sizeof(scope_control::Reply), 8, 4);
static scope_control::Switch output_switch;
static scope_acq::Settings settings;
K_MSGQ_DEFINE(generator_replies, sizeof(scope_gen::Reply), 8, 4);
K_MSGQ_DEFINE(settings_replies, sizeof(scope_acq::Reply), 8, 4);
static uint8_t output_mode = scope_control::SPI;
static bool reply_reserved = false;
static struct k_thread output_thread_data;
K_THREAD_STACK_DEFINE(output_stack, 4096);
static const device *const scope_uart =
    DEVICE_DT_GET(DT_PHANDLE_BY_IDX(DT_PATH(zephyr_user), serials, 0));
static Packet uart_packet = {{'D','A','T','A'}, 1U, SERIAL_BLOCK_PAIRS, {}};

static void enqueue_reply(const scope_control::Reply &reply) {
    // Reserved capacity: commands are accepted only with two free reply slots.
    if (k_msgq_put(&control_replies, &reply, K_NO_WAIT) != 0) {
        acquisition::fail(); // Never silently lose an APPLIED acknowledgement.
    }
}
#if defined(__GNUC__) && !defined(__clang__)
__attribute__((optimize("O2")))
#endif
static void build_samples(uint8_t *frame, acquisition::Node *node, unsigned offset,
                          unsigned count) {
    memset(frame, 0, BLOCK_BYTES);
    put32(frame + 48, 1000000U / acquisition::period);
    put32(frame + 52, node ? node->index * DMA_NODE_PAIRS + offset : 0);
    put32(frame + 56, acquisition::dropped_nodes);
    put32(frame + 60, acquisition::fatal_errors);
    put16(frame + 64, count); frame[66] = acquisition::bits; frame[67] = 2;
    put32(frame + 68, acquisition::period);
    put32(frame + 72, node ? node->index : 0);
    put32(frame + 76, (acquisition::epoch << 1) | (acquisition::fatal_errors ? 1 : 0));
    if (count) memcpy(frame + 80, node->samples + offset, count * sizeof(Sample));
}
static void output_worker(void *, void *, void *) {
    for (;;) {
        k_mutex_lock(&output_lock, K_FOREVER);
        if (settings.pending()) {
            const auto request = settings.requested();
            const bool ok = !acquisition::fatal_errors && !acquisition::dropped_nodes &&
                acquisition::reconfigure(request.bits, request.period);
            const auto result = settings.complete(ok);
            if (k_msgq_put(&settings_replies, &result, K_NO_WAIT) != 0 || !ok) {
                acquisition::fail(); ready = false;
            }
        }
        k_mutex_unlock(&output_lock);
        auto *node = acquisition::take();
        if (!node) continue;
        // This is the first sample of a whole, owned node. The previous node
        // finished its physical transmission before release(). Control stays live.
        k_mutex_lock(&output_lock, K_FOREVER);
        scope_control::Reply applied{};
        if (output_switch.pending()) {
            const bool healthy = !acquisition::fatal_errors && !acquisition::dropped_nodes;
            if (output_switch.complete(node->index * DMA_NODE_PAIRS, healthy, applied)) {
                output_mode = applied.active;
                enqueue_reply(applied);
                reply_reserved = false;
            }
        }
        const uint8_t mode = output_mode;
        k_mutex_unlock(&output_lock);
        const uint32_t diag_node=k_cycle_get_32();
        if (mode == scope_control::UART) {
            for (unsigned offset = 0; offset < DMA_NODE_PAIRS; offset += SERIAL_BLOCK_PAIRS) {
                memcpy(uart_packet.samples, node->samples + offset, sizeof(uart_packet.samples));
                const auto *bytes = reinterpret_cast<const uint8_t *>(&uart_packet);
                for (size_t i = 0; i < sizeof(uart_packet); ++i) uart_poll_out(scope_uart, bytes[i]);
            }
            // uart_poll_out may return with the last byte in the peripheral.
            // APPLIED must follow the last stop bit, not just the final register write.
            while (!uart_irq_tx_complete(scope_uart)) k_yield();
        } else {
            for (unsigned offset = 0; offset < DMA_NODE_PAIRS;) {
                const unsigned count = min(unsigned(53), unsigned(DMA_NODE_PAIRS - offset));
                const uint32_t diag_frame=k_cycle_get_32();
                build_samples(sample_frame, node, offset, count);
                k_sem_give(&frame_available);
                k_sem_take(&frame_sent, K_FOREVER);
                timing_diag::record(timing_diag::HANDOFF,diag_frame);
                offset += count;
            }
        }
        timing_diag::record(timing_diag::NODE_SEND,diag_node);
        acquisition::release();
    }
}

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
    if (!device_is_ready(scope_uart)) { ready = false; return; }
    Serial1.begin(SERIAL_BAUD);
    uart_irq_tx_disable(scope_uart);
    uart_irq_rx_disable(scope_uart);
    k_mutex_init(&output_lock);
    k_sem_init(&frame_available, 0, 1);
    k_sem_init(&frame_sent, 0, 1);
    ready = acquisition::start();
    if (ready) k_thread_create(&output_thread_data, output_stack,
        K_THREAD_STACK_SIZEOF(output_stack), output_worker, nullptr, nullptr, nullptr,
        PRIORITY_SERIAL, 0, K_NO_WAIT);
}

void loop() {
    if (!ready) { k_sleep(K_MSEC(100)); return; }
    if(acquisition::dropped_nodes || acquisition::fatal_errors || timing_diag::frozen) {
        if(!timing_diag::frozen) {
            LL_TIM_DisableCounter(TIM2);
            k_thread_abort(&acquisition::producer_thread_data);
            k_thread_abort(&output_thread_data);
            timing_diag::frozen=true;
        }
        timing_diag::encode(tx,sequence++,acquisition::period,acquisition::epoch,
                            acquisition::dropped_nodes,acquisition::fatal_errors);
        exchange();return;
    }
    scope_control::Reply reply{};
    scope_acq::Reply config_reply{};
    scope_gen::Reply generator_reply{};
    k_mutex_lock(&output_lock, K_FOREVER);
    const bool have_generator = k_msgq_get(&generator_replies, &generator_reply, K_NO_WAIT) == 0;
    const bool have_config = !have_generator && k_msgq_get(&settings_replies, &config_reply, K_NO_WAIT) == 0;
    const bool have_reply = !have_generator && !have_config && k_msgq_get(&control_replies, &reply, K_NO_WAIT) == 0;
    const bool have_samples = !have_generator && !have_config && !have_reply && k_sem_take(&frame_available, K_NO_WAIT) == 0;
    uint32_t started = k_cycle_get_32();
    if (have_generator) scope_gen::encode(tx, sequence, generator_reply);
    else if (have_config) scope_acq::encode(tx, sequence, config_reply);
    else if (have_reply) scope_control::encode(tx, sequence, reply);
    else {
        data_frame(tx, sequence, last_ping, spi_errors, bad_ping, short_transfers,
                   last_result, last_error, prepare_us, check_us);
        put16(tx + 6, 3);
        if (have_samples) memcpy(tx + 48, sample_frame + 48, BLOCK_BYTES - 48 - CRC_BYTES);
        else {
            uint8_t idle[BLOCK_BYTES];
            build_samples(idle, nullptr, 0, 0);
            memcpy(tx + 48, idle + 48, BLOCK_BYTES - 48 - CRC_BYTES);
        }
        seal(tx);
    }
    timing_diag::record(timing_diag::PREPARE,started);
    prepare_us = elapsed_us(started);
    k_mutex_unlock(&output_lock);
    last_result = exchange();
    started = k_cycle_get_32();
    if (last_result < 0) {
        ++spi_errors;
        last_error = fault_dma ? -int32_t(0x2000000U | fault_dma) :
            (fault_sr ? -int32_t(0x10000U | (fault_sr & 0xffffU)) : last_result);
        if (last_result == -EMSGSIZE) ++short_transfers;
        // Do not advance sample ownership after a failed physical transfer.
        acquisition::fail(); ready = false;
    } else if (last_result != int(BLOCK_BYTES)) {
        ++short_transfers; acquisition::fail(); ready = false;
    } else if(!memcmp(rx,"SCP1",4) && get32(rx+8)>=0x80000000U && get32(rx+8)!=0xffffffffU && get16(rx+6)==12 && get16(rx+4)==VERSION && get32(rx+12)==PAYLOAD_BYTES &&
            get32(rx+BLOCK_BYTES-4)==crc32(rx,BLOCK_BYTES-4)) {
        bool padding_ok=true;for(unsigned i=16;i<BLOCK_BYTES-4;++i)if(rx[i])padding_ok=false;
        if(padding_ok) {
            LL_TIM_DisableCounter(TIM2);
            k_thread_abort(&acquisition::producer_thread_data);
            k_thread_abort(&output_thread_data);
            timing_diag::frozen=true;
        } else ++bad_ping;
    } else if (valid_ping(rx)) last_ping = get32(rx + 8);
    else {
        scope_control::Request request{};
        scope_acq::Request config_request{};
        scope_gen::Request generator_request{};
        if (scope_gen::decode(rx, BLOCK_BYTES, generator_request)) {
            if (k_msgq_num_free_get(&generator_replies)) {
                const auto result=generator::submit(generator_request);
                if(k_msgq_put(&generator_replies,&result,K_NO_WAIT)!=0) { acquisition::fail();ready=false; }
            } else { acquisition::fail();ready=false; }
        } else if (scope_acq::decode(rx, BLOCK_BYTES, config_request)) {
            k_mutex_lock(&output_lock, K_FOREVER);
            if (k_msgq_num_free_get(&settings_replies) >= 3U) {
                const auto accepted = settings.submit(config_request,
                    !output_switch.pending() && output_mode == scope_control::SPI);
                if (k_msgq_put(&settings_replies, &accepted, K_NO_WAIT) != 0) {
                    acquisition::fail(); ready = false;
                }
            } else { acquisition::fail(); ready = false; }
            k_mutex_unlock(&output_lock);
        } else if (scope_control::decode(rx, BLOCK_BYTES, request)) {
            k_mutex_lock(&output_lock, K_FOREVER);
            // At most one outstanding switch; reserve ACCEPTED + APPLIED space.
            if (k_msgq_num_free_get(&control_replies) >= (reply_reserved ? 2U : 3U)) {
                const auto accepted = request.mode == scope_control::UART && acquisition::period < 32 ? scope_control::Reply{
                    request.id, request.mode, output_mode, scope_control::REJECTED,
                    scope_control::UNSUPPORTED, 0} : settings.pending() ? scope_control::Reply{
                    request.id, request.mode, output_mode, scope_control::REJECTED,
                    scope_control::BUSY, 0} : output_switch.submit(request);
                enqueue_reply(accepted);
                reply_reserved = output_switch.pending();
            } else { acquisition::fail(); ready = false; }
            k_mutex_unlock(&output_lock);
        } else ++bad_ping;
    }
    timing_diag::record(timing_diag::CHECK,started);
    check_us = elapsed_us(started);
    ++sequence;
    if (have_samples && ready) k_sem_give(&frame_sent);
    // Idle status traffic is bounded; SPI remains available during UART output.
    if (!have_generator && !have_config && !have_reply && !have_samples) k_sleep(K_MSEC(1));
}
