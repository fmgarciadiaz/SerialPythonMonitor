import unittest
import numpy as np
from scipy.signal import lfilter, freqz
from monitor.v17.radio_am import AMDemodulator, RadioConfig, PolyphaseDecimator


class AMTests(unittest.TestCase):
    def test_polyphase_matches_full_filter_with_irregular_chunks(self):
        rng = np.random.default_rng(17)
        values = rng.normal(size=4097) + 1j*rng.normal(size=4097)
        for factor in (4, 8):
            d = PolyphaseDecimator(factor)
            reference = lfilter(d.taps, [1], values)[::factor]
            chunks = []
            offset = 0
            while offset < len(values):
                size = int(rng.integers(1, 211))
                chunks.append(d.process(values[offset:offset+size]))
                offset += size
                self.assertEqual(len(d.history), len(d.taps)-1)
            np.testing.assert_allclose(np.concatenate(chunks), reference, atol=1e-12)
            d.reset()
            np.testing.assert_allclose(d.process(values), reference, atol=1e-12)

    def test_polyphase_passband_and_alias_rejection(self):
        for factor in (4, 8):
            d = PolyphaseDecimator(factor)
            frequencies, response = freqz(d.taps, worN=65536, fs=1)
            gain = abs(response)
            self.assertLess(np.max(abs(gain[frequencies <= .25/factor]-1)), .001)
            self.assertLess(np.max(gain[frequencies >= .5/factor]), .0002)

    def test_fused_mixer_matches_mix_then_filter(self):
        values = np.random.default_rng(42).normal(size=8193)
        step = 2*np.pi*550000/(160000000/114)
        reference_filter = PolyphaseDecimator(8)
        reference = lfilter(reference_filter.taps, [1],
            values*np.exp(-1j*step*np.arange(len(values))))[::8]
        fused = PolyphaseDecimator(8, step)
        chunks = [fused.process(values[i:i+73]) for i in range(0, len(values), 73)]
        np.testing.assert_allclose(np.concatenate(chunks), reference, atol=1e-11)
        fused.reset()
        np.testing.assert_allclose(fused.process(values), reference, atol=1e-11)

    def test_audio_and_streaming(self):
        rate = 160000000 / 114
        t = np.arange(int(rate * .12)) / rate
        x = 1.65 + (1 + .5 * np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*550000*t)
        cfg = RadioConfig(rate, 550000)
        whole = AMDemodulator(cfg).process(x, 0)
        demod = AMDemodulator(cfg)
        chunks = np.concatenate([demod.process(x[i:i+3456], i) for i in range(0,len(x),3456)])
        np.testing.assert_allclose(chunks, whole, atol=1e-9)
        self.assertAlmostEqual(demod.output_rate, rate/32)
        y = whole[int(.04*demod.output_rate):]
        spectrum = np.abs(np.fft.rfft(y))
        freq = np.fft.rfftfreq(len(y), 1/demod.output_rate)
        self.assertLess(abs(freq[np.argmax(spectrum)]-1000), 15)
        self.assertGreater(np.std(y), .1)

    def test_gap_and_invalid_band(self):
        d = AMDemodulator(RadioConfig(40000, 10000))
        d.process(np.ones(32), 0)
        with self.assertRaises(ValueError): d.process(np.ones(32), 33)
        self.assertIsNone(d.next_index)
        for frequency in (0, 19999):
            with self.assertRaises(ValueError): AMDemodulator(RadioConfig(40000, frequency))

    def test_adjacent_station_rejected(self):
        rate = 160000000 / 114
        t = np.arange(int(rate*.1))/rate
        carrier = 550000
        station = (1+.5*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*carrier*t)
        neighbor = (1+.5*np.sin(2*np.pi*2000*t))*np.cos(2*np.pi*(carrier+20000)*t)
        d = AMDemodulator(RadioConfig(rate,carrier))
        y = d.process(station+neighbor)[int(.04*d.output_rate):]
        def amplitude(f):
            return abs(np.sum(y*np.exp(-2j*np.pi*f*np.arange(len(y))/d.output_rate)))
        self.assertGreater(amplitude(1000), 20*amplitude(2000))

    def test_empty_small_blocks_and_silence(self):
        cfg = RadioConfig(40000,10000)
        d = AMDemodulator(cfg)
        self.assertEqual(len(d.process([])),0)
        output=np.concatenate([d.process(np.zeros(7),i*7) for i in range(50)])
        np.testing.assert_array_equal(output,0)
        with self.assertRaises(ValueError):d.process([np.nan])
