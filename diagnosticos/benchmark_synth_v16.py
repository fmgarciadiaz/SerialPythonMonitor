"""Local A/B CPU benchmark; no MIDI device, board I/O, or firmware changes."""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.signal import fftconvolve

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from monitor.historico.v16 import virtual_instruments as instruments

def fft_envelope(force,count,pole):
    return fftconvolve(force,np.exp(np.log(pole)*np.arange(count)))[:count]

def previous_release(count,coefficients,state,weights,age,fade_samples,limit):
    tail=instruments.body_kernel(np.zeros(count),coefficients,state,weights)
    clock=age+np.arange(count)
    return tail*np.minimum(clock/fade_samples,1.)*(clock<limit)

def main():
    instruments.warmup()
    results=[]
    for rate in (20000,40000):
        for label,kernel in (('fft_reference',fft_envelope),('recurrence',instruments.contact_envelope_kernel)):
            elapsed=[]
            with patch.object(instruments,'contact_envelope_kernel',kernel):
                for repeat in range(30):
                    for note in (36,48,60,72,84,96):
                        instruments.attack_texture.cache_clear()
                        began=time.perf_counter()
                        instruments.attack_texture(rate,440*2**((note-69)/12),.7,.78,(.02,)*6)
                        elapsed.append((time.perf_counter()-began)*1000)
            results.append(dict(stage='attack',rate=rate,version=label,
                median_ms=float(np.median(elapsed)),p95_ms=float(np.percentile(elapsed,95))))
        body=instruments.InstrumentBody(rate,'piano')
        body.set_open_notes(tuple(range(36,89)))
        body.render(np.random.default_rng(1).normal(size=rate//2)*.01,.45,.2)
        body.set_open_notes(())
        tracks=list(body.release_tracks.values())
        reference=None
        for label,kernel in (('numpy_reference',previous_release),('compiled',instruments.release_kernel)):
            elapsed=[]
            for repeat in range(100):
                states=[t[1].copy() for t in tracks]
                began=time.perf_counter();output=np.zeros(480)
                for track,state in zip(tracks,states):
                    coefficients,_,weights,age,t60=track
                    output+=kernel(480,coefficients,state,weights,age,round(.01*rate),round(1.5*t60*rate))
                elapsed.append((time.perf_counter()-began)*1000)
            if reference is None:reference=output
            else:np.testing.assert_allclose(output,reference,atol=1e-12,rtol=1e-12)
            results.append(dict(stage='release',rate=rate,version=label,tracks=len(tracks),
                median_ms=float(np.median(elapsed)),p95_ms=float(np.percentile(elapsed,95))))
    folder=ROOT/'diagnosticos/resultados_piano/eficiencia_v16';folder.mkdir(exist_ok=True)
    (folder/'benchmark_ab.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
