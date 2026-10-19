#pragma once
#include "profile_config.h"
namespace stage_profile {
enum Stage { CACHE, VALIDATE_COPY, PACK, BUILD_FRAME, FRAME_FREE_WAIT, SEAL,
             EXCHANGE_SETUP, READY_TO_DONE, EXCHANGE_CLEANUP, RX_CHECK, PROBE, STAGES };
struct Stats { uint32_t count, sum, maximum; };
static Stats values[STAGES]{};
static inline uint32_t begin() { return SCOPE_STAGE_PROFILE ? k_cycle_get_32() : 0; }
static inline void end(Stage stage, uint32_t started) {
    if (!SCOPE_STAGE_PROFILE) return;
    const uint32_t elapsed = k_cycle_get_32() - started;
    const unsigned key = irq_lock();
    auto &s = values[stage];
    ++s.count; s.sum += elapsed; if (elapsed > s.maximum) s.maximum = elapsed;
    irq_unlock(key);
}
// Preserve frame size, padding, CRC32 and every acquisition/error field.
// Only the experimental DATA timing slots at40/44 carry a tagged snapshot.
static inline void emit(uint8_t *p) {
    if (!SCOPE_STAGE_PROFILE) return;
    static unsigned tag = 0;
    static Stats snapshot{};
    const unsigned field = tag % 3, stage = tag / 3;
    if (!field) {
        const unsigned key = irq_lock(); snapshot = values[stage]; irq_unlock(key);
    }
    scope_bench::put32(p + 40, 0xd17a0000U | tag);
    scope_bench::put32(p + 44, field == 0 ? snapshot.count : field == 1 ? snapshot.sum : snapshot.maximum);
    tag = (tag + 1) % (STAGES * 3);
}
}
