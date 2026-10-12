import unittest
import numpy as np
from monitor.v16.digital_filter import DigitalFilter,FilterConfig
class FilterTests(unittest.TestCase):
 def test_chunks_match(self):
  x=np.random.default_rng(4).normal(size=10000);cfg=FilterConfig()
  a=DigitalFilter().process(x,40000,cfg);f=DigitalFilter();b=np.concatenate([f.process(x[i:i+226],40000,cfg) for i in range(0,len(x),226)])
  np.testing.assert_array_equal(a,b)
 def test_lowpass_and_highpass(self):
  t=np.arange(40000)/40000;x=np.sin(2*np.pi*100*t)+np.sin(2*np.pi*5000*t)
  for mode,accepted,rejected in [('lowpass',100,5000),('highpass',5000,100)]:
   y=DigitalFilter().process(x,40000,FilterConfig(mode=mode))
   spectrum=abs(np.fft.rfft(y[10000:]))
   freq=np.fft.rfftfreq(30000,1/40000)
   self.assertGreater(spectrum[np.argmin(abs(freq-accepted))],10*spectrum[np.argmin(abs(freq-rejected))])
 def test_constant_no_startup_jump(self):
  for design in ('RC','Butterworth'):
   y=DigitalFilter().process(np.full(400,1.65),40000,FilterConfig(design=design));np.testing.assert_allclose(y,1.65,atol=1e-10)
 def test_band_and_range(self):
  for design in ('RC','Butterworth'):
   y=DigitalFilter().process(np.ones(500),2500,FilterConfig(design=design,mode='bandpass',cutoff=1000,upper=5000))
   self.assertTrue(np.isfinite(y).all());self.assertLess(abs(y[-1]),1e-5)
 def test_gap_rejected(self):
  f=DigitalFilter();f.process([1,1],40000,FilterConfig(),[0,1],[0,25])
  with self.assertRaises(ValueError):f.process([1],40000,FilterConfig(),[3],[75])

 def test_added_families_are_stable_and_chunk_invariant(self):
  x=np.random.default_rng(8).normal(size=8000)
  for design in ('Bessel','Chebyshev I','Chebyshev II','Elliptic'):
   for mode in ('lowpass','highpass','bandpass'):
    config=FilterConfig(design=design,mode=mode,order=4)
    whole=DigitalFilter().process(x,40000,config)
    f=DigitalFilter();parts=np.concatenate([f.process(x[i:i+226],40000,config) for i in range(0,len(x),226)])
    np.testing.assert_array_equal(whole,parts);self.assertTrue(np.isfinite(whole).all())
    self.assertLess(max(abs(whole)),10)
