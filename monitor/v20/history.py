"""Bounded numeric history, with batch writes and NumPy window copies."""
import numpy as np

class SampleHistory:
    def __init__(self, maxlen):
        self.maxlen = maxlen
        self.data = np.empty(maxlen, dtype=float)
        self.count = self.head = 0
    def resize(self, maxlen):
        if maxlen == self.maxlen: return
        values = self.window(max(0, self.count-maxlen), self.count)
        data = np.empty(maxlen, dtype=float)
        self.maxlen, self.data = maxlen, data
        self.count = self.head = 0
        self.extend(values)
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
    def window_view(self,start,end):
        """Use ring storage directly for a synchronous live draw when contiguous."""
        parts=self.window_parts(start,end)
        return parts[0] if len(parts)==1 else np.concatenate(parts)
    def window_parts(self,start,end):
        """Return logical window as one or two ring-backed views, without copying."""
        if not 0 <= start <= end <= self.count: raise IndexError('History window out of range')
        offset=(self.head-self.count+start)%self.maxlen
        n=end-start;first=min(n,self.maxlen-offset)
        parts=(self.data[offset:offset+first],)
        if first<n:parts+=(self.data[:n-first],)
        return parts
    def searchsorted(self, value, side='left'):
        """Binary search a sorted logical clock without copying its circular data."""
        if side not in ('left','right'): raise ValueError(side)
        low, high = 0, self.count
        offset = (self.head-self.count)%self.maxlen
        while low < high:
            middle = (low+high)//2
            item = self.data[(offset+middle)%self.maxlen]
            if item < value or (side == 'right' and item == value): low = middle+1
            else: high = middle
        return low
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
