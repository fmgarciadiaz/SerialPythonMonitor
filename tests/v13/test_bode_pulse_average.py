import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import Mock, patch
import numpy as np
from scipy.signal import lfilter
from PyQt6 import QtWidgets
from monitor.v13.bode_pulse import PulseAverage
from monitor.v13.app import SerialMonitorWindow
from monitor.v13.receiver.unoq_generator import GeneratorReply
from monitor.v13.receiver.unoq_switch import Phase, Reason

class PulseAverageTests(unittest.TestCase):
 def test_cross_spectra_preserve_rc_transfer_with_common_timing_shifts(self):
  fs=40000;post=20000;pole=np.exp(-1/fs/.001);avg=PulseAverage(fs,.5)
  for onset in (2000,2753,5100,4000):
   x=np.r_[np.zeros(onset),np.ones(4),np.zeros(post-4)]
   y=lfilter([1-pole],[1,-pole],x)
   avg.add(np.column_stack((np.arange(len(x))/fs,1.65+x,1.65+y)),onset)
  data=avg.result();valid=np.isfinite(data[:,2])
  h=(1-pole)/(1-pole*np.exp(-2j*np.pi*data[valid,0]/fs))
  np.testing.assert_allclose(data[valid,1],20*np.log10(abs(h)),atol=1e-6)
  np.testing.assert_allclose(data[valid,2],np.angle(h,deg=True),atol=1e-6)
  np.testing.assert_allclose(avg.coherence,1,atol=1e-12)
 def test_more_shots_reduce_random_output_noise_without_averaging_db(self):
  fs=40000;onset=2000;x=np.r_[np.zeros(onset),np.ones(4),np.zeros(19996)]
  errors={1:[],4:[],8:[],16:[]}
  for seed in range(10):
   rng=np.random.default_rng(seed);avg=PulseAverage(fs,.5)
   for shot in range(1,17):
    y=.3*x+rng.normal(0,.004,len(x))
    avg.add(np.column_stack((np.arange(len(x))/fs,x,y)),onset)
    if shot in errors:
     data=avg.result();valid=np.isfinite(data[:,1])
     errors[shot].append(np.sqrt(np.mean((data[valid,1]-20*np.log10(.3))**2)))
  self.assertLess(np.mean(errors[8]),np.mean(errors[1])*.5)
  self.assertLess(np.mean(errors[16]),np.mean(errors[4]))
 def test_spectral_nulls_and_incoherent_output_phase_are_not_invented(self):
  fs=40000;onset=2000;x=np.r_[np.zeros(onset),np.ones(40),np.zeros(19960)]
  avg=PulseAverage(fs,.5)
  for seed in range(8):
   y=np.random.default_rng(seed).normal(0,.005,len(x))
   avg.add(np.column_stack((np.arange(len(x))/fs,x,y)),onset)
  data=avg.result();i=np.argmin(abs(data[:,0]-1000))
  self.assertTrue(np.isnan(data[i,1]));self.assertTrue(np.all(np.isnan(data[:,2])))
 def test_discontinuity_or_unfinished_response_rejects_a_shot(self):
  fs=40000;onset=2000;x=np.r_[np.zeros(onset),np.ones(4),np.zeros(19996)]
  d=np.column_stack((np.arange(len(x))/fs,x,x));avg=PulseAverage(fs,.5)
  d[3000:,0]+=.001
  with self.assertRaisesRegex(ValueError,'Discontinuidad'):avg.add(d,onset)
  self.assertEqual(avg.count,0)
  d[:,0]=np.arange(len(x))/fs;d[-4000:,2]=1
  with self.assertRaisesRegex(ValueError,'no terminó'):avg.add(d,onset)

class PulseSequenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  with patch('monitor.v13.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
  self.w.serial_worker=Mock();self.w.is_running=True;self.w._generator_state_known=True
  self.w._generator_requested=None;self.w._pulse_us_capable=True;self.w._auto_apply_timer.stop()
  self.w.spectral.select_bode(1);self.p=self.w.spectral.bode.panels[1]
 def tearDown(self):
  self.p.active=False;self.w.serial_worker=None;self.w.close()
 def ack(self):
  p=self.p;p.confirmed(GeneratorReply(0x80000001,Phase.APPLIED,Reason.OK,True,p.config,p.config))
 def test_multiple_shots_share_one_result_and_cancel_restores_controls(self):
  p=self.p;p.averages.setValue(2);p.begin();self.assertTrue(p.active)
  fs=p.result_profile.rate
  for shot in range(2):
   self.ack()
   low=p.pulse_config.low*3.3/4095;high=p.pulse_config.high*3.3/4095
   t=(np.arange(round(fs*.31))+shot*fs)/fs
   p.batch([{'Tiempo (us)':round(ts*1e6),'V_IN':low,'V_OUT':low} for ts in t])
   self.assertEqual(p.stage,'capture');self.ack()
   start=p.last_timestamp+1/fs
   vals=np.full(round(fs*p.capture.value()),low);vals[:4]=high
   p.batch([{'Tiempo (us)':round((start+i/fs)*1e6),'V_IN':v,'V_OUT':v} for i,v in enumerate(vals)])
   self.assertEqual(p.pulse_average.count,shot+1)
   if shot==0:
    self.assertTrue(p.active);self.assertEqual(p.stage,'baseline');self.assertFalse(p.result)
  self.assertFalse(p.active);self.assertTrue(p.result)
  self.assertEqual(p.status.text(),'Promedio completo · 2 pulsos')
  self.assertTrue(p.averages.isEnabled());self.assertFalse(self.w.serial_worker.request_generator.call_args.args[0].enabled)
 def test_cancel_does_not_leave_a_series_running(self):
  p=self.p;p.begin();p.cancel()
  self.assertFalse(p.active);self.assertTrue(p.averages.isEnabled())
  count=self.w.serial_worker.request_generator.call_count
  p.batch([{'Tiempo (us)':0,'V_IN':0,'V_OUT':0}])
  self.assertEqual(self.w.serial_worker.request_generator.call_count,count)
