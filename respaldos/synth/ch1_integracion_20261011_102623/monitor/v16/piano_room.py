"""Mono acoustic propagation and a small, stable four-line room FDN."""
import numpy as np
from monitor.v16.fm_feedback import njit

def _reflections(signal,buffer,position,taps,weights):
    result=np.empty(len(signal))
    normalization=1+np.sum(np.abs(weights))
    for i in range(len(signal)):
        value=signal[i]
        for j in range(len(taps)):value+=weights[j]*buffer[(position-taps[j])%len(buffer)]
        buffer[position]=signal[i]
        result[i]=value/normalization
        position=(position+1)%len(buffer)
    return result,position

def _room(signal,lines,lengths,positions,damped,feedback,pole):
    output=np.empty(len(signal))
    for i in range(len(signal)):
        a=lines[0,positions[0]];b=lines[1,positions[1]]
        c=lines[2,positions[2]];d=lines[3,positions[3]]
        mixed=((a+b+c+d)*.5,(a-b+c-d)*.5,(a+b-c-d)*.5,(a-b-c+d)*.5)
        for j in range(4):
            damped[j]=pole*damped[j]+(1-pole)*mixed[j]
            lines[j,positions[j]]=signal[i]*.5+feedback[j]*damped[j]
            positions[j]=(positions[j]+1)%lengths[j]
        output[i]=(a-b+c-d)*.5
    return output

reflections_kernel=njit(cache=True,nogil=True)(_reflections) if njit else None
room_kernel=njit(cache=True,nogil=True)(_room) if njit else None

class PianoRoom:
    def __init__(self,rate):
        self.rate=rate
        self.lengths=np.rint(np.array((.0311,.0437,.0593,.0719))*rate).astype(np.int64)
        self.lines=np.zeros((4,max(self.lengths)))
        self.positions=np.zeros(4,dtype=np.int64);self.damped=np.zeros(4)
        self.pole=np.exp(-2*np.pi*3500/rate)
    def render(self,signal,mix=.06,decay=1.2):
        if room_kernel is None:return signal
        feedback=10**(-3*self.lengths/(self.rate*max(decay,.1)))
        wet=room_kernel(signal,self.lines,self.lengths,self.positions,self.damped,feedback,self.pole)
        return signal+mix*wet

def warmup():
    if room_kernel is not None:
        PianoRoom(20000).render(np.zeros(8))
        reflections_kernel(np.zeros(8),np.zeros(400),0,np.array([3,5],dtype=np.int64),np.array([.01,.01]))
