#pragma once
#include <stdint.h>
// Exact CH1 profiles with the validated SPI38/FIFO10 pipeline.
static inline int scope_high_rate(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return channels==1 && ((bits==8 && ticks==98 && pairs==3456) || (bits==10 && ticks==124 && pairs==5568) || (bits==12 && ticks==146 && pairs==7488) || (bits==14 && ticks==176 && pairs==5952) || (bits==14 && ticks==188 && pairs==5952) ||
        (bits==10 && ticks==128 && pairs==5568) ||
        (bits==12 && ticks==150 && pairs==7488) ||
        (bits==8 && (ticks==114 || ticks==100 || ticks==112) && pairs==3456) ||
        (bits==10 && ticks==137 && pairs==5568) ||
        (bits==10 && ticks==140 && pairs==2784) ||
        (bits==12 && ticks==163 && pairs==4608) ||
        (bits==12 && ticks==172 && pairs==4608) ||
        (bits==14 && ticks==188 && pairs==1984) ||
        (bits==14 && ticks==192 && pairs==1984));
}

// ADC8/CH1 1600k and its private warm-up share the SPI40/WORD recipe.
static inline int scope_spi40(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return bits==8 && channels==1 && (ticks==98 || ticks==100 || ticks==112) && pairs==3456;
}

static inline unsigned scope_queue_capacity(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return scope_spi40(bits,channels,ticks,pairs)?8U:4U;
}
