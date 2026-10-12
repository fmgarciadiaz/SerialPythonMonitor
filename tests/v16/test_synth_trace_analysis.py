import unittest
from diagnosticos.analizar_tiempos_synth_v16 import analyze


class SynthTraceAnalysisTests(unittest.TestCase):
    def test_wait_cpu_and_gc_are_separate_and_nested_pump_not_double_counted(self):
        trace = [
            ('send', 1., 1.001, 7, .0001),
            ('gc', 1.002, 1.004, 0),
            ('decode', 1.001, 1.005, None, .003),
            ('read', 1.005, 1.010, None, .0001),
            ('pump', 1.001, 1.010, None, .0031),
            ('ack', 1.011, 1.011, 7),
            ('queue_growth', 1.011, 1.011, 7),
        ]
        result = analyze(trace)
        row = result['worst'][0]
        self.assertAlmostEqual(row['send_return_to_ack_ms'], 10.)
        self.assertAlmostEqual(row['unaccounted_ms'], 1.)
        self.assertAlmostEqual(result['slow_decode'][0]['gc_overlap_ms'], 2.)
        self.assertAlmostEqual(result['slow_stages']['read'][0]['cpu_ms'], .1)
        self.assertEqual(result['queue_growth'][0]['target'], 7)

    def test_legacy_trace_without_cpu_is_supported(self):
        result = analyze([('generate', 1., 1.002, None)])
        self.assertIsNone(result['slow_generate'][0]['cpu_ms'])
        self.assertEqual(result['requests'], 0)


if __name__ == '__main__':
    unittest.main()
