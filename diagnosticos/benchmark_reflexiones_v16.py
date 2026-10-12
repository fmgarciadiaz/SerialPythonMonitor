"""Exact reflection normalization A/B, warmed ABBA timings and full piano DAC."""
import sys,json,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from monitor.v16 import piano_room, fm_source
from monitor.v16.fm_feedback import njit
from diagnosticos.benchmark_alloc_synth_v16 import run

def reference(signal,buffer,position,taps,weights):
    result=np.empty(len(signal))
    for i in range(len(signal)):
        value=signal[i]
        for j in range(len(taps)):value+=weights[j]*buffer[(position-taps[j])%len(buffer)]
        buffer[position]=signal[i]
        result[i]=value/(1+np.sum(np.abs(weights)))
        position=(position+1)%len(buffer)
    return result,position
reference_kernel=njit(cache=True,nogil=True)(reference)

def verify():
    rng=np.random.default_rng(88)
    for n in (0,1,7,480,960):
        for count in (0,2,4,12):
            signal=rng.normal(size=n);taps=np.arange(count,dtype=np.int64)*17+1;weights=rng.normal(size=count)
            a=rng.normal(size=400);b=a.copy()
            x,p=reference_kernel(signal,a,399,taps,weights);y,q=piano_room.reflections_kernel(signal,b,399,taps,weights)
            np.testing.assert_array_equal(x,y);np.testing.assert_array_equal(a,b);assert p==q

def main():
    verify();signal=np.random.default_rng(3).normal(size=480);taps=np.array([34,86,178,294],dtype=np.int64);weights=np.array([.045,-.025,.018,.012]);times={'before':[],'after':[]}
    for repetition in range(10):
        for name,kernel in [('before',reference_kernel),('after',piano_room.reflections_kernel),('after',piano_room.reflections_kernel),('before',reference_kernel)]:
            buffer=np.zeros(400);position=0;began=time.perf_counter()
            for i in range(500):_,position=kernel(signal,buffer,position,taps,weights)
            times[name].append((time.perf_counter()-began)*1000/500)
    dac=[]
    for rate in (20000,40000):
        with patch.object(piano_room,'reflections_kernel',reference_kernel):a,before=run(fm_source,rate,'piano',300)
        b,after=run(fm_source,rate,'piano',300);np.testing.assert_array_equal(a,b)
        dac.append(dict(rate=rate,samples=len(a),exact=True,before=before,after=after))
    result=dict(exact_output_state_position=True,kernel={k:dict(median_ms=float(np.median(v)),p95_ms=float(np.percentile(v,95))) for k,v in times.items()},dac=dac)
    path=ROOT/'diagnosticos/resultados_piano/eficiencia_v16/20261010_astra_reflexiones.json';path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
