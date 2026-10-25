#pragma once
#include "generator_protocol.h"
namespace radio_test {
constexpr unsigned STEP_HZ=25;
constexpr unsigned POINTS=5120;
constexpr unsigned RATE=128000;
static_assert(RATE==POINTS*STEP_HZ,"RADIO TEST table frequency grid");
inline bool valid(const scope_gen::Config &c) { return c.mode==3 && scope_gen::valid(c); }
// One immutable 40-ms table contains integer cycles of every accepted frequency.
// The 256-entry sine LUT retains the normal generator's phase resolution.
__attribute__((always_inline)) inline uint16_t sample_cycles(unsigned i,unsigned first_cycles,
        unsigned second_cycles,unsigned tone_cycles,uint16_t low,uint16_t span,const uint16_t *sine) {
    const unsigned tone_phase=(i*tone_cycles/20)&255;
    const unsigned first_phase=(i*first_cycles/20+64)&255;
    const unsigned second_phase=(i*second_cycles/20+64)&255;
    const int32_t tone=tone_cycles?int32_t(sine[tone_phase])-32768:0;
    const int32_t first=first_cycles?int32_t(sine[first_phase])-32768:0;
    const int32_t second=second_cycles?int32_t(sine[second_phase])-32768:0;
    int32_t unit=32768+(first+second)*(16384+tone/4)/49152;
    if(unit<0)unit=0;if(unit>65535)unit=65535;
    return low+uint16_t((uint32_t(span)*uint32_t(unit)+32767)/65535);
}
inline uint16_t sample(const scope_gen::Config &c,unsigned i,const uint16_t *sine) {
    return sample_cycles(i,c.frequency/(1000*STEP_HZ),c.final_frequency/(1000*STEP_HZ),
                         c.duration/STEP_HZ,c.low,c.high-c.low,sine);
}
#if defined(__GNUC__) && !defined(__clang__)
__attribute__((optimize("O2")))
#endif
inline void fill(const scope_gen::Config &c,uint32_t *output,const uint16_t *sine) {
    const unsigned first=c.frequency/(1000*STEP_HZ),second=c.final_frequency/(1000*STEP_HZ),tone=c.duration/STEP_HZ;
    const uint16_t low=c.low,span=c.high-c.low;
    for(unsigned i=0;i<POINTS;++i)output[i]=sample_cycles(i,first,second,tone,low,span,sine);
}
}
