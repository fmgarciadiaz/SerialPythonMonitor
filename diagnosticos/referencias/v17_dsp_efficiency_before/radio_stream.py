"""Independent, uniformly sampled RADIO audio timeline."""
from types import SimpleNamespace
from fractions import Fraction
import numpy as np
from monitor.v17.history import SampleHistory
from monitor.v17.radio_am import AMDemodulator, RadioConfig


class AudioResampler:
    """Stateful windowed sinc conversion with bounded look-ahead latency."""
    def __init__(self, input_rate, output_rate):
        if not 8000 <= output_rate <= 48000:
            raise ValueError('FS audio fuera de rango')
        self.input_rate, self.output_rate = input_rate, output_rate
        self.radius = 64
        self.buffer = np.empty(0)
        self.origin = self.total = self.output_count = 0
        ratio=input_rate/output_rate
        fraction=Fraction(ratio).limit_denominator(4096)
        self.weights=None
        if abs(float(fraction)-ratio)<1e-12:
            self.numerator,self.denominator=fraction.numerator,fraction.denominator
            offsets=np.arange(-self.radius+1,self.radius+1)
            distance=np.arange(self.denominator)[:,None]/self.denominator-offsets
            self.weights=self._weights(distance)

    def _weights(self,distance):
        cutoff=.45*min(1,self.output_rate/self.input_rate)
        window=np.i0(8.6*np.sqrt(np.maximum(0,1-(distance/self.radius)**2)))/np.i0(8.6)
        weights=2*cutoff*np.sinc(2*cutoff*distance)*window
        return weights/weights.sum(axis=1)[:,None]

    def process(self, values):
        self.buffer = np.concatenate((self.buffer, values))
        self.total += len(values)
        ratio = self.input_rate / self.output_rate
        stop = max(0, int(np.ceil((self.total-self.radius) / ratio)))
        if stop <= self.output_count:
            return np.empty(0)
        output_indices=np.arange(self.output_count,stop)
        positions = output_indices * ratio
        offsets = np.arange(-self.radius+1, self.radius+1)
        if self.weights is not None:
            phase=output_indices*self.numerator
            indices=(phase//self.denominator)[:,None]+offsets
            weights=self.weights[phase%self.denominator]
        else:
            indices=np.floor(positions).astype(int)[:,None]+offsets
            weights=self._weights(positions[:,None]-indices)
        local = indices-self.origin
        valid = (local>=0)&(local<len(self.buffer))
        samples = self.buffer[np.clip(local,0,len(self.buffer)-1)]
        output = np.sum(weights*np.where(valid,samples,0),axis=1)
        self.output_count = stop
        keep = max(self.origin, int(np.floor(stop*ratio))-self.radius)
        self.buffer = self.buffer[keep-self.origin:]
        self.origin = keep
        return output


class RadioStream:
    def __init__(self, config, output_rate=20000, capacity=200000):
        self.demod = AMDemodulator(config)
        self.resampler = AudioResampler(self.demod.output_rate, output_rate)
        self.rate = output_rate
        self.counter = 0
        self.series = {name: SampleHistory(capacity) for name in ('RADIO','FILTER','Tiempo (us)')}
        self.sample_numbers = SampleHistory(capacity)

    def process(self, samples, first_index=None):
        return self.resampler.process(self.demod.process(samples, first_index))

    def append(self, audio, filtered):
        count = len(audio)
        numbers = np.arange(self.counter,self.counter+count)
        self.sample_numbers.extend(numbers)
        self.series['Tiempo (us)'].extend(numbers*(1e6/self.rate))
        self.series['RADIO'].extend(audio)
        self.series['FILTER'].extend(filtered)
        self.counter += count

    def analysis_owner(self, owner):
        return SimpleNamespace(series=self.series,sample_numbers=self.sample_numbers,
            sample_counter=self.counter,current_fs_hz=self.rate,is_running=owner.is_running,
            channel_colors=owner.channel_colors,_reduce_trace_for_display=owner._reduce_trace_for_display)
