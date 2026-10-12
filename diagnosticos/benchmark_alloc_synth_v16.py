"""A/B host render benchmark against a saved fm_source.py; no board access."""
import argparse,gc,importlib.util,json,sys,time
from pathlib import Path
from dataclasses import replace
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.v16 import fm_source as current
from monitor.v16.virtual_instruments import warmup
from monitor.v16.fm_feedback import warmup as feedback_warmup


def run(module,rate,kind,blocks):
    p=module.FMParameters(preset='Piano Virtual' if kind=='piano' else 'Manual',
        waveform='virtual' if kind=='piano' else 'fm',virtual_model='piano',
        oscillator_levels=(1.,0.,0.) if kind=='piano' else (1.,.25,.15),notes=())
    source=module.FMSource(rate,p);source.prepare_audio()
    elapsed=[];audio=[];collections=[];starts={}
    def observe(phase,info):
        g=info['generation']
        if phase=='start':starts[g]=time.perf_counter()
        elif g in starts:collections.append((time.perf_counter()-starts.pop(g))*1000)
    gc.collect();gc.callbacks.append(observe)
    try:
        for block in range(blocks):
            if block%15==0:
                step=block//15;base=36+(step%4)*7
                notes=tuple((base+i,70+i*5%55) for i in range(11)) if step%4!=3 else ()
                source.update(replace(p,notes=notes,note_id=step+1,virtual_sustain=step%4!=3))
            start=block*480;began=time.perf_counter()
            codes=source.render_dac_codes(start,start+480,1.0,1.65)
            elapsed.append((time.perf_counter()-began)*1000);audio.append(codes)
    finally:gc.callbacks.remove(observe)
    return np.concatenate(audio),dict(median_ms=float(np.median(elapsed)),p95_ms=float(np.percentile(elapsed,95)),max_ms=max(elapsed),gc_count=len(collections),gc_max_ms=max(collections,default=0))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference',type=Path);p.add_argument('--blocks',type=int,default=300);p.add_argument('--output',type=Path);args=p.parse_args()
    spec=importlib.util.spec_from_file_location('fm_alloc_reference',args.reference);reference=importlib.util.module_from_spec(spec);sys.modules[spec.name]=reference;spec.loader.exec_module(reference)
    warmup();feedback_warmup();report=[]
    # Warm both implementations before comparisons; alternate order to limit bias.
    for module in (reference,current):run(module,20000,'piano',2)
    for rate in (20000,40000):
        for kind in ('piano','fm'):
            old,a=run(reference,rate,kind,args.blocks);new,b=run(current,rate,kind,args.blocks)
            np.testing.assert_array_equal(new,old)
            report.append(dict(rate=rate,model=kind,samples=len(new),identical=True,before=a,after=b))
    result=dict(scope='Host only, sequential runs, not MIDI/acoustic/transport latency',cases=report)
    text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text)

if __name__=='__main__':main()
