"""Generate an isolated relay timing observer; never operates hardware."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
HEADER=r'''#pragma once
/* Diagnostic only: wall-time stages, not CPU utilization. */
#include <time.h>
enum { SCOPE_TRACE_STAGES=7, SCOPE_TRACE_PHASES=4, SCOPE_TRACE_BINS=11 };
static const char *scope_trace_names[]={"tx_prepare","ready_wait","spi_ioctl","validate","policy","pc_receive","pc_send"};
static const uint64_t scope_trace_limits[]={5000,20000,50000,100000,200000,400000,600000,1000000,2000000,10000000};
typedef struct { uint64_t count,sum[SCOPE_TRACE_STAGES],max[SCOPE_TRACE_STAGES],hist[SCOPE_TRACE_STAGES][SCOPE_TRACE_BINS];unsigned queue_peak; } ScopeTrace;
static ScopeTrace scope_trace_groups[SCOPE_TRACE_PHASES];
static unsigned scope_trace_phase=0;
static bool scope_trace_active=false;
static uint64_t scope_trace_clock(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)<0)return 0;
    return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static void scope_trace_flush(void) {
    for(unsigned p=0;p<SCOPE_TRACE_PHASES;++p) {
        const ScopeTrace *s=&scope_trace_groups[p];if(!s->count)continue;
        fprintf(stderr,"SCOPE_LATENCY {\"phase\":%u,\"count\":%" PRIu64 ",\"tcp_queue_peak\":%u,\"stages\":{",p,s->count,s->queue_peak);
        for(unsigned i=0;i<SCOPE_TRACE_STAGES;++i) {
            fprintf(stderr,"%s\"%s\":{\"sum_ns\":%" PRIu64 ",\"max_ns\":%" PRIu64 ",\"hist\":[",i?",":"",scope_trace_names[i],s->sum[i],s->max[i]);
            for(unsigned b=0;b<SCOPE_TRACE_BINS;++b)fprintf(stderr,"%s%" PRIu64,b?",":"",s->hist[i][b]);
            fprintf(stderr,"]}");
        }
        fprintf(stderr,"}}\n");
    }
    memset(scope_trace_groups,0,sizeof scope_trace_groups);
    scope_trace_active=false;scope_trace_phase=0;
}
static void scope_trace_update(bool target,const uint8_t *rx) {
    if(!target) {if(scope_trace_active)scope_trace_flush();return;}
    scope_trace_active=true;
    for(unsigned half=0;half<2;++half) {
        const uint8_t *p=rx+half*BLOCK;
        if(get16(p+6)==12 && get32(p+40)==40000) {
            const unsigned state=p[24];
            scope_trace_phase=state==2?2:state==1?1:state>=4?3:0;
        }
    }
}
static void scope_trace_observe(const uint64_t t[8],unsigned queue) {
    if(!scope_trace_active)return;
    ScopeTrace *s=&scope_trace_groups[scope_trace_phase];++s->count;
    if(queue>s->queue_peak)s->queue_peak=queue;
    for(unsigned i=0;i<SCOPE_TRACE_STAGES;++i) {
        const uint64_t elapsed=t[i+1]-t[i];
        s->sum[i]+=elapsed;if(elapsed>s->max[i])s->max[i]=elapsed;
        unsigned b=0;while(b<SCOPE_TRACE_BINS-1 && elapsed>=scope_trace_limits[b])++b;
        ++s->hist[i][b];
    }
}
'''


def replace_once(text, before, after):
    if text.count(before)!=1:raise ValueError('Relay anchor is not unique: '+before[:60])
    return text.replace(before,after,1)


def instrument(text):
    changes=[
        ('#include "frame_send_queue.h"','#include "frame_send_queue.h"\n#include "scope_latency_trace.h"'),
        ('    while (running) {\n        scope_batch2_prepare_tx',
         '    while (running) {\n        uint64_t trace_t[8];trace_t[0]=scope_trace_clock();\n        scope_batch2_prepare_tx'),
        ('pending); pending=false;','pending); pending=false;\n        trace_t[1]=scope_trace_clock();'),
        ('        previous_io=now();','        trace_t[2]=scope_trace_clock();\n        previous_io=now();'),
        ('        DualChecker before=checker;','        trace_t[3]=scope_trace_clock();\n        DualChecker before=checker;'),
        ('        const ScopeNativeProfile *profile=scope_native_find(checker.bits,checker.period);',
         '        trace_t[4]=scope_trace_clock();\n        const ScopeNativeProfile *profile=scope_native_find(checker.bits,checker.period);\n        scope_trace_update(profile && profile->bits==8 && profile->channels==1 && profile->ticks==86 && profile->node_pairs==3488,rx);'),
        ('        previous_tx=get32(tx+BLOCK+8);','        trace_t[5]=scope_trace_clock();\n        previous_tx=get32(tx+BLOCK+8);'),
        ('        if (client>=0) {\n            // Validation of both halves',
         '        trace_t[6]=scope_trace_clock();\n        if (client>=0) {\n            // Validation of both halves'),
        ('        if (now()-progress>=10) {','        trace_t[7]=scope_trace_clock();\n        if(before.bits==checker.bits && before.period==checker.period && before.epoch==checker.epoch)\n            scope_trace_observe(trace_t,send_queue.count);\n        if (now()-progress>=10) {'),
        ('done:\n    if(scope_cpu_restore()', 'done:\n    scope_trace_flush();\n    if(scope_cpu_restore()'),
    ]
    for before,after in changes:text=replace_once(text,before,after)
    return text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('New private diagnostic directory required')
    source=ROOT/'arduino/v19/relay'
    # Copy the complete standalone source tree; originals stay untouched.
    shutil.copytree(source,out)
    path=out/'unoq_config_stream.c';path.write_text(instrument(path.read_text()))
    (out/'scope_latency_trace.h').write_text(HEADER)
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (out.parent/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
