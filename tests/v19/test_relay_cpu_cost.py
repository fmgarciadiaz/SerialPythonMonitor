import unittest
from tools.probe_relay_gui_v19 import relay_cpu_cost


class RelayCpuCostTests(unittest.TestCase):
    def test_process_identity_and_wall_interval(self):
        before=dict(pid=10,start_ticks=100,hz=100,cpu_ticks=100,monotonic=10)
        after=dict(before,cpu_ticks=200,monotonic=12)
        self.assertEqual(relay_cpu_cost(before,after)['fraction_of_one_core'],.5)
        for value in (dict(after,pid=11),dict(after,start_ticks=101),dict(after,hz=1000),
                      dict(after,monotonic=9),dict(after,cpu_ticks=99)):
            with self.subTest(value=value),self.assertRaises(ValueError):relay_cpu_cost(before,value)
