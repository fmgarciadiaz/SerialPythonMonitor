"""Bounded single-owner grouping of validated numeric records, experimental."""
import time
import numpy as np
from monitor.v17.receiver.native_unpack import NativeRecords


class SampleCoalescer:
    def __init__(self,maximum=16000,seconds=.01,clock=time.monotonic):
        self.maximum=maximum;self.seconds=seconds;self.clock=clock
        self.parts=[];self.count=0;self.callback=None;self.context=None;self.since=None
        self.stats=dict(inputs=0,outputs=0,samples=0,peak_samples=0,peak_parts=0,max_age_ms=0.)
        self.slow_top=[]

    def flush(self,reason='explicit'):
        if not self.count:return
        parts,callback,since=self.parts,self.callback,self.since
        self.parts=[];self.count=0;self.since=None
        rows=parts[0] if len(parts)==1 else NativeRecords(np.concatenate([p.array for p in parts]))
        self.stats['outputs']+=1
        self.stats['samples']+=len(rows)
        now=self.clock();age_ms=(now-since)*1000
        self.stats['max_age_ms']=max(self.stats['max_age_ms'],age_ms)
        if age_ms>=20:
            self.slow_top.append(dict(start=since,flushed_at=now,age_ms=age_ms,
                                      reason=reason,samples=len(rows),parts=len(parts)))
            self.slow_top.sort(key=lambda event:event['age_ms'],reverse=True)
            del self.slow_top[8:]
        # Clear before callback: an exception must not duplicate these records.
        callback(rows)

    def expire(self):
        if self.count and self.clock()-self.since>=self.seconds:self.flush('deadline')

    def push(self,rows,callback,context):
        self.stats['inputs']+=1
        if self.callback is not callback or self.context!=context:self.flush('context')
        self.callback,self.context=callback,context
        if not isinstance(rows,NativeRecords):
            self.flush('fallback');callback(rows);return
        self.expire()
        for start in range(0,len(rows),self.maximum):
            part=rows[start:start+self.maximum]
            if self.count+len(part)>self.maximum or len(self.parts)>=32:self.flush('capacity')
            if not self.count:self.since=self.clock()
            self.parts.append(part);self.count+=len(part)
            self.stats['peak_samples']=max(self.stats['peak_samples'],self.count)
            self.stats['peak_parts']=max(self.stats['peak_parts'],len(self.parts))
            if self.count>=self.maximum:self.flush('full')
