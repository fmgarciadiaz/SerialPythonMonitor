#pragma once
#include "generator_protocol.h"
namespace generator {
struct Timing { uint16_t prescaler, reload; };
constexpr uint32_t DAC_TIMER_HZ=160000000;
inline unsigned points_for(const scope_gen::Config &c) {
    if(c.wave==0) return c.duty==50?2:unsigned(c.frequency<=10000000?100:uint64_t(scope_gen::UPDATE_HZ)*1000/c.frequency);
    uint32_t maximum=c.mode && c.final_frequency>c.frequency?c.final_frequency:c.frequency;
    // Preserve existing <=50 kHz tables exactly. High sine uses the largest
    // integer point count within the existing DAC update budget.
    if(maximum>50000000U && c.wave==1)
        return unsigned(uint64_t(scope_gen::UPDATE_HZ)*1000/maximum);
    unsigned points=256;
    while(uint64_t(maximum)*points>uint64_t(scope_gen::UPDATE_HZ)*1000 && points>16) points/=2;
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
