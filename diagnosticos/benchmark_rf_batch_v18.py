"""CPU/serialization-only comparison; no sockets or Q."""
import json,pickle,time
from pathlib import Path
import numpy as np
from monitor.v18.numeric_batch import NumericBatch,SampleClock
from monitor.v18.io.rf_batch import RawRfBatch
from monitor.v18.receiver.unoq_acquisition import Configuration

def main():
    results=[]
    for config in (Configuration(8,1600000),Configuration(14,40000)):
        n=round(config.actual_rate*.02)
        raw=np.zeros((n,4),dtype=np.uint32)
        raw[:,0]=np.arange(n,dtype=np.uint32)*config.period
        raw[:,3]=np.arange(n,dtype=np.uint32)
        old=NumericBatch(raw,config.maximum,SampleClock(config.timestamp_hz),config.channels)
        new=RawRfBatch(raw,config,1,1,time.monotonic())
        row=dict(bits=config.bits,rate=config.rate,samples=n)
        for name,obj in [('columns',old),('raw',new)]:
            trials=[]
            for _ in range(200):
                started=time.perf_counter_ns();payload=pickle.dumps(obj,protocol=5);pickle.loads(payload)
                trials.append((time.perf_counter_ns()-started)/1e6)
            row[name]=dict(bytes=len(payload),p50_ms=float(np.percentile(trials,50)),p95_ms=float(np.percentile(trials,95)))
        results.append(row)
    out=Path('diagnosticos/resultados_v18/rf_batch_cpu.json');out.write_text(json.dumps(dict(scope='pickle roundtrip only, not actual IPC or physical acceptance',results=results),indent=2)+'\n')
    print(out.read_text())
if __name__=='__main__':main()
