"""Pipeline native dual frames without borrowing their active timestamp RAM.

Separate candidate: the physically qualified BatchFast sources stay unchanged.
ADC validation and SPI clock/DMA recipe selection remain unchanged.
"""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent
OUT=EXP/'batchnative'

def prepare():
    for name in ('oscilloscope','relay'):
        shutil.copytree(EXP/'batchfast'/name,OUT/name,dirs_exist_ok=True)
    shutil.copyfile(EXP/'batchfast/candidate_profiles.json',OUT/'candidate_profiles.json')
    p=OUT/'oscilloscope/sketch/sketch.ino';s=p.read_text()
    s=s.replace('static bool batch_dma_word=false, batch_dma_high=false;',
                'static bool batch_dma_word=false, batch_dma_high=false, batch_pipeline=false;')
    s=s.replace('static SampleFrame ordinary_frame;',
                'static SampleFrame ordinary_frame;\n'
                '// Native dual DMA uses its timestamp arena: never place scratch there.\n'
                'static SampleFrame dual_pipeline_frames[FRAME_SLOTS-1U];')
    s=s.replace('    if(!slot) return &ordinary_frame;',
                '    if(!slot) return &ordinary_frame;\n'
                '    if(acquisition::native() && !acquisition::single())\n'
                '        return &dual_pipeline_frames[slot-1U];')
    s=s.replace('const bool pipelined=high_rate_transport();',
                'const bool pipelined=high_rate_transport() || (acquisition::native() && !acquisition::single());')
    s=s.replace('const bool pipelined=batch_dma_high;',
                'const bool pipelined=batch_pipeline;')
    s=s.replace('    batch_dma_high=high_rate_transport();',
                '    batch_dma_high=high_rate_transport();\n'
                '    batch_pipeline=batch_dma_high || (acquisition::native() && !acquisition::single());')
    # No new acquisition fast path: dual packing and validation are unchanged.
    assert s.count('dual_pipeline_frames')==2
    assert s.count('batch_pipeline')==3
    p.write_text(s)
    for rel in ('oscilloscope/app.yaml','oscilloscope/python/main.py'):
        p=OUT/rel;p.write_text(p.read_text().replace('Scope V18 Rate Probe BatchFast','Scope V18 Rate Probe BatchNative'))

if __name__=='__main__':prepare()
