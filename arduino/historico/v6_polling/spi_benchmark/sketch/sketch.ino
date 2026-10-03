#include <Arduino.h>
#include <Arduino_RouterBridge.h> // Dependencia del core, sin transporte RPC.
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <zephyr/irq.h>
#include <stm32u5xx.h>
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
static uint8_t tx[BLOCK_BYTES], rx[BLOCK_BYTES];
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

// Una sola CPU atiende ambos FIFO. No spi_transceive, ISR SPI, DMA ni irq_lock.
// Las IRQ ajenas a SPI siguen habilitadas; el polling consume CPU incluso ocioso.
static int exchange() {
    fault_sr = 0;
    uint32_t started = k_cycle_get_32();
    // Nunca rearmar a mitad de una selección del maestro.
    while (selected()) {
        if (elapsed_us(started) >= ACTIVE_TIMEOUT_US) return -EBUSY;
    }
    SPI3->CR2 = BLOCK_BYTES;
    SPI3->IFCR = CLEAR_FLAGS;
    SPI3->CR1 = SPI_CR1_SPE;
    __DSB();

    auto *const txdr = reinterpret_cast<volatile uint8_t *>(&SPI3->TXDR);
    auto *const rxdr = reinterpret_cast<volatile uint8_t *>(&SPI3->RXDR);
    size_t sent = 0, received = 0;
    // FIFO físico de 8 bytes. Limitar explícitamente evita sobrellenado.
    while (sent < 8 && (SPI3->SR & SPI_SR_TXP)) *txdr = tx[sent++];
    bool active = false;
    unsigned polls = 0;
    int result = -EIO;
    for (;;) {
        const uint32_t status = SPI3->SR;
        if (status & ERROR_FLAGS) {
            fault_sr = status; // Capturar ANTES de deshabilitar o limpiar.
            break;
        }
        // Tras EOT pueden quedar bytes residuales en FIFO sin RXP: comprobar
        // también los niveles de recepción, igual que el polling de ST.
        if ((status & (SPI_SR_RXP | SPI_SR_RXWNE | SPI_SR_RXPLVL)) && received < BLOCK_BYTES)
            rx[received++] = *rxdr;
        if ((status & SPI_SR_TXP) && sent < BLOCK_BYTES && sent - received < 8)
            *txdr = tx[sent++];
        if (status & SPI_SR_EOT) {
            if (received == BLOCK_BYTES && sent == BLOCK_BYTES) {
                result = BLOCK_BYTES;
                break;
            }
            // EOT no sustituye al drenado de RX. Esperar hasta recibir todo;
            // el timeout inferior limita una transferencia realmente cortada.
        }
        if (!active && (received || selected())) {
            active = true;
            started = k_cycle_get_32();
        }
        // No penalizar cada byte con conversiones de tiempo. Sin timeout ocioso:
        // esperar al maestro no representa un error ni consume secuencias.
        if (active && (++polls & 255U) == 0 && elapsed_us(started) >= ACTIVE_TIMEOUT_US) {
            result = -ETIMEDOUT;
            break;
        }
    }
    stop_spi();
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
        last_error = fault_sr ? -int32_t(0x10000U | (fault_sr & 0xffffU)) : last_result;
        if (last_result == -EMSGSIZE) ++short_transfers;
    } else if (last_result != int(BLOCK_BYTES)) ++short_transfers;
    else if (valid_ping(rx)) last_ping = get32(rx + 8);
    else ++bad_ping;
    check_us = elapsed_us(started);
    ++sequence;
}
