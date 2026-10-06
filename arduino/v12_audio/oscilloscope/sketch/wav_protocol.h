#pragma once
#include "control_protocol.h"
namespace scope_wav {
constexpr uint8_t COMMAND=11, STATUS=12, CHUNK=13;
constexpr unsigned POINTS=480, SLOTS=16;
constexpr uint32_t RATE=20000;
static uint32_t active_rate=RATE;
inline bool valid_rate(uint32_t n) { return n==20000 || n==40000 || n==50000; }
enum Op : uint8_t { QUERY=0, BEGIN=1, PLAY=2, STOP=3 };
enum State : uint8_t { IDLE=0, BUFFERING=1, PLAYING=2, DONE=3, UNDERRUN=4, FAULT=5 };
struct Request { uint32_t id, session, offset, total, fingerprint; uint16_t count; uint8_t op; bool chunk; const uint8_t *samples; uint32_t rate; };
struct Reply { uint32_t id, session; uint8_t state, reason; uint16_t free; uint32_t accepted, played, total; };
inline uint16_t get16(const uint8_t *p) { return uint16_t(p[0])|uint16_t(p[1])<<8; }
inline bool decode(const uint8_t *p,size_t size,Request &r) {
    if(size!=scope_control::BLOCK || memcmp(p,"SCP1",4) || p[4]!=3 || p[5] || p[7] ||
       (p[6]!=COMMAND && p[6]!=CHUNK) || scope_control::get32(p+12)!=972 ||
       !scope_control::pc_id(scope_control::get32(p+8)) || scope_control::get32(p+988)!=scope_control::crc(p,988)) return false;
    const bool chunk=p[6]==CHUNK;
    const unsigned count=chunk?get16(p+24):0;
    if(chunk && (!count || count>POINTS || p[26] || p[27])) return false;
    if(!chunk && (p[21] || p[22] || p[23])) return false;
    for(unsigned i=chunk?28+count*2:(p[20]==BEGIN?32:28);i<988;++i) if(p[i]) return false;
    r={scope_control::get32(p+8),scope_control::get32(p+16),chunk?scope_control::get32(p+20):0,chunk?0:scope_control::get32(p+24),
       scope_control::get32(p+988),uint16_t(count),chunk?uint8_t(0):p[20],chunk,p+28,(!chunk && p[20]==BEGIN)?scope_control::get32(p+28):0};
    return true;
}
inline void encode(uint8_t *p,uint32_t seq,const Reply &r) {
    memset(p,0,scope_control::BLOCK);memcpy(p,"SCP1",4);p[4]=3;p[6]=STATUS;scope_control::put32(p+8,seq);scope_control::put32(p+12,972);
    scope_control::put32(p+16,r.id);scope_control::put32(p+20,r.session);p[24]=r.state;p[25]=r.reason;
    p[26]=uint8_t(r.free);p[27]=uint8_t(r.free>>8);scope_control::put32(p+28,r.accepted);
    scope_control::put32(p+32,r.played);scope_control::put32(p+36,r.total);scope_control::put32(p+40,active_rate);scope_control::put32(p+44,7);scope_control::put32(p+988,scope_control::crc(p,988));
}
}
