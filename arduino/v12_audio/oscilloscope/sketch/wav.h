#pragma once
#include "wav_queue.h"
#ifndef WAV_TEST
#include "wav_dma.h"
#endif
namespace wav {
static Queue queue;
static scope_gen::Config saved=scope_gen::defaults();
static bool owned=false, restore_pending=false;
static uint32_t last_id=0,last_fingerprint=0;
static uint8_t last_reason=scope_control::OK;
static void finish(uint8_t state) {
    const bool ok=generator_hw::stop(2048);
    wav_hw::clear_underrun();
    queue.state=ok?state:scope_wav::FAULT;
    if(state==scope_wav::DONE) restore_pending=true;
}
static void poll() {
    if(queue.state!=scope_wav::PLAYING) return;
    if(wav_hw::errors()) { finish(scope_wav::FAULT);return; }
    const int current=wav_hw::current();
    if(current==-1) return; // Initial DMA linked-list load has not received its first request.
    if(current==-2) {
        // Every unfilled descriptor and the EOF successor is a finite neutral
        // guard. Hardware therefore cannot wrap into old waveform data even if
        // supervision is delayed. Guard arrival proves all preceding queued data
        // was transferred; EOF and starvation remain distinct outcomes.
        if(queue.accepted==queue.total) {
            while(queue.used) { wav_hw::descriptor(queue.head,true);queue.release(); }
            finish(scope_wav::DONE);
        } else finish(scope_wav::UNDERRUN);
        return;
    }
    unsigned distance=(unsigned(current)+scope_wav::SLOTS-queue.head)%scope_wav::SLOTS;
    if(distance>=queue.used) { finish(scope_wav::FAULT);return; }
    while(distance--) {
        wav_hw::descriptor(queue.head,true);
        queue.release();
    }
    if(!generator_hw::healthy()) { finish(scope_wav::FAULT);return; }
    if(queue.guarded()) finish(scope_wav::UNDERRUN);
}
static scope_wav::Reply reply(uint32_t id,uint8_t reason=scope_control::OK) {
    return {id,queue.session,queue.state,reason,uint16_t(queue.free()),queue.accepted,queue.played,queue.total};
}
// Main loop owns restoration; preparing the prior waveform uses floating point
// and must never run in the timer callback. Errors retain neutral until Stop.
static void service() {
    if(!restore_pending) return;
    const unsigned key=irq_lock();
    restore_pending=false;generator::external_tick=nullptr;owned=false;
    irq_unlock(key);
    if(!generator::apply(saved)) queue.state=scope_wav::FAULT;
}
static scope_wav::Reply submit(const scope_wav::Request &r) {
    const unsigned key=irq_lock();
    poll();
    if(r.id==last_id) {
        const auto result=reply(r.id,r.fingerprint==last_fingerprint?last_reason:scope_control::ID_CONFLICT);
        irq_unlock(key);return result;
    }
    uint8_t reason=scope_control::OK;
    if(r.chunk) {
        if(r.session!=queue.session || !queue.accepts(r.offset,r.count)) reason=scope_control::BUSY;
        else {
            for(unsigned i=0;i<r.count;++i) if(scope_wav::get16(r.samples+2*i)>4095) reason=scope_control::UNSUPPORTED;
            if(reason==scope_control::OK) {
                wav_hw::publish(queue.tail,r.samples,r.count,queue.accepted+r.count==queue.total);
                queue.publish(r.count);
            }
        }
    } else if(r.op==scope_wav::QUERY) {
        if(r.session && r.session!=queue.session) reason=scope_control::ID_CONFLICT;
    } else if(r.op==scope_wav::BEGIN) {
        if(!r.session || !r.total || (r.rate && !scope_wav::valid_rate(r.rate))) reason=scope_control::UNSUPPORTED;
        else if(queue.state==scope_wav::PLAYING || queue.state==scope_wav::BUFFERING) reason=scope_control::BUSY;
        else {
            if(!owned) { saved=generator::active;if(!generator::running) saved.enabled=0; }
            generator::running=false;generator::external_tick=poll;owned=true;restore_pending=false;
            if(!wav_hw::prepare()) { queue.state=scope_wav::FAULT;reason=scope_control::HARDWARE; }
            else { scope_wav::active_rate=r.rate?r.rate:scope_wav::RATE;queue.begin(r.session,r.total); }
        }
    } else if(r.op==scope_wav::PLAY) {
        if(r.session!=queue.session || queue.state!=scope_wav::BUFFERING || !queue.ready()) reason=scope_control::BUSY;
        else if(!wav_hw::start(queue.head)) { queue.state=scope_wav::FAULT;reason=scope_control::HARDWARE; }
        else queue.state=scope_wav::PLAYING;
    } else if(r.op==scope_wav::STOP) {
        if(r.session!=queue.session) reason=scope_control::ID_CONFLICT;
        else if(owned) { finish(scope_wav::IDLE);restore_pending=true; }
    } else reason=scope_control::UNSUPPORTED;
    last_id=r.id;last_fingerprint=r.fingerprint;last_reason=reason;
    const auto result=reply(r.id,reason);
    irq_unlock(key);return result;
}
}
