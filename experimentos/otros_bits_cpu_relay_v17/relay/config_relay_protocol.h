#pragma once
#include "native_profiles.h"
#include "high_rate_profile.h"
static bool acquisition_valid(unsigned bits,uint32_t period) {
    if(scope_native_find(bits,period)) return true;
    if(period==133) return bits==8;
    if(period==267 || period==242) return bits==14;
    if(bits!=8 && bits!=10 && bits!=12 && bits!=14 && bits!=16) return false;
    if (bits==16 && period<14) return false;
    switch(period) { case 3: case 4: case 5: case 8: case 10: case 14: case 15: case 16: case 20: case 25: case 32:case 40:case 50:case 64:case 80:case 100:case 125:
        case 200:case 250:case 500:case 1000:return true; }
    return false;
}
typedef struct {
    Checker adc;
    bool have_sequence,expect_boundary;
    uint32_t sequence,boundary,period,epoch;
    unsigned mode,bits;
} DualChecker;
static bool native_feed(DualChecker *d,const uint8_t *p,const ScopeNativeProfile *native) {
    unsigned kind=get16(p+6);
    const uint32_t ticks=d->period&65535U,n=(d->period>>16)&32767U;
    if(kind!=20 || !acquisition_valid(d->bits,d->period) || get32(p+20) || get32(p+24) || get32(p+28) ||
       ((int32_t)get32(p+32)!=0 && get32(p+32)!=BLOCK) || get32(p+36) || get32(p+56) || get32(p+60) ||
       get32(p+76)!=(d->epoch<<1) || get32(p+48)!=160000000U/ticks || p[66]!=d->bits || p[67]!=native->channels ||
       get32(p+68)!=ticks || get32(p+84)!=n || get32(p+88)>scope_queue_capacity(d->bits,native->channels,ticks,n) || get32(p+92)>scope_queue_capacity(d->bits,native->channels,ticks,n)) return false;
    unsigned count=get16(p+64),limit=(872U*8U/(d->bits*native->channels))&~3U;
    uint32_t index=get32(p+52),offset=index-get32(p+72)*n;
    if(count>limit || (count && (d->mode || offset>=n || count>n-offset || count%4))) return false;
    unsigned used=count*d->bits*native->channels/8;
    for(unsigned i=116+used;i<988;++i) if(p[i]) return false;
    if(!count) return !index && !get32(p+72) && !get32(p+80);
    if(d->expect_boundary && index!=d->boundary) return false;
    d->expect_boundary=false;
    if(scope_high_rate(d->bits,native->channels,ticks,n)) {
        // Whole N-bit groups bound each ADC value; interior timestamps
        // and indices have a fixed encoded step. Check both boundaries.
        // MCU retains every raw ADC/timestamp DMA check.
        const uint32_t first=get32(p+80);
        if(d->adc.have_sample && (index-d->adc.previous_sample!=1 || first-d->adc.previous_timestamp!=ticks)) return false;
        d->adc.previous_sample=index+count-1;
        d->adc.previous_timestamp=first+(count-1)*ticks;
        d->adc.have_sample=true;
        d->adc.sample_pairs+=count;
        ++d->adc.valid_blocks;
        return true;
    }
    uint64_t accumulator=0;unsigned available=0,pos=116;
    if(native->channels==1) {
        // Same per-sample checks as the isolated CH1 experiment. Move the
        // channel loop outside the hot path; retain decoding and every check.
        for(unsigned i=0;i<count;++i) {
            while(available<d->bits) {accumulator|=(uint64_t)p[pos++]<<available;available+=8;}
            uint32_t value=(uint32_t)accumulator&((1U<<d->bits)-1U);accumulator>>=d->bits;available-=d->bits;
            uint32_t timestamp=get32(p+80)+i*ticks,current=index+i;
            if(value>((1U<<d->bits)-1U)) return false;
            if(d->adc.have_sample && (current-d->adc.previous_sample!=1 || timestamp-d->adc.previous_timestamp!=ticks)) return false;
            d->adc.have_sample=true;d->adc.previous_sample=current;d->adc.previous_timestamp=timestamp;++d->adc.sample_pairs;
        }
        ++d->adc.valid_blocks;return true;
    }
    for(unsigned i=0;i<count;++i) {
        for(unsigned channel=0;channel<native->channels;++channel) {
        while(available<d->bits) {accumulator|=(uint64_t)p[pos++]<<available;available+=8;}
        uint32_t value=(uint32_t)accumulator&((1U<<d->bits)-1U);accumulator>>=d->bits;available-=d->bits;
        if(value>((1U<<d->bits)-1U)) return false;
        }
        uint32_t timestamp=get32(p+80)+i*ticks,current=index+i;
        if(d->adc.have_sample && (current-d->adc.previous_sample!=1 || timestamp-d->adc.previous_timestamp!=ticks)) return false;
        d->adc.have_sample=true;d->adc.previous_sample=current;d->adc.previous_timestamp=timestamp;++d->adc.sample_pairs;
    }
    ++d->adc.valid_blocks;return true;
}
static bool dual_feed(DualChecker *d,const uint8_t *p) {
    if(memcmp(p,"SCP1",4) || get16(p+4)!=4 || get32(p+12)!=972 || get32(p+988)!=crc32(p,988)) return false;
    uint32_t seq=get32(p+8);
    if(d->have_sequence && seq-d->sequence!=1) return false;
    d->sequence=seq; d->have_sequence=true;
    unsigned kind=get16(p+6);
    if(kind==12) {
        uint32_t rid=get32(p+16),accepted=get32(p+28),played=get32(p+32),total=get32(p+36);
        if(rid<UINT32_C(0x80000000) || rid==UINT32_MAX || p[24]>5 || p[25]>4 || get16(p+26)>16 ||
           played>accepted || accepted>total || (get32(p+40)!=20000 && get32(p+40)!=40000 && get32(p+40)!=50000) || get32(p+44)!=7) return false;
        for(unsigned i=48;i<988;++i) if(p[i]) return false;
        return true;
    }
    if(kind==9) {
        uint32_t rid=get32(p+16);
        unsigned phase=p[20],reason=p[21];
        if(rid<UINT32_C(0x80000000) || rid==UINT32_MAX || phase<1 || phase>3 || reason>4 ||
            ((phase==3)!=(reason!=0)) || p[22]>1 || p[23]>31) return false;
        if((p[23]&16) && (p[23]&12)!=12) return false;
        for(unsigned base=24;base<=44;base+=20) {
            if(base==44 && phase==3) break;
            const uint8_t *c=p+base;
            if(c[2]==3 && (!(p[23]&4) || c[0]!=1 || c[3] ||
                (!(p[23]&16) && (!get32(c+4) || !get32(c+8))) || get32(c+4)%25000 || get32(c+8)%25000 || (get32(c+4) && get32(c+4)==get32(c+8)) ||
                get32(c+16)>5000 || get32(c+16)%25)) return false;
            unsigned duty=p[base==24?64:65];
            if(duty && (duty>99 || c[0] || c[2] || !(p[23]&2))) return false;
            if(c[0]>4 || c[1]>1 || c[2]>3 || c[3]>1 || (c[3] && (c[0]!=4 || c[2])) || (c[2]!=3 && get32(c+4)<100) || get32(c+4)>50000000 ||
                (c[2]!=3 && get32(c+8)<100) || get32(c+8)>50000000 || get16(c+12)>get16(c+14) || get16(c+14)>4095 ||
                (!get32(c+16) && c[2]!=3) || (c[3] ? (get32(c+16)<100 || get32(c+16)>65535) : get32(c+16)>600000) || (c[0]==4 && c[2])) return false;
        }
        if(p[22] && !p[25]) return false;
        if(phase==2 && (memcmp(p+24,p+44,20) || p[64]!=p[65])) return false;
        for(unsigned i=66;i<988;++i) if(p[i]) return false;
        return true;
    }
    if(kind==5 || kind==7) {
        unsigned target=p[20],active=p[21],phase=p[22],reason=p[23];
        uint32_t rid=get32(p+16),boundary=get32(p+24);
        if(rid<UINT32_C(0x80000000) || rid==UINT32_MAX || phase<1 || phase>3 || reason>4 ||
            ((phase==3)!=(reason!=0))) return false;
        if(kind==5) {
            if(active>1 || boundary%2048 || (phase!=3 && target>1) ||
                (phase==1 && boundary) || (phase==2 && active!=target)) return false;
            for(unsigned i=28;i<988;++i) if(p[i]) return false;
            if(phase==2 && d->mode!=active) {
                d->mode=active;
                if(!active) { d->adc.have_sample=false; d->boundary=boundary; d->expect_boundary=true; }
            }
        } else {
            uint32_t period=get32(p+28),epoch=get32(p+32);
            if(!acquisition_valid(active,period) || epoch>UINT32_C(0x7fffffff) ||
               (phase!=3 && !acquisition_valid(target,boundary)) ||
               (phase==2 && (target!=active || boundary!=period || d->mode))) return false;
            for(unsigned i=36;i<988;++i) if(p[i]) return false;
            if(phase==2 && epoch==d->epoch && (active!=d->bits || period!=d->period)) return false;
            if(phase==2 && epoch!=d->epoch) {
                d->bits=active; d->period=period; d->epoch=epoch;
                d->adc.have_sample=false; d->expect_boundary=true; d->boundary=0;
            }
        }
        return true;
    }
    const ScopeNativeProfile *native=scope_native_find(d->bits,d->period);
    if(kind==20) return native && native_feed(d,p,native);
    if(native) return false;
    const bool mega=kind==19;
    const unsigned node_pairs=mega?3584U:2048U;
    const bool single=kind==16 || mega;
    const bool packed=kind==15 || kind==16;
    if((kind!=3 && !packed && !mega) || (packed && d->bits!=14) || (single!=(d->period==267 || d->period==242 || d->period==133)) || (mega!=(d->period==133)) || (mega && d->bits!=8) || get32(p+20) || get32(p+24) || get32(p+28) ||
       ((int32_t)get32(p+32)!=0 && get32(p+32)!=BLOCK) || get32(p+36) ||
       get32(p+56) || get32(p+60) || get32(p+76)!=(d->epoch<<1) ||
       get32(p+48)!=(single?160000000U:1000000U)/d->period || p[66]!=d->bits || p[67]!=(single?1:2) || get32(p+68)!=d->period) return false;
    unsigned count=get16(p+64); uint32_t index=get32(p+52);
    uint32_t node_offset=index-get32(p+72)*node_pairs;
    if(count>(mega?904U:single?516U:packed?258U:226U) || (packed && ((count|index)&(kind==16?3U:1U))) || (count && (d->mode || node_offset>=node_pairs || count>node_pairs-node_offset))) return false;
    for(unsigned i=84+(mega?count:single?count/4*7:packed?count/2*7:count*4);i<988;++i) if(p[i]) return false;
    if(!count) return !index && !get32(p+72) && !get32(p+80);
    if(d->expect_boundary && index!=d->boundary) return false;
    d->expect_boundary=false;
    for(unsigned i=0;i<count;++i) {
        uint32_t timestamp=get32(p+80)+i*d->period,current=index+i;
        uint32_t a=0,b=0;
        if(mega) { a=p[84+i]; } else if(single) {
            const uint8_t *group=p+84+(i/4)*7;
            const uint64_t word=(uint64_t)get32(group)|((uint64_t)group[4]<<32)|((uint64_t)group[5]<<40)|((uint64_t)group[6]<<48);
            a=(uint32_t)(word>>((i%4)*14))&16383U;
        } else if(packed) {
            const uint8_t *group=p+84+(i/2)*7;
            const uint32_t lo=get32(group),hi=(uint32_t)group[4]|((uint32_t)group[5]<<8)|((uint32_t)group[6]<<16);
            if(i&1) { a=(lo>>28)|((hi&1023U)<<4);b=hi>>10; }
            else { a=lo&16383U;b=(lo>>14)&16383U; }
        }
        else { const uint8_t *sample=p+84+i*4;a=get16(sample);b=get16(sample+2); }
        if(a>((1U<<d->bits)-1) || b>((1U<<d->bits)-1)) return false;
        if(d->adc.have_sample && (current-d->adc.previous_sample!=1 || timestamp-d->adc.previous_timestamp!=d->period)) return false;
        d->adc.have_sample=true; d->adc.previous_sample=current; d->adc.previous_timestamp=timestamp;
        ++d->adc.sample_pairs;
    }
    ++d->adc.valid_blocks;
    return true;
}
static bool dual_command(const uint8_t *p) {
    uint32_t id=get32(p+8);
    if(id<UINT32_C(0x80000000) || id==UINT32_MAX) return false;
    unsigned kind=get16(p+6);
    if(kind==2) { uint8_t expected[BLOCK]; ping(expected,id); return !memcmp(p,expected,BLOCK); }
    if(memcmp(p,"SCP1",4) || get16(p+4)!=4 || (kind!=4 && kind!=6 && kind!=8 && kind!=10 && kind!=11 && kind!=13) ||
       get32(p+12)!=972 || get32(p+988)!=crc32(p,988)) return false;
    if(kind==11 || kind==13) {
        unsigned end=28;
        if(kind==11) { if(p[20]>3 || p[21] || p[22] || p[23]) return false; if(p[20]==1) { uint32_t rate=get32(p+28); if(rate && rate!=20000 && rate!=40000 && rate!=50000) return false; end=32; } }
        else {
            unsigned count=get16(p+24);
            if(!count || count>480 || p[26] || p[27]) return false;
            end+=count*2;
            for(unsigned i=28;i<end;i+=2) if(get16(p+i)>4095) return false;
        }
        for(unsigned i=end;i<988;++i) if(p[i]) return false;
    } else if(kind==8 || kind==10) {
        if(kind==8 && (p[19]>1 || (p[19] && (p[16]!=4 || p[18])))) return false;
        if(kind==8 && p[36] && (p[36]>99 || p[16] || p[18])) return false;
        for(unsigned i=kind==10?16:37;i<988;++i) if(p[i]) return false;
    } else if(kind==6) {
        if(p[17] || p[18] || p[19]) return false;
        for(unsigned i=24;i<988;++i) if(p[i]) return false;
    } else for(unsigned i=17;i<988;++i) if(p[i]) return false;
    return true;
}
