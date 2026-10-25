import unittest
import numpy as np
from monitor.v17.spectral_analysis import _fft
from .fft_workspace import fft_workspace


class FftWorkspaceTests(unittest.TestCase):
    def test_identical_transform_and_readonly_input_preserved(self):
        rng = np.random.default_rng(71)
        for n in (255,256,65536):
            blocks = rng.normal(size=(4,n)) + 2
            before = blocks.copy()
            blocks.setflags(write=False)
            for window in ('Hann','Hamming','Blackman','Rectangular'):
                for remove_dc in (False,True):
                    expected = _fft(blocks,40000,window,remove_dc)
                    actual = fft_workspace(blocks,40000,window,remove_dc)
                    for left,right in zip(expected,actual):
                        np.testing.assert_array_equal(left,right)
                    np.testing.assert_array_equal(blocks,before)
