import unittest
import numpy as np
from scipy.signal import sosfreqz
from monitor.v17.digital_filter import DigitalFilter, FilterConfig
from monitor.v17.filter_presets import FILTER_PRESETS, apply_filter_preset


class FilterPresetTests(unittest.TestCase):
    def test_presets_preserve_source_and_do_not_enable_by_default(self):
        for name in FILTER_PRESETS:
            self.assertEqual(apply_filter_preset(name).source, 'OFF')
            self.assertEqual(apply_filter_preset(name, 'RADIO').source, 'RADIO')

    def test_narrow_rejection_at_audio_and_high_adc_rates(self):
        for rate in (40000, 981595, 1167883, 1509434):
            for name, center in (('reject_50', 50), ('reject_60', 60)):
                f = DigitalFilter()
                y = f.process(np.full(4096, 1.65), rate, apply_filter_preset(name, 'CH1'))
                self.assertTrue(np.isfinite(y).all())
                np.testing.assert_allclose(y, 1.65, atol=2e-5)
                _, response = sosfreqz(f.sos, worN=[10, center, 1000], fs=rate)
                self.assertLess(abs(response[1]), .001)
                self.assertGreater(min(abs(response[[0, 2]])), .99)

    def test_bandstop_families_chunk_invariance(self):
        x = np.random.default_rng(17).normal(size=12000)
        for design in ('Butterworth', 'Bessel', 'Chebyshev I', 'Chebyshev II', 'Elliptic'):
            cfg = FilterConfig(mode='bandstop', design=design, cutoff=49, upper=51)
            expected = DigitalFilter().process(x, 1509434, cfg)
            f = DigitalFilter()
            actual = np.concatenate([f.process(x[i:i+226], 1509434, cfg) for i in range(0, len(x), 226)])
            self.assertTrue(np.isfinite(actual).all())
            np.testing.assert_array_equal(actual, expected)

    def test_invalid_bandstop_and_rc_fail_explicitly(self):
        for cfg in (FilterConfig(mode='bandstop', design='RC'),
                    FilterConfig(mode='bandstop', cutoff=51, upper=49),
                    FilterConfig(mode='bandstop', cutoff=49, upper=20000)):
            with self.assertRaises(ValueError):
                DigitalFilter().process(np.ones(20), 40000, cfg)
