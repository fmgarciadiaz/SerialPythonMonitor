"""Columnar acquisition blocks; sample dictionaries are materialized only on demand."""
import time
import numpy as np

class NumericBatch:
    def __init__(self, samples, maximum, clock=None, channels=2):
        data=np.asarray(samples)
        timestamps=data[:,0].astype(np.float64,copy=False)
        self.columns={'Tiempo (us)':clock.convert(timestamps) if clock is not None else timestamps, 'CH1':data[:,1]*(3.3/maximum),
                      'CH2':data[:,2]*(3.3/maximum) if channels==2 else np.full(len(data),np.nan), 'Muestra':data[:,3]}
        self.published_at=time.monotonic()
    def __len__(self):return len(self.columns['CH1'])
    def __iter__(self):
        keys=tuple(self.columns)
        for row in zip(*(self.columns[key] for key in keys)):
            yield dict(zip(keys,row))

class SampleClock:
    """Convert fast-mode uint32 ticks to continuous microseconds across wraps."""
    def __init__(self,hz=1000000):
        self.hz=hz;self.previous=None;self.total=None
    def convert(self,raw):
        if self.hz==1000000:return raw
        ticks=np.asarray(raw,dtype=np.uint64)
        delta=np.empty(len(ticks),dtype=np.uint64)
        delta[0]=0 if self.previous is None else (int(ticks[0])-self.previous)&0xffffffff
        delta[1:]=(ticks[1:]-ticks[:-1])&0xffffffff
        if self.total is None:self.total=int(ticks[0])
        unwrapped=np.cumsum(delta,dtype=np.uint64)+self.total
        self.total=int(unwrapped[-1]);self.previous=int(ticks[-1])
        return unwrapped.astype(np.float64)*(1000000/self.hz)
