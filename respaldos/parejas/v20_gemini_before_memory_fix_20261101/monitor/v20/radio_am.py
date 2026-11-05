"""Streaming AM envelope detector; output retains its actual sample rate."""
from dataclasses import dataclass
import numpy as np
from scipy.signal import butter, sosfilt, firwin, kaiserord, upfirdn


class PolyphaseDecimator:
    """Causal FIR: compute only retained outputs, preserving the sample grid."""
    def __init__(self, factor, mix_step=0.0):
        self.factor = factor
        self.mix_step = mix_step
        # Pass band ends at .25 of the output rate, stop band at .5.
        taps, beta = kaiserord(80, .5 / factor)
        self.taps = firwin(taps | 1, .75 / factor, window=('kaiser', beta))
        if mix_step:
            # Heterodyne inside the FIR; rotate only the decimated outputs.
            self.taps = self.taps * np.exp(1j*mix_step*np.arange(len(self.taps)))
        self.reset()

    def reset(self):
        self.history = np.zeros(len(self.taps) - 1, dtype=float if self.mix_step else complex)
        self.total = 0
        self.phase = 0.0

    def process(self, values):
        if not len(values):
            return np.empty(0, dtype=complex)
        combined = np.concatenate((self.history, values))
        origin = self.total - len(self.history)
        padding = origin % self.factor
        if padding:
            combined = np.pad(combined, (padding, 0))
        aligned_origin = origin - padding
        start = (self.total - aligned_origin + self.factor - 1) // self.factor
        stop = (self.total + len(values) - aligned_origin + self.factor - 1) // self.factor
        output = upfirdn(self.taps, combined, down=self.factor)[start:stop]
        if self.mix_step:
            positions = np.arange(start, stop)*self.factor + aligned_origin - self.total
            output *= np.exp(-1j*(self.phase + self.mix_step*positions))
            self.phase = (self.phase + self.mix_step*len(values)) % (2*np.pi)
        self.history = combined[-len(self.history):].copy()
        self.total += len(values)
        return output


@dataclass(frozen=True)
class RadioConfig:
    rate: float
    frequency: float
    bandwidth: float = 8000.0
    gain: float = 1.0


def radio_input_supported(config):
    # RADIO always demodulates CH1; dual transport still provides that channel.
    return config.channels in (1,2) and config.bits in (8,10,12,14,16) and radio_tuning_max(config.actual_rate)>=5000


def radio_tuning_max(rate, bandwidth=8000.):
    # Keep the entire selected RF channel strictly below Nyquist.
    return int(np.ceil(rate/2-bandwidth/2))-1


class AMDemodulator:
    def __init__(self, config):
        if not (np.isfinite([config.rate, config.frequency, config.bandwidth, config.gain]).all()
                and config.rate > 0 and config.bandwidth > 100
                and config.bandwidth / 2 < config.frequency < config.rate / 2 - config.bandwidth / 2
                and 0 <= config.gain <= 10):
            raise ValueError('Configuración AM fuera de banda')
        self.config = config
        self.stages = []
        rate = config.rate
        for factor in (8, 4):
            if rate / factor >= config.bandwidth * 4:
                mix_step = 2*np.pi*config.frequency/config.rate if not self.stages else 0.0
                self.stages.append(PolyphaseDecimator(factor, mix_step))
                rate /= factor
        self.output_rate = rate
        self.channel = butter(6, config.bandwidth / 2, fs=rate, output='sos')
        self.audio = butter(6, config.bandwidth * .44, fs=rate, output='sos')
        self.dc = butter(2, 30, btype='highpass', fs=rate, output='sos')
        self.reset()

    def reset(self):
        self.phase = 0.0
        for stage in self.stages:
            stage.reset()
        self.channel_state = np.zeros((len(self.channel), 2), complex)
        self.dc_state = np.zeros((len(self.dc), 2))
        self.audio_state = np.zeros((len(self.audio), 2))
        self.next_index = None

    def process(self, samples, first_index=None):
        samples = np.asarray(samples, dtype=float)
        if samples.ndim != 1 or not np.isfinite(samples).all():
            self.reset()
            raise ValueError('Muestras RF inválidas')
        if first_index is not None and self.next_index is not None and first_index != self.next_index:
            self.reset()
            raise ValueError('Discontinuidad RF; RADIO reiniciada')
        if not len(samples):
            return np.empty(0)
        if self.stages:
            iq = samples
        else:
            step = 2 * np.pi * self.config.frequency / self.config.rate
            iq = samples * np.exp(-1j * (self.phase + step * np.arange(len(samples))))
            self.phase = (self.phase + step * len(samples)) % (2 * np.pi)
        if first_index is not None:
            self.next_index = (first_index + len(samples)) & 0xffffffff
        for stage in self.stages:
            iq = stage.process(iq)
            if not len(iq):
                return np.empty(0)
        iq, self.channel_state = sosfilt(self.channel, iq, zi=self.channel_state)
        audio, self.dc_state = sosfilt(self.dc, np.abs(iq), zi=self.dc_state)
        audio, self.audio_state = sosfilt(self.audio, audio, zi=self.audio_state)
        return audio * self.config.gain
