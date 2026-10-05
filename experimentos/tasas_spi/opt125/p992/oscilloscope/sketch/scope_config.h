#pragma once
#include <Arduino.h>
#include <zephyr/kernel.h>

// Firmware V9 SPI experimental: Arduino Core Zephyr 1.0.0, UNO Q / STM32U585.
// Recursos exclusivos: ADC1, TIM2, TIM5, GPDMA1 canales 0/1 (ADC), 4 (DAC), TIM6, A2/A3 (ADC), A0 (DAC0), DAC1 canal 1, Serial1.
// No usar analogRead() ni otros drivers sobre esos periféricos durante adquisición.
#if !defined(CONFIG_SOC_STM32U585XX)
#error "Este firmware requiere el STM32U585 del UNO Q"
#endif

constexpr auto DAC_OUTPUT = DAC0;
constexpr uint16_t DAC_MAXIMUM = 4095U;
constexpr auto ADC_IN_PIN = A2;
constexpr auto ADC_OUT_PIN = A3;
constexpr uint32_t SAMPLE_RATE_HZ = 31250U; // 32 us exactos con base de 1 MHz.
constexpr uint32_t TOGGLE_PERIOD_MS = 200U;
constexpr uint32_t SERIAL_BAUD = 3000000U;
constexpr uint32_t DMA_NODE_PAIRS = 2048U; // 65.536 ms por nodo a 31.25 kHz
constexpr uint32_t DMA_NODE_RESULTS = DMA_NODE_PAIRS * 2U;
constexpr uint32_t DMA_NODE_BYTES = DMA_NODE_RESULTS * sizeof(uint16_t);
constexpr uint32_t DMA_TIMESTAMP_NODE_BYTES = DMA_NODE_PAIRS * sizeof(uint32_t);
constexpr uint32_t DMA_NODE_COUNT = 2U;
constexpr uint32_t DMA_BUFFER_RESULTS = DMA_NODE_RESULTS * DMA_NODE_COUNT;
constexpr uint16_t SERIAL_BLOCK_PAIRS = 512U;
constexpr int PRIORITY_TOGGLE = 6;
constexpr int PRIORITY_SERIAL = 7;
constexpr uint32_t DMA_POLL_MS = 1U;
// TIM2 y TIM5 a 1 MHz: disparo cada 32 ticks, timestamps en microsegundos.
constexpr uint32_t TIMER_CLOCK_HZ = 160000000U;
constexpr uint32_t SAMPLE_PERIOD_US = 1000000U / SAMPLE_RATE_HZ;
constexpr uint32_t TIM2_PRESCALER = TIMER_CLOCK_HZ / 1000000U - 1U;
constexpr uint32_t TIM2_AUTORELOAD = SAMPLE_PERIOD_US - 1U;
constexpr uint32_t TIM5_PRESCALER = TIMER_CLOCK_HZ / 1000000U - 1U;

static_assert(CONFIG_SYS_CLOCK_HW_CYCLES_PER_SEC == 160000000U,
              "Revisar el reloj TIM2/TIM5 si cambia la plataforma");
static_assert(1000000U % SAMPLE_RATE_HZ == 0U, "Periodo debe ser entero en us");
static_assert(TIMER_CLOCK_HZ % 1000000U == 0U, "TIM5 debe conservar ticks de 1 us");
static_assert(DMA_NODE_PAIRS % SERIAL_BLOCK_PAIRS == 0U, "Paquetes completos por nodo");
static_assert(DMA_NODE_COUNT == 2U, "Consumidor ping-pong");
static_assert(DMA_NODE_BYTES % CONFIG_DCACHE_LINE_SIZE == 0U, "Alineacion cache ADC");
static_assert(DMA_TIMESTAMP_NODE_BYTES % CONFIG_DCACHE_LINE_SIZE == 0U, "Alineacion cache tiempo");

// UART 8N1: 10 bits por byte, incluida la cabecera de cada paquete.
constexpr uint32_t SERIAL_REQUIRED_BPS =
    (uint64_t(SAMPLE_RATE_HZ) * (7U + 8U * SERIAL_BLOCK_PAIRS) * 10U
     + SERIAL_BLOCK_PAIRS - 1U) / SERIAL_BLOCK_PAIRS;
static_assert(SERIAL_REQUIRED_BPS < SERIAL_BAUD, "El enlace no alcanza para esta Fs");
