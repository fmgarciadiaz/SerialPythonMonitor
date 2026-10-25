#pragma once
#include <new>
#include "scope_protocol.h"
#include "native_profiles.h"
#include "frame_buffer.h"

namespace scope_storage {
constexpr unsigned slots = 4;
constexpr unsigned max_slots = 8;
struct SingleSample { uint16_t ch1; };
struct Node {
    uint32_t index, timestamp;
    ChannelPair *samples;
    SingleSample *single_samples;
};
struct FastSingleSamples {
    SingleSample samples[max_slots][3488U];
    Node nodes[max_slots];
};
struct SingleMemory {
    alignas(32) uint16_t adc[SCOPE_NATIVE_MAX_SINGLE * 2U];
    alignas(32) uint32_t timestamps[SCOPE_NATIVE_MAX_SINGLE * 2U];
    union {
        SingleSample samples[slots*SCOPE_NATIVE_MAX_SINGLE];
        FastSingleSamples fast;
    };
};
struct DualMemory {
    alignas(32) uint16_t adc[SCOPE_NATIVE_MAX_DUAL * 4U];
    alignas(32) uint32_t timestamps[SCOPE_NATIVE_MAX_DUAL * 2U];
    ChannelPair samples[slots][SCOPE_NATIVE_MAX_DUAL];
    // Producer/SPI own these until the final physical DMA ACK.
    SampleFrame spi_scratch[2];
};
union Memory { SingleMemory single; DualMemory dual; };

// Preserve the original DMA and sample offsets; scratch occupies only the tail.
static_assert(offsetof(DualMemory, adc) == 0U, "Dual ADC offset unchanged");
static_assert(offsetof(DualMemory, timestamps) == sizeof(DualMemory::adc),
              "Dual timestamp DMA offset unchanged");
static_assert(offsetof(DualMemory, samples) == sizeof(DualMemory::adc)+sizeof(DualMemory::timestamps),
              "Dual samples offset unchanged and DMA arrays do not overlap");
static_assert(offsetof(DualMemory, spi_scratch) == offsetof(DualMemory, samples)+sizeof(DualMemory::samples),
              "Dual SPI scratch follows all DMA and sample storage");
static_assert(offsetof(DualMemory, spi_scratch) % alignof(SampleFrame) == 0U,
              "Dual SPI scratch alignment");
static_assert(alignof(DualMemory) >= alignof(SampleFrame), "Dual arena frame alignment");
static_assert(sizeof(SampleFrame) == scope_bench::BLOCK_BYTES, "No SPI frame padding");
static_assert(sizeof(DualMemory::spi_scratch) == 2U*scope_bench::BLOCK_BYTES,
              "Exactly two dual pipeline scratch frames");
static_assert(sizeof(DualMemory) <= sizeof(SingleMemory), "Dual scratch fits existing union arena");
static_assert(sizeof(Memory) == sizeof(SingleMemory), "SPI scratch must not increase Memory size");

struct Storage {
    Memory memory;
    Node queue[slots];
    uint16_t *adc;
    uint32_t *timestamps;
    Node &at(unsigned index,unsigned active_slots=slots) {
        if(active_slots==max_slots) {
            return memory.single.fast.nodes[index];
        }
        return queue[index];
    }
    // Caller stops both DMA channels and the producer, and owns no borrowed
    // queue slot. Placement construction changes union lifetime, without heap.
    void bind(bool compact_single,unsigned active_slots=slots,unsigned pairs=SCOPE_NATIVE_MAX_SINGLE) {
        if (compact_single) {
            auto *m = new (&memory.single) SingleMemory;
            adc=m->adc; timestamps=m->timestamps;
            if(active_slots==max_slots) {
                auto *fast=new (&m->fast) FastSingleSamples;
                for(unsigned i=0;i<max_slots;++i) {
                    fast->nodes[i].single_samples=fast->samples[i];
                    fast->nodes[i].samples=nullptr;
                }
            } else {
                for(unsigned i=0;i<slots;++i) {
                    queue[i].single_samples=m->samples+i*pairs;
                    queue[i].samples=nullptr;
                }
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

static_assert(scope_storage::max_slots*3488U <= scope_storage::slots*SCOPE_NATIVE_MAX_SINGLE,"Eight 3488-sample nodes fit existing CH1 sample arena");

static_assert(scope_storage::max_slots*3488U*sizeof(scope_storage::SingleSample)+scope_storage::max_slots*sizeof(scope_storage::Node) <= sizeof(scope_storage::SingleMemory::samples),"Eight nodes plus descriptors fit existing sample arena");

static_assert(sizeof(scope_storage::FastSingleSamples)<=sizeof(scope_storage::SingleMemory::samples),"Fast descriptors do not increase static arena size");
