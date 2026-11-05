#pragma once
#include <cstddef>
#include <cstdint>

#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "SPI16 direct byte buffers require a little-endian MCU"
#endif

namespace scope_spi16 {
constexpr uint32_t data_size_field = 15U; // DSIZE=16 bits.
constexpr uint32_t crc_size_field = 15U;  // Valid even while CRC is disabled.
constexpr size_t physical_bytes = 2U * 992U;
constexpr int logical_result(int physical_result) {
    return physical_result == int(physical_bytes) ? 992 : physical_result;
}
constexpr uint32_t transfer_words(size_t bytes) { return uint32_t(bytes / 2U); }
constexpr unsigned dma_bytes(bool high_rate_word) { return high_rate_word ? 4U : 2U; }
constexpr uint32_t fifo_threshold_field(bool high_rate_word) {
    return high_rate_word ? 1U : 0U; // FTHLV: two or one 16-bit frames.
}
static_assert(992U % 4U == 0U, "SCP frame must suit both DMA access widths");
static_assert(transfer_words(physical_bytes) == 992U && transfer_words(physical_bytes) <= 1023U,
              "Two SCP frames must fit SPI3 TSIZE");
static_assert(dma_bytes(false) == 2U && dma_bytes(true) == 4U,
              "Normal and high-rate GPDMA access widths");
static_assert(fifo_threshold_field(false) == 0U && fifo_threshold_field(true) == 1U,
              "FIFO thresholds match one and two halfwords");
}
