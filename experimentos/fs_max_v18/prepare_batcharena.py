"""Place BatchNative's two dual pipeline frames inside the existing union arena.

Only the DualMemory tail and frame_slot backing store change. The SingleMemory
member still determines Memory/Storage size; DMA offsets, pipeline ownership,
ADC validation, clocks, and worker stack are inherited unchanged.
"""
import shutil
from pathlib import Path

EXP = Path(__file__).resolve().parent
OUT = EXP / 'batcharena'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected one BatchNative source anchor: {old!r}')
    return text.replace(old, new, 1)


ASSERTIONS = '''
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
'''


def prepare(output=OUT):
    output = Path(output)
    for name in ('oscilloscope', 'relay'):
        shutil.copytree(EXP / 'batchnative' / name, output / name, dirs_exist_ok=True)
    shutil.copyfile(EXP / 'batchnative/candidate_profiles.json', output / 'candidate_profiles.json')
    path = output / 'oscilloscope/sketch/acquisition_storage.h'
    text = replace_once(path.read_text(), '#include "native_profiles.h"',
                        '#include "native_profiles.h"\n#include "frame_buffer.h"')
    text = replace_once(text, '    ChannelPair samples[slots][SCOPE_NATIVE_MAX_DUAL];\n};',
                        '    ChannelPair samples[slots][SCOPE_NATIVE_MAX_DUAL];\n'
                        '    // Producer/SPI own these until the final physical DMA ACK.\n'
                        '    SampleFrame spi_scratch[2];\n};')
    text = replace_once(text, 'union Memory { SingleMemory single; DualMemory dual; };',
                        'union Memory { SingleMemory single; DualMemory dual; };\n' + ASSERTIONS)
    path.write_text(text)
    path = output / 'oscilloscope/sketch/sketch.ino'
    text = replace_once(path.read_text(),
        '// Native dual DMA uses its timestamp arena: never place scratch there.\n'
        'static SampleFrame dual_pipeline_frames[FRAME_SLOTS-1U];',
        '// Native dual scratch lives after DMA and samples, inside the existing union arena.\n'
        'static_assert(FRAME_SLOTS-1U == 2U, "Dual arena scratch frame count");')
    text = replace_once(text, '        return &dual_pipeline_frames[slot-1U];',
                        '        return &acquisition::storage.memory.dual.spi_scratch[slot-1U];')
    path.write_text(text)
    for relative in ('oscilloscope/app.yaml', 'oscilloscope/python/main.py'):
        path = output / relative
        path.write_text(replace_once(path.read_text(), 'Scope V18 Rate Probe BatchNative',
                                     'Scope V18 Rate Probe BatchArena'))


if __name__ == '__main__':
    prepare()
