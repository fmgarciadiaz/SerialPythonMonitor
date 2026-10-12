"""Columnar acquisition blocks; sample dictionaries are materialized only on demand."""
import time
import numpy as np

class NumericBatch:
    def __init__(self, samples, maximum):
        data=np.asarray(samples,dtype=np.float64)
        self.columns={'Tiempo (us)':data[:,0], 'CH1':data[:,1]*(3.3/maximum),
                      'CH2':data[:,2]*(3.3/maximum), 'Muestra':data[:,3]}
        self.published_at=time.monotonic()
    def __len__(self):return len(self.columns['CH1'])
    def __iter__(self):
        keys=tuple(self.columns)
        for row in zip(*(self.columns[key] for key in keys)):
            yield dict(zip(keys,row))
