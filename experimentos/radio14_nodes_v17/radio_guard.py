"""Bounded, passive evidence of A0 returning to CH1; no probe is injected."""
from collections import deque
from threading import Lock
import numpy as np
from scipy.signal import correlate


class RadioLoopGuard:
    rate = 4000

    def __init__(self, output_rate=40000):
        if output_rate not in (20000,40000):raise ValueError('FS A0 no soportada')
        self.output_stride=output_rate//self.rate
        self.output = deque(maxlen=8000)
        self._output_lock=Lock()
        self.input = deque(maxlen=512)
        self.next_input = 0.
        self.input_count = 0
        self.next_check = 512
        self.hits = 0
        self.score = 0.
        self.detected = False
        self.input_rate = None

    def sent(self, codes, start):
        # Align downsampling across arbitrary packet boundaries.
        first = (-start) % self.output_stride
        values=np.asarray(codes[first::self.output_stride], dtype=float)*3.3/4095
        with self._output_lock:self.output.extend(values)

    def observe(self, values, rate):
        if self.input_rate != rate:
            self.input.clear();self.input_count=0;self.next_input=0.
            self.next_check=512;self.hits=0;self.input_rate=rate
        values = np.asarray(values)
        if not len(values):return False
        end = self.input_count + len(values)
        positions = np.arange(self.next_input, end, rate/self.rate)
        if len(positions):
            local=positions-self.input_count
            lo=local.astype(np.int64);hi=np.minimum(lo+1,len(values)-1)
            a=values[lo].astype(float);b=values[hi].astype(float)
            self.input.extend(a+(b-a)*(local-lo))
            self.next_input = positions[-1]+rate/self.rate
        self.input_count = end
        if len(self.input)<512 or len(self.output)<1024:return False
        self.next_check -= len(positions)
        if self.next_check>0:return False
        self.next_check=512
        x=np.asarray(self.input);x=x-x.mean()
        with self._output_lock:y=np.asarray(self.output)
        energy=float(x@x)
        self.score=0.
        # Silence and narrow single tones cannot identify a physical loop.
        spectrum=abs(np.fft.rfft(x*np.hanning(len(x))))**2
        richness=spectrum.sum()**2/max(float(spectrum@spectrum),1e-30)
        if energy/len(x)>.002**2 and richness>=4 and np.isfinite(y).all():
            # ADC and DAC do not share a sampling phase. Test fractional
            # alignment without weakening the evidence threshold.
            for phase in (0.,.25,.5,.75):
                aligned=y if phase==0 else y[:-1]*(1-phase)+y[1:]*phase
                cumulative=np.r_[0.,np.cumsum(aligned)]
                cumulative2=np.r_[0.,np.cumsum(aligned*aligned)]
                sums=cumulative[len(x):]-cumulative[:-len(x)]
                squares=cumulative2[len(x):]-cumulative2[:-len(x)]
                variance=np.maximum(squares-sums*sums/len(x),0)
                corr=abs(correlate(aligned,x,mode='valid',method='fft'))
                valid=variance>len(x)*.002**2
                if valid.any():self.score=max(self.score,float(np.max(corr[valid]/np.sqrt(energy*variance[valid]))))
        self.hits=self.hits+1 if self.score>=.985 else 0
        self.detected=self.hits>=3
        return self.detected
