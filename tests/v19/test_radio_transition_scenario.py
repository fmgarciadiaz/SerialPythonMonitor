import unittest
from tools.radio_transition_scenario_v19 import RadioTransitions

class TransitionsTests(unittest.TestCase):
    def test_restart_then_scan_require_new_sessions_and_reset_hold_clock(self):
        flow=RadioTransitions(True,True)
        self.assertFalse(flow.playing(10,1))
        self.assertIsNone(flow.action(5,False))
        self.assertEqual(flow.action(6,False),'stop');self.assertTrue(flow.expected_pause)
        self.assertFalse(flow.playing(10,7))
        self.assertIsNone(flow.action(7,False))
        self.assertEqual(flow.action(8,True),'start')
        self.assertTrue(flow.playing(11,9));self.assertFalse(flow.expected_pause)
        self.assertEqual(flow.since,9);self.assertFalse(flow.complete)
        self.assertEqual(flow.action(14,False),'scan')
        self.assertFalse(flow.playing(12,15,False))
        self.assertTrue(flow.playing(12,16,True));self.assertTrue(flow.complete)
        self.assertEqual(flow.since,16);self.assertIsNone(flow.action(30,False))
    def test_expected_pause_has_bounded_deadline(self):
        flow=RadioTransitions(scan=True);flow.playing(1,0)
        self.assertEqual(flow.action(5,False),'scan')
        with self.assertRaises(TimeoutError):flow.action(31,False)
    def test_plain_hold_never_requests_transitions(self):
        flow=RadioTransitions();flow.playing(1,0)
        self.assertTrue(flow.complete);self.assertIsNone(flow.action(120,False))
