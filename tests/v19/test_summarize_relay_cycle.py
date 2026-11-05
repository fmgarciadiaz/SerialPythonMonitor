import json
import unittest
from tools.summarize_relay_cycle_v19 import summarize


class CycleSummaryTests(unittest.TestCase):
    def test_merge_partition_and_reject_malformed_trace(self):
        row=dict(phase=2,count=2,covered_ns=1400,gap_ns=600,cycle_ns=2000,max_gap_ns=400,max_cycle_ns=1100)
        line='SCOPE_CYCLE '+json.dumps(row)
        result=summarize(line+'\n'+line)
        self.assertEqual(result['phases']['2']['count'],4)
        self.assertEqual(result['phases']['2']['cycle_mean_us'],1.)
        self.assertEqual(result['phases']['2']['gap_fraction'],.3)
        bad=dict(row,cycle_ns=2001)
        with self.assertRaisesRegex(ValueError,'partition'):summarize('SCOPE_CYCLE '+json.dumps(bad))
        with self.assertRaisesRegex(ValueError,'No completed'):summarize('unrelated log')
