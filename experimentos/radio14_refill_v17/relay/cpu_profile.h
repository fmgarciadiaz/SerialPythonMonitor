#pragma once
#include "high_rate_profile.h"
// Isolated candidate: CPU policy changes, no new ADC rates or SPI clocks.
static inline int scope_cpu_profile(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return scope_spi40(bits,channels,ticks,pairs) || (channels==1 && (
        (bits==14 && (ticks==188 || ticks==192) && pairs==1984) ||
        (bits==10 && ticks==128 && pairs==5568) ||
        (bits==12 && ticks==150 && pairs==7488) ||
        (bits==10 && ticks==137 && pairs==5568) ||
        (bits==12 && ticks==163 && pairs==4608)));
}
