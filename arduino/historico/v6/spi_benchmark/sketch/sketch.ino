#include <Arduino.h>
#include <Arduino_RouterBridge.h> // Dependencia del core; no transporta datos del benchmark.
#include <zephyr/device.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/kernel.h>
#include "benchmark_protocol.h"

#if !defined(CONFIG_SOC_STM32U585XX) || !defined(CONFIG_SPI_SLAVE)
#error "Requiere UNO Q con SPI peripheral habilitado"
#endif

using namespace scope_bench;
static const device *const spi_device = DEVICE_DT_GET(DT_NODELABEL(spi3));
static spi_config config = {}; // Debe conservar dirección/vida útil entre llamadas.
static uint8_t tx[BLOCK_BYTES] __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
static uint8_t rx[BLOCK_BYTES] __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
static spi_buf tx_buf = {tx, sizeof(tx)};
static spi_buf rx_buf = {rx, sizeof(rx)};
static spi_buf_set tx_set = {&tx_buf, 1};
static spi_buf_set rx_set = {&rx_buf, 1};
static uint32_t sequence = 0, last_ping = 0xFFFFFFFFU;
static uint32_t spi_errors = 0, bad_ping = 0, short_transfers = 0;
static int32_t last_result = 0;
static int32_t last_error = 0;
static uint32_t prepare_us = 0, check_us = 0;
static bool ready = false;

void setup() {
    // SPI3 tiene zephyr,deferred-init en el core 1.0.0.
    const int result = device_init(spi_device);
    ready = (result == 0 || result == -EALREADY) && device_is_ready(spi_device);
    config.frequency = 1000000; // En peripheral, el reloj efectivo lo genera Linux.
    config.operation = SPI_OP_MODE_SLAVE | SPI_WORD_SET(8); // Mode 0, MSB first.
    // Driver instalado por interrupciones, sin DMA SPI. No reclama GPDMA/ADC/TIM.
}

void loop() {
    if (!ready) { k_sleep(K_MSEC(100)); return; }
    uint32_t started = k_cycle_get_32();
    data_frame(tx, sequence, last_ping, spi_errors, bad_ping, short_transfers,
               last_result, last_error, prepare_us, check_us);
    prepare_us = k_cyc_to_us_floor32(uint32_t(k_cycle_get_32() - started));
    // Sin tocar tx/rx hasta finalizar. Linux debe transferir exactamente BLOCK_BYTES.
    last_result = spi_transceive(spi_device, &config, &tx_set, &rx_set);
    started = k_cycle_get_32();
    if (last_result < 0) { ++spi_errors; last_error = last_result; }
    else if (last_result != int(BLOCK_BYTES)) ++short_transfers;
    else if (valid_ping(rx)) last_ping = get32(rx + 8);
    else ++bad_ping;
    check_us = k_cyc_to_us_floor32(uint32_t(k_cycle_get_32() - started));
    ++sequence; // También cuenta intentos fallidos: nunca oculta pérdidas.
}
