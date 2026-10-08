"""Stateful two-sample FM feedback; no Python audio loop in production."""
import math
import numpy as np
try:
    from numba import njit
except ImportError:
    njit = None

def _feedback(phase, amount, state):
    output = np.empty(len(phase))
    older, previous = state[0], state[1]
    gain = (2.0 ** amount - 1.0) / 32.0
    for i in range(len(phase)):
        value = math.sin(phase[i] + gain * (older + previous) * .5)
        output[i] = value
        older, previous = previous, value
    state[0], state[1] = older, previous
    return output

kernel = njit(cache=True, nogil=True)(_feedback) if njit else None

def warmup():
    if kernel is not None:
        kernel(np.zeros(8), 0.0, np.zeros(2))
        envelope_kernel(8,0,0,0.0,0.0,80,80,.5,80)
    return kernel is not None

def modulate(phase, amount, state):
    if not amount:
        result = np.sin(phase)
        if len(result) >= 2: state[:] = result[-2:]
        return result
    if kernel is None:
        raise RuntimeError('Feedback requiere Numba; instalar requirements de V15')
    return kernel(phase, float(amount), state)


def _envelope(count, stage, position, start, value, attack, decay, sustain, release):
    output=np.empty(count)
    for i in range(count):
        while stage in (0,1,3):
            length=attack if stage==0 else decay if stage==1 else release
            target=1.0 if stage==0 else sustain if stage==1 else 0.0
            if position < length: break
            stage=1 if stage==0 else 2 if stage==1 else 4
            position=0;start=value=target
        if stage==2 or stage==4:
            value=sustain if stage==2 else 0.0
        else:
            position+=1
            value=start+(target-start)*(position/length)
            if position>=length:
                stage=1 if stage==0 else 2 if stage==1 else 4
                position=0;start=target
        output[i]=value
    return output,stage,position,start,value

envelope_kernel=njit(cache=True,nogil=True)(_envelope) if njit else None
