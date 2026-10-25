import unittest
import numpy as np
from monitor.historico.v16.synth_oscillator import kernel

def reference(phase,frequency,rate,square):
    t=(phase/(2*np.pi))%1;dt=np.maximum(frequency/rate,1e-12)
    def blep(position):
        result=np.zeros_like(position);left=position<dt;right=position>1-dt
        x=position[left]/dt[left];result[left]=2*x-x*x-1
        x=(position[right]-1)/dt[right];result[right]=x*x+2*x+1
        return result
    return np.where(t<.5,1.,-1.)+blep(t)-blep((t+.5)%1) if square else 2*t-1-blep(t)

@unittest.skipIf(kernel is None,'Numba unavailable')
class OscillatorTests(unittest.TestCase):
    def test_exact_waveforms_edges_variable_pitch_and_readonly_frequency(self):
        rng=np.random.default_rng(42)
        for n in (0,1,13,480,960):
            phase=rng.uniform(-10000,10000,n);frequency=rng.uniform(0,50000,n)
            if n>12:phase[:7]=np.array([-1,-.5,0,.25,.5,.75,1])*2*np.pi;frequency[7:13]=0
            for square in (False,True):
                np.testing.assert_array_equal(kernel(phase,frequency,40000,square),reference(phase,frequency,40000,square))
                frequency.setflags(write=False)
                np.testing.assert_array_equal(kernel(phase,frequency,40000,square),reference(phase,frequency,40000,square))
