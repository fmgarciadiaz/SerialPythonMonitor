"""Regression cases reproduced in Astra's Bode review."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from types import SimpleNamespace
import numpy as np
from PyQt6 import QtWidgets
from monitor.v13.app import SerialMonitorWindow
from monitor.v13.receiver.unoq_generator import GeneratorReply
from monitor.v13.receiver.unoq_switch import Phase, Reason
from monitor.v13.bode_calibration import load_reference, correct_transfer

class BodeReviewTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  with patch('monitor.v13.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
 def tearDown(self):
  for p in self.w.spectral.bode.panels:p.active=False
  self.w.serial_worker=None;self.w.close()
 def ready(self):
  w=self.w;w.serial_worker=Mock();w.is_running=True;w._generator_state_known=True
  w._generator_requested=None;w._pulse_us_capable=True;w._auto_apply_timer.stop()
 def reply(self,p,phase=Phase.APPLIED):
  return GeneratorReply(0x80000001,phase,Reason.OK if phase==Phase.APPLIED else Reason.BUSY,True,p.config,p.config if phase==Phase.APPLIED else None)
 def test_historical_calibration_cannot_apply_even_with_same_profile(self):
  self.assertIsNone(load_reference())
  ref={'acquisition':{'bits':16,'rate':50000},'points':[[20,1,5],[5000,1,5]]}
  data=[[100,0,0]];out,mask=correct_transfer(data,ref,SimpleNamespace(bits=16,rate=50000))
  np.testing.assert_array_equal(out,data);self.assertFalse(mask.any())
  self.assertFalse(self.w.spectral.bode.panels[0].calibrated.isEnabled())
 def test_verified_reference_is_gated_by_board_firmware_profile_and_method(self):
  identity={'board_serial':'Q-test','app':'scope-test','firmware_sha256':'a'*64}
  ref={'instrument':identity,'method':'tone','validation':{'accepted':True},'acquisition':{'bits':14,'rate':40000},
       'points':[[20,.1,2],[5000,.1,2]]}
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/'bode_reference_test.json';path.write_text(json.dumps(ref))
   with patch('monitor.v13.bode_calibration.CALIBRATION_DIR',Path(root)):
    self.w.spectral.bode.set_instrument(identity)
    p=self.w.spectral.bode.panels[0]
    self.assertTrue(p.calibrated.isEnabled());self.assertTrue(p.calibrated.isChecked())
    self.assertFalse(self.w.spectral.bode.panels[1].calibrated.isEnabled())
    p.result_instrument=identity;p.result_profile=self.w.applied_configuration
    p.result=[(20,.1,2),(5000,.1,2)]
    self.w.spectral.select_bode(0)
    np.testing.assert_allclose(p.curve_sets[0][0].yData,[0,0],atol=1e-12)
    np.testing.assert_allclose(p.curve_sets[0][1].yData,[0,0],atol=1e-12)
    changed=dict(identity,firmware_sha256='b'*64)
    self.w.spectral.bode.set_instrument(changed)
    self.assertFalse(p.calibrated.isEnabled())
    self.assertIsNone(load_reference(path,changed))
    out,mask=correct_transfer(p.result,ref,SimpleNamespace(bits=14,rate=100000),identity)
    self.assertFalse(mask.any())
    np.testing.assert_array_equal(out,p.result)
 def test_polls_do_not_extend_capture_deadline(self):
  for p in self.w.spectral.bode.panels:
   p.active=True;p.waiting=False;p.config=self.w._generator_config();p.deadline=1
   with patch('time.monotonic',return_value=100):p.confirmed(self.reply(p))
   self.assertEqual(p.deadline,1)
   p.cancel=Mock()
   with patch('time.monotonic',return_value=100):
    self.w.is_running=True;self.w.serial_worker=Mock();p.tick()
   p.cancel.assert_called_once();p.active=False
 def test_rejected_tone_without_requested_payload_is_reported(self):
  p=self.w.spectral.bode.panels[0];p.active=True;p.waiting=True;p.config=self.w._generator_config()
  p.confirmed(self.reply(p,Phase.REJECTED))
  self.assertFalse(p.active);self.assertIn('BUSY',p.status.text())
 def test_restores_current_and_history_curves_after_mode_changes(self):
  b=self.w.spectral.bode
  for p in b.panels:
   p.result=[(20,0,0),(100,-1,-10)];p.history=[[(20,-2,-3),(100,-4,-5)]]
   p.history_profiles=[None]
  for mode in (0,1,2):
   self.w.spectral.set_mode(mode)
   for i,p in enumerate(b.panels):
    self.w.spectral.select_bode(i)
    np.testing.assert_array_equal(p.curve_sets[0][0].xData,[20,100])
    self.assertTrue(p.curve_sets[1][0].isVisible())
 def test_transients_wait_for_pending_acquisition(self):
  self.ready();self.w._auto_apply_timer.start(10000)
  for p in self.w.spectral.bode.panels[1:]:
   p.begin();self.assertFalse(p.active)
  self.w.serial_worker.request_generator.assert_not_called()
 def test_tone_batch_does_not_alias_discarded_samples(self):
  self.ready();p=self.w.spectral.bode.panels[0]
  p.start.setValue(20);p.end.setValue(21);p.settle.setValue(0);p.cycles.setValue(3)
  p.begin();p.confirmed(self.reply(p));p.next_tone=Mock()
  fs=self.w.applied_configuration.rate;t=np.arange(6002)/fs
  x=np.cos(2*np.pi*20*t);y=x+.2*np.cos(2*np.pi*(fs/62-20)*t)
  p.batch([{'Tiempo (us)':round(ts*1e6),'V_IN':a,'V_OUT':b} for ts,a,b in zip(t,x,y)])
  self.assertTrue(p.result);self.assertLess(abs(p.result[0][1]),.02)
  self.assertLess(abs(p.result[0][2]),.02)
