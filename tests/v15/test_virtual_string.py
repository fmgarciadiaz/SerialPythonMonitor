import unittest
import numpy as np
from monitor.v15.virtual_string import PluckedString, warmup, kernel
from monitor.v15.fm_source import FMSource, FMParameters

class VirtualStringTests(unittest.TestCase):
    def setUp(self):
        if kernel is None:self.skipTest('Numba no instalado')
        warmup()
    def test_pitch_decay_and_chunk_continuity(self):
        for rate in (20000,40000):
            audio=PluckedString(rate,220).render(rate,decay=1)
            power=abs(np.fft.rfft(audio[:rate//2]*np.hanning(rate//2)))
            frequency=np.fft.rfftfreq(rate//2,1/rate)[np.argmax(power)]
            self.assertLess(abs(frequency-220),3)
            self.assertLess(np.std(audio[-rate//10:]),np.std(audio[:rate//10])*.3)
            whole=PluckedString(rate,329.63).render(4800)
            chunked=PluckedString(rate,329.63)
            np.testing.assert_array_equal(whole,np.concatenate([chunked.render(480) for _ in range(10)]))
    def test_pluck_position_changes_timbre_and_polyphony_runs(self):
        near=PluckedString(20000,220,.1).render(2000)
        middle=PluckedString(20000,220,.5).render(2000)
        self.assertGreater(np.std(near-middle),.05)
        source=FMSource(rate=20000,parameters=FMParameters(preset='Guitarra',waveform='virtual',notes=((48,100),(60,127)),envelope=(.001,.01,1,.1)))
        data=source[0:4800]
        self.assertEqual(len(source.voices),2)
        self.assertGreater(np.std(data),100)
