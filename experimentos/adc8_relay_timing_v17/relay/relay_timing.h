#pragma once
/* Fixed storage; no allocation or per-frame output. All durations are ns. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

enum { RT_READY,RT_COMMAND_POLICY,RT_SPI,RT_CHECK_POLICY,RT_SOCKET,RT_HEARTBEAT,RT_FRAME,RT_STAGES };
static const char *rt_names[RT_STAGES]={"ready_wait","command_policy","spi_ioctl","checker_policy","socket_control_send","heartbeat","frame_wall"};
static const uint32_t rt_upper_us[]={1,2,5,10,20,50,100,200,500,1000,5000,20000,100000};
#define RT_BINS (sizeof(rt_upper_us)/sizeof(rt_upper_us[0])+1U)
struct RtHistogram { uint64_t count,sum_ns,max_ns,bins[RT_BINS]; };
struct RtProfile { unsigned ticks;uint64_t iterations,completed,socket_queue_peak;struct RtHistogram stages[RT_STAGES]; };
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
static void rt_hist_json(FILE *out,const struct RtHistogram *h) {
    fprintf(out,"{\"count\":%llu,\"sum_ns\":%llu,\"max_ns\":%llu,\"bins\":[",(unsigned long long)h->count,(unsigned long long)h->sum_ns,(unsigned long long)h->max_ns);
    for(unsigned b=0;b<RT_BINS;++b)fprintf(out,"%s%llu",b?",":"",(unsigned long long)h->bins[b]);
    fputs("]}",out);
}
static void rt_emit(struct RelayTiming *t,FILE *out,const char *reason) {
    if(!t->profiles[0].iterations && !t->profiles[1].iterations)return;
    fprintf(out,"SPM_RELAY_TIMING {\"version\":1,\"reason\":\"%s\",\"histogram_upper_us\":[",reason);
    for(unsigned b=0;b<RT_BINS-1U;++b)fprintf(out,"%s%u",b?",":"",rt_upper_us[b]);
    fputs("],\"last_bin\":\"overflow\",\"clock_pair\":",out);rt_hist_json(out,&t->clock_pair);
    fputs(",\"profiles\":[",out);
    for(unsigned p=0;p<2;++p){
        const struct RtProfile *r=&t->profiles[p];
        fprintf(out,"%s{\"ticks\":%u,\"iterations\":%llu,\"completed\":%llu,\"socket_queue_peak\":%llu,\"stages\":{",p?",":"",r->ticks,(unsigned long long)r->iterations,(unsigned long long)r->completed,(unsigned long long)r->socket_queue_peak);
        for(unsigned s=0;s<RT_STAGES;++s){fprintf(out,"%s\"%s\":",s?",":"",rt_names[s]);rt_hist_json(out,&r->stages[s]);}
        fputs("}}",out);
    }
    fputs("]}\n",out);fflush(out);
    struct RtHistogram calibration=t->clock_pair;rt_reset(t);t->clock_pair=calibration;
}
