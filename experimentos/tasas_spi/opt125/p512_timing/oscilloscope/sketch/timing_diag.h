#pragma once
namespace timing_diag {
enum Metric { PREPARE, ARM, READY_TO_IRQ, IRQ_TO_RETURN, CHECK, HANDOFF, NODE_SEND, POLL, COPY, COUNT };
struct Stats { uint64_t cycles=0; uint32_t count=0, maximum=0; };
static Stats stats[COUNT];
static volatile uint32_t irq_cycle=0;
static uint32_t queue_max=0, queue_count=0;
static uint8_t queue_first[64]{},queue_last[64]{};
static void observe_queue(uint32_t used) { if(queue_count<64)queue_first[queue_count]=used;queue_last[queue_count%64]=used;++queue_count; }
static bool frozen=false;
static inline void record(Metric metric,uint32_t start,uint32_t end=k_cycle_get_32()) {
    if(frozen) return;
    const uint32_t delta=end-start;
    auto &s=stats[metric];s.cycles+=delta;++s.count;if(delta>s.maximum)s.maximum=delta;
}
static void reset() { for(auto &s:stats)s=Stats{};queue_max=queue_count=0;memset(queue_first,0,64);memset(queue_last,0,64); }
static void encode(uint8_t *p,uint32_t seq,uint32_t period,uint32_t epoch,uint32_t dropped,uint32_t fatal) {
    memset(p,0,scope_bench::BLOCK_BYTES);memcpy(p,"SCP1",4);scope_bench::put16(p+4,scope_bench::VERSION);scope_bench::put16(p+6,11);
    scope_bench::put32(p+8,seq);scope_bench::put32(p+12,scope_bench::PAYLOAD_BYTES);
    scope_bench::put32(p+16,period);scope_bench::put32(p+20,epoch);
    scope_bench::put32(p+24,dropped);scope_bench::put32(p+28,fatal);scope_bench::put32(p+32,queue_max);
    scope_bench::put32(p+36,COUNT);scope_bench::put32(p+40,CONFIG_SYS_CLOCK_HW_CYCLES_PER_SEC);
    for(unsigned i=0;i<COUNT;++i) {
        const auto &s=stats[i];auto *q=p+48+i*16;
        scope_bench::put32(q,s.count);scope_bench::put32(q+4,uint32_t(s.cycles));
        scope_bench::put32(q+8,uint32_t(s.cycles>>32));scope_bench::put32(q+12,s.maximum);
    }
    memcpy(p+192,"QTR1",4);scope_bench::put32(p+196,queue_count);
    scope_bench::put32(p+200,queue_count<64?queue_count:64);scope_bench::put32(p+204,queue_count<64?queue_count:64);
    memcpy(p+208,queue_first,64);memcpy(p+272,queue_last,64);
    scope_bench::put32(p+scope_bench::BLOCK_BYTES-4,scope_bench::crc32(p,scope_bench::BLOCK_BYTES-4));
}
}
