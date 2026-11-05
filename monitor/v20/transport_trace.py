"""Opt-in preallocated numeric transport trace; never used by normal UI.

Avoid retaining hundreds of thousands of GC-tracked event tuples during audio.
When full, retain the latest window and report overwritten events explicitly.
JSON conversion happens only after playback/restoration in the diagnostic.
"""
import math
import numpy as np


class NumericTransportTrace:
    rolling = True

    def __init__(self, capacity=500000):
        if capacity < 1:raise ValueError('Trace capacity must be positive')
        self.capacity=capacity
        self._data=np.empty((capacity,6),dtype=np.float64)
        self._stages={}
        self.total=0

    def __len__(self):return min(self.total,self.capacity)

    def append(self,event):
        stage,start,end,rid=event[:4]
        code=self._stages.setdefault(stage,len(self._stages))
        self._data[self.total%self.capacity]=(code,start,end,math.nan if rid is None else rid,event[4] if len(event)>4 and event[4] is not None else math.nan,event[5] if len(event)>5 else math.nan)
        self.total+=1

    def export(self):
        names={code:name for name,code in self._stages.items()}
        records=[]
        for index in range(max(0,self.total-self.capacity),self.total):
            code,start,end,rid,cpu,process_cpu=self._data[index%self.capacity]
            entry=[names[int(code)],float(start),float(end),None if math.isnan(rid) else int(rid)]
            if not math.isnan(cpu) or not math.isnan(process_cpu):entry.append(None if math.isnan(cpu) else float(cpu))
            if not math.isnan(process_cpu):entry.append(float(process_cpu))
            records.append(entry)
        return dict(events=records,metadata=dict(storage='numeric_ring',capacity=self.capacity,total_events=self.total,overwritten=max(0,self.total-self.capacity)))
