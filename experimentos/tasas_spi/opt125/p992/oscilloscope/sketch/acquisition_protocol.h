#pragma once
#include "control_protocol.h"
namespace scope_acq {
using namespace scope_control;
constexpr uint16_t SET_ACQUISITION=6, ACQUISITION_STATUS=7;
inline bool valid(uint8_t bits,uint32_t period) {
    if (bits!=8 && bits!=10 && bits!=12 && bits!=14 && bits!=16) return false;
    if (bits==16 && period<20) return false;
    switch(period) { case 4: case 5: case 8: case 10: case 16: case 20: case 25: case 32: case 40: case 50: case 64: case 80: case 100:
        case 125: case 200: case 250: case 500: case 1000: return true; }
    return false;
}
struct Request { uint32_t id; uint8_t bits; uint32_t period; };
struct Reply { uint32_t id; uint8_t requested, active, phase, reason;
    uint32_t requested_period, active_period, epoch; };
inline bool decode(const uint8_t *p,size_t size,Request &r) {
    if(size!=992 || memcmp(p,"SCP1",4) || p[4]!=3 || p[5] || p[6]!=6 || p[7] ||
       get32(p+12)!=972 || !pc_id(get32(p+8)) || get32(p+988)!=crc(p,988)) return false;
    if(p[17] || p[18] || p[19]) return false;
    for(unsigned i=24;i<988;++i) if(p[i]) return false;
    r={get32(p+8),p[16],get32(p+20)}; return true;
}
inline void encode(uint8_t *p,uint32_t seq,const Reply &r) {
    memset(p,0,992); memcpy(p,"SCP1",4); p[4]=3; p[6]=7;
    put32(p+8,seq); put32(p+12,972); put32(p+16,r.id);
    p[20]=r.requested; p[21]=r.active; p[22]=r.phase; p[23]=r.reason;
    put32(p+24,r.requested_period); put32(p+28,r.active_period); put32(p+32,r.epoch);
    put32(p+988,crc(p,988));
}
class Settings {
    Reply last_{0,14,14,APPLIED,OK,32,32,0};
    bool have_=false,pending_=false;
public:
    bool pending() const { return pending_; }
    Request requested() const { return {last_.id,last_.requested,last_.requested_period}; }
    Reply submit(Request r,bool available) {
        if(have_ && last_.id==r.id) {
            if(last_.requested==r.bits && last_.requested_period==r.period) return last_;
            return {r.id,r.bits,last_.active,REJECTED,ID_CONFLICT,r.period,last_.active_period,last_.epoch};
        }
        if(pending_ || !available)
            return {r.id,r.bits,last_.active,REJECTED,BUSY,r.period,last_.active_period,last_.epoch};
        have_=true;
        last_={r.id,r.bits,last_.active,ACCEPTED,OK,r.period,last_.active_period,last_.epoch};
        if(!valid(r.bits,r.period)) { last_.phase=REJECTED; last_.reason=UNSUPPORTED; }
        else pending_=true;
        return last_;
    }
    Reply complete(bool ok) {
        pending_=false;
        last_.phase=ok?APPLIED:REJECTED; last_.reason=ok?OK:HARDWARE;
        if(ok) { last_.active=last_.requested; last_.active_period=last_.requested_period;
            last_.epoch=(last_.epoch+1)&0x7fffffffU; }
        return last_;
    }
};
}
