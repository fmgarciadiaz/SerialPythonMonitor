import unittest
import numpy as np
from scipy.signal import butter,sosfilt
from monitor.v16.synth_filters import kernel

@unittest.skipIf(kernel is None,'Numba unavailable')
class SynthFilterTests(unittest.TestCase):
    def test_exact_scipy_output_and_state_across_chunks_and_strided_input(self):
        rng=np.random.default_rng(19)
        for order in (2,4,8):
            coefficients=butter(order,.2,output='sos')
            for readonly in (False,True):
                coefficients.setflags(write=not readonly);state=rng.normal(size=(len(coefficients),2));expected_state=state.copy()
                signal=rng.normal(size=2000)[::2]
                for start,stop in ((0,1),(1,17),(17,497),(497,1000)):
                    before=state.copy()
                    expected,expected_state=sosfilt(coefficients.copy(),signal[start:stop],zi=expected_state)
                    actual,new_state=kernel(coefficients,signal[start:stop],state)
                    np.testing.assert_array_equal(state,before)
                    np.testing.assert_array_equal(actual,expected)
                    np.testing.assert_array_equal(new_state,expected_state);state=new_state
