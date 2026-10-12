import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from monitor.v16 import piano_calibration as calibration
from monitor.v16.virtual_instruments import PianoStrings,warmup,modal_kernel

class PianoCalibrationTests(unittest.TestCase):
    def tearDown(self):
        calibration._rows.cache_clear();calibration.modal_correction.cache_clear()

    def test_missing_optional_profile_keeps_physical_fallback(self):
        with patch.object(calibration,'DATA',Path('/tmp/nonexistent_piano_profile.json')):
            calibration._rows.cache_clear();calibration.modal_correction.cache_clear()
            self.assertIsNone(calibration.modal_correction(261.626,.5))

    def test_identified_piano_is_bounded_and_chunk_continuous_across_register(self):
        if modal_kernel is None:self.skipTest('Numba no instalado')
        warmup()
        for rate in (20000,40000):
            for note in (24,48,60,63,72,96,108):
                frequency=440*2**((note-69)/12)
                whole=PianoStrings(rate,frequency,velocity=.8,calibrated=True).render(4000,brightness=.78)
                source=PianoStrings(rate,frequency,velocity=.8,calibrated=True)
                chunks=np.concatenate([source.render(n,brightness=.78) for n in (1,13,137,480,3369)])
                np.testing.assert_array_equal(whole,chunks)
                self.assertTrue(np.isfinite(whole).all())
                self.assertLess(np.max(abs(whole)),2.)
                self.assertGreater(np.std(whole),1e-8)
