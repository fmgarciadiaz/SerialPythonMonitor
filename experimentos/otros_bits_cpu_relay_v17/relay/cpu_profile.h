#pragma once
#include "high_rate_profile.h"
// Isolated candidate: CPU policy changes, no new ADC rates or SPI clocks.
static inline int scope_cpu_profile(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return scope_spi40(bits,channels,ticks,pairs) || (channels==1 && (
        (bits==10 && ticks==137 && pairs==5568) ||
        (bits==12 && ticks==163 && pairs==4608) ||
        (bits==14 && ticks==188 && pairs==1984)));
}
