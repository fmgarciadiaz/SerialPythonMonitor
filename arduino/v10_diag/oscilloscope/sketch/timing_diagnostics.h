#pragma once
// RAM counters only; one snapshot in unused tail of the last DATA fragment.
namespace scope_diag {
struct Metric { uint32_t count, total_us, max_us; };
enum Stage { POLL_GAP, COPY_NODE, SEND_NODE, BUILD, HANDOFF, PREPARE, CHECK,
             SPI_SETUP, SPI_WAIT, SPI_CLEANUP, LOOP_GAP, STAGES };
static Metric metrics[STAGES]{};
static uint32_t queue_peak=0;
static void add(Stage stage,uint32_t us) {
    auto &m=metrics[stage]; ++m.count; m.total_us+=us;
    if(us>m.max_us) m.max_us=us;
}
static void reset() { memset(metrics,0,sizeof(metrics));queue_peak=0; }
static void observe_queue(uint32_t used) { unsigned key=irq_lock(); if(used>queue_peak)queue_peak=used; irq_unlock(key); }
static void snapshot(uint8_t *p,uint32_t used,uint32_t dropped,uint32_t fatal) {
    observe_queue(used);
    scope_bench::put32(p,0x31474454U); // TDG1
    for(unsigned i=0;i<STAGES;++i) {
        scope_bench::put32(p+4+12*i,metrics[i].count);
        scope_bench::put32(p+8+12*i,metrics[i].total_us);
        scope_bench::put32(p+12+12*i,metrics[i].max_us);
    }
    scope_bench::put32(p+136,used);scope_bench::put32(p+140,queue_peak);
    scope_bench::put32(p+144,dropped);scope_bench::put32(p+148,fatal);
}
static_assert(4+STAGES*12+16==152,"Diagnostic tail layout");
}
