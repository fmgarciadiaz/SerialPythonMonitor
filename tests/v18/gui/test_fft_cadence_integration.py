"""Exercise cadence through the actual display render entry point, never Q."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets
from monitor.v18.app import SerialMonitorWindow
from monitor.v18.receiver.unoq_acquisition import Configuration

class FftCadenceIntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  with patch('monitor.v18.app.usb_devices',return_value=[]),patch('monitor.v18.app.list_ports.comports',return_value=[]):
   self.w=SerialMonitorWindow()
  self.w.render_timer.stop();self.d=self.w.spectral
  self.w.applied_configuration=Configuration(8,1860465)
  self.w.current_fs_hz=self.w.applied_configuration.actual_rate
  self.d.set_mode(1);self.d.size.setCurrentText('65536')
  self.d.channels[1].setCurrentText('Ninguno')
  self.w.sample_numbers=np.arange(65536)
  self.w.series={'Tiempo (us)':np.arange(65536)*1e6/self.w.current_fs_hz}
  self.w.serial_worker=SimpleNamespace(pending_batches=0)
 def tearDown(self):
  self.w.serial_worker=None;self.w.close();self.app.processEvents()
 def turn(self,now,cost=.005,new=True):
  def analyze(*args,**kwargs):
   if new:self.d.last_end=self.w.sample_counter
  with patch('monitor.v18.spectrum.time.monotonic',return_value=now),patch('monitor.v18.spectrum.time.perf_counter',side_effect=[0.,cost]),patch.object(self.d,'_render_fft_analysis',side_effect=analyze) as render:
   self.d.render()
   return render.call_count
 def warm(self):
  for i in range(8):
   self.w.sample_counter=i+1
   self.assertEqual(self.turn(100+i*.101),1)
 def test_warmup_speedup_then_backlog_requires_new_warmup(self):
  self.warm();self.assertEqual(len(self.d._fft_render_costs),8)
  self.w.sample_counter+=1;self.assertEqual(self.turn(100.77),1)
  self.w.serial_worker.pending_batches=2
  self.assertEqual(self.turn(100.9),0)
  self.assertFalse(self.d._fft_render_costs)
  self.w.serial_worker.pending_batches=0
  self.w.sample_counter+=1;self.assertEqual(self.turn(100.91),1)
  self.w.sample_counter+=1;self.assertEqual(self.turn(100.98),0)
 def test_audio_playback_keeps_ten_hz_even_after_light_warmup(self):
  self.warm();self.w._wav_active=True;self.w.sample_counter+=1
  self.assertEqual(self.turn(100.77),0)
  self.assertEqual(self.turn(100.81),1)
  self.w._wav_active=False
 def test_brief_backlog_cannot_bypass_cold_interval(self):
  self.w.sample_counter=1;self.assertEqual(self.turn(100),1)
  self.w.serial_worker.pending_batches=2;self.assertEqual(self.turn(100.01),0)
  self.w.serial_worker.pending_batches=0;self.w.sample_counter=2
  self.assertEqual(self.turn(100.02),0)
  self.assertEqual(self.turn(100.11),1)
 def test_heavy_completed_frame_returns_to_ten_hz(self):
  self.warm();self.w.sample_counter+=1
  self.assertEqual(self.turn(100.77,cost=.026),1)
  self.w.sample_counter+=1;self.assertEqual(self.turn(100.84),0)
  self.assertEqual(self.turn(100.87),1)
 def test_no_new_result_does_not_create_fast_cadence_evidence(self):
  self.assertEqual(self.turn(100,new=False),1)
  self.assertFalse(self.d._fft_render_costs)
  self.d.last_fast_render=0
  self.warm();self.d.reset();self.assertFalse(self.d._fft_render_costs)
