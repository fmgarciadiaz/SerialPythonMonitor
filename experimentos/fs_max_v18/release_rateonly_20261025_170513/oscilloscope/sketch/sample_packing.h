#pragma once
#include <stdint.h>

namespace maxfreq_packing {
template <class Sample>
#if defined(__GNUC__) && !defined(__clang__)
__attribute__((always_inline))
#endif
inline unsigned pack(uint8_t *dest, const Sample *samples, unsigned count, unsigned bits) {
    if (bits == 8) {
        for (unsigned i = 0; i < count; ++i) dest[i] = uint8_t(samples[i].ch1);
        return count;
    }
    if (bits == 16) {
        for (unsigned i=0;i<count;++i) {
            dest[2*i]=uint8_t(samples[i].ch1);
            dest[2*i+1]=uint8_t(samples[i].ch1 >> 8);
        }
        return count*2U;
    }
    for (unsigned i = 0; i < count; i += 4) {
        const uint32_t a = samples[i].ch1, b = samples[i+1].ch1;
        const uint32_t c = samples[i+2].ch1, d = samples[i+3].ch1;
        uint32_t lo, hi;
        if (bits == 10) {
            lo = a | (b << 10) | (c << 20) | ((d & 3U) << 30);
            hi = d >> 2;
        } else if (bits == 12) {
            lo = a | (b << 12) | ((c & 255U) << 24);
            hi = (c >> 8) | (d << 4);
        } else {
            lo = a | (b << 14) | ((c & 15U) << 28);
            hi = (c >> 4) | (d << 10);
        }
        dest[0] = uint8_t(lo); dest[1] = uint8_t(lo >> 8);
        dest[2] = uint8_t(lo >> 16); dest[3] = uint8_t(lo >> 24);
        dest[4] = uint8_t(hi);
        if (bits >= 12) dest[5] = uint8_t(hi >> 8);
        if (bits == 14) dest[6] = uint8_t(hi >> 16);
        dest += bits / 2;
    }
    return count * bits / 8;
}
}

namespace maxfreq_packing {
template <class Pair>
#if defined(__GNUC__) && !defined(__clang__)
__attribute__((always_inline))
#endif
inline unsigned pack_dual(uint8_t *dest, const Pair *samples, unsigned count, unsigned bits) {
    if (bits == 8) {
        for (unsigned i=0;i<count;++i) {
            dest[2*i]=uint8_t(samples[i].ch1);
            dest[2*i+1]=uint8_t(samples[i].ch2);
        }
    } else if (bits == 12) {
        for (unsigned i=0;i<count;++i) {
            const uint32_t word=uint32_t(samples[i].ch1)|(uint32_t(samples[i].ch2)<<12);
            dest[3*i]=uint8_t(word);dest[3*i+1]=uint8_t(word>>8);dest[3*i+2]=uint8_t(word>>16);
        }
    } else if (bits == 16) {
        for (unsigned i=0;i<count;++i) {
            dest[4*i]=uint8_t(samples[i].ch1);dest[4*i+1]=uint8_t(samples[i].ch1>>8);
            dest[4*i+2]=uint8_t(samples[i].ch2);dest[4*i+3]=uint8_t(samples[i].ch2>>8);
        }
    } else {
        for (unsigned i=0;i<count;i+=2) {
            const uint32_t a=samples[i].ch1,b=samples[i].ch2,c=samples[i+1].ch1,d=samples[i+1].ch2;
            const uint32_t lo=bits==10?a|(b<<10)|(c<<20)|((d&3U)<<30):a|(b<<14)|((c&15U)<<28);
            const uint32_t hi=bits==10?d>>2:(c>>4)|(d<<10);
            dest[0]=uint8_t(lo);dest[1]=uint8_t(lo>>8);dest[2]=uint8_t(lo>>16);dest[3]=uint8_t(lo>>24);dest[4]=uint8_t(hi);
            if(bits==14){dest[5]=uint8_t(hi>>8);dest[6]=uint8_t(hi>>16);}
            dest+=bits==10?5:7;
        }
    }
    return count*bits*2U/8U;
}
}
