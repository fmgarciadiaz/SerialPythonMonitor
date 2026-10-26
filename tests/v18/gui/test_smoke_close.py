import unittest
from types import SimpleNamespace
from tools.gui_live_smoke_v18 import close_ready
class SmokeCloseTests(unittest.TestCase):
 def test_hidden_window_is_not_an_owner_release(self):
  window=SimpleNamespace(isVisible=lambda:False,serial_worker=object(),serial_thread=None,_close_pending=True)
  self.assertFalse(close_ready(window))
  window.serial_worker=None;self.assertFalse(close_ready(window))
  window._close_pending=False;self.assertTrue(close_ready(window))
 def test_thread_must_finish_and_window_must_close(self):
  window=SimpleNamespace(isVisible=lambda:False,serial_worker=None,serial_thread=SimpleNamespace(isRunning=lambda:True))
  self.assertFalse(close_ready(window))
  window.serial_thread=None;window.isVisible=lambda:True
  self.assertFalse(close_ready(window))

class ScanCaptureReadinessTests(unittest.TestCase):
 def test_three_blocks_must_be_new_since_generator_boundary(self):
  from types import SimpleNamespace
  from tools.gui_live_smoke_v18 import scan_capture_ready
  owner=SimpleNamespace(sample_counter=198288,_radio_scan_not_before_sample=4752)
  self.assertFalse(scan_capture_ready(owner))
  owner.sample_counter=201360
  self.assertTrue(scan_capture_ready(owner))
