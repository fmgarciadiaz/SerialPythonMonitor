#pragma once
static bool acquisition_valid(unsigned bits,uint32_t period) {
    if(bits!=8 && bits!=10 && bits!=12 && bits!=14 && bits!=16) return false;
    if (bits==16 && period<16) return false;
    switch(period) { case 4: case 5: case 8: case 10: case 16: case 20: case 25: case 32:case 40:case 50:case 64:case 80:case 100:case 125:
        case 200:case 250:case 500:case 1000:return true; }
    return false;
}
typedef struct {
    Checker adc;
    bool have_sequence,expect_boundary;
    uint32_t sequence,boundary,period,epoch;
    unsigned mode,bits;
} DualChecker;
static bool dual_feed(DualChecker *d,const uint8_t *p) {
    if(memcmp(p,"SCP1",4) || get16(p+4)!=3 || get32(p+12)!=972 || get32(p+988)!=crc32(p,988)) return false;
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
            ((phase==3)!=(reason!=0)) || p[22]>1 || p[23]>1) return false;
        for(unsigned base=24;base<=44;base+=20) {
            if(base==44 && phase==3) break;
            const uint8_t *c=p+base;
            if(c[0]>4 || c[1]>1 || c[2]>2 || c[3]>1 || (c[3] && (c[0]!=4 || c[2])) || get32(c+4)<100 || get32(c+4)>20000000 ||
                get32(c+8)<100 || get32(c+8)>20000000 || get16(c+12)>get16(c+14) || get16(c+14)>4095 ||
                !get32(c+16) || (c[3] ? (get32(c+16)<100 || get32(c+16)>65535) : get32(c+16)>600000) || (c[0]==4 && c[2])) return false;
        }
        if(p[22] && !p[25]) return false;
        if(phase==2 && memcmp(p+24,p+44,20)) return false;
        for(unsigned i=64;i<988;++i) if(p[i]) return false;
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
    if(kind!=3 || get32(p+20) || get32(p+24) || get32(p+28) ||
       ((int32_t)get32(p+32)!=0 && get32(p+32)!=BLOCK) || get32(p+36) ||
       get32(p+56) || get32(p+60) || get32(p+76)!=(d->epoch<<1) ||
       get32(p+48)!=1000000/d->period || p[66]!=d->bits || p[67]!=2 || get32(p+68)!=d->period) return false;
    unsigned count=get16(p+64); uint32_t index=get32(p+52);
    if(count>113 || (count && (d->mode || get32(p+72)*2048U!=index-index%2048 || count>2048-index%2048))) return false;
    for(unsigned i=80+count*8;i<988;++i) if(p[i]) return false;
    if(!count) return !index && !get32(p+72);
    if(d->expect_boundary && index!=d->boundary) return false;
    d->expect_boundary=false;
    for(unsigned i=0;i<count;++i) {
        const uint8_t *sample=p+80+i*8; uint32_t timestamp=get32(sample),current=index+i;
        if(get16(sample+4)>((1U<<d->bits)-1) || get16(sample+6)>((1U<<d->bits)-1)) return false;
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
    if(memcmp(p,"SCP1",4) || get16(p+4)!=3 || (kind!=4 && kind!=6 && kind!=8 && kind!=10 && kind!=11 && kind!=13) ||
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
        for(unsigned i=kind==10?16:36;i<988;++i) if(p[i]) return false;
    } else if(kind==6) {
        if(p[17] || p[18] || p[19]) return false;
        for(unsigned i=24;i<988;++i) if(p[i]) return false;
    } else for(unsigned i=17;i<988;++i) if(p[i]) return false;
    return true;
}
