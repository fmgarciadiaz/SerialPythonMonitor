#pragma once
// Only this experimental header changes between the two physical variants.
static constexpr unsigned SPI_DMA_BYTES = 4;
static_assert(SPI_DMA_BYTES == 1 || SPI_DMA_BYTES == 4, "BYTE or WORD only");
static constexpr uint32_t SPI_DMA_WIDTH = SPI_DMA_BYTES == 4
    ? (2U << DMA_CTR1_SDW_LOG2_Pos) | (2U << DMA_CTR1_DDW_LOG2_Pos) : 0U;
// ES0499: preserve CRCSIZE=7 even while SPI CRC calculation is disabled.
static constexpr uint32_t SPI_FRAME_CONFIG = 7U | (7U << SPI_CFG1_CRCSIZE_Pos) |
    ((SPI_DMA_BYTES == 4 ? 3U : 0U) << SPI_CFG1_FTHLV_Pos);
