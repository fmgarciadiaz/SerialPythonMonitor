import unittest
import numpy as np
from monitor.v16.fm_source import _phase,_phase_final,_sample_positions

class UnusedPhaseTests(unittest.TestCase):
    def test_final_state_is_exact_for_constant_pitch_and_pitch_changes(self):
        for count in (1,7,480,1920):
            for rate in (20000,40000):
                for start,end in ((0.,0.),(220.,220.),(123.45,123.45),(220.,440.),(440.,110.)):
                    for previous in (0.,.17,-3.):
                        self.assertEqual(_phase_final(previous,start,end,count,rate,4),_phase(previous,start,end,_sample_positions(count),rate,4)[-1])
