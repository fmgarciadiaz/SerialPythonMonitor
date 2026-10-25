"""Offline synth CPU measurement; never opens hardware. Run from repository root."""
import json,platform,time
from dataclasses import replace
from pathlib import Path
import numpy as np
from monitor.v18.fm_source import FMSource,FMParameters

PATCHES={
 'Seno limpio':FMParameters(preset='Seno limpio',waveform='sine'),
 'DX Piano (3 osciladores)':FMParameters(preset='DX Piano',index=2,modulator=440,
     envelope=(.003,3.4,0,.28),oscillator_levels=(.555,.185,.26),
     osc2_wave='fm',osc2_fm_ratio=14,osc2_fm_amount=.55,osc2_detune=3.5,
     osc2_envelope=(.003,1.8,0,.16),osc3_amount=1.4,osc3_detune=-7,
     osc3_feedback=4.0,bell_ratio=1,bell_mix=0,brightness_decay=2.4,
     fm_body_envelope=(.003,3.4,0,.28)),
 'Piano Virtual':FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',room_mix=.06),
}

def main():
 results=[]
 for rate in (20000,40000):
  for name,patch in PATCHES.items():
   for count in (11,20):
    p=replace(patch,notes=tuple((n,100) for n in range(48,48+count)))
    started=time.perf_counter();warm=FMSource(rate,p);warm.render_dac_codes(0,480,1.,1.65)
    warm_ms=(time.perf_counter()-started)*1000
    source=FMSource(rate,p);times=[]
    # Every case covers the same 1.2 s phrase. Exclude compilation/prewarm.
    blocks=round(1.2*rate/480)
    for i in range(blocks):
     began=time.perf_counter_ns();codes=source.render_dac_codes(i*480,(i+1)*480,1.,1.65)
     times.append((time.perf_counter_ns()-began)/1e6)
     assert codes.shape==(480,) and np.isfinite(codes).all()
    budget=480/rate*1000
    result=dict(rate=rate,patch=name,voices=count,blocks=blocks,warmup_ms=warm_ms,
      p50_ms=float(np.percentile(times,50)),p95_ms=float(np.percentile(times,95)),max_ms=max(times),
      budget_ms=budget,over_budget_blocks=sum(t>budget for t in times),final_voices=len(source.voices))
    results.append(result);print(json.dumps(result),flush=True)
 output=dict(platform=platform.platform(),python=platform.python_version(),block_samples=480,
             method='Sequential isolated CPU-only 1.2 s phrases; compilation warmup separate; 11 and 20 use identical parameters and V18 renderer.',results=results)
 Path('diagnosticos/resultados_v18/synth20_cpu.json').write_text(json.dumps(output,indent=2)+'\n')
if __name__=='__main__':main()
