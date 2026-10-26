// Generated from complete physical acceptances. Do not add untested rates.
#pragma once
#include <stdint.h>
typedef struct { uint8_t bits, channels; uint16_t ticks, node_pairs; } ScopeNativeProfile;
#define SCOPE_NATIVE_MAX_NODE 8192U
#define SCOPE_NATIVE_MAX_RESULTS 8352U
#define SCOPE_NATIVE_MAX_DUAL 4176U
#define SCOPE_NATIVE_MAX_SINGLE 8192U
static const ScopeNativeProfile scope_native_profiles[] = {
    {8, 1, 100, 3456},
    {8, 1, 112, 3456},
    {8, 1, 114, 3456},
    {8, 1, 143, 8192},
    {8, 1, 131, 6912},
    {10, 1, 176, 8192},
    {14, 1, 228, 7936},
    {14, 1, 214, 7936},
    {8, 2, 268, 3456},
    {8, 2, 253, 3888},
    {10, 2, 323, 4176},
    {10, 2, 308, 4176},
    {12, 2, 390, 4032},
    {12, 2, 366, 4032},
    {14, 2, 450, 1984},
    {14, 2, 440, 3968},
    {16, 2, 2099, 3456},
    {10, 1, 137, 5568},
    {10, 1, 140, 2784},
    {12, 1, 163, 4608},
    {12, 1, 172, 4608},
    {14, 1, 188, 1984},
    {14, 1, 192, 1984},
    // Isolated unmeasured candidates; not public rates.
    {10, 1, 128, 5568},
    {12, 1, 150, 7488},

    {14, 1, 188, 5952},

// Private screening candidates.
    {16, 1, 2000, 3488},
    {8, 1, 98, 3456},
    {8, 1, 96, 3456},
    {8, 1, 94, 3456},
    {8, 1, 92, 3456},
    {8, 1, 90, 3456},
    {8, 1, 89, 3456},
    {8, 1, 88, 3456},
    {10, 1, 126, 5568},
    {10, 1, 124, 5568},
    {10, 1, 122, 5568},
    {12, 1, 148, 7488},
    {12, 1, 146, 7488},
    {14, 1, 184, 5952},
    {14, 1, 180, 5952},
    {14, 1, 176, 5952},
    {16, 1, 1100, 3488},

    {8, 1, 88, 3488},
// ADC16 private staircase: same oversampling and clock.
    {16, 1, 1080, 3488},
    {16, 1, 1060, 3488},
    {16, 1, 1048, 3488},
    {16, 2, 2090, 3456},
    {16, 2, 2088, 3456},
    {16, 2, 2086, 3456},

// Private rate-only staircase.
    {8, 1, 87, 3488},
    {8, 1, 86, 3488},
    {8, 1, 84, 3488},
    {10, 1, 120, 5568},
    {10, 1, 118, 5568},
    {10, 1, 116, 5568},
    {12, 1, 144, 7488},
    {12, 1, 142, 7488},
    {12, 1, 140, 7488},
    {14, 1, 174, 5952},
    {14, 1, 172, 5952},
    {14, 1, 170, 5952},

};
static inline uint32_t scope_native_code(const ScopeNativeProfile *p) {
    return ((uint32_t)p->node_pairs << 16) | p->ticks | (p->channels == 2 ? UINT32_C(0x80000000) : 0);
}
#include "additional_profiles.h"
static inline const ScopeNativeProfile *scope_native_find(unsigned bits, uint32_t encoded) {
    for (unsigned i = 0; i < sizeof(scope_native_profiles)/sizeof(scope_native_profiles[0]); ++i)
        if (scope_native_profiles[i].bits == bits && scope_native_code(&scope_native_profiles[i]) == encoded)
            return &scope_native_profiles[i];
    for (unsigned i = 0; i < sizeof(scope_additional_profiles)/sizeof(scope_additional_profiles[0]); ++i)
        if (scope_additional_profiles[i].bits == bits && scope_native_code(&scope_additional_profiles[i]) == encoded)
            return &scope_additional_profiles[i];
    return 0;
}
