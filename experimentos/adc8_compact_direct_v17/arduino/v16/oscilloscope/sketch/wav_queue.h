#pragma once
#include "wav_protocol.h"
// Monotonic sample positions establish ownership independently of modulo slot indices.
// Completed DMA blocks are released only after hardware has moved to another source.
namespace wav {
struct Queue {
    uint32_t session=0,total=0,accepted=0,played=0;
    unsigned head=0,tail=0,used=0;
    uint16_t lengths[scope_wav::SLOTS]{};
    uint8_t state=scope_wav::IDLE;
    void begin(uint32_t sid,uint32_t n) { *this=Queue{};session=sid;total=n;state=scope_wav::BUFFERING; }
    unsigned free() const { return scope_wav::SLOTS-used; }
    bool accepts(uint32_t offset,unsigned n) const {
        return (state==scope_wav::BUFFERING || state==scope_wav::PLAYING) && free() &&
            offset==accepted && accepted<total && n && n<=scope_wav::POINTS && n<=total-accepted &&
            (n==scope_wav::POINTS || n==total-accepted) &&
            (state!=scope_wav::PLAYING || used>=2);
    }
    void publish(unsigned n) { lengths[tail]=n;tail=(tail+1)%scope_wav::SLOTS;++used;accepted+=n; }
    void release() { played+=lengths[head];lengths[head]=0;head=(head+1)%scope_wav::SLOTS;--used; }
    bool ready() const { return used>=4 || (used && accepted==total); }
    bool guarded() const { return used<=1 && accepted<total; }
};
}
