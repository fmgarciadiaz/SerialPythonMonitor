"""Bounded complete GUI delivery; audio DSP credit is tracked separately."""
from collections import deque
import math

class DeliveryBudget:
    max_seconds=1.
    max_samples=1600000
    max_bytes=64*1024*1024
    max_batches=256
    def __init__(self):
        self.entries=deque();self.samples=0;self.seconds=0.;self.bytes=0;self.radio_entries=0
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
            raise RuntimeError('Entrega GUI atrasada: presupuesto de muestras/tiempo/memoria excedido; adquisición detenida sin descartar datos.')
        radio=bool(getattr(settings,'radio_enabled',False))
        self.entries.append((batch,samples,seconds,size,radio));self.samples+=samples;self.seconds+=seconds;self.bytes+=size
        self.radio_entries+=int(radio)
    def release(self,batch=None):
        if not self.entries:return
        index=0 if batch is None else next((i for i,e in enumerate(self.entries) if e[0] is batch),None)
        if index is None:return
        entry=self.entries[index];del self.entries[index]
        self.samples-=entry[1];self.seconds=max(0.,self.seconds-entry[2]);self.bytes-=entry[3];self.radio_entries-=int(entry[4])
