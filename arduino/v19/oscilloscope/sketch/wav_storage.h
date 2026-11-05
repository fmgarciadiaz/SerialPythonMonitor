#pragma once
#include <cstdint>
#include <new>
#include "wav_protocol.h"
namespace wav_storage {
constexpr unsigned PCM_POINTS=scope_wav::SLOTS*scope_wav::POINTS;
constexpr unsigned WAVEFORM_POINTS=PCM_POINTS/2;
union Memory { uint16_t pcm[PCM_POINTS];uint32_t waveform[WAVEFORM_POINTS]; };
static_assert(sizeof(Memory)<=16U*480U*sizeof(uint32_t),"DAC RAM must not grow");
inline uint16_t *begin_pcm(Memory &memory) {return new (&memory.pcm) uint16_t[PCM_POINTS];}
inline uint32_t *begin_waveform(Memory &memory) {return new (&memory.waveform) uint32_t[WAVEFORM_POINTS];}
}
