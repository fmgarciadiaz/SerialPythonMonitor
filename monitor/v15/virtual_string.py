"""Fractional-delay, lossy digital waveguide plucked string prototype."""
import numpy as np
from monitor.v15.fm_feedback import njit

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

kernel=njit(cache=True,nogil=True)(_advance) if njit else None

def warmup():
    if kernel is not None:kernel(np.zeros(32),0,0.,8,20.,.65,.99)

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
        self.cursor=0;self.previous=0.
    def render(self,count,brightness=.65,decay=3.,bridge=0.):
        if kernel is None:raise RuntimeError('Virtual requiere Numba')
        # Compensate first-order loss-filter phase delay at the fundamental.
        omega=2*np.pi*self.frequency/self.rate
        lag=-np.angle(brightness+(1-brightness)*np.exp(-1j*omega))/omega
        delay=max(2.,self.rate/self.frequency-lag)
        gain=10**(-3*(1+bridge*.5)/(self.frequency*decay))
        output,self.cursor,self.previous=kernel(self.buffer,self.cursor,self.previous,count,delay,float(brightness),float(gain))
        return output
