"""Bounded numeric history, with batch writes and NumPy window copies."""
import numpy as np

class SampleHistory:
    def __init__(self, maxlen):
        self.maxlen = maxlen
        self.data = np.empty(maxlen, dtype=float)
        self.count = self.head = 0
    def __len__(self): return self.count
    def clear(self): self.count = self.head = 0
    def append(self, value):
        self.data[self.head] = value
        self.head = (self.head+1) % self.maxlen
        self.count = min(self.count+1,self.maxlen)
    def extend(self, values):
        values = np.asarray(values, dtype=float) if isinstance(values, (list,tuple,np.ndarray)) else np.fromiter(values,dtype=float)
        n = len(values)
        if not n: return
        if n >= self.maxlen:
            self.data[:] = values[-self.maxlen:]
            self.count = self.maxlen; self.head = 0
            return
        first = min(n,self.maxlen-self.head)
        self.data[self.head:self.head+first] = values[:first]
        self.data[:n-first] = values[first:]
        self.head = (self.head+n)%self.maxlen
        self.count = min(self.count+n,self.maxlen)
    def window(self,start,end):
        if not 0 <= start <= end <= self.count: raise IndexError('History window out of range')
        offset = (self.head-self.count+start)%self.maxlen
        n = end-start; first = min(n,self.maxlen-offset)
        # Copies keep frozen trigger frames independent of subsequent writes.
        if first == n: return self.data[offset:offset+n].copy()
        return np.concatenate((self.data[offset:],self.data[:n-first]))
    def __getitem__(self,index):
        if isinstance(index,slice):
            start,end,step=index.indices(self.count)
            if step < 0: return self.window(0,self.count)[index]
            if start >= end: return np.empty(0,dtype=float)
            return self.window(start,end)[::step]
        if index < 0: index += self.count
        if not 0 <= index < self.count: raise IndexError(index)
        return self.data[(self.head-self.count+index)%self.maxlen]
    def __iter__(self): return iter(self.window(0,self.count))
    def __reversed__(self): return iter(self.window(0,self.count)[::-1])
