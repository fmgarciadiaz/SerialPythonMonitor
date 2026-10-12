"""Correlate long owner reads with independent readiness samples; not wire timestamps."""
import sys,json,argparse
from pathlib import Path
import numpy as np


def analyze(trace,samples):
    events=trace['events'] if isinstance(trace,dict) else trace
    rows=[]
    for event in events:
        if event[0]!='read' or event[2]-event[1]<.01:continue
        start,end=event[1:3]
        # Readiness observed earlier than completion is positive evidence only;
        # no observed readiness cannot prove no data (reader may consume first).
        a,b=np.searchsorted(samples[:,0],[start,end]) if len(samples) else (0,0)
        window=samples[a:b]
        ready=window[window[:,2]>0] if len(window) else window
        rows.append(dict(start=start,wall_ms=(end-start)*1000,cpu_ms=event[4]*1000 if len(event)>4 else None,
            probe_samples=len(window),max_probe_wake_gap_ms=float(window[:,1].max()*1000) if len(window) else None,
            first_ready_to_read_end_ms=(end-ready[0,0])*1000 if len(ready) else None))
    return dict(scope='Probe sampling bounds, not packet arrival. Thread also depends on scheduler/GIL; absence of readiness proves nothing.',long_reads=sorted(rows,key=lambda r:r['wall_ms'],reverse=True)[:20])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);p.add_argument('probe',type=Path);args=p.parse_args()
    with np.load(args.probe) as data:result=analyze(json.loads(args.trace.read_text()),data['samples'])
    path=args.trace.with_name(args.trace.stem+'_socket_analysis.json');path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
