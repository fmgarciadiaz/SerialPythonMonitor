#pragma once
#include <new>
#include "scope_protocol.h"
#include "native_profiles.h"

namespace scope_storage {
constexpr unsigned slots = 4;
struct SingleSample { uint16_t ch1; };
struct Node {
    uint32_t index, timestamp;
    ChannelPair *samples;
    SingleSample *single_samples;
};
struct SingleMemory {
    alignas(32) uint16_t adc[SCOPE_NATIVE_MAX_SINGLE * 2U];
    alignas(32) uint32_t timestamps[SCOPE_NATIVE_MAX_SINGLE * 2U];
    SingleSample samples[slots][SCOPE_NATIVE_MAX_SINGLE];
};
struct DualMemory {
    alignas(32) uint16_t adc[SCOPE_NATIVE_MAX_DUAL * 4U];
    alignas(32) uint32_t timestamps[SCOPE_NATIVE_MAX_DUAL * 2U];
    ChannelPair samples[slots][SCOPE_NATIVE_MAX_DUAL];
};
union Memory { SingleMemory single; DualMemory dual; };
struct Storage {
    Memory memory;
    Node queue[slots];
    uint16_t *adc;
    uint32_t *timestamps;
    // Caller stops both DMA channels and the producer, and owns no borrowed
    // queue slot. Placement construction changes union lifetime, without heap.
    void bind(bool compact_single) {
        if (compact_single) {
            auto *m = new (&memory.single) SingleMemory;
            adc=m->adc; timestamps=m->timestamps;
            for(unsigned i=0;i<slots;++i) {
                queue[i].single_samples=m->samples[i]; queue[i].samples=nullptr;
            }
        } else {
            auto *m = new (&memory.dual) DualMemory;
            adc=m->adc; timestamps=m->timestamps;
            for(unsigned i=0;i<slots;++i) {
                queue[i].samples=m->samples[i]; queue[i].single_samples=nullptr;
            }
        }
    }
};
static_assert(SCOPE_NATIVE_MAX_DUAL >= 3584U, "Legacy pair-backed CH1 fits");
static_assert(sizeof(DualMemory::timestamps) >= 4096U*sizeof(uint32_t)+sizeof(Packet),
              "Legacy UART timestamp nodes and scratch fit");
}
