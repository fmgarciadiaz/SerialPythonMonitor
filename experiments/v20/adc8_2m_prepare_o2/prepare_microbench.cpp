// Isolated proxy for the ADC8/2M sample half of prepare_batch_half.
// It does not include Zephyr scheduling, DMA, queues, or the SPI wire.
#include "benchmark_protocol.h"

#define PREP_BODY() do { \
    __builtin_memcpy(packet, sample, scope_bench::BLOCK_BYTES); \
    scope_bench::data_frame(packet, sequence, 0x81234567U, 0, 0, 0, 992, 0, 140, 60); \
    scope_bench::put16(packet + 6, 20); \
    scope_bench::seal(packet); \
} while (0)

#if defined(__GNUC__) && !defined(__clang__)
#define BASE_ATTR __attribute__((noinline,optimize("Os")))
#define CAND_ATTR __attribute__((noinline,optimize("O2")))
#else
#define BASE_ATTR __attribute__((noinline))
#define CAND_ATTR __attribute__((noinline))
#endif

extern "C" BASE_ATTR void prepare_os(unsigned char *packet, const unsigned char *sample,
                                      unsigned sequence) { PREP_BODY(); }
extern "C" CAND_ATTR void prepare_o2(unsigned char *packet, const unsigned char *sample,
                                      unsigned sequence) { PREP_BODY(); }

#ifndef ARM_CHECK
#include <chrono>
#include <cstdio>
#include <cstring>

using Clock = std::chrono::steady_clock;
using Prepare = void (*)(unsigned char *, const unsigned char *, unsigned);

static double measure(Prepare prepare, const unsigned char *source, unsigned rounds,
                      volatile unsigned &sink) {
    alignas(32) unsigned char packet[scope_bench::BLOCK_BYTES];
    auto begin=Clock::now();
    for(unsigned i=0;i<rounds;++i) {
        prepare(packet,source,i);
        sink=sink ^ packet[i%scope_bench::BLOCK_BYTES];
    }
    return std::chrono::duration<double,std::micro>(Clock::now()-begin).count()/rounds;
}

int main() {
    alignas(32) unsigned char source[scope_bench::BLOCK_BYTES];
    alignas(32) unsigned char a[scope_bench::BLOCK_BYTES],b[scope_bench::BLOCK_BYTES];
    for(unsigned i=0;i<sizeof(source);++i)source[i]=static_cast<unsigned char>((i*17U+43U)^0x5aU);
    for(unsigned i=0;i<256;++i) {
        prepare_os(a,source,i);prepare_o2(b,source,i);
        if(std::memcmp(a,b,sizeof(a))!=0 || scope_bench::get32(a+988)!=scope_bench::crc32(a,988))return 2;
    }
    volatile unsigned sink=0;
    constexpr unsigned rounds=20000;
    measure(prepare_os,source,rounds,sink);measure(prepare_o2,source,rounds,sink);
    std::printf("{\"equal_frames\":256,\"crc_checked\":true,\"rounds\":%u,\"pairs\":[",rounds);
    for(unsigned pair=0;pair<7;++pair) {
        const bool reverse=(pair&1U)!=0;
        const double first=measure(reverse?prepare_o2:prepare_os,source,rounds,sink);
        const double second=measure(reverse?prepare_os:prepare_o2,source,rounds,sink);
        std::printf("%s{\"os_us\":%.6f,\"o2_us\":%.6f}",pair?",":"",reverse?second:first,reverse?first:second);
    }
    std::printf("],\"sink\":%u}\n",static_cast<unsigned>(sink));
}
#endif
