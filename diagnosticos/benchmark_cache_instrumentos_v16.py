"""Exact full-DAC comparison across actual presets and controls, before/after."""
import sys,json,time,importlib.util,argparse
from pathlib import Path
from dataclasses import replace,asdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from monitor.v16 import fm_source as current
from diagnosticos.synth_presets_v16 import panel_presets

def render(module,p,rate,blocks=180):
    p=module.FMParameters(**asdict(p));source=module.FMSource(rate,p);source.prepare_audio();audio=[];times=[]
    for block in range(blocks):
        if block%15==0:
            step=block//15;base=36+(step%4)*7;notes=tuple((base+i,70+i*5%55) for i in range(11)) if step%4!=3 else ()
            source.update(replace(p,notes=notes,note_id=step+1,virtual_sustain=step%4!=3,drive=1+step%3*.3,filter_mix=.25+(step%3)*.25))
        began=time.perf_counter();audio.append(source.render_dac_codes(block*480,(block+1)*480,2.5,1.65));times.append((time.perf_counter()-began)*1000)
    return np.concatenate(audio),dict(median_ms=float(np.median(times)),p95_ms=float(np.percentile(times,95)))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('reference',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('fm_cache_reference',args.reference);old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    cases=[]
    for rate in (20000,40000):
        for name,p in panel_presets(current.PRESETS,rate).items():
            render(old,p,rate,2);render(current,p,rate,2)
            a,before=render(old,p,rate);b,after=render(current,p,rate);np.testing.assert_array_equal(a,b)
            cases.append(dict(preset=name,rate=rate,samples=len(a),exact=True,before=before,after=after))
    path=args.output or ROOT/'diagnosticos/resultados_piano/eficiencia_v16/20261010_cache_instrumentos.json';path.write_text(json.dumps(dict(scope='Host only, sequential full-DAC A/B, timing can vary',cases=cases),indent=2)+'\n');print(path)
if __name__=='__main__':main()
