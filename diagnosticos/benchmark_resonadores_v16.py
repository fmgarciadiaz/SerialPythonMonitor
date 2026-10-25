"""A/B resonator loop layout, exact output/state and piano DAC checks; no Q."""
import sys,json,time,argparse
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from monitor.historico.v16 import virtual_instruments as instruments
from monitor.historico.v16.fm_feedback import njit
from diagnosticos.benchmark_alloc_synth_v16 import run
from monitor.historico.v16 import fm_source


def reference(signal,coefficients,state,weights):
    output=np.zeros(len(signal))
    for i in range(len(signal)):
        for j in range(len(weights)):
            b0,b1,b2,a1,a2=coefficients[j]
            value=b0*signal[i]+state[j,0]
            state[j,0]=b1*signal[i]-a1*value+state[j,1]
            state[j,1]=b2*signal[i]-a2*value
            output[i]+=weights[j]*value
    return output

reference_kernel=njit(cache=True,nogil=True)(reference)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);args=p.parse_args()
    rng=np.random.default_rng(77);report=[];instruments.warmup()
    for modes in (8,32,96,192):
        coefficients=instruments._peak_bank(20000,tuple((100.+j*31,10.+j) for j in range(modes)))
        signal=rng.normal(size=480)*.01;weights=rng.normal(size=modes);initial=rng.normal(size=(modes,2))*.001
        expected_state=initial.copy();actual_state=initial.copy()
        old=reference_kernel(signal,coefficients,expected_state,weights);new=instruments.body_kernel(signal,coefficients,actual_state,weights)
        np.testing.assert_array_equal(new,old);np.testing.assert_array_equal(actual_state,expected_state)
        timings={}
        for name,kernel in (('before',reference_kernel),('after',instruments.body_kernel)):
            elapsed=[]
            for i in range(100):
                state=initial.copy();began=time.perf_counter();kernel(signal,coefficients,state,weights);elapsed.append((time.perf_counter()-began)*1000)
            timings[name]=dict(median_ms=float(np.median(elapsed)),p95_ms=float(np.percentile(elapsed,95)))
        report.append(dict(modes=modes,output_and_state_exact=True,**timings))
    dac=[]
    for rate in (20000,40000):
        with patch.object(instruments,'body_kernel',reference_kernel):old,before=run(fm_source,rate,'piano',300)
        new,after=run(fm_source,rate,'piano',300)
        np.testing.assert_array_equal(new,old);dac.append(dict(rate=rate,samples=len(new),exact=True,before=before,after=after))
    result=dict(scope='Host A/B; no board/acoustic latency acceptance',kernels=report,dac=dac)
    text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text)

if __name__=='__main__':main()
