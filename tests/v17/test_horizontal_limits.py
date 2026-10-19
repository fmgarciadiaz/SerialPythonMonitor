import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets
from monitor.v17.app import SerialMonitorWindow
from monitor.v17.receiver.unoq_native import PROFILES
from monitor.v17.history import SampleHistory

class HorizontalLimitsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  with patch('monitor.v17.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
 def tearDown(self):self.w.close()
 def test_all_profiles_have_four_seconds_and_sufficient_history(self):
  for bits,rate in [(14,1000),(14,40000)]+[(p['bits'],160000000//p['ticks']) for p in PROFILES]:
   self.w._acquisition_confirmed(bits,rate)
   lo,hi=self.w._horizontal_sample_limits();dt=self.w.applied_configuration.dt_us
   self.assertEqual(lo,8)
   self.assertGreaterEqual(hi*dt/1e6,4)
   self.assertGreater(self.w.sample_numbers.maxlen,hi)
   self.assertTrue(all(h.maxlen==self.w.sample_numbers.maxlen for h in self.w.series.values()))
   self.w.dial_h_scale.setValue(1000);self.assertEqual(self.w.h_scale,hi)
   self.w.dial_h_scale.setValue(0);self.assertEqual(self.w.h_scale,lo)
 def test_duration_is_preserved_in_time_and_sample_display(self):
  for time_mode in (True,False):
   self.w.x_axis_time_mode=time_mode
   self.w._acquisition_confirmed(14,40000);self.w.on_h_scale_changed(80000)
   self.w._acquisition_confirmed(8,1221374)
   self.assertAlmostEqual(self.w.h_scale*self.w.applied_configuration.dt_us/1e6,2,places=5)
   self.w._acquisition_confirmed(14,1000);self.assertEqual(self.w.h_scale,2000)
 def test_unavailable_duration_clamps_and_low_rate_can_show_more(self):
  self.w._acquisition_confirmed(14,1000);self.w.on_h_scale_changed(20000)
  self.assertEqual(self.w.lbl_h_scale.suffix(),' s')
  self.w._acquisition_confirmed(8,1221374)
  self.assertEqual(self.w.h_scale,self.w._horizontal_sample_limits()[1])
  self.w._on_h_scale_input(2)
  self.assertAlmostEqual(self.w.h_scale*self.w.applied_configuration.dt_us/1e6,2,places=5)
 def test_history_resize_keeps_recent_values_across_wrap(self):
  h=SampleHistory(7);h.extend(np.arange(12));h.resize(5)
  np.testing.assert_array_equal(h.window(0,len(h)),np.arange(7,12))
  h.resize(10);h.extend(np.arange(12,15))
  np.testing.assert_array_equal(h.window(0,len(h)),np.arange(7,15))

 def test_fastest_history_really_retains_four_seconds(self):
  from monitor.v17.receiver.unoq_acquisition import Configuration
  c=Configuration(8,1221374);n=int(np.ceil(4*c.actual_rate))
  h=SampleHistory(n+260000);total=n+500000
  for start in range(0,total,8192):h.extend(np.arange(start,min(start+8192,total)))
  window=h.window(len(h)-n,len(h))
  self.assertEqual(len(window),n)
  self.assertEqual(window[0],total-n);self.assertEqual(window[-1],total-1)
  self.assertTrue(np.all(np.diff(window)==1))
