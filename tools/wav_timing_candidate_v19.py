"""Exact private instrumentation of accepted WAV; no production file writes.

Native type20 offsets40/44 carry a paged snapshot instead of prepare/check.
Only this exact firmware binding authorizes that schema. Relay prepare/check
aggregates and ordinary SPI cost summaries are invalid in this experiment.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKETCH=ROOT/'arduino/v19/oscilloscope/sketch'
SCHEMA='wav-chunk-cycles-v1'
MAGIC=0xD7000000
FIELDS=('serial','request','session','count_state','clock_hz','irq','poll_main',
        'validate','copy','cache','descriptor','publish','elapsed','max_irq','max_irq_request')

HEADER=r'''
// Private wav-chunk-cycles-v1: only loop writes these snapshots. Timer poll
// never writes them. Last-CHUNK sampling is not an all-CHUNK distribution.
namespace scope_wav_timing {
struct Sample {
    uint32_t serial=0,request=0,session=0,count_state=0,clock_hz=0;
    uint32_t irq=0,poll_main=0,validate=0,copy=0,cache=0,descriptor=0,publish=0,elapsed=0;
    uint32_t max_irq=0,max_irq_request=0;
};
static Sample latest,frozen;
static uint32_t copy_cycles=0,cache_cycles=0,descriptor_cycles=0;
static unsigned page=0;static uint16_t snapshot_id=0;
static inline uint32_t now(){
    __asm__ volatile("" ::: "memory");
    const uint32_t value=k_cycle_get_32();
    __asm__ volatile("" ::: "memory");
    return value;
}
static void record(const Sample &s){
    Sample next=s;next.serial=latest.serial+1U;
    next.max_irq=latest.max_irq;next.max_irq_request=latest.max_irq_request;
    if(next.irq>next.max_irq){next.max_irq=next.irq;next.max_irq_request=next.request;}
    latest=next;
}
static void emit(uint8_t *packet){
    if(!page){frozen=latest;++snapshot_id;}
    const uint32_t values[]={frozen.serial,frozen.request,frozen.session,frozen.count_state,
        frozen.clock_hz,frozen.irq,frozen.poll_main,frozen.validate,frozen.copy,frozen.cache,
        frozen.descriptor,frozen.publish,frozen.elapsed,frozen.max_irq,frozen.max_irq_request};
    scope_bench::put32(packet+40,0xd7000000U|(page<<16)|snapshot_id);
    scope_bench::put32(packet+44,values[page]);
    page=(page+1U)%15U;
}
}
'''


def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('Private WAV timing anchor is not unique: '+old[:72])
    return text.replace(old,new)


def candidate_sources(originals):
    """Only the reviewed timing hooks in these three exact baseline files."""
    if set(originals)!={'wav.h','wav_dma.h','sketch.ino'}:raise ValueError('Exact WAV timing source set required')
    dma=replace_once(originals['wav_dma.h'],'namespace wav_hw {',HEADER+'\nnamespace wav_hw {')
    dma=replace_once(dma,'''    for(unsigned i=0;i<count;++i) data[slot*scope_wav::POINTS+i]=scope_wav::get16(p+2*i);
    cache_flush_invalidate(data+slot*scope_wav::POINTS,scope_wav::POINTS*sizeof(uint16_t));
    descriptor(slot,false,count,final);
    __DSB();''','''    const uint32_t copy_at=scope_wav_timing::now();
    for(unsigned i=0;i<count;++i) data[slot*scope_wav::POINTS+i]=scope_wav::get16(p+2*i);
    const uint32_t cache_at=scope_wav_timing::now();
    cache_flush_invalidate(data+slot*scope_wav::POINTS,scope_wav::POINTS*sizeof(uint16_t));
    const uint32_t descriptor_at=scope_wav_timing::now();
    descriptor(slot,false,count,final);
    const uint32_t descriptor_done=scope_wav_timing::now();
    __DSB();
    scope_wav_timing::copy_cycles=cache_at-copy_at;
    scope_wav_timing::cache_cycles=descriptor_at-cache_at;
    scope_wav_timing::descriptor_cycles=descriptor_done-descriptor_at;''')
    wav=replace_once(originals['wav.h'],'''SCOPE_WAV_FAST static scope_wav::Reply submit(const scope_wav::Request &r) {
    const unsigned key=irq_lock();
    poll();''','''SCOPE_WAV_FAST static scope_wav::Reply submit(const scope_wav::Request &r) {
    scope_wav_timing::Sample timing;
    bool timed_chunk=false;
    const uint32_t entered_at=scope_wav_timing::now();
    const unsigned key=irq_lock();
    const uint32_t locked_at=scope_wav_timing::now();
    poll();
    const uint32_t polled_at=scope_wav_timing::now();''')
    loop='            for(unsigned i=0;i<r.count;++i) if(scope_wav::get16(r.samples+2*i)>4095) reason=scope_control::UNSUPPORTED;'
    wav=replace_once(wav,loop,'''            const uint32_t validation_at=scope_wav_timing::now();
'''+loop+'''
            timing.validate=scope_wav_timing::now()-validation_at;''')
    wav=replace_once(wav,'''                wav_hw::publish(queue.tail,r.samples,r.count,queue.accepted+r.count==queue.total);
                queue.publish(r.count);''','''                const uint32_t publication_at=scope_wav_timing::now();
                wav_hw::publish(queue.tail,r.samples,r.count,queue.accepted+r.count==queue.total);
                queue.publish(r.count);
                timing.publish=scope_wav_timing::now()-publication_at;
                timed_chunk=true;''')
    wav=replace_once(wav,'''    const auto result=reply(r.id,reason);
    irq_unlock(key);return result;''','''    const auto result=reply(r.id,reason);
    const uint32_t unlocking_at=scope_wav_timing::now();
    irq_unlock(key);
    const uint32_t returned_at=scope_wav_timing::now();
    if(timed_chunk){
        timing.request=r.id;timing.session=r.session;
        timing.count_state=uint32_t(r.count)|(uint32_t(result.state)<<16)|(1U<<24);
        timing.clock_hz=sys_clock_hw_cycles_per_sec();
        timing.irq=unlocking_at-locked_at;timing.poll_main=polled_at-locked_at;
        timing.copy=scope_wav_timing::copy_cycles;timing.cache=scope_wav_timing::cache_cycles;
        timing.descriptor=scope_wav_timing::descriptor_cycles;timing.elapsed=returned_at-entered_at;
        scope_wav_timing::record(timing);
    }
    return result;''')
    ino=replace_once(originals['sketch.ino'],'''        else if(!have_samples) build_samples(packet,nullptr,0,0);
        seal(packet);''','''        else if(!have_samples) build_samples(packet,nullptr,0,0);
        // Private schema replaces only diagnostic timing fields, after all producers.
        if(acquisition::native()) scope_wav_timing::emit(packet);
        seal(packet);''')
    return {'wav.h':wav,'wav_dma.h':dma,'sketch.ino':ino}


def accepted_sources():
    return {name:(SKETCH/name).read_text() for name in ('wav.h','wav_dma.h','sketch.ino')}
