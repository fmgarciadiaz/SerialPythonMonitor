"""Fractional-delay, lossy digital waveguide plucked string prototype."""
import numpy as np
from functools import lru_cache
from monitor.v16.fm_feedback import njit

def _advance(buffer, cursor, previous, count, delay, brightness, gain):
    output=np.empty(count)
    size=len(buffer)
    for i in range(count):
        read=(cursor-delay)%size
        left=int(read);fraction=read-left
        value=buffer[left]*(1-fraction)+buffer[(left+1)%size]*fraction
        buffer[cursor]=gain*(brightness*value+(1-brightness)*previous)
        previous=value
        output[i]=value
        cursor=(cursor+1)%size
    return output,cursor,previous

def _interpolation(size,delay):
    left=np.empty(size,dtype=np.int64);fraction=np.empty(size)
    for cursor in range(size):
        read=(cursor-delay)%size
        left[cursor]=int(read);fraction[cursor]=read-int(read)
    return left,fraction


def _advance_table(buffer,cursor,previous,count,left,fraction,brightness,gain):
    output=np.empty(count);size=len(buffer)
    for i in range(count):
        index=left[cursor];f=fraction[cursor]
        right=index+1
        if right==size:right=0
        value=buffer[index]*(1-f)+buffer[right]*f
        buffer[cursor]=gain*(brightness*value+(1-brightness)*previous)
        previous=value;output[i]=value
        cursor+=1
        if cursor==size:cursor=0
    return output,cursor,previous

interpolation_kernel=njit(cache=True,nogil=True)(_interpolation) if njit else None
table_kernel=njit(cache=True,nogil=True)(_advance_table) if njit else None

kernel=njit(cache=True,nogil=True)(_advance) if njit else None

def warmup():
    if kernel is not None:
        kernel(np.zeros(32),0,0.,8,20.,.65,.99)
        left,fraction=interpolation_kernel(32,20.)
        table_kernel(np.zeros(32),0,0.,8,left,fraction,.65,.99)

@lru_cache(maxsize=512)
def _loss_coefficients(rate,frequency,brightness,decay,bridge):
    # Parameters remain fixed across most blocks; cache no evolving state.
    omega=2*np.pi*frequency/rate
    lag=-np.angle(brightness+(1-brightness)*np.exp(-1j*omega))/omega
    delay=max(2.,rate/frequency-lag)
    gain=10**(-3*(1+bridge*.5)/(frequency*decay))
    return delay,gain

class PluckedString:
    def __init__(self, rate, frequency, position=.22):
        self.rate=rate;self.frequency=frequency
        period=rate/frequency
        self.buffer=np.zeros(int(np.ceil(period))+3)
        # Triangular displacement of a string fixed at both ends.
        x=(np.arange(len(self.buffer))%period)/period
        shape=np.where(x<position,x/position,(1-x)/(1-position))
        self.buffer[:]=shape-shape.mean()
        self.buffer*=.85/max(np.max(abs(self.buffer)),1e-9)
        self.cursor=0;self.previous=0.;self._delay=None
    def render(self,count,brightness=.65,decay=3.,bridge=0.):
        if kernel is None:raise RuntimeError('Virtual requiere Numba')
        delay,gain=_loss_coefficients(self.rate,self.frequency,brightness,decay,bridge)
        if delay!=self._delay:
            self._left,self._fraction=interpolation_kernel(len(self.buffer),delay)
            self._delay=delay
        output,self.cursor,self.previous=table_kernel(self.buffer,self.cursor,self.previous,count,self._left,self._fraction,float(brightness),float(gain))
        return output
