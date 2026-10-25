import unittest
from experimentos.fs_max_all_bits_v17.run import attempted_bits
class ContinuationTests(unittest.TestCase):
 def test_normal_adc14_controls_do_not_hide_untested_adc14(self):
  rows=[dict(stage='adc8_screen60',adc=dict(bits=8)),dict(stage='adc8_screen60_normal',adc=dict(bits=14)),dict(stage='adc10_acceptance_1_normal',adc=dict(bits=14)),dict(stage='adc12_baseline',adc=dict(bits=12)),dict(stage='adc12_acceptance_1',adc=dict(bits=12),ok=False)]
  self.assertEqual(attempted_bits([dict(cases=rows)]),{8,12})
 def test_ancestors_preserve_all_previous_attempts_including_failed(self):
  reports=[dict(cases=[dict(stage='adc16_acceptance_3',adc=dict(bits=16))]),dict(cases=[dict(stage='adc8_screen60',adc=dict(bits=8)),dict(stage='adc10_acceptance_1',adc=dict(bits=10)),dict(stage='adc12_acceptance_1',adc=dict(bits=12),ok=False)])]
  self.assertEqual(set((8,10,12,14,16))-attempted_bits(reports),{14})
 def test_wrong_resolution_is_rejected(self):
  with self.assertRaises(ValueError):attempted_bits([dict(cases=[dict(stage='adc8_screen60',adc=dict(bits=14))])])
