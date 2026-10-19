"""Read WAV, select mono channel and prepare band-limited 20 ksps DAC codes."""
from dataclasses import dataclass
from math import gcd
from pathlib import Path
import struct
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

RATE = 20000

@dataclass(frozen=True)
class WavSource:
    codes: np.ndarray
    original_rate: int
    channels: int
    path: str
    output_rate: int = RATE
    @property
    def duration(self):
        return len(self.codes) / self.output_rate

def prepare_wav(path, channel='Mix', amplitude=2.0, offset=1.65, rate_out=20000):
    if rate_out not in (20000,40000,50000): raise ValueError('Tasa WAV no soportada')
    if channel not in ('L', 'R', 'Mix'):
        raise ValueError('Canal WAV inválido')
    if not (0 <= amplitude <= 3.3 and amplitude / 2 <= offset <= 3.3 - amplitude / 2):
        raise ValueError('Amplitud y offset fuera de 0–3,3 V')
    rate, data = wavfile.read(path)
    if rate <= 0 or data.size == 0 or data.ndim not in (1, 2):
        raise ValueError('WAV vacío o formato inválido')
    channels = 1 if data.ndim == 1 else data.shape[1]
    if channels not in (1, 2):
        raise ValueError('Seleccionar un WAV mono o estéreo')
    # Convert before averaging, avoiding integer overflow and unsigned PCM bias.
    if data.dtype.kind == 'u':
        midpoint = 2 ** (data.dtype.itemsize * 8 - 1)
        signal = (data.astype(np.float64) - midpoint) / midpoint
    elif data.dtype.kind == 'i':
        signal = data.astype(np.float64) / 2 ** (data.dtype.itemsize * 8 - 1)
    elif data.dtype.kind == 'f':
        signal = data.astype(np.float64)
    else:
        raise ValueError('Codificación WAV no soportada')
    if not np.isfinite(signal).all():
        raise ValueError('WAV contiene muestras no finitas')
    if channels == 2:
        signal = signal[:, 0] if channel == 'L' else signal[:, 1] if channel == 'R' else signal.mean(axis=1)
    signal -= signal.mean()
    divisor = gcd(int(rate), rate_out)
    signal = resample_poly(signal, rate_out // divisor, int(rate) // divisor)
    signal -= signal.mean()
    peak = np.max(np.abs(signal))
    if peak > 1e-12:
        signal *= (amplitude / 2) / peak
    else:
        signal[:] = 0
    codes = np.rint((signal + offset) * 4095 / 3.3).clip(0, 4095).astype('<u2')
    codes.setflags(write=False)
    return WavSource(codes, int(rate), channels, str(Path(path)),rate_out)


def inspect_wav(path):
    """Read bounded RIFF metadata without loading/resampling the audio."""
    with open(path, 'rb') as stream:
        header = stream.read(12)
        if len(header) != 12 or header[:4] != b'RIFF' or header[8:] != b'WAVE':
            raise ValueError('Archivo WAV RIFF inválido')
        end = min(Path(path).stat().st_size, struct.unpack_from('<I', header, 4)[0] + 8)
        fmt = None
        data_size = 0
        while stream.tell() + 8 <= end:
            chunk = stream.read(8)
            name, size = struct.unpack('<4sI', chunk)
            start = stream.tell()
            if start + size > end:
                raise ValueError('WAV incompleto o truncado')
            if name == b'fmt ':
                raw = stream.read(min(size, 64))
                if len(raw) < 16: raise ValueError('Formato WAV incompleto')
                encoding, channels, rate, byte_rate, align, bits = struct.unpack_from('<HHIIHH', raw)
                if encoding == 65534 and len(raw) >= 40:
                    encoding = struct.unpack_from('<H', raw, 24)[0]
                if encoding not in (1, 3): raise ValueError('WAV comprimido no soportado')
                if channels not in (1, 2) or not rate or not align or bits not in (8,16,24,32,64):
                    raise ValueError('Frecuencia, bits o canales WAV no soportados')
                fmt = {'rate':rate, 'bits':bits, 'channels':channels, 'encoding':'float' if encoding==3 else 'PCM', 'align':align}
            elif name == b'data': data_size += size
            stream.seek(start + size + (size & 1))
        if fmt is None or not data_size or data_size % fmt['align']:
            raise ValueError('WAV vacío o datos incompletos')
        fmt['duration'] = data_size / fmt['align'] / fmt['rate']
        return fmt


def seek_playback(receiver, codes, origin, seconds):
    """Restart the DAC session at a bounded absolute position after confirmed Stop."""
    rate = receiver.wav_rate
    position = origin + receiver.wav_status.played
    target = max(0, min(len(codes), position + round(seconds * rate)))
    receiver.reset_wav_output()
    if target < len(codes):
        receiver.wav_request(1, codes[target:], rate)
    return target
