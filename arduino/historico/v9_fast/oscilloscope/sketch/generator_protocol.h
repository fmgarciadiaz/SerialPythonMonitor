#pragma once
#include "control_protocol.h"
namespace scope_gen {
using namespace scope_control;
constexpr uint16_t SET_GENERATOR=8, GENERATOR_STATUS=9, GET_GENERATOR=10;
constexpr uint32_t UPDATE_HZ=1000000;
constexpr uint32_t MAX_FREQUENCY_MHZ=20000000;
constexpr uint32_t CONTROL_HZ=2000;
struct Config {
    uint8_t wave, enabled, mode;
    uint32_t frequency, final_frequency;
    uint16_t low, high;
    uint32_t duration;
};
inline Config defaults() { return {0,1,0,2500,2500,0,4095,1000}; }
inline bool equal(const Config &a,const Config &b) {
    return a.wave==b.wave && a.enabled==b.enabled && a.mode==b.mode &&
        a.frequency==b.frequency && a.final_frequency==b.final_frequency &&
        a.low==b.low && a.high==b.high && a.duration==b.duration;
}
inline bool valid(const Config &c) {
    return c.wave<=4 && c.enabled<=1 && c.mode<=2 && c.frequency>=100 && c.frequency<=MAX_FREQUENCY_MHZ &&
        c.final_frequency>=100 && c.final_frequency<=MAX_FREQUENCY_MHZ && c.low<=c.high && c.high<=4095 &&
        c.duration>=1 && c.duration<=600000 && (c.wave!=4 || c.mode==0);
}
inline Config read(const uint8_t *p) {
    return {p[0],p[1],p[2],scope_control::get32(p+4),scope_control::get32(p+8),
        uint16_t(p[12]|uint16_t(p[13])<<8),uint16_t(p[14]|uint16_t(p[15])<<8),scope_control::get32(p+16)};
}
inline void write(uint8_t *p,const Config &c) {
    p[0]=c.wave; p[1]=c.enabled; p[2]=c.mode;
    scope_control::put32(p+4,c.frequency);scope_control::put32(p+8,c.final_frequency);
    p[12]=uint8_t(c.low);p[13]=uint8_t(c.low>>8);p[14]=uint8_t(c.high);p[15]=uint8_t(c.high>>8);
    scope_control::put32(p+16,c.duration);
}
struct Request { uint32_t id; Config config; bool query; };
struct Reply { uint32_t id; uint8_t phase, reason, running; Config active, requested; };
inline bool decode(const uint8_t *p,size_t size,Request &r) {
    if(size!=512 || memcmp(p,"SCP1",4) || p[4]!=2 || p[5] || p[7] ||
        (p[6]!=8 && p[6]!=10) || scope_control::get32(p+12)!=492 || !scope_control::pc_id(scope_control::get32(p+8)) ||
        scope_control::get32(p+508)!=scope_control::crc(p,508)) return false;
    const bool query=p[6]==10;
    if(!query && p[19]) return false;
    for(unsigned i=query?16:36;i<508;++i) if(p[i]) return false;
    r={scope_control::get32(p+8),query?defaults():read(p+16),query};return true;
}
inline void encode(uint8_t *p,uint32_t seq,const Reply &r) {
    memset(p,0,512);memcpy(p,"SCP1",4);p[4]=2;p[6]=9;scope_control::put32(p+8,seq);scope_control::put32(p+12,492);
    scope_control::put32(p+16,r.id);p[20]=r.phase;p[21]=r.reason;p[22]=r.running;
    write(p+24,r.active);write(p+44,r.requested);scope_control::put32(p+508,scope_control::crc(p,508));
}
}
