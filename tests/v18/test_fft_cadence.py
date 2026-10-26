import unittest
from monitor.v18.fft_cadence import live_interval

class FftCadenceTests(unittest.TestCase):
 def test_long_fft_requires_eight_light_updates_before_speedup(self):
  for count in range(8):self.assertEqual(live_interval(1,65536,True,[.015]*count),.1)
  self.assertAlmostEqual(live_interval(1,65536,True,[.015]*8),1/15)
  self.assertAlmostEqual(live_interval(1,65536,True,[.025]*8),1/15)
 def test_slow_or_invalid_update_immediately_restores_old_budget(self):
  for slow in (.025001,.05,float('nan'),float('inf'),-.1):
   self.assertEqual(live_interval(1,65536,True,[.01]*7+[slow]),.1)
  self.assertAlmostEqual(live_interval(1,65536,True,[.09]+[.01]*8),1/15)
 def test_small_fft_demo_and_heatmap_keep_their_previous_budgets(self):
  self.assertAlmostEqual(live_interval(1,8192,True),1/30)
  self.assertAlmostEqual(live_interval(1,65536,False),1/30)
  self.assertEqual(live_interval(2,65536,True,[.001]*8),.1)
  self.assertEqual(live_interval(2,8192,True),.05)

 def test_dac_playback_preserves_previous_long_fft_budget(self):
  self.assertEqual(live_interval(1,65536,True,[.001]*8,audio_active=True),.1)
  self.assertAlmostEqual(live_interval(1,8192,True,[.001]*8,audio_active=True),1/30)
  self.assertAlmostEqual(live_interval(1,65536,True,[.001]*8,audio_active=False),1/15)
