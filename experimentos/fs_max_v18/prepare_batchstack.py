"""Keep native dual scratch in the permanent output worker stack, not new BSS.

The output thread never returns; its two aligned frames remain live while the
producer builds and SPI copies them. Ownership credits still wait for DMA EOT.
"""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent
OUT=EXP/'batchstack'

def prepare():
    for name in ('oscilloscope','relay'):
        shutil.copytree(EXP/'batchnative'/name,OUT/name,dirs_exist_ok=True)
    shutil.copyfile(EXP/'batchnative/candidate_profiles.json',OUT/'candidate_profiles.json')
    p=OUT/'oscilloscope/sketch/sketch.ino';s=p.read_text()
    s=s.replace('static SampleFrame dual_pipeline_frames[FRAME_SLOTS-1U];',
                'static SampleFrame *dual_pipeline_frames=nullptr;')
    s=s.replace('static void output_worker(void *, void *, void *) {',
                'static void output_worker(void *, void *, void *) {\n'
                '    // Worker lifetime is permanent, including across acquisition epochs.\n'
                '    // Frames use 1984 of its existing 4096-byte stack; no new BSS arena.\n'
                '    SampleFrame dual_scratch[FRAME_SLOTS-1U];\n'
                '    dual_pipeline_frames=dual_scratch;')
    assert s.count('dual_scratch')==2
    p.write_text(s)
    for rel in ('oscilloscope/app.yaml','oscilloscope/python/main.py'):
        p=OUT/rel;p.write_text(p.read_text().replace('Scope V18 Rate Probe BatchNative','Scope V18 Rate Probe BatchStack'))

if __name__=='__main__':prepare()
