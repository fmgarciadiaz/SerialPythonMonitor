#pragma once
#include <stdint.h>
// Exact CH1 profiles with the validated SPI38/FIFO10 pipeline.
static inline int scope_high_rate(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return channels==1 && ((bits==8 && ticks==170 && pairs==3488) || (bits==8 && ticks==128 && pairs==3488) || (bits==8 && ticks==104 && pairs==3488) || (bits==10 && ticks==220 && pairs==5568) || (bits==10 && ticks==171 && pairs==5568) || (bits==10 && ticks==141 && pairs==5568) || (bits==12 && ticks==265 && pairs==7488) || (bits==12 && ticks==208 && pairs==7488) || (bits==12 && ticks==171 && pairs==7488) || (bits==14 && ticks==306 && pairs==5952) || (bits==14 && ticks==235 && pairs==5952) || (bits==14 && ticks==190 && pairs==5952) || (bits==8 && ticks==85 && pairs==3488) || (bits==10 && ticks==119 && pairs==5568) || (bits==12 && ticks==145 && pairs==7488) || (bits==14 && ticks==168 && pairs==5952) || (bits==14 && ticks==166 && pairs==5952) || (bits==14 && ticks==164 && pairs==5952) || (bits==14 && ticks==162 && pairs==5952) || (bits==14 && ticks==160 && pairs==5952) || (bits==8 && ticks==87 && pairs==3488) || (bits==8 && ticks==86 && pairs==3488) || (bits==8 && ticks==84 && pairs==3488) || (bits==10 && ticks==120 && pairs==5568) || (bits==10 && ticks==118 && pairs==5568) || (bits==10 && ticks==116 && pairs==5568) || (bits==12 && ticks==144 && pairs==7488) || (bits==12 && ticks==142 && pairs==7488) || (bits==12 && ticks==140 && pairs==7488) || (bits==14 && ticks==174 && pairs==5952) || (bits==14 && ticks==172 && pairs==5952) || (bits==14 && ticks==170 && pairs==5952) || (bits==8 && ticks==88 && pairs==3488) || (bits==8 && ticks==98 && pairs==3456) || (bits==8 && ticks==96 && pairs==3456) || (bits==8 && ticks==94 && pairs==3456) || (bits==8 && ticks==92 && pairs==3456) || (bits==8 && ticks==90 && pairs==3456) || (bits==8 && ticks==89 && pairs==3456) || (bits==8 && ticks==88 && pairs==3456) || (bits==10 && ticks==126 && pairs==5568) || (bits==10 && ticks==124 && pairs==5568) || (bits==10 && ticks==122 && pairs==5568) || (bits==12 && ticks==148 && pairs==7488) || (bits==12 && ticks==146 && pairs==7488) || (bits==14 && ticks==184 && pairs==5952) || (bits==14 && ticks==180 && pairs==5952) || (bits==14 && ticks==176 && pairs==5952) || (bits==14 && ticks==188 && pairs==5952) ||
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
    return (bits==8 && channels==1 && pairs==3488 && (ticks==170 || ticks==128 || ticks==104)) || (bits==8 && channels==1 && pairs==3488 && (ticks==85)) || (bits==8 && channels==1 && pairs==3488 && (ticks==87 || ticks==86 || ticks==84)) || (bits==8 && channels==1 && ticks==88 && pairs==3488) || (bits==8 && channels==1 && (ticks==88 || ticks==89 || ticks==90 || ticks==92 || ticks==94 || ticks==96 || ticks==98 || ticks==100 || ticks==112) && pairs==3456);
}

static inline unsigned scope_queue_capacity(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return scope_spi40(bits,channels,ticks,pairs)?8U:4U;
}
