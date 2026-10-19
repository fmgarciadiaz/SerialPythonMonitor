#pragma once
/* Diagnostic only. Fixed memory, no output while acquiring. */
#define TRACE_RING 1024U
#define TRACE_POST 128U
#define TRACE_TOP 64U
struct TraceRow {
    uint32_t seq,index,node,epoch,queue,peak,send,slack,produced;
    uint64_t host_ns,ns[9];
};
static struct TraceRow trace_ring[TRACE_RING],trace_event[TRACE_RING+TRACE_POST],trace_top[TRACE_TOP];
static unsigned trace_used,trace_cursor,trace_event_used,trace_remaining,trace_peak,trace_top_used;
static uint64_t trace_count,trace_sum[9],trace_max[9];
static double trace_previous;
static double trace_now(void) { int saved=errno; double t=now();errno=saved;return t; }
static uint64_t trace_ns(double dt) { return dt>0?(uint64_t)(dt*1e9):0; }
static void trace_add(struct TraceRow row) {
    ++trace_count;
    for(unsigned i=0;i<9;++i) {
        trace_sum[i]+=row.ns[i];
        if(row.ns[i]>trace_max[i])trace_max[i]=row.ns[i];
    }
    uint64_t score=row.ns[7]+row.ns[8];
    unsigned at=0;
    while(at<trace_top_used && trace_top[at].ns[7]+trace_top[at].ns[8]>=score)++at;
    if(at<TRACE_TOP) {
        unsigned end=trace_top_used<TRACE_TOP?trace_top_used++:TRACE_TOP-1;
        while(end>at){trace_top[end]=trace_top[end-1];--end;}
        trace_top[at]=row;
    }
    if(row.peak>=3 && row.peak>trace_peak) {
        trace_peak=row.peak;trace_event_used=0;
        unsigned first=(trace_cursor+TRACE_RING-trace_used)%TRACE_RING;
        for(unsigned i=0;i<trace_used;++i)
            trace_event[trace_event_used++]=trace_ring[(first+i)%TRACE_RING];
        trace_remaining=TRACE_POST;
    }
    if(trace_remaining) {
        trace_event[trace_event_used++]=row;--trace_remaining;
    }
    trace_ring[trace_cursor]=row;trace_cursor=(trace_cursor+1)%TRACE_RING;
    if(trace_used<TRACE_RING)++trace_used;
}
static void trace_record(const uint8_t *p,const double t[8]) {
    double previous=trace_previous;trace_previous=t[7];
    if(get16(p+6)!=20 || get32(p+68)!=100)return;
    struct TraceRow row={.seq=get32(p+8),.index=get32(p+52),.node=get32(p+72),
        .epoch=get32(p+76)>>1,.queue=get32(p+88),.peak=get32(p+92),
        .send=get32(p+108),.slack=get32(p+104),.produced=get32(p+112),
        .host_ns=trace_ns(t[0])};
    for(unsigned i=0;i<7;++i)row.ns[i]=trace_ns(t[i+1]-t[i]);
    row.ns[7]=trace_ns(t[7]-t[0]);
    row.ns[8]=previous?trace_ns(t[0]-previous):0;
    trace_add(row);
}
static void trace_print(const char *group,const struct TraceRow *r) {
    fprintf(stderr,"CAUSAL %s %"PRIu32" %"PRIu32" %"PRIu32" %"PRIu32" %"PRIu32" %"PRIu32" %"PRIu32" %"PRIu32" %"PRIu32" %"PRIu64,
        group,r->seq,r->index,r->node,r->epoch,r->queue,r->peak,r->send,r->slack,r->produced,r->host_ns);
    for(unsigned i=0;i<9;++i)fprintf(stderr," %"PRIu64,r->ns[i]);
    fputc('\n',stderr);
}
static void trace_dump(void) {
    fprintf(stderr,"CAUSAL_SUMMARY count=%"PRIu64" event_peak=%u event_rows=%u\n",trace_count,trace_peak,trace_event_used);
    for(unsigned i=0;i<9;++i)
        fprintf(stderr,"CAUSAL_STAGE %u %"PRIu64" %"PRIu64"\n",i,trace_sum[i],trace_max[i]);
    for(unsigned i=0;i<trace_top_used;++i)trace_print("top",trace_top+i);
    if(trace_event_used)for(unsigned i=0;i<trace_event_used;++i)trace_print("event",trace_event+i);
    else for(unsigned i=0;i<trace_used;++i)trace_print("recent",trace_ring+(trace_cursor+TRACE_RING-trace_used+i)%TRACE_RING);
}
