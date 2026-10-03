import unittest
from types import SimpleNamespace
import numpy as np
from monitor.v10.bode_calibration import correct_transfer


class CalibrationTests(unittest.TestCase):
    def test_profile_range_and_log_interpolation(self):
        profile=SimpleNamespace(bits=16,rate=50000)
        reference={'acquisition':{'bits':16,'rate':50000},'points':[[100,1,10],[10000,3,30]]}
        data=[[10,-5,-45],[1000,-10,-90],[20000,-20,float('nan')]]
        corrected, mask=correct_transfer(data,reference,profile)
        np.testing.assert_array_equal(mask,[False,True,False])
        np.testing.assert_allclose(corrected[1],[1000,-12,-110])
        np.testing.assert_allclose(corrected[0],data[0])
        self.assertTrue(np.isnan(corrected[2,2]))
        profile.rate=31250
        corrected,mask=correct_transfer(data,reference,profile)
        self.assertFalse(mask.any())
        np.testing.assert_allclose(corrected,data,equal_nan=True)

    def test_zero_output_stays_zero(self):
        reference={'acquisition':{'bits':16,'rate':50000},'points':[[100,1,10],[10000,3,30]]}
        corrected,_=correct_transfer([[1000,float('-inf'),float('nan')]],reference,SimpleNamespace(bits=16,rate=50000))
        self.assertTrue(np.isneginf(corrected[0,1]))
        self.assertTrue(np.isnan(corrected[0,2]))
