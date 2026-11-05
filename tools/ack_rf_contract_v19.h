#pragma once
// Offline contract only: no accepted firmware includes this file.
#include <cstdint>
#include "wav_queue.h"
#include "batch2_ownership.h"
namespace scope_ack_rf_private {
constexpr unsigned buffering_kind=22,playing_kind=23; // Provisional, not public.
inline bool eligible(const scope_wav::Request &r,const scope_wav::Reply &s,bool duplicate) {
    if(!r.chunk || duplicate || s.reason!=scope_control::OK || r.id!=s.id ||
       r.session!=s.session || !r.session || !scope_control::pc_id(r.id) ||
       !r.count || r.count>scope_wav::POINTS || r.offset%scope_wav::POINTS ||
       r.offset>UINT32_MAX-r.count || s.accepted!=r.offset+r.count ||
       s.accepted>s.total || s.played>s.accepted || s.played%scope_wav::POINTS ||
       (r.count!=scope_wav::POINTS && s.accepted!=s.total)) return false;
    if(s.state!=scope_wav::BUFFERING && s.state!=scope_wav::PLAYING) return false;
    const uint32_t queued=s.accepted-s.played;
    const uint32_t used=queued/scope_wav::POINTS+unsigned(queued%scope_wav::POINTS!=0);
    return used && used<=scope_wav::SLOTS && s.free==scope_wav::SLOTS-used &&
        (s.state!=scope_wav::BUFFERING || !s.played) &&
        (s.state!=scope_wav::PLAYING || used>=3);
}
struct Plan {
    bool take_wav,take_rf,fused;
    scope_batch2::Half half;
};
// An RF token is consumed exactly when take_rf is true. No waiting or lookahead.
// final_node comes from that actual RF frame, never from the ACK.
inline Plan select(bool wav_head,bool combinable,bool other_reply,bool rf_available,
                   bool word,bool pipeline,bool final_node) {
    const bool fused=wav_head && combinable && rf_available;
    const bool reply=(wav_head && !fused) || (!wav_head && other_reply);
    const bool rf=rf_available && !reply;
    return {wav_head,rf,fused,{scope_batch2::select_source(reply,rf,word,pipeline),rf && final_node}};
}
}
