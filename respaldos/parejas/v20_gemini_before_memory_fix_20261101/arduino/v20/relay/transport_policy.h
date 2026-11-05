#pragma once
#include "high_rate_profile.h"
// Transport scheduling only. This does not select the CH1 validation fast path.
static inline int scope_fast_transport(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return scope_high_rate(bits,channels,ticks,pairs) ||
        (bits==10 && channels==2 && ticks==308 && pairs==4176);
}
