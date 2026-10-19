#pragma once
#include <stdint.h>
// Only the accepted ADC8/CH1 1.403508 MHz profile needs the fast transport.
static inline int scope_high_rate(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return bits==8 && channels==1 && ticks==114 && pairs==3456;
}
