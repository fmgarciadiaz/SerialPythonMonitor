import unittest
from experimentos.radio_ipc_compact_v17.adaptive_refresh import AdaptiveRefresh


class PolicyTests(unittest.TestCase):
    def test_only_active_radio_session_is_reduced(self):
        p=AdaptiveRefresh(); source=object()
        self.assertEqual(p.interval(0,None,9,9),0)
        self.assertEqual(p.interval(1,source),0)
        self.assertEqual(p.interval(2,source,3),.125)
        self.assertEqual(p.interval(3,None,9,9),0)
        self.assertFalse(p.snapshot(3)['reduced'])

    def test_quiet_hysteresis_and_snapshot_do_not_reset_pressure(self):
        p=AdaptiveRefresh(); source=object()
        p.interval(0,source,3)
        self.assertEqual(p.interval(1,source),.125)
        self.assertEqual(p.interval(2,source,0,3),.125)
        self.assertEqual(p.interval(4.99,source),.125)
        self.assertEqual(p.interval(5,source),0)
        self.assertEqual(p.snapshot(6)['reduced_seconds'],5)
        self.assertEqual(p.snapshot(6)['entries'],1)

    def test_ack_must_be_fresh_and_match_current_session(self):
        p=AdaptiveRefresh(); source=object(); other=object()
        p.interval(0,source)
        p.observe_ack(other,.3,0)
        self.assertEqual(p.interval(.1,source),0)
        p.observe_ack(source,.04,1)
        self.assertEqual(p.interval(1.2,source),.125)
        self.assertEqual(p.interval(4.3,source),0)
        self.assertEqual(p.interval(5,other),0)
        p.observe_ack(source,.3,5)
        self.assertEqual(p.interval(5.1,other),0)

    def test_single_and_other_modes_bypass_and_do_not_poison_new_session(self):
        p=AdaptiveRefresh(); source=object()
        p.interval(0,source,4)
        self.assertEqual(p.interval(1,source,4,eligible=False),0)
        self.assertEqual(p.interval(2,object()),0)

    def test_transition_storage_is_bounded(self):
        p=AdaptiveRefresh(); source=object()
        for n in range(100):
            p.interval(n*5,source,3)
            p.interval(n*5+4,source)
        self.assertEqual(len(p.snapshot(500)['transitions']),32)
        self.assertEqual(p.snapshot(500)['entries'],100)


if __name__ == '__main__':
    unittest.main()
