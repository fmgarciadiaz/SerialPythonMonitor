#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#if defined(__arm__) && defined(__GNUC__) && !defined(__clang__)
#define C8_HOT __attribute__((optimize("O2")))
#else
#define C8_HOT
#endif

/* SCP1 v4 experimental kind21: ADC8/CH1 only, 80-byte header, 908 samples.
 * Canonical scratch storage needs1024 bytes; physical SPI remains992.
 * count bit15 encodes prior SPI return992; bit14 signals transport fault.
 * Every dynamic acquisition/timing metric is retained. */
C8_HOT static inline uint16_t c8_u16(const uint8_t *p) { return (uint16_t)(p[0]|((uint16_t)p[1]<<8)); }
C8_HOT static inline uint32_t c8_u32(const uint8_t *p) { return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
C8_HOT static inline void c8_p16(uint8_t *p,uint16_t v) {p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
C8_HOT static inline void c8_p32(uint8_t *p,uint32_t v) {for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
C8_HOT static inline void c8_pack(uint8_t *p) {
    uint8_t h[80]={0};memcpy(h,p,16);c8_p16(h+6,21);
    c8_p32(h+16,c8_u32(p+16));
    c8_p32(h+20,(c8_u32(p+84)<<16)|c8_u32(p+68));
    const unsigned old_fields[]={52,72,76,80};
    for(unsigned i=0;i<4;i++)c8_p32(h+24+4*i,c8_u32(p+old_fields[i]));
    uint16_t count=c8_u16(p+64);
    const uint32_t result=c8_u32(p+32);
    const bool fault=c8_u32(p+20)||c8_u32(p+24)||c8_u32(p+28)||c8_u32(p+36)||
        (result && result!=992)||c8_u32(p+88)>4||c8_u32(p+92)>4;
    c8_p16(h+40,(uint16_t)(count|(result==992?0x8000:0)|(fault?0x4000:0)));
    h[42]=(uint8_t)c8_u32(p+88);h[43]=(uint8_t)c8_u32(p+92);
    const unsigned fields[]={56,60,40,44,96,100,104,108,112};
    for(unsigned i=0;i<9;i++)c8_p32(h+44+4*i,c8_u32(p+fields[i]));
    memmove(p+80,p+116,count);memcpy(p,h,80);
    memset(p+80+count,0,988-80-count);
}
C8_HOT static inline void c8_expand(uint8_t *out,const uint8_t *p) {
    memset(out,0,1024);memcpy(out,p,16);c8_p16(out+6,20);
    c8_p32(out+16,c8_u32(p+16));
    uint32_t config=c8_u32(p+20),ticks=config&65535,n=config>>16;
    c8_p32(out+32,c8_u16(p+40)&0x8000?992:0);
    c8_p32(out+20,c8_u16(p+40)&0x4000?1:0); /* propagate fault, never erase it */
    const unsigned old_fields[]={52,72,76,80};
    for(unsigned i=0;i<4;i++)c8_p32(out+old_fields[i],c8_u32(p+24+4*i));
    c8_p16(out+64,c8_u16(p+40)&0x3fff);out[66]=8;out[67]=1;
    c8_p32(out+48,ticks?160000000U/ticks:0);c8_p32(out+68,ticks);c8_p32(out+84,n);
    c8_p32(out+88,p[42]);c8_p32(out+92,p[43]);
    const unsigned fields[]={56,60,40,44,96,100,104,108,112};
    for(unsigned i=0;i<9;i++)c8_p32(out+fields[i],c8_u32(p+44+4*i));
    memcpy(out+116,p+80,908);
}

#undef C8_HOT
