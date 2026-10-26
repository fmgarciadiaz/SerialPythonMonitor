"""Bounded complete GUI delivery; audio DSP credit is tracked separately."""
from collections import deque
import math
from monitor.v18.flow_limits import FlowLimitExceeded

class DeliveryBudget:
    max_seconds=1.
    max_samples=1600000
    max_bytes=64*1024*1024
    max_batches=256
    def __init__(self):
        self.entries=deque();self.samples=0;self.seconds=0.;self.bytes=0;self.radio_entries=0
        self.peak_samples=0;self.peak_seconds=0.;self.peak_bytes=0;self.peak_batches=0
    def reserve(self,batch,settings,config):
        columns=getattr(batch,'columns',{})
        samples=len(columns.get('CH1',()))
        seconds=samples/config.actual_rate
        size=sum(getattr(v,'nbytes',0) for v in columns.values())
        # Reserve output audio, FILTER, time metadata and possible RF FILTER.
        size+=math.ceil(seconds*getattr(settings,'audio_rate',40000))*8*4
        size+=samples*8 if getattr(getattr(settings,'filter',None),'source',None) in ('CH1','CH2') else 0
        if (len(self.entries)>=self.max_batches or self.samples+samples>self.max_samples
                or self.seconds+seconds>self.max_seconds+1e-9 or self.bytes+size>self.max_bytes):
            current=self.snapshot()
            projected=dict(samples=self.samples+samples,seconds=self.seconds+seconds,
                           bytes=self.bytes+size,batches=len(self.entries)+1)
            limits=self.limits()
            exceeded=[key for key in limits if projected[key]>limits[key]+(1e-9 if key=='seconds' else 0)]
            raise FlowLimitExceeded('Entrega GUI',current,projected,limits,exceeded,
                peaks=self.peaks(),context=dict(bits=config.bits,channels=config.channels,
                                               actual_rate=config.actual_rate))
        radio=bool(getattr(settings,'radio_enabled',False))
        self.entries.append((batch,samples,seconds,size,radio));self.samples+=samples;self.seconds+=seconds;self.bytes+=size
        self.radio_entries+=int(radio)
        self.peak_samples=max(self.peak_samples,self.samples)
        self.peak_seconds=max(self.peak_seconds,self.seconds)
        self.peak_bytes=max(self.peak_bytes,self.bytes)
        self.peak_batches=max(self.peak_batches,len(self.entries))
    def snapshot(self):
        return dict(samples=self.samples,seconds=self.seconds,bytes=self.bytes,batches=len(self.entries))
    def limits(self):
        return dict(samples=self.max_samples,seconds=self.max_seconds,bytes=self.max_bytes,batches=self.max_batches)
    def peaks(self):
        return dict(samples=self.peak_samples,seconds=self.peak_seconds,bytes=self.peak_bytes,batches=self.peak_batches)
    def release(self,batch=None):
        if not self.entries:return
        index=0 if batch is None else next((i for i,e in enumerate(self.entries) if e[0] is batch),None)
        if index is None:return
        entry=self.entries[index];del self.entries[index]
        self.samples-=entry[1];self.seconds=max(0.,self.seconds-entry[2]);self.bytes-=entry[3];self.radio_entries-=int(entry[4])
