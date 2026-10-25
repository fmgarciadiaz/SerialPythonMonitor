"""Render every actual GUI preset under eleven-note chord/pedal/release load."""
import sys,time,json
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from diagnosticos.synth_presets_v16 import panel_presets
from monitor.historico.v16.fm_source import FMSource,PRESETS
from monitor.historico.v16.virtual_instruments import warmup
from monitor.historico.v16.fm_feedback import warmup as feedback_warmup

def main():
    warmup();feedback_warmup();cases=[]
    for rate in (20000,40000):
        for name,p in panel_presets(PRESETS,rate).items():
            source=FMSource(rate,p);source.prepare_audio();elapsed=[];peak=0
            for block in range(180):
                if block%15==0:
                    step=block//15;base=36+(step%4)*7
                    notes=tuple((base+i,70+i*5%55) for i in range(11)) if step%4!=3 else ()
                    source.update(replace(p,notes=notes,note_id=step+1,virtual_sustain=step%4!=3))
                began=time.perf_counter();codes=source.render_dac_codes(block*480,(block+1)*480,2.5,1.65);elapsed.append((time.perf_counter()-began)*1000)
                assert codes.dtype==np.uint16 and len(codes)==480 and np.max(codes)<=4095
                peak=max(peak,len(source.voices))
            cases.append(dict(preset=name,rate=rate,voices=peak,median_ms=float(np.median(elapsed)),p95_ms=float(np.percentile(elapsed,95)),max_ms=max(elapsed),block_ms=480000/rate))
    path=ROOT/'diagnosticos/resultados_piano/eficiencia_v16/20261010_instrumentos.json';path.write_text(json.dumps(dict(scope='Host only, actual GUI patches, no acoustic/transport acceptance',cases=cases),indent=2)+'\n');print(path)
if __name__=='__main__':main()
