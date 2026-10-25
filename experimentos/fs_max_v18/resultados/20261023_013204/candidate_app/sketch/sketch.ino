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
#include "frame_buffer.h"

#if !defined(CONFIG_SOC_STM32U585XX)
#error "Sólo UNO Q STM32U585"
#endif

namespace scope_storage { struct Node; }
namespace acquisition { using Node = scope_storage::Node; }
using namespace scope_bench;
#define SPI_NODE DT_NODELABEL(spi3)
static const device *const spi_device = DEVICE_DT_GET(SPI_NODE);
static const device *const dma_device = DEVICE_DT_GET(DT_NODELABEL(gpdma1));
static_assert(DT_REG_ADDR(SPI_NODE) == SPI3_BASE, "Revisar mapa SPI3");
static_assert(BLOCK_BYTES % 32 == 0, "DMA frame alignment");
static_assert(BLOCK_BYTES <= 1023, "SPI3 tiene TSIZE limitado a 10 bits");
static constexpr uint32_t ERROR_FLAGS = SPI_SR_UDR | SPI_SR_OVR | SPI_SR_CRCE |
                                        SPI_SR_TIFRE | SPI_SR_MODF;
static constexpr uint32_t CLEAR_FLAGS = SPI_IFCR_EOTC | SPI_IFCR_TXTFC |
    SPI_IFCR_UDRC | SPI_IFCR_OVRC | SPI_IFCR_CRCEC | SPI_IFCR_TIFREC |
    SPI_IFCR_MODFC | SPI_IFCR_SUSPC;
static constexpr uint32_t ACTIVE_TIMEOUT_US = 50000;
static_assert(BLOCK_BYTES % CONFIG_DCACHE_LINE_SIZE == 0, "DMA cache alignment");
static uint8_t *tx;
static uint8_t *active_tx;
static bool high_rate_transport();
static bool word_transport();
static uint8_t *rx;
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

struct SpiDmaConfig { uint32_t ctr1, ctr2, ccr; bool initialized; unsigned bytes; };
static SpiDmaConfig spi_dma_config[2]{};
static int configure_dma(DMA_Channel_TypeDef *channel, bool transmit) {
    const uint8_t *tx_buffer=high_rate_transport()?active_tx:tx;
    const unsigned bytes = word_transport()?4U:1U;
    auto &saved = spi_dma_config[transmit ? 0 : 1];
    if (high_rate_transport() && saved.initialized && saved.bytes==bytes) {
        // Fixed single-block geometry and callbacks. Both channels have been
        // stopped/reset before reaching this point; do not rewrite live DMA.
        if (channel->CCR & (DMA_CCR_EN | DMA_CCR_RESET)) return -EBUSY;
        channel->CTR1 = saved.ctr1;
        channel->CTR2 = saved.ctr2;
        channel->CBR1 = BLOCK_BYTES;
        channel->CSAR = transmit ? reinterpret_cast<uint32_t>(tx_buffer)
                                : reinterpret_cast<uint32_t>(&SPI3->RXDR);
        channel->CDAR = transmit ? reinterpret_cast<uint32_t>(&SPI3->TXDR)
                                : reinterpret_cast<uint32_t>(rx);
        channel->CLLR = 0;
        channel->CCR = saved.ccr;
        __DSB();
        return 0;
    }
    struct dma_block_config block = {};
    block.block_size = BLOCK_BYTES;
    block.source_address = transmit ? reinterpret_cast<uint32_t>(tx_buffer)
                                    : reinterpret_cast<uint32_t>(&SPI3->RXDR);
    block.dest_address = transmit ? reinterpret_cast<uint32_t>(&SPI3->TXDR)
                                  : reinterpret_cast<uint32_t>(rx);
    block.source_addr_adj = transmit ? DMA_ADDR_ADJ_INCREMENT : DMA_ADDR_ADJ_NO_CHANGE;
    block.dest_addr_adj = transmit ? DMA_ADDR_ADJ_NO_CHANGE : DMA_ADDR_ADJ_INCREMENT;
    struct dma_config config = {};
    config.dma_slot = transmit ? LL_GPDMA1_REQUEST_SPI3_TX : LL_GPDMA1_REQUEST_SPI3_RX;
    config.channel_direction = transmit ? MEMORY_TO_PERIPHERAL : PERIPHERAL_TO_MEMORY;
    config.source_data_size = config.dest_data_size = bytes;
    config.source_burst_length = config.dest_burst_length = bytes;
    config.channel_priority = 3;
    config.block_count = 1;
    config.head_block = &block;
    config.dma_callback = dma_done;
    int result = dma_config(dma_device, transmit ? 2 : 3, &config);
    if (result < 0) return result;
    // Mantener los puertos RAM/SPI del ensayo anterior, transferencias de byte.
    channel->CTR1 = (bytes==4 ? (2U << DMA_CTR1_SDW_LOG2_Pos) | (2U << DMA_CTR1_DDW_LOG2_Pos) : 0U) |
        (transmit ? (DMA_CTR1_SINC | DMA_CTR1_SAP) : (DMA_CTR1_DINC | DMA_CTR1_DAP));
    saved.bytes = bytes;
    saved.ctr1 = channel->CTR1;
    saved.ctr2 = channel->CTR2;
    saved.ccr = channel->CCR & ~(DMA_CCR_EN | DMA_CCR_RESET | DMA_CCR_SUSP);
    saved.initialized = high_rate_transport();
    return 0;
}

#if defined(__GNUC__) && !defined(__clang__)
__attribute__((optimize("O2")))
#endif
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
    cache_flush_invalidate(high_rate_transport()?active_tx:tx, BLOCK_BYTES);
    cache_flush_invalidate(rx, BLOCK_BYTES);
    if (configure_dma(rx_dma, false) < 0 || configure_dma(tx_dma, true) < 0) {
        ready = false;
        return -EIO;
    }
    SPI3->CR2 = BLOCK_BYTES;
    SPI3->IFCR = CLEAR_FLAGS;
    SPI3->CFG1 = 7U | (7U << SPI_CFG1_CRCSIZE_Pos) |
        ((word_transport()?3U:0U) << SPI_CFG1_FTHLV_Pos) | SPI_CFG1_RXDMAEN | SPI_CFG1_TXDMAEN;
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
    cache_invalidate(rx, BLOCK_BYTES);
    return result;
}

#include "acquisition.h"
#include "high_rate_profile.h"
static bool high_rate_transport() {
    return scope_high_rate(acquisition::bits,acquisition::single()?1U:2U,
        acquisition::period,acquisition::node_pairs());
}
static bool word_transport() {
    return scope_spi40(acquisition::bits,acquisition::single()?1U:2U,acquisition::period,acquisition::node_pairs());
}
#include "wav.h"

// SPI owns tx/rx exclusively. Output worker owns acquisition::take/release.
// Legacy rates retain one-frame acknowledgement; only high-rate ADC8 pipelines.
static k_mutex output_lock;
static constexpr unsigned FRAME_SLOTS=3;
static k_sem frame_available, frame_sent, spi40_free, spi40_node_sent;
static SampleFrame ordinary_frame;
static_assert(sizeof(SampleFrame)==BLOCK_BYTES,"No frame padding");
static_assert(3456U*2U*sizeof(uint32_t)+(FRAME_SLOTS-1U)*BLOCK_BYTES <= sizeof(scope_storage::SingleMemory::timestamps),"Fast DMA nodes and frame scratch must not overlap");
static SampleFrame *frame_slot(unsigned slot) {
    if(!slot) return &ordinary_frame;
    // Only the high-rate profile borrows unused timestamp RAM. Its two DMA
    // nodes occupy 27648 bytes; the aligned buffers start at byte 63552.
    // Reconfiguration occurs after the last physical ACK, before union rebinding.
    auto *end=reinterpret_cast<uint8_t *>(acquisition::timestampBuffer)+acquisition::timestamp_storage_bytes();
    return new (end-(FRAME_SLOTS-slot)*BLOCK_BYTES) SampleFrame;
}
static SampleFrame *sample_ready[FRAME_SLOTS];
static bool spi40_last[FRAME_SLOTS];
static unsigned spi40_read=0;
static unsigned read_frame=0;
K_MSGQ_DEFINE(control_replies, sizeof(scope_control::Reply), 8, 4);
static scope_control::Switch output_switch;
static scope_acq::Settings settings;
K_MSGQ_DEFINE(wav_replies, sizeof(scope_wav::Reply), 8, 4);
K_MSGQ_DEFINE(generator_replies, sizeof(scope_gen::Reply), 8, 4);
K_MSGQ_DEFINE(settings_replies, sizeof(scope_acq::Reply), 8, 4);
static uint8_t output_mode = scope_control::SPI;
static bool reply_reserved = false;
static struct k_thread output_thread_data;
K_THREAD_STACK_DEFINE(output_stack, 4096);
static const device *const scope_uart =
    DEVICE_DT_GET(DT_PHANDLE_BY_IDX(DT_PATH(zephyr_user), serials, 0));
// UART uses only the first two 2048-timestamp nodes. Its packet scratch lives
// beyond those nodes; native-clock modes reject UART and own the full buffer.
constexpr unsigned UART_TIMESTAMP_WORDS = DMA_NODE_PAIRS * DMA_NODE_COUNT;
static_assert(sizeof(scope_storage::DualMemory::timestamps) >=
              UART_TIMESTAMP_WORDS*sizeof(uint32_t)+sizeof(Packet), "UART scratch fits");
static void build_uart_samples(uint8_t *bytes, acquisition::Node *node, unsigned offset) {
    memcpy(bytes,"DATA",4);bytes[4]=1;put16(bytes+5,SERIAL_BLOCK_PAIRS);
    for(unsigned i=0;i<SERIAL_BLOCK_PAIRS;++i) {
        const auto &pair=node->samples[offset+i];
        uint8_t *sample=bytes+7+i*8;
        put32(sample,node->timestamp+(offset+i)*acquisition::period);
        put16(sample+4,pair.ch1);put16(sample+6,pair.ch2);
    }
}

static void enqueue_reply(const scope_control::Reply &reply) {
    // Reserved capacity: commands are accepted only with two free reply slots.
    if (k_msgq_put(&control_replies, &reply, K_NO_WAIT) != 0) {
        acquisition::fail(); // Never silently lose an APPLIED acknowledgement.
    }
}
#include "sample_packing.h"
#if defined(__GNUC__) && !defined(__clang__)
__attribute__((optimize("O2")))
#endif
static void build_native_samples(uint8_t *frame, acquisition::Node *node, unsigned offset,
                          unsigned count) {
    const unsigned channels=acquisition::single()?1U:2U;
    const unsigned used=count*acquisition::bits*channels/8U;
    memset(frame+116+used,0,988U-116U-used);
    put32(frame+48,160000000U/acquisition::period);
    put32(frame+52,node?node->index*acquisition::node_pairs()+offset:0);
    put32(frame+56,acquisition::dropped_nodes);put32(frame+60,acquisition::fatal_errors);
    put16(frame+64,count);frame[66]=acquisition::bits;frame[67]=channels;
    put32(frame+68,acquisition::period);put32(frame+72,node?node->index:0);
    put32(frame+76,(acquisition::epoch<<1)|(acquisition::fatal_errors?1U:0U));
    put32(frame+80,count?node->timestamp+offset*acquisition::period:0);
    put32(frame+84,acquisition::node_pairs());
    put32(frame+88,acquisition::QUEUE_SLOTS-k_sem_count_get(&acquisition::empty_slots));
    put32(frame+92,acquisition::queue_peak);put32(frame+96,acquisition::copy_max);
    put32(frame+100,acquisition::poll_max);put32(frame+104,acquisition::slack_min);
    put32(frame+108,acquisition::send_previous);put32(frame+112,acquisition::produced);
    if(count) {
        if(acquisition::single()) maxfreq_packing::pack(frame+116,node->single_samples+offset,count,acquisition::bits);
        else maxfreq_packing::pack_dual(frame+116,node->samples+offset,count,acquisition::bits);
    }
}

#if defined(__GNUC__) && !defined(__clang__)
__attribute__((optimize("O2")))
#endif
static void build_samples(uint8_t *frame, acquisition::Node *node, unsigned offset,
                          unsigned count) {
    if(acquisition::native()) { build_native_samples(frame,node,offset,count); return; }
    const bool mega=acquisition::period==133U;
    const bool packed=acquisition::bits==14;
    const bool single=acquisition::single();
    const unsigned used=mega?count:single?count/4*7:packed ? count/2*7 : count*4;
    memset(frame+84+used,0,BLOCK_BYTES-CRC_BYTES-84-used);
    put32(frame + 48, (acquisition::single()?160000000U:1000000U) / acquisition::period);
    put32(frame + 52, node ? node->index * acquisition::node_pairs() + offset : 0);
    put32(frame + 56, acquisition::dropped_nodes);
    put32(frame + 60, acquisition::fatal_errors);
    put16(frame + 64, count); frame[66] = acquisition::bits; frame[67] = acquisition::single()?1:2;
    put32(frame + 68, acquisition::period);
    put32(frame + 72, node ? node->index : 0);
    put32(frame + 76, (acquisition::epoch << 1) | (acquisition::fatal_errors ? 1 : 0));
    put32(frame+80,count ? node->timestamp+offset*acquisition::period : 0);
    if (count) {
        if(mega) {
            for(unsigned i=0;i<count;++i) frame[84+i]=uint8_t(node->samples[offset+i].ch1);
        } else if(single) {
            for(unsigned i=0;i<count;i+=4) {
                const uint32_t a=node->samples[offset+i].ch1,b=node->samples[offset+i+1].ch1,c=node->samples[offset+i+2].ch1,d=node->samples[offset+i+3].ch1;
                const uint32_t lo=a|(b<<14)|((c&15U)<<28),hi=(c>>4)|(d<<10);
                uint8_t *dest=frame+84+i/4*7;put32(dest,lo);dest[4]=uint8_t(hi);dest[5]=uint8_t(hi>>8);dest[6]=uint8_t(hi>>16);
            }
        } else if(packed) {
            for(unsigned i=0;i<count;i+=2) {
                const auto a=node->samples[offset+i],b=node->samples[offset+i+1];
                const uint32_t lo=uint32_t(a.ch1)|(uint32_t(a.ch2)<<14)|(uint32_t(b.ch1&15U)<<28);
                const uint32_t hi=(uint32_t(b.ch1)>>4)|(uint32_t(b.ch2)<<10);
                uint8_t *dest=frame+84+(i/2)*7;put32(dest,lo);
                dest[4]=uint8_t(hi);dest[5]=uint8_t(hi>>8);dest[6]=uint8_t(hi>>16);
            }
        } else memcpy(frame + 84, node->samples + offset, count * sizeof(ChannelPair));
    }
}
static void output_worker(void *, void *, void *) {
    unsigned next_frame=0, spi40_write=0;
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
            if (output_switch.complete(node->index * acquisition::node_pairs(), healthy, applied)) {
                output_mode = applied.active;
                enqueue_reply(applied);
                reply_reserved = false;
            }
        }
        const uint8_t mode = output_mode;
        k_mutex_unlock(&output_lock);
        if (mode == scope_control::UART) {
            if(acquisition::native() || acquisition::single() || acquisition::node_pairs()!=DMA_NODE_PAIRS) {
                acquisition::fail();acquisition::release();continue;
            }
            uint8_t *bytes=reinterpret_cast<uint8_t *>(acquisition::timestampBuffer+UART_TIMESTAMP_WORDS);
            for (unsigned offset = 0; offset < acquisition::node_pairs(); offset += SERIAL_BLOCK_PAIRS) {
                build_uart_samples(bytes,node,offset);
                for (size_t i = 0; i < sizeof(Packet); ++i) uart_poll_out(scope_uart, bytes[i]);
            }
            // uart_poll_out may return with the last byte in the peripheral.
            // APPLIED must follow the last stop bit, not just the final register write.
            while (!uart_irq_tx_complete(scope_uart)) k_yield();
        } else if(word_transport()) {
            for(unsigned offset=0;offset<acquisition::node_pairs();) {
                const unsigned count=min(864U,unsigned(acquisition::node_pairs()-offset));
                k_sem_take(&spi40_free,K_FOREVER);
                auto *frame=frame_slot(spi40_write);
                build_samples(frame->bytes,node,offset,count);
                offset+=count;
                sample_ready[spi40_write]=frame;
                spi40_last[spi40_write]=offset==acquisition::node_pairs();
                spi40_write=(spi40_write+1U)%FRAME_SLOTS;
                k_sem_give(&frame_available);
            }
            // Node remains immutable until its last physical frame completes.
            k_sem_take(&spi40_node_sent,K_FOREVER);
        } else {
            const bool pipelined=high_rate_transport();
            unsigned in_flight=0;
            for (unsigned offset = 0; offset < acquisition::node_pairs();) {
                const unsigned count = min(acquisition::native()?(acquisition::single()?(acquisition::bits==8?864U:acquisition::bits==10?696U:acquisition::bits==12?576U:acquisition::bits==14?496U:436U):acquisition::bits==8?432U:((872U*8U/(acquisition::bits*2U))&~3U)):acquisition::period==133U?904U:acquisition::single()?516U:acquisition::bits==14 ? 258U : 226U, unsigned(acquisition::node_pairs() - offset));
                if(pipelined && in_flight==FRAME_SLOTS) {
                    k_sem_take(&frame_sent,K_FOREVER);--in_flight;
                }
                auto *frame=frame_slot(pipelined?next_frame:0);
                build_samples(frame->bytes,node,offset,count);
                offset+=count;
                if(pipelined) {
                    sample_ready[next_frame]=frame;
                    next_frame=(next_frame+1U)%FRAME_SLOTS;
                    ++in_flight;
                }
                k_sem_give(&frame_available);
                if(!pipelined) k_sem_take(&frame_sent,K_FOREVER);
            }
            while(in_flight) {k_sem_take(&frame_sent,K_FOREVER);--in_flight;}
        }
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
    k_sem_init(&frame_available,0,FRAME_SLOTS);
    k_sem_init(&spi40_free,FRAME_SLOTS,FRAME_SLOTS);
    k_sem_init(&spi40_node_sent,0,1);
    k_sem_init(&frame_sent, 0, FRAME_SLOTS);
    ready = acquisition::start();
    if (ready) k_thread_create(&output_thread_data, output_stack,
        K_THREAD_STACK_SIZEOF(output_stack), output_worker, nullptr, nullptr, nullptr,
        PRIORITY_SERIAL, 0, K_NO_WAIT);
}

#if defined(__GNUC__) && !defined(__clang__)
// Keep the LLEXT load footprint bounded; CRC/validation/packing stay O2.
__attribute__((optimize("Os")))
#endif
void loop() {
    if (!ready) { k_sleep(K_MSEC(100)); return; }
    // The core main thread has a 32 KiB stack outside the sketch arena.
    // These buffers remain alive until exchange stops/resets both DMA channels.
    alignas(CONFIG_DCACHE_LINE_SIZE) uint8_t tx_storage[BLOCK_BYTES],rx_storage[BLOCK_BYTES];
    tx=tx_storage;rx=rx_storage;
    wav::service();
    if ((acquisition::native() || acquisition::period==133U) && acquisition::threads_started &&
        !acquisition::fatal_errors && !acquisition::dropped_nodes &&
        !k_sem_count_get(&frame_available) && !k_msgq_num_used_get(&wav_replies) &&
        !k_msgq_num_used_get(&generator_replies) && !k_msgq_num_used_get(&settings_replies) &&
        !k_msgq_num_used_get(&control_replies)) { if(!high_rate_transport()) k_busy_wait(5); k_yield(); return; }
    scope_wav::Reply wav_reply{};
    scope_control::Reply reply{};
    scope_acq::Reply config_reply{};
    scope_gen::Reply generator_reply{};
    k_mutex_lock(&output_lock, K_FOREVER);
    const bool have_wav = k_msgq_get(&wav_replies, &wav_reply, K_NO_WAIT) == 0;
    const bool have_generator = !have_wav && k_msgq_get(&generator_replies, &generator_reply, K_NO_WAIT) == 0;
    const bool have_config = !have_wav && !have_generator && k_msgq_get(&settings_replies, &config_reply, K_NO_WAIT) == 0;
    const bool have_reply = !have_wav && !have_generator && !have_config && k_msgq_get(&control_replies, &reply, K_NO_WAIT) == 0;
    const bool pipelined=high_rate_transport();
    const bool have_samples = !have_wav && !have_generator && !have_config && !have_reply &&
        k_sem_take(&frame_available,K_NO_WAIT)==0;
    uint8_t *packet=tx;
    const bool word=word_transport();
    bool word_last=false;
    if(have_samples && word) {
        packet=sample_ready[spi40_read]->bytes;
        word_last=spi40_last[spi40_read];
        spi40_read=(spi40_read+1U)%FRAME_SLOTS;
    } else if(have_samples && pipelined) {
        packet=sample_ready[read_frame]->bytes;
        read_frame=(read_frame+1U)%FRAME_SLOTS;
    }
    active_tx=packet;
    uint32_t started = k_cycle_get_32();
    if (have_wav) scope_wav::encode(packet, sequence, wav_reply);
    else if (have_generator) scope_gen::encode(packet, sequence, generator_reply);
    else if (have_config) scope_acq::encode(packet, sequence, config_reply);
    else if (have_reply) scope_control::encode(packet, sequence, reply);
    else {
        data_frame(packet, sequence, last_ping, spi_errors, bad_ping, short_transfers,
                   last_result, last_error, prepare_us, check_us);
        put16(packet + 6, acquisition::native()?20:acquisition::period==133U?19:acquisition::single()?16:acquisition::bits==14 ? 15 : 3);
        if (have_samples && !pipelined) memcpy(packet+48,ordinary_frame.bytes+48,BLOCK_BYTES-48-CRC_BYTES);
        else if(!have_samples) {
            uint8_t idle[BLOCK_BYTES];
            build_samples(idle, nullptr, 0, 0);
            memcpy(packet + 48, idle + 48, BLOCK_BYTES - 48 - CRC_BYTES);
        }
        seal(packet);
    }
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
    } else if (valid_ping(rx)) last_ping = get32(rx + 8);
    else {
        scope_control::Request request{};
        scope_acq::Request config_request{};
        scope_gen::Request generator_request{};
        scope_wav::Request wav_request{};
        if (scope_wav::decode(rx, BLOCK_BYTES, wav_request)) {
            if(k_msgq_num_free_get(&wav_replies)) {
                const auto result=wav::submit(wav_request);
                if(k_msgq_put(&wav_replies,&result,K_NO_WAIT)!=0) { acquisition::fail();ready=false; }
            } else { acquisition::fail();ready=false; }
        } else if (scope_gen::decode(rx, BLOCK_BYTES, generator_request)) {
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
                const auto accepted = request.mode == scope_control::UART && (acquisition::native() || acquisition::single() || acquisition::period < 32) ? scope_control::Reply{
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
    check_us = elapsed_us(started);
    ++sequence;
    // Physical completion acknowledges every fragment. The producer drains all
    // acknowledgements before releasing the node; no reuse after an error.
    if(have_samples && ready) {
        if(word) {
            k_sem_give(&spi40_free);
            if(word_last)k_sem_give(&spi40_node_sent);
        } else k_sem_give(&frame_sent);
    }
    // Never unwind stack-owned DMA buffers after an unsuccessful stop/reset.
    // A failed acquisition already requires the validated board restart path.
    if(!ready) for(;;) k_sleep(K_MSEC(100));
    // Idle status traffic is bounded; SPI remains available during UART output.
    if (!have_wav && !have_generator && !have_config && !have_reply && !have_samples) k_sleep(K_MSEC(1));
}
