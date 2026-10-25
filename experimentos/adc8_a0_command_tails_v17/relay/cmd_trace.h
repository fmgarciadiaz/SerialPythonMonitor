#pragma once
/* Q CLOCK_MONOTONIC ns only. Fixed records; no allocation or high-rate output. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CT_CAPACITY 128U
enum { CT_FIRST_COMPLETE,CT_COMPLETE_SPI,CT_SPI_ACK,CT_ACK_ENQUEUE,CT_COMPLETE_ACK,CT_STAGE_COUNT };
static const char *ct_stage_names[CT_STAGE_COUNT]={"first_read_to_complete","complete_to_spi_start","spi_end_to_ack_rx","ack_rx_to_enqueue_return","complete_to_ack_rx"};
struct CtRecord {
    uint32_t id,session,offset,count;unsigned kind,op;
    uint64_t first_byte_ns,complete_ns,spi_start_ns,spi_end_ns,ack_rx_ns,ack_enqueue_return_ns;
    unsigned ack_state,ack_reason,ack_free,enqueue_queue_count;uint32_t accepted,played;
    unsigned stats_mask;
};
struct CtTail {uint64_t ns;struct CtRecord record;};
struct CtStatistics {uint64_t count,sum_ns,max_ns,rejected,censored_overwrite,missing_at_freeze;unsigned top_count;struct CtTail top[8];};
struct CommandTrace {
    struct CtRecord ring[CT_CAPACITY],frozen[CT_CAPACITY];
    unsigned next,count,frozen_count,frozen_valid,dirty;uint32_t fault_id;
    uint64_t commands,overwrites,unknown_acks,commands_after_freeze;
    struct CtStatistics stages[CT_STAGE_COUNT];
};
static void ct_reset(struct CommandTrace *t){memset(t,0,sizeof *t);}
static struct CtRecord *ct_find(struct CommandTrace *t,uint32_t id) {
    for(unsigned i=0;i<t->count;++i){struct CtRecord *r=&t->ring[(t->next+CT_CAPACITY-1U-i)%CT_CAPACITY];if(r->id==id)return r;}
    return NULL;
}
static void ct_observe(struct CommandTrace *t,struct CtRecord *r,unsigned stage,uint64_t start,uint64_t end) {
    if(stage>=CT_STAGE_COUNT || (r->stats_mask&(1U<<stage)))return;
    r->stats_mask|=1U<<stage;
    struct CtStatistics *s=&t->stages[stage];
    /* Zero is missing; values outside signed monotonic range include negative casts. */
    if(!start || !end || start>INT64_MAX || end>INT64_MAX || end<start){++s->rejected;return;}
    uint64_t duration=end-start;++s->count;s->sum_ns+=duration;if(duration>s->max_ns)s->max_ns=duration;
    unsigned slot=s->top_count;
    if(slot<8)++s->top_count;else{slot=7;if(duration<=s->top[slot].ns)return;}
    while(slot && duration>s->top[slot-1].ns){s->top[slot]=s->top[slot-1];--slot;}
    s->top[slot]=(struct CtTail){.ns=duration,.record=*r};
}
static void ct_command(struct CommandTrace *t,uint32_t id,unsigned kind,uint32_t session,unsigned op,uint32_t offset,uint32_t count,uint64_t first,uint64_t complete) {
    ++t->commands;t->dirty=1;
    if(t->frozen_valid){++t->commands_after_freeze;return;}
    if(t->count==CT_CAPACITY){
        ++t->overwrites;
        for(unsigned stage=0;stage<CT_STAGE_COUNT;++stage)if(!(t->ring[t->next].stats_mask&(1U<<stage)))++t->stages[stage].censored_overwrite;
    }else ++t->count;
    t->ring[t->next]=(struct CtRecord){.id=id,.kind=kind,.session=session,.op=op,.offset=offset,.count=count,.first_byte_ns=first,.complete_ns=complete};
    ct_observe(t,&t->ring[t->next],CT_FIRST_COMPLETE,first,complete);
    t->next=(t->next+1U)%CT_CAPACITY;
}
static void ct_spi(struct CommandTrace *t,uint32_t id,uint64_t stamp,int ended) {
    if(t->frozen_valid)return;
    struct CtRecord *r=ct_find(t,id);if(!r)return;
    if(ended){if(!r->spi_end_ns)r->spi_end_ns=stamp;}
    else if(!r->spi_start_ns){r->spi_start_ns=stamp;ct_observe(t,r,CT_COMPLETE_SPI,r->complete_ns,stamp);}
}
static void ct_ack(struct CommandTrace *t,uint32_t id,unsigned state,unsigned reason,unsigned free_blocks,uint32_t accepted,uint32_t played,uint64_t stamp) {
    if(t->frozen_valid)return;
    struct CtRecord *r=ct_find(t,id);
    if(r && !r->ack_rx_ns){
        r->ack_rx_ns=stamp;r->ack_state=state;r->ack_reason=reason;r->ack_free=free_blocks;r->accepted=accepted;r->played=played;
        ct_observe(t,r,CT_SPI_ACK,r->spi_end_ns,stamp);ct_observe(t,r,CT_COMPLETE_ACK,r->complete_ns,stamp);
    }
    else if(!r)++t->unknown_acks;
    if(state==4){
        t->frozen_valid=1;t->frozen_count=t->count;t->fault_id=id;t->dirty=1;
        for(unsigned i=0;i<t->count;++i){
            t->frozen[i]=t->ring[(t->next+CT_CAPACITY-t->count+i)%CT_CAPACITY];
            for(unsigned stage=0;stage<CT_STAGE_COUNT;++stage)if(!(t->frozen[i].stats_mask&(1U<<stage)))++t->stages[stage].missing_at_freeze;
        }
    }
}
static void ct_enqueue(struct CommandTrace *t,uint32_t id,uint64_t stamp,unsigned queued) {
    if(t->frozen_valid){
        /* Only annotate terminal ACK handoff, after its first-UNDERRUN snapshot. */
        if(id==t->fault_id)for(unsigned i=0;i<t->frozen_count;++i)if(t->frozen[i].id==id && !t->frozen[i].ack_enqueue_return_ns){
            t->frozen[i].ack_enqueue_return_ns=stamp;t->frozen[i].enqueue_queue_count=queued;
            ct_observe(t,&t->frozen[i],CT_ACK_ENQUEUE,t->frozen[i].ack_rx_ns,stamp);
        }
        return;
    }
    struct CtRecord *r=ct_find(t,id);if(r && !r->ack_enqueue_return_ns){r->ack_enqueue_return_ns=stamp;r->enqueue_queue_count=queued;ct_observe(t,r,CT_ACK_ENQUEUE,r->ack_rx_ns,stamp);}
}
static void ct_record_json(FILE *out,const struct CtRecord *r){
    fprintf(out,"{\"id\":%u,\"kind\":%u,\"session\":%u,\"op\":%u,\"offset\":%u,\"count\":%u,\"first_byte_ns\":%llu,\"complete_ns\":%llu,\"spi_start_ns\":%llu,\"spi_end_ns\":%llu,\"ack_rx_ns\":%llu,\"ack_state\":%u,\"ack_reason\":%u,\"ack_free\":%u,\"accepted\":%u,\"played\":%u,\"ack_enqueue_return_ns\":%llu,\"enqueue_queue_count\":%u}",r->id,r->kind,r->session,r->op,r->offset,r->count,(unsigned long long)r->first_byte_ns,(unsigned long long)r->complete_ns,(unsigned long long)r->spi_start_ns,(unsigned long long)r->spi_end_ns,(unsigned long long)r->ack_rx_ns,r->ack_state,r->ack_reason,r->ack_free,r->accepted,r->played,(unsigned long long)r->ack_enqueue_return_ns,r->enqueue_queue_count);
}
static void ct_emit(struct CommandTrace *t,FILE *out,const char *reason){
    if(!t->dirty)return;
    fprintf(out,"SPM_COMMAND_TRACE {\"version\":2,\"reason\":\"%s\",\"clock\":\"Q_CLOCK_MONOTONIC_ns\",\"commands\":%llu,\"overwrites\":%llu,\"commands_after_freeze\":%llu,\"unknown_acks\":%llu,\"frozen\":%u,\"fault_id\":%u,\"records\":[",reason,(unsigned long long)t->commands,(unsigned long long)t->overwrites,(unsigned long long)t->commands_after_freeze,(unsigned long long)t->unknown_acks,t->frozen_valid,t->fault_id);
    unsigned count=t->frozen_valid?t->frozen_count:t->count;
    for(unsigned i=0;i<count;++i){if(i)fputc(',',out);ct_record_json(out,t->frozen_valid?&t->frozen[i]:&t->ring[(t->next+CT_CAPACITY-t->count+i)%CT_CAPACITY]);}
    fputs("],\"stages\":{",out);
    for(unsigned stage=0;stage<CT_STAGE_COUNT;++stage){
        const struct CtStatistics *s=&t->stages[stage];
        fprintf(out,"%s\"%s\":{\"count\":%llu,\"sum_ns\":%llu,\"max_ns\":%llu,\"rejected\":%llu,\"censored_overwrite\":%llu,\"missing_at_freeze\":%llu,\"top\":[",stage?",":"",ct_stage_names[stage],(unsigned long long)s->count,(unsigned long long)s->sum_ns,(unsigned long long)s->max_ns,(unsigned long long)s->rejected,(unsigned long long)s->censored_overwrite,(unsigned long long)s->missing_at_freeze);
        for(unsigned i=0;i<s->top_count;++i){fprintf(out,"%s{\"ns\":%llu,\"record\":",i?",":"",(unsigned long long)s->top[i].ns);ct_record_json(out,&s->top[i].record);fputc('}',out);}
        fputs("]}",out);
    }
    fputs("}}\n",out);fflush(out);t->dirty=0;
}
