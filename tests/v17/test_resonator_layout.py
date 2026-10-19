import unittest
import numpy as np
from diagnosticos.benchmark_resonadores_v16 import reference_kernel
from monitor.v17.virtual_instruments import body_kernel,_peak_bank

class ResonatorLayoutTests(unittest.TestCase):
    def test_exact_signal_and_state_across_irregular_blocks(self):
        rng=np.random.default_rng(51)
        for modes in (0,1,32,96):
            coefficients=_peak_bank(20000,tuple((100.+i*33,20.+i) for i in range(modes))) if modes else np.zeros((0,5))
            weights=rng.normal(size=modes)
            a=rng.normal(size=(modes,2))*.001;b=a.copy()
            for count in (0,1,13,480,7,480):
                signal=rng.normal(size=count)*.01
                np.testing.assert_array_equal(body_kernel(signal,coefficients,b,weights),reference_kernel(signal,coefficients,a,weights))
                np.testing.assert_array_equal(a,b)

if __name__=='__main__':unittest.main()
