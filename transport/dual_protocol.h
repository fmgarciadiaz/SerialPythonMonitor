#pragma once
/* Uses the validated ADC checker included by the relay. */
typedef struct {
    Checker adc;
    bool have_sequence, expect_boundary;
    uint32_t sequence, boundary;
    unsigned mode;
} DualChecker;
static bool dual_feed(DualChecker *d, const uint8_t *p) {
    if (memcmp(p,"SCP1",4) || get16(p+4)!=2 || get32(p+12)!=492 ||
        get32(p+508)!=crc32(p,508)) return false;
    uint32_t seq=get32(p+8);
    if (d->have_sequence && seq-d->sequence!=1) return false;
    d->sequence=seq; d->have_sequence=true;
    unsigned kind=get16(p+6);
    if (kind==5) {
        unsigned target=p[20], active=p[21], phase=p[22], reason=p[23];
        uint32_t rid=get32(p+16), boundary=get32(p+24);
        if (rid<UINT32_C(0x80000000) || rid==UINT32_MAX || active>1 ||
            phase<1 || phase>3 || reason>4 || boundary%2048 ||
            ((phase==3)!=(reason!=0)) || (phase!=3 && target>1) ||
            (phase==1 && boundary) || (phase==2 && active!=target)) return false;
        for (unsigned i=28;i<508;++i) if (p[i]) return false;
        if (phase==2 && d->mode!=active) {
            d->mode=active;
            if (!active) {
                d->adc.have_sample=false;
                d->boundary=boundary; d->expect_boundary=true;
            }
        }
        return true;
    }
    if (kind!=3 || get32(p+20) || get32(p+24) || get32(p+28) ||
        ((int32_t)get32(p+32)!=0 && get32(p+32)!=BLOCK) || get32(p+36) ||
        get32(p+56) || get32(p+60) || get32(p+76) ||
        get32(p+48)!=31250 || p[66]!=14 || p[67]!=2 || get32(p+68)!=32) return false;
    unsigned count=get16(p+64);
    if (!count) {
        if (get32(p+52) || get32(p+72)) return false;
        for (unsigned i=80;i<508;++i) if (p[i]) return false;
        return true;
    }
    if (d->mode || (d->expect_boundary && get32(p+52)!=d->boundary)) return false;
    d->expect_boundary=false;
    /* DATA checker retains sample continuity across control/idle frames.
       Replace only its private sequence with a DATA-only sequence. */
    d->adc.previous=seq-1;
    d->adc.have_previous=true;
    feed(&d->adc,p,BLOCK,false,0);
    return integrity(&d->adc) && !d->adc.first[0] && !d->adc.first[1] && !d->adc.first[2];
}
static bool dual_command(const uint8_t *p) {
    uint32_t id=get32(p+8);
    if (id<UINT32_C(0x80000000) || id==UINT32_MAX) return false;
    if (get16(p+6)==2) {
        uint8_t expected[BLOCK]; ping(expected,id);
        return !memcmp(p,expected,BLOCK);
    }
    if (memcmp(p,"SCP1",4) || get16(p+4)!=2 || get16(p+6)!=4 ||
        get32(p+12)!=492 || get32(p+508)!=crc32(p,508)) return false;
    for (unsigned i=17;i<508;++i) if (p[i]) return false;
    return true; /* Unsupported mode gets an explicit MCU rejection. */
}
