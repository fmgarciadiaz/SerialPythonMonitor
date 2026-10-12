import copy
import unittest
from experimentos.maxfreq_v16.accepted import accepted_profiles, firmware_header


class AcceptanceGateTests(unittest.TestCase):
    def report(self):
        winner = dict(bits=8, ticks=131, node_pairs=6912, integrity_accepted=True, headroom_accepted=True)
        rows = [dict(bits=8, ticks=131, node_pairs=6912, stage=stage, seconds=seconds,
                     ok=True, headroom_ok=True, host_awake_control=True,
                     wall_monotonic_drift_seconds=0, status=dict(dropped=0, fatal=0))
                for stage, seconds in [('finalist',60),('acceptance_1',120),('acceptance_2',120),
                                       ('acceptance_3',120),('endurance',600)]]
        return dict(ok=True, restored=True, winners={'8':dict(maximum_integrity=winner,maximum_headroom=winner)}, cases=rows)

    def test_only_complete_controlled_acceptance_can_be_published(self):
        report = self.report()
        selected = accepted_profiles(report)
        self.assertEqual(len(selected),1)
        self.assertEqual(selected[0].rate,1221374)
        self.assertIn('SCOPE_NATIVE_MAX_DUAL 3584U',firmware_header(selected))
        for change in ('sleep','short','loss','missing','unfinished','headroom'):
            data = copy.deepcopy(report)
            if change == 'sleep': data['cases'][-1]['host_awake_control']=False
            elif change == 'short': data['cases'][-1]['seconds']=599
            elif change == 'loss': data['cases'][-1]['status']['dropped']=1
            elif change == 'missing': data['cases'].pop()
            elif change == 'unfinished': data['ok']=False
            elif change == 'headroom': data['cases'][-1]['headroom_ok']=False
            with self.subTest(change=change), self.assertRaises(ValueError): accepted_profiles(data)
