"""Small stateful SOS audio filter; scipy-compatible output and final state."""
import numpy as np
from functools import lru_cache
from monitor.historico.v16.fm_feedback import njit
from scipy.signal import sosfilt as scipy_sosfilt

def _filter(coefficients,signal,state):
    output=np.empty(len(signal));state=state.copy()
    for i in range(len(signal)):
        value=signal[i]
        for j in range(len(coefficients)):
            row=coefficients[j]
            filtered=row[0]*value+state[j,0]
            state[j,0]=row[1]*value-row[4]*filtered+state[j,1]
            state[j,1]=row[2]*value-row[5]*filtered
            value=filtered
        output[i]=value
    return output,state

kernel=njit(cache=True,nogil=True)(_filter) if njit else None

def sosfilt(coefficients,signal,zi):
    if kernel is None:return scipy_sosfilt(coefficients,signal,zi=zi)
    return kernel(coefficients,signal,zi)

@lru_cache(maxsize=1)
def warmup():
    if kernel is not None:
        coefficients=np.array([[1.,0,0,1.,0,0]])
        for readonly in (False,True):
            coefficients.setflags(write=not readonly)
            for signal in (np.zeros(8),np.zeros(16)[::2]):
                kernel(coefficients,signal,np.zeros((1,2)))
