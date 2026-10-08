#pragma once
#include "generator_protocol.h"
namespace generator {
struct Timing { uint16_t prescaler, reload; };
constexpr uint32_t DAC_TIMER_HZ=160000000;
inline unsigned points_for(const scope_gen::Config &c) {
    if(c.wave==0) return 2;
    uint32_t maximum=c.mode && c.final_frequency>c.frequency?c.final_frequency:c.frequency;
    unsigned points=256;
    while(uint64_t(maximum)*points>uint64_t(scope_gen::UPDATE_HZ)*1000 && points>32) points/=2;
    return points;
}
inline Timing timing(uint32_t frequency,unsigned points) {
    const uint64_t rate=uint64_t(frequency)*points;
    const uint64_t divisor=(uint64_t(DAC_TIMER_HZ)*1000+rate/2)/rate;
    const uint32_t prescaler=uint32_t((divisor+65535)/65536);
    uint32_t reload=uint32_t((divisor+prescaler/2)/prescaler);
    if(reload>65536) reload=65536;
    return {uint16_t(prescaler-1),uint16_t(reload-1)};
}
}
