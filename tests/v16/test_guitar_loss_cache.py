import unittest
import numpy as np
from monitor.v16.virtual_string import PluckedString,kernel

@unittest.skipIf(kernel is None,'Numba unavailable')
class GuitarLossCacheTests(unittest.TestCase):
    def test_parameter_changes_and_different_strings_preserve_buffer_state(self):
        for rate in (20000,40000):
            for frequency in (65.4,220.,987.8):
                actual=PluckedString(rate,frequency);expected=PluckedString(rate,frequency)
                for count,brightness,decay,bridge in ((0,.65,3.,.2),(1,.65,3.,.2),(480,.65,3.,.2),(17,.9,.8,.8),(480,.65,3.,.2)):
                    omega=2*np.pi*frequency/rate
                    lag=-np.angle(brightness+(1-brightness)*np.exp(-1j*omega))/omega
                    delay=max(2.,rate/frequency-lag);gain=10**(-3*(1+bridge*.5)/(frequency*decay))
                    reference,expected.cursor,expected.previous=kernel(expected.buffer,expected.cursor,expected.previous,count,delay,float(brightness),float(gain))
                    np.testing.assert_array_equal(actual.render(count,brightness,decay,bridge),reference)
                    np.testing.assert_array_equal(actual.buffer,expected.buffer)
                    self.assertEqual((actual.cursor,actual.previous),(expected.cursor,expected.previous))
