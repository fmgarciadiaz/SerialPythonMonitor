"""Compare optimized Scan against its frozen reference, without board access."""
from pathlib import Path
import importlib.util
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import scipy
from scipy.signal import lfilter
from monitor.v17.radio_scan import scan_carriers,SCAN_SIZE,SCAN_BLOCKS
spec=importlib.util.spec_from_file_location('scan_reference',ROOT/'diagnosticos/referencias/radio_scan_preoptimization.py')
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
rate=160000000/114
count=SCAN_SIZE*SCAN_BLOCKS;t=np.arange(count)/rate
rng=np.random.default_rng(61)
noise=rng.normal(0,.015,count)
colored=lfilter([1],[1,-.95],noise);colored*=.015/colored.std()
impulsive=noise.copy();impulsive[rng.choice(count,100,replace=False)]+=rng.uniform(-1,1,100)
transient=noise.copy()+.02*np.cos(2*np.pi*52000*t)
transient[:SCAN_SIZE]+=.5*np.cos(2*np.pi*50000*t[:SCAN_SIZE])
cases={
    'white_noise':noise,
    'colored_noise_am':colored+(.5+.15*np.cos(2*np.pi*750*t))*np.cos(2*np.pi*20525*t)+.003*np.cos(2*np.pi*300000*t),
    'impulsive_noise':impulsive+.3*np.cos(2*np.pi*100000*t),
    'strong_transient_weak_neighbor':transient,
    'adc8_many_images':np.rint((1.65+.5*np.cos(2*np.pi*50000*t))*255/3.3)*3.3/255,
    'band_edges':noise+.3*np.cos(2*np.pi*5010*t)+.3*np.cos(2*np.pi*599990*t),
}
report={'environment':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__},
        'scope':'Offline exact-output equivalence and CPU cost; no physical acceptance',
        'equivalence_checks':0,'cases':{}}
for name,values in cases.items():
    for threshold in (6,12,30,60):
        for persistence in (2,3):
            expected=reference.scan_carriers(values,rate,threshold,persistence)
            actual=scan_carriers(values,rate,threshold,persistence)
            assert actual==expected,(name,threshold,persistence)
            report['equivalence_checks']+=1
    case={}
    for label,function in [('before',reference.scan_carriers),('after',scan_carriers)]:
        function(values,rate,12)
        samples=[]
        for _ in range(9):
            start=time.perf_counter();peaks=function(values,rate,12);samples.append((time.perf_counter()-start)*1000)
        case[label]={'median_ms':float(np.median(samples)),'p95_ms':float(np.percentile(samples,95)),
                     'candidates':len(peaks)}
    case['speedup']=case['before']['median_ms']/case['after']['median_ms']
    report['cases'][name]=case
report['ok']=True
output=ROOT/'diagnosticos/resultados_v17/scan_optimized_benchmark.json'
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
