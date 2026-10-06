#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

// Experimental V7 dual control contract; V6 ADC/V8 keep their fixed-SPI contract.
namespace scope_control {
constexpr size_t BLOCK = 512;
enum : uint16_t { SET_TRANSPORT = 4, TRANSPORT_STATUS = 5 };
enum Mode : uint8_t { SPI = 0, UART = 1 };
enum Phase : uint8_t { ACCEPTED = 1, APPLIED = 2, REJECTED = 3 };
enum Reason : uint8_t { OK = 0, UNSUPPORTED = 1, BUSY = 2, ID_CONFLICT = 3, HARDWARE = 4 };
inline uint32_t get32(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1])<<8 | uint32_t(p[2])<<16 | uint32_t(p[3])<<24;
}
inline void put32(uint8_t *p, uint32_t n) {
    for (unsigned i=0;i<4;++i) p[i]=uint8_t(n>>(8*i));
}
inline uint32_t crc(const uint8_t *p,size_t n) {
    uint32_t c=0xffffffffU;
    for(size_t i=0;i<n;++i) {
        c^=p[i];
        for(unsigned b=0;b<8;++b) c=(c>>1)^((c&1)?0xedb88320U:0);
    }
    return c^0xffffffffU;
}
inline bool pc_id(uint32_t id) { return id>=0x80000000U && id!=0xffffffffU; }
struct Request { uint32_t id; uint8_t mode; };
struct Reply { uint32_t id; uint8_t requested, active, phase, reason; uint32_t boundary; };
inline bool decode(const uint8_t *p, size_t size, Request &r) {
    if(size!=BLOCK || memcmp(p,"SCP1",4) || p[4]!=2 || p[5] ||
       p[6]!=SET_TRANSPORT || p[7] || get32(p+12)!=492 ||
       get32(p+508)!=crc(p,508) || !pc_id(get32(p+8))) return false;
    for(size_t i=17;i<508;++i) if(p[i]) return false;
    r={get32(p+8),p[16]}; return true;
}
inline void encode(uint8_t *p,uint32_t sequence,const Reply &r) {
    memset(p,0,BLOCK); memcpy(p,"SCP1",4); p[4]=2; p[6]=TRANSPORT_STATUS;
    put32(p+8,sequence); put32(p+12,492); put32(p+16,r.id);
    p[20]=r.requested; p[21]=r.active; p[22]=r.phase; p[23]=r.reason;
    put32(p+24,r.boundary); put32(p+508,crc(p,508));
}
// One command in flight. Call complete() only after the hardware output has
// changed at a full-node boundary. This class never changes peripherals itself.
class Switch {
    uint8_t active_=SPI;
    bool have_=false, pending_=false;
    Reply last_{};
public:
    bool pending() const { return pending_; }
    Reply submit(Request r) {
        if(have_ && r.id==last_.id) {
            if(r.mode==last_.requested) return last_; // immediate retry is idempotent
            return {r.id,r.mode,active_,REJECTED,ID_CONFLICT,0};
        }
        if(pending_) return {r.id,r.mode,active_,REJECTED,BUSY,0};
        have_=true;
        last_={r.id,r.mode,active_,ACCEPTED,OK,0};
        if(r.mode>UART) { last_.phase=REJECTED; last_.reason=UNSUPPORTED; }
        else pending_=true;
        return last_;
    }
    bool complete(uint32_t next_index,bool hardware_ok,Reply &out) {
        if(!pending_ || next_index%2048) return false;
        pending_=false;
        if(hardware_ok) { active_=last_.requested; last_.phase=APPLIED; }
        else { last_.phase=REJECTED; last_.reason=HARDWARE; }
        last_.active=active_; last_.boundary=next_index; out=last_; return true;
    }
};
} // namespace scope_control
