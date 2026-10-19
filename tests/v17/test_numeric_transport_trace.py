import unittest
from monitor.v17.transport_trace import NumericTransportTrace
from diagnosticos.analizar_tiempos_synth_v16 import analyze

class NumericTraceTests(unittest.TestCase):
    def test_wrap_preserves_latest_order_ids_and_optional_cpu(self):
        trace=NumericTransportTrace(3)
        trace.append(('read',1.,2.,None,.1))
        trace.append(('send',2.,2.1,0xfffffffe,.01))
        trace.append(('ack',2.2,2.2,0xfffffffe))
        trace.append(('queue_growth',2.3,2.3,7))
        exported=trace.export()
        self.assertEqual(exported['metadata']['overwritten'],1)
        self.assertEqual(exported['events'][0],['send',2.,2.1,0xfffffffe,.01])
        self.assertEqual(exported['events'][-1],['queue_growth',2.3,2.3,7])
        result=analyze(exported)
        self.assertEqual(result['requests'],1)
        self.assertTrue(result['trace_window']['receiver_limit_reached'])
        self.assertEqual(result['queue_growth'][0]['target'],7)
    def test_process_cpu_and_parent_gc_overlap_are_not_wall_time(self):
        trace=NumericTransportTrace(2)
        trace.append(('generate',1.,1.1,None,.02,.03))
        exported=trace.export()
        self.assertEqual(exported['events'][0],['generate',1.,1.1,None,.02,.03])
        result=analyze(exported,[dict(start=1.05,end=1.2,gc_ms=10)])
        row=result['slow_stages']['generate'][0]
        self.assertAlmostEqual(row['cpu_ms'],20)
        self.assertAlmostEqual(row['process_cpu_ms'],30)
        self.assertAlmostEqual(row['parent_pause_overlap_ms'],50)
        self.assertAlmostEqual(row['parent_gc_overlap_ms'],10)

    def test_empty_and_invalid_capacity(self):
        self.assertEqual(analyze(NumericTransportTrace(1).export())['requests'],0)
        with self.assertRaises(ValueError):NumericTransportTrace(0)
    def test_ipc_time_accounts_for_gap_without_counting_nested_pump(self):
        trace=NumericTransportTrace(10)
        for e in [('send',1.,1.01,1),('adc_ipc',1.01,1.05,None,.001),('pump',1.01,1.05,None,.002),('ack',1.06,1.06,1)]:trace.append(e)
        row=analyze(trace.export())['worst'][0]
        self.assertAlmostEqual(row['adc_ipc_ms'],40.)
        self.assertAlmostEqual(row['unaccounted_ms'],10.)

if __name__=='__main__':unittest.main()
