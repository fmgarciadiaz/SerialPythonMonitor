// Generated from complete physical acceptances. Do not add untested rates.
#pragma once
#include <stdint.h>
typedef struct { uint8_t bits, channels; uint16_t ticks, node_pairs; } ScopeNativeProfile;
#define SCOPE_NATIVE_MAX_NODE 8192U
#define SCOPE_NATIVE_MAX_RESULTS 8192U
#define SCOPE_NATIVE_MAX_DUAL 3584U
#define SCOPE_NATIVE_MAX_SINGLE 8192U
static const ScopeNativeProfile scope_native_profiles[] = {
    {8, 1, 143, 8192},
    {8, 1, 131, 6912},
    {10, 1, 176, 8192},
    {14, 1, 228, 7936},
    {14, 1, 214, 7936},
};
static inline uint32_t scope_native_code(const ScopeNativeProfile *p) {
    return ((uint32_t)p->node_pairs << 16) | p->ticks | (p->channels == 2 ? UINT32_C(0x80000000) : 0);
}
static inline const ScopeNativeProfile *scope_native_find(unsigned bits, uint32_t encoded) {
    for (unsigned i = 0; i < sizeof(scope_native_profiles)/sizeof(scope_native_profiles[0]); ++i)
        if (scope_native_profiles[i].bits == bits && scope_native_code(&scope_native_profiles[i]) == encoded)
            return &scope_native_profiles[i];
    return 0;
}
