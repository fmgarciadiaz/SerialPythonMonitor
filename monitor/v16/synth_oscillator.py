"""Allocation-light PolyBLEP saw/square, preserving sample operation order."""
import numpy as np
from functools import lru_cache
from monitor.v16.fm_feedback import njit

def _blep(position,dt):
    result=0.
    if position<dt:
        x=position/dt;result=2*x-x*x-1
    if position>1-dt:
        x=(position-1)/dt;result=x*x+2*x+1
    return result

_blep_kernel=njit(inline='always')(_blep) if njit else _blep

def _oscillator(phase,frequency,rate,square):
    output=np.empty(len(phase))
    for i in range(len(phase)):
        t=(phase[i]/(2*np.pi))%1
        dt=max(frequency[i]/rate,1e-12)
        correction=_blep_kernel(t,dt)
        if square:
            shifted=(t+.5)%1
            output[i]=(1. if t<.5 else -1.)+correction-_blep_kernel(shifted,dt)
        else:output[i]=2*t-1-correction
    return output

kernel=njit(cache=True,nogil=True)(_oscillator) if njit else None

@lru_cache(maxsize=1)
def warmup():
    if kernel is not None:
        phase=np.zeros(8);frequency=np.ones(8)
        kernel(phase,frequency,40000,False)
        frequency.setflags(write=False)
        kernel(phase,frequency,40000,False)
