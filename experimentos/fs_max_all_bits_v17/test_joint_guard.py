import unittest
from types import SimpleNamespace
import numpy as np
from experimentos.fs_max_all_bits_v17.joint import private_profile_access
from monitor.v17.radio_output import RadioDacSource
import monitor.v17.radio_output_panel as panel
class PrivateGuardTests(unittest.TestCase):
 def result(self,bits,rate):
  return dict(settings=SimpleNamespace(acquisition=SimpleNamespace(bits=bits,rate=rate),radio_offset=1.65),audio=np.ones(480)*1.65,radio_key=(rate,20000,40000))
 def test_private_panel_and_actual_feed_agree_and_restore_production(self):
  for bits,rate in ((8,1632653),(14,909090)):
   with self.subTest(bits=bits):
    result=self.result(bits,rate);blocked=RadioDacSource();blocked.feed_result(result)
    self.assertIsNotNone(blocked.error)
    with private_profile_access(bits,rate):
     self.assertIsNone(panel.acquisition_error(result['settings'].acquisition))
     live=RadioDacSource();live.feed_result(result)
     self.assertIsNone(live.error);self.assertEqual(live._available,480)
     other=RadioDacSource();other.feed_result(self.result(bits,rate+1))
     self.assertIsNotNone(other.error);self.assertEqual(other._available,0)
    again=RadioDacSource();again.feed_result(result)
    self.assertIsNotNone(again.error)
