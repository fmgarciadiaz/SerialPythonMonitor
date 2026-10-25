"""Independent, uniformly sampled RADIO audio timeline."""
from types import SimpleNamespace
from fractions import Fraction
import numpy as np
from monitor.v18.history import SampleHistory
from monitor.v18.radio_am import AMDemodulator, RadioConfig


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
        # Exact rational bounds prevent roundoff from publishing one output
        # before its final look-ahead sample arrives at a block boundary.
        if self.weights is not None:
            stop = max(0,((self.total-self.radius)*self.denominator+self.numerator-1)//self.numerator)
        else:
            stop = max(0, int(np.ceil((self.total-self.radius) / ratio)))
        if stop <= self.output_count:
            return np.empty(0)
        output_indices=np.arange(self.output_count,stop)
        if self.weights is not None:
            phase=output_indices*self.numerator
            centers=phase//self.denominator
            weights=self.weights[phase%self.denominator]
        else:
            positions = output_indices * ratio
            centers=np.floor(positions).astype(int)
            offsets = np.arange(-self.radius+1, self.radius+1)
            weights=self._weights((positions-centers)[:,None]-offsets)
        # Every output uses one contiguous 128-sample window. Gather those
        # windows directly instead of allocating full index/validity matrices.
        # Only startup needs left zero padding; the look-ahead keeps the right
        # edge in the available input. Retain padding for floating point edges.
        starts=centers-self.origin-self.radius+1
        left=max(0,-int(starts[0]))
        right=max(0,int(starts[-1])+2*self.radius-len(self.buffer))
        source=np.pad(self.buffer,(left,right)) if left or right else self.buffer
        windows=np.lib.stride_tricks.sliding_window_view(source,2*self.radius)
        samples=windows[starts+left]
        output=np.einsum('ij,ij->i',weights,samples)
        self.output_count = stop
        keep = max(self.origin, int(np.floor(stop*ratio))-self.radius)
        self.buffer = self.buffer[keep-self.origin:]
        self.origin = keep
        return output


class RadioTimeline:
    """Audio history owned by its consumer, without mutable DSP state."""
    def __init__(self, output_rate=20000, capacity=200000):
        self.rate = output_rate
        self.counter = 0
        self.series = {name: SampleHistory(capacity) for name in ('RADIO','FILTER','Tiempo (us)')}
        self.sample_numbers = SampleHistory(capacity)

    def append(self, audio, filtered, first_time_us=None):
        count = len(audio)
        numbers = np.arange(self.counter,self.counter+count)
        self.sample_numbers.extend(numbers)
        times=numbers*(1e6/self.rate) if first_time_us is None else first_time_us+np.arange(count)*(1e6/self.rate)
        self.series['Tiempo (us)'].extend(times)
        self.series['RADIO'].extend(audio)
        if filtered is not None:self.series['FILTER'].extend(filtered)
        self.counter += count

    def analysis_owner(self, owner):
        return SimpleNamespace(series=self.series,sample_numbers=self.sample_numbers,
            sample_counter=self.counter,current_fs_hz=self.rate,is_running=owner.is_running,
            channel_colors=owner.channel_colors,_reduce_trace_for_display=owner._reduce_trace_for_display)


class RadioStream(RadioTimeline):
    def __init__(self, config, output_rate=20000, capacity=200000):
        super().__init__(output_rate, capacity)
        self.demod = AMDemodulator(config)
        self.resampler = AudioResampler(self.demod.output_rate, output_rate)

    def process(self, samples, first_index=None):
        return self.resampler.process(self.demod.process(samples, first_index))
