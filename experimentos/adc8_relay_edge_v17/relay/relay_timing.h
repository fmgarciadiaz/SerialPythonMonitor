#pragma once
/* Fixed storage; no allocation or per-frame output. All durations are ns. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

enum { RT_READY,RT_COMMAND_POLICY,RT_SPI,RT_CHECK_POLICY,RT_SOCKET,RT_HEARTBEAT,RT_FRAME,RT_EDGE_AGE,RT_EDGE_BEFORE,RT_EDGE_AFTER,RT_RECV,RT_ACCEPT,RT_SEND,RT_STAGES };
static const char *rt_names[RT_STAGES]={"ready_wait","command_policy","spi_ioctl","checker_policy","socket_control_send","heartbeat","frame_wall","ready_edge_age","edge_before_wait","edge_after_wait","socket_recv","socket_accept","socket_send"};
static const uint32_t rt_upper_us[]={1,2,5,10,20,50,100,200,500,1000,5000,20000,100000};
#define RT_BINS (sizeof(rt_upper_us)/sizeof(rt_upper_us[0])+1U)
struct RtHistogram { uint64_t count,sum_ns,max_ns,bins[RT_BINS]; };
struct RtTail {uint64_t wait_start_ns,edge_ns,returned_ns;uint32_t frame_sequence;unsigned ticks;
    unsigned rx_valid,rx_kind,has_adc_metrics;uint32_t rx_sequence,node,queue,queue_peak,produced,sample_count,epoch;};
struct RtProfile { unsigned ticks;uint64_t iterations,completed,socket_queue_peak;
    uint64_t edge_valid,edge_absent,edge_stale,edge_future,edge_preexisting,edge_new,edge_equal;
    unsigned tail_count;struct RtTail tails[8];struct RtHistogram stages[RT_STAGES]; };
struct RelayTiming {struct RtProfile profiles[2];struct RtHistogram clock_pair;};

static uint64_t rt_now(void) {struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;}
static int rt_profile(unsigned bits,unsigned channels,unsigned ticks,unsigned pairs) {
    return bits==8 && channels==1 && pairs==3456?(ticks==100?0:ticks==98?1:-1):-1;
}
static unsigned rt_bin(uint64_t ns) {
    unsigned bin=0;while(bin<RT_BINS-1U && ns>(uint64_t)rt_upper_us[bin]*1000U)++bin;return bin;
}
static void rt_add(struct RtHistogram *h,uint64_t ns) {
    ++h->count;h->sum_ns+=ns;if(ns>h->max_ns)h->max_ns=ns;++h->bins[rt_bin(ns)];
}
static void rt_reset(struct RelayTiming *t) {memset(t,0,sizeof *t);t->profiles[0].ticks=100;t->profiles[1].ticks=98;}
static void rt_calibrate(struct RelayTiming *t) {
    /* Run once before the frame loop, while the stack starts at low ADC load. */
    for(unsigned i=0;i<128;++i){uint64_t a=rt_now(),b=rt_now();rt_add(&t->clock_pair,b-a);}
}
static void rt_stage(struct RelayTiming *t,int profile,unsigned stage,uint64_t began,uint64_t ended) {
    if(profile>=0 && stage<RT_STAGES)rt_add(&t->profiles[profile].stages[stage],ended-began);
}
static int rt_ready_edge(struct RelayTiming *t,int profile,uint64_t start,uint64_t edge,uint64_t returned,uint64_t after,uint32_t frame_sequence) {
    if(profile<0)return -1;
    struct RtProfile *p=&t->profiles[profile];
    if(!edge)++p->edge_absent;
    else if(edge<after)++p->edge_stale;
    else if(edge>returned || returned<start)++p->edge_future;
    else {
        ++p->edge_valid;rt_stage(t,profile,RT_EDGE_AGE,edge,returned);
        if(edge<=start){++p->edge_preexisting;rt_stage(t,profile,RT_EDGE_BEFORE,edge,start);}
        if(edge>=start){++p->edge_new;rt_stage(t,profile,RT_EDGE_AFTER,start,edge);}
        if(edge==start)++p->edge_equal;
    }
    if(returned>=start && returned-start>UINT64_C(1000000)) {
        unsigned slot=p->tail_count;
        if(slot<8)++p->tail_count;
        else {
            slot=0;for(unsigned i=1;i<8;++i)if(p->tails[i].returned_ns-p->tails[i].wait_start_ns<p->tails[slot].returned_ns-p->tails[slot].wait_start_ns)slot=i;
            if(returned-start<=p->tails[slot].returned_ns-p->tails[slot].wait_start_ns)return -1;
        }
        p->tails[slot]=(struct RtTail){.wait_start_ns=start,.edge_ns=edge,.returned_ns=returned,.frame_sequence=frame_sequence,.ticks=p->ticks};
        return (int)slot;
    }
    return -1;
}
static void rt_tail_frame(struct RelayTiming *t,int profile,int slot,unsigned kind,uint32_t sequence,uint32_t node,uint32_t queue,uint32_t peak,uint32_t produced,uint32_t count,uint32_t epoch) {
    if(profile<0 || slot<0)return;
    struct RtTail *tail=&t->profiles[profile].tails[slot];
    tail->rx_valid=1;tail->rx_kind=kind;tail->rx_sequence=sequence;
    if(kind==20){tail->has_adc_metrics=1;tail->node=node;tail->queue=queue;tail->queue_peak=peak;tail->produced=produced;tail->sample_count=count;tail->epoch=epoch;}
}
static void rt_hist_json(FILE *out,const struct RtHistogram *h) {
    fprintf(out,"{\"count\":%llu,\"sum_ns\":%llu,\"max_ns\":%llu,\"bins\":[",(unsigned long long)h->count,(unsigned long long)h->sum_ns,(unsigned long long)h->max_ns);
    for(unsigned b=0;b<RT_BINS;++b)fprintf(out,"%s%llu",b?",":"",(unsigned long long)h->bins[b]);
    fputs("]}",out);
}
static void rt_emit(struct RelayTiming *t,FILE *out,const char *reason) {
    if(!t->profiles[0].iterations && !t->profiles[1].iterations)return;
    fprintf(out,"SPM_RELAY_TIMING {\"version\":2,\"reason\":\"%s\",\"histogram_upper_us\":[",reason);
    for(unsigned b=0;b<RT_BINS-1U;++b)fprintf(out,"%s%u",b?",":"",rt_upper_us[b]);
    fputs("],\"last_bin\":\"overflow\",\"clock_pair\":",out);rt_hist_json(out,&t->clock_pair);
    fputs(",\"profiles\":[",out);
    for(unsigned p=0;p<2;++p){
        const struct RtProfile *r=&t->profiles[p];
        fprintf(out,"%s{\"ticks\":%u,\"iterations\":%llu,\"completed\":%llu,\"socket_queue_peak\":%llu,\"edge_valid\":%llu,\"edge_absent\":%llu,\"edge_stale\":%llu,\"edge_future\":%llu,\"edge_preexisting\":%llu,\"edge_new\":%llu,\"edge_equal\":%llu,\"tails\":[",p?",":"",r->ticks,(unsigned long long)r->iterations,(unsigned long long)r->completed,(unsigned long long)r->socket_queue_peak,(unsigned long long)r->edge_valid,(unsigned long long)r->edge_absent,(unsigned long long)r->edge_stale,(unsigned long long)r->edge_future,(unsigned long long)r->edge_preexisting,(unsigned long long)r->edge_new,(unsigned long long)r->edge_equal);
        for(unsigned i=0;i<r->tail_count;++i){const struct RtTail *tail=&r->tails[i];fprintf(out,"%s{\"wait_start_ns\":%llu,\"edge_ns\":%llu,\"returned_ns\":%llu,\"frame_sequence\":%u,\"ticks\":%u,\"rx_valid\":%u,\"rx_kind\":%u,\"rx_sequence\":%u,\"has_adc_metrics\":%u,\"node\":%u,\"queue\":%u,\"queue_peak\":%u,\"produced\":%u,\"sample_count\":%u,\"epoch\":%u}",i?",":"",(unsigned long long)tail->wait_start_ns,(unsigned long long)tail->edge_ns,(unsigned long long)tail->returned_ns,tail->frame_sequence,tail->ticks,tail->rx_valid,tail->rx_kind,tail->rx_sequence,tail->has_adc_metrics,tail->node,tail->queue,tail->queue_peak,tail->produced,tail->sample_count,tail->epoch);}
        fputs("],\"stages\":{",out);
        for(unsigned s=0;s<RT_STAGES;++s){fprintf(out,"%s\"%s\":",s?",":"",rt_names[s]);rt_hist_json(out,&r->stages[s]);}
        fputs("}}",out);
    }
    fputs("]}\n",out);fflush(out);
    struct RtHistogram calibration=t->clock_pair;rt_reset(t);t->clock_pair=calibration;
}
