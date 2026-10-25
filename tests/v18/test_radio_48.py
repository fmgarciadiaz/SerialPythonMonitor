import unittest
from types import SimpleNamespace
import numpy as np
from monitor.v18.radio_output import RadioDacSource
class Radio48Tests(unittest.TestCase):
    def test_48k_audio_converts_to_40k_dac_without_pitch_or_block_seams(self):
        source=RadioDacSource(1,buffer_seconds=0,rate=40000,input_rate=48000)
        settings=SimpleNamespace(radio_offset=0)
        t=np.arange(4800)/48000
        signal=.2*np.sin(2*np.pi*1000*t)
        for part in np.array_split(signal,10):source.feed_result(dict(settings=settings,radio_key=(1600000,500000,48000,8000),audio=part))
        self.assertIsNone(source.error)
        samples=np.concatenate(list(source._chunks))
        self.assertLess(abs(len(samples)-4000),60)
        f=np.fft.rfftfreq(len(samples),1/source.rate)
        self.assertAlmostEqual(f[np.argmax(abs(np.fft.rfft(samples)))],1000,delta=12)
        self.assertLess(np.max(abs(np.diff(samples[100:]))),.04)
