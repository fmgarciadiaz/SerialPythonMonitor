#pragma once
#include "benchmark_protocol.h"
struct SampleFrame {
    uint8_t bytes[scope_bench::BLOCK_BYTES] __attribute__((aligned(CONFIG_DCACHE_LINE_SIZE)));
};
