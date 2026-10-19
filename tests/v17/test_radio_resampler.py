"""Streaming resampling against the direct windowed-sinc definition."""
import unittest
from fractions import Fraction
import numpy as np
from monitor.v17.radio_stream import AudioResampler


def direct_sinc(values, input_rate, output_rate):
    ratio = input_rate/output_rate
    fraction = Fraction(ratio).limit_denominator(4096)
    if abs(float(fraction)-ratio)<1e-12:
        # Evaluate the time grid using exact scalar fractions, independently
        # from the vectorized phase table and streaming buffer implementation.
        positions = [i*fraction for i in range(int(np.ceil(max(0,len(values)-64)/ratio))+1)
                     if i*fraction < len(values)-64]
        centers = np.array([int(position) for position in positions])
        phases = np.array([float(position-int(position)) for position in positions])
    else:
        positions = np.arange(max(0,int(np.ceil((len(values)-64)/ratio))))*ratio
        centers = np.floor(positions).astype(int)
        phases = positions-centers
    indices = centers[:,None]+np.arange(-63,65)
    distance = phases[:,None]-np.arange(-63,65)
    cutoff = .45*min(1,output_rate/input_rate)
    window = np.i0(8.6*np.sqrt(np.maximum(0,1-(distance/64)**2)))/np.i0(8.6)
    weights = 2*cutoff*np.sinc(2*cutoff*distance)*window
    weights /= weights.sum(axis=1)[:,None]
    samples = values[np.clip(indices,0,len(values)-1)]
    samples = np.where((indices>=0)&(indices<len(values)),samples,0)
    return np.sum(weights*samples,axis=1)


class RadioResamplerTests(unittest.TestCase):
    def test_direct_sinc_startup_irregular_blocks_and_all_audio_rates(self):
        rng = np.random.default_rng(814)
        values = rng.normal(size=4123)
        for input_rate in (160000000/114/32, np.sqrt(2)*20000):
            for output_rate in (8000,20000,40000,48000):
                with self.subTest(input_rate=input_rate,output_rate=output_rate):
                    expected = direct_sinc(values,input_rate,output_rate)
                    resampler = AudioResampler(input_rate,output_rate)
                    chunks = []
                    offset = 0
                    while offset < len(values):
                        self.assertEqual(len(resampler.process(np.empty(0))),0)
                        size = int(rng.integers(1,200))
                        chunks.append(resampler.process(values[offset:offset+size]))
                        offset += size
                        self.assertLessEqual(len(resampler.buffer),129)
                    actual = np.concatenate(chunks)
                    np.testing.assert_allclose(actual,expected,atol=2e-11,rtol=1e-11)
                    self.assertEqual(resampler.output_count,len(expected))

    def test_impulse_delay_gain_and_alias_rejection(self):
        rate = 160000000/114/32
        t = np.arange(10000)/rate
        for output_rate in (20000,40000,48000):
            with self.subTest(output_rate=output_rate):
                impulse = np.zeros(len(t)); impulse[123] = 1
                actual = AudioResampler(rate,output_rate).process(impulse)
                np.testing.assert_allclose(actual,direct_sinc(impulse,rate,output_rate),atol=1e-13)
                self.assertLessEqual(abs(np.argmax(abs(actual))-123*output_rate/rate),1)
                dc = AudioResampler(rate,output_rate).process(np.ones(len(t)))
                np.testing.assert_allclose(dc[100:],1,atol=1e-14)
        passed = AudioResampler(rate,20000).process(np.sin(2*np.pi*1000*t))[200:]
        rejected = AudioResampler(rate,20000).process(np.sin(2*np.pi*15000*t))[200:]
        self.assertLess(np.std(rejected)/np.std(passed),1e-4)

    def test_partition_equivalence_over_many_phase_cycles(self):
        rate = 160000000/114/32
        values = np.random.default_rng(77).normal(size=100003)
        for output_rate in (20000,40000,48000):
            resampler = AudioResampler(rate,output_rate)
            actual = np.concatenate([resampler.process(values[i:i+877]) for i in range(0,len(values),877)])
            expected = AudioResampler(rate,output_rate).process(values)
            np.testing.assert_allclose(actual,expected,atol=2e-14,rtol=1e-14)


if __name__ == '__main__':
    unittest.main()
