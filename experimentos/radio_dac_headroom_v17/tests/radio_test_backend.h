#pragma once
#include "../oscilloscope/sketch/wav_protocol.h"
namespace wav_hw {
constexpr unsigned WAVEFORM_POINTS=scope_wav::SLOTS*scope_wav::POINTS/2;
static uint32_t data[WAVEFORM_POINTS];
inline uint32_t *begin_waveform(){return data;}
}
