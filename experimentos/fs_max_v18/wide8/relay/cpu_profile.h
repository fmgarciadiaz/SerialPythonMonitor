#pragma once
#include "high_rate_profile.h"
// Isolated candidate: CPU policy changes, no new ADC rates or SPI clocks.
static inline int scope_cpu_profile(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {
    return (bits==8 && channels==1 && ticks==88 && pairs==6912) || (channels==1 && ((bits==16 && ticks==2000 && pairs==3488) || (bits==8 && ticks==98 && pairs==3456) || (bits==8 && ticks==96 && pairs==3456) || (bits==8 && ticks==94 && pairs==3456) || (bits==8 && ticks==92 && pairs==3456) || (bits==8 && ticks==90 && pairs==3456) || (bits==8 && ticks==89 && pairs==3456) || (bits==8 && ticks==88 && pairs==3456) || (bits==10 && ticks==126 && pairs==5568) || (bits==10 && ticks==124 && pairs==5568) || (bits==10 && ticks==122 && pairs==5568) || (bits==12 && ticks==148 && pairs==7488) || (bits==12 && ticks==146 && pairs==7488) || (bits==14 && ticks==184 && pairs==5952) || (bits==14 && ticks==180 && pairs==5952) || (bits==14 && ticks==176 && pairs==5952) || (bits==16 && ticks==1100 && pairs==3488))) || (bits==14 && channels==1 && ticks==188 && pairs==5952) || scope_spi40(bits,channels,ticks,pairs) || (channels==1 && (
        (bits==14 && (ticks==188 || ticks==192) && pairs==1984) ||
        (bits==10 && ticks==128 && pairs==5568) ||
        (bits==12 && ticks==150 && pairs==7488) ||
        (bits==10 && ticks==137 && pairs==5568) ||
        (bits==12 && ticks==163 && pairs==4608)));
}
