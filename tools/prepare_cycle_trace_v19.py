"""Generate isolated full-cycle relay diagnostics from accepted V19 sources."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from tools.prepare_latency_trace_v19 import HEADER, instrument, replace_once, ROOT

CYCLE_HEADER=r'''#pragma once
/* Wall time only. MCU counters are observations, not causal timestamps. */
typedef struct {
    uint64_t start,end,cycle,gap;
    unsigned phase,sequence,native,epoch,node,queue,peak,copy,poll,send;
} ScopeCycle;
typedef struct {uint64_t count,covered,gap,cycle,max_gap,max_cycle;} ScopeCycleGroup;
static ScopeCycleGroup scope_cycle_groups[4];
static ScopeCycle scope_cycle_pending,scope_cycle_tails[8],scope_cycle_peaks[16];
static unsigned scope_cycle_tail_count,scope_cycle_peak_count,scope_cycle_peak_omitted;
static unsigned scope_cycle_epoch,scope_cycle_peak;
static bool scope_cycle_have_pending,scope_cycle_have_epoch;
static void scope_cycle_begin(uint64_t start) {
    if(!scope_cycle_have_pending)return;
    ScopeCycle c=scope_cycle_pending;scope_cycle_have_pending=false;
    if(start<c.end || c.end<c.start)return;
    c.cycle=start-c.start;c.gap=start-c.end;
    ScopeCycleGroup *g=&scope_cycle_groups[c.phase];++g->count;
    g->covered+=c.end-c.start;g->gap+=c.gap;g->cycle+=c.cycle;
    if(c.gap>g->max_gap)g->max_gap=c.gap;
    if(c.cycle>g->max_cycle)g->max_cycle=c.cycle;
    unsigned pos=0;
    while(pos<scope_cycle_tail_count && scope_cycle_tails[pos].cycle>=c.cycle)++pos;
    if(pos<8) {
        unsigned end=scope_cycle_tail_count<8?scope_cycle_tail_count++:7;
        while(end>pos) {scope_cycle_tails[end]=scope_cycle_tails[end-1];--end;}
        scope_cycle_tails[pos]=c;
    }
    if(c.native) {
        if(!scope_cycle_have_epoch || c.epoch!=scope_cycle_epoch) {
            scope_cycle_epoch=c.epoch;scope_cycle_peak=0;scope_cycle_have_epoch=true;
        }
        if(c.peak>scope_cycle_peak) {
            scope_cycle_peak=c.peak;
            if(scope_cycle_peak_count<16)scope_cycle_peaks[scope_cycle_peak_count++]=c;
            else ++scope_cycle_peak_omitted;
        }
    }
}
static void scope_cycle_end(const uint64_t t[8],const uint8_t *rx) {
    if(!scope_trace_active)return;
    ScopeCycle c={.start=t[0],.end=t[7],.phase=scope_trace_phase,.sequence=get32(rx+8)};
    for(unsigned half=0;half<2;++half) {
        const uint8_t *p=rx+half*BLOCK;
        if(get16(p+6)!=20)continue;
        c.native=1;c.epoch=get32(p+76)>>1;c.node=get32(p+72);
        c.queue=get32(p+88);c.peak=get32(p+92);c.copy=get32(p+96);
        c.poll=get32(p+100);c.send=get32(p+108);
        if(get16(p+64))break;
    }
    scope_cycle_pending=c;scope_cycle_have_pending=true;
}
static void scope_cycle_print(const char *kind,const ScopeCycle *c) {
    fprintf(stderr,"SCOPE_CYCLE_EVENT {\"kind\":\"%s\",\"phase\":%u,\"sequence\":%u,\"covered_ns\":%" PRIu64
        ",\"gap_ns\":%" PRIu64 ",\"cycle_ns\":%" PRIu64 ",\"has_native\":%u,\"epoch\":%u,\"node\":%u,\"queue\":%u,\"peak\":%u,\"copy_max_ticks\":%u,\"poll_max_ticks\":%u,\"previous_node_send_ticks\":%u}\n",
        kind,c->phase,c->sequence,c->end-c->start,c->gap,c->cycle,c->native,c->epoch,c->node,c->queue,c->peak,c->copy,c->poll,c->send);
}
static void scope_cycle_flush(void) {
    for(unsigned p=0;p<4;++p) {
        const ScopeCycleGroup *g=&scope_cycle_groups[p];if(!g->count)continue;
        fprintf(stderr,"SCOPE_CYCLE {\"phase\":%u,\"count\":%" PRIu64 ",\"covered_ns\":%" PRIu64
            ",\"gap_ns\":%" PRIu64 ",\"cycle_ns\":%" PRIu64 ",\"max_gap_ns\":%" PRIu64 ",\"max_cycle_ns\":%" PRIu64 "}\n",
            p,g->count,g->covered,g->gap,g->cycle,g->max_gap,g->max_cycle);
    }
    for(unsigned i=0;i<scope_cycle_tail_count;++i)scope_cycle_print("slow_cycle",&scope_cycle_tails[i]);
    for(unsigned i=0;i<scope_cycle_peak_count;++i)scope_cycle_print("peak_observed",&scope_cycle_peaks[i]);
    fprintf(stderr,"SCOPE_CYCLE_END {\"peak_events_omitted\":%u,\"incomplete_final_cycle\":%u}\n",scope_cycle_peak_omitted,scope_cycle_have_pending?1U:0U);
    memset(scope_cycle_groups,0,sizeof scope_cycle_groups);
    scope_cycle_tail_count=scope_cycle_peak_count=scope_cycle_peak_omitted=0;
    scope_cycle_have_pending=scope_cycle_have_epoch=false;
}
'''


def cycle_instrument(text):
    text=instrument(text)
    text=replace_once(text,'#include "scope_latency_trace.h"',
                     '#include "scope_latency_trace.h"\n#include "scope_cycle_trace.h"')
    text=replace_once(text,'trace_t[0]=scope_trace_clock();',
                     'trace_t[0]=scope_trace_clock();scope_cycle_begin(trace_t[0]);')
    text=replace_once(text,'            scope_trace_observe(trace_t,send_queue.count);',
                     '            {scope_trace_observe(trace_t,send_queue.count);scope_cycle_end(trace_t,rx);}')
    return text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('New private diagnostic directory required')
    shutil.copytree(ROOT/'arduino/v19/relay',out)
    p=out/'unoq_config_stream.c';p.write_text(cycle_instrument(p.read_text()))
    header=replace_once(HEADER,'static void scope_trace_flush(void) {',
        'static void scope_cycle_flush(void);\nstatic void scope_trace_flush(void) {\n    scope_cycle_flush();')
    (out/'scope_latency_trace.h').write_text(header)
    (out/'scope_cycle_trace.h').write_text(CYCLE_HEADER)
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (out.parent/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(out)

if __name__=='__main__':main()
