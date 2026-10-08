import unittest
import numpy as np
from monitor.historico.v13.audio_dc import DCBlocker

class DCBlockerTests(unittest.TestCase):
    def test_constant_dc_removed_independently(self):
        data = np.tile([10000., -20000.], (1000, 1))
        np.testing.assert_allclose(DCBlocker(40000).process(data), 0, atol=1e-7)

    def test_batch_boundaries_match_continuous_filter(self):
        rate = 40000
        t = np.arange(rate) / rate
        data = np.column_stack((10000 + 5000*np.sin(2*np.pi*1000*t),
                                -2000 + 3000*np.cos(2*np.pi*200*t)))
        expected = DCBlocker(rate).process(data)
        block = DCBlocker(rate)
        actual = np.concatenate([block.process(part) for part in np.array_split(data, 137)])
        np.testing.assert_allclose(actual, expected, atol=1e-7)
        self.assertLess(abs(actual[-rate//2:,0].mean()), 1)
        self.assertGreater(np.std(actual[-rate//2:,0]), 3500)
