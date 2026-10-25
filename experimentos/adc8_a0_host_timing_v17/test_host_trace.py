"""Synthetic transport milestones only; never reads clocks or hardware."""
import unittest
from experimentos.adc8_a0_host_timing_v17.host_trace import HostTiming,RollingTrace,cpu_description
from experimentos.adc8_a0_host_timing_v17.run import certified_sources,EXPECTED_RELAY,validate_relay_digest,argument_parser
from experimentos.adc8_a0_host_timing_v17.radio_child import trial_arguments


class HostTraceTests(unittest.TestCase):
    def test_opt_out_bounded_rolling_trace_and_cpu_classification(self):
        disabled=HostTiming(enabled=False)
        disabled.observe('read',1.,2.,thread_cpu=.1,process_cpu=.2)
        disabled.observe('ack',3.,3.,rid=42,sent=1.)
        self.assertEqual(disabled.snapshot()['ack_observations'],0)
        self.assertEqual(disabled.snapshot()['stages']['read']['count'],0)
        ring=RollingTrace(maxlen=3000)
        for i in range(4000):ring.append(i)
        self.assertTrue(ring.rolling);self.assertEqual((len(ring),ring[0]),(3000,1000))
        self.assertEqual(cpu_description(1.,.8,.9)['classification'],'thread_cpu_dominant')
        self.assertEqual(cpu_description(1.,.1,.8)['classification'],'off_thread_wall_dominant')
        self.assertEqual(cpu_description(1.,None,None)['classification'],'cpu_unavailable')

    def test_top8_bounds_and_ack_rid_keeps_its_completion_read_and_decode(self):
        trace=HostTiming()
        trace.observe('read',10.,11.,thread_cpu=.2,process_cpu=.3)
        trace.observe('decode',11.1,11.4,thread_cpu=.2,process_cpu=.25)
        trace.observe('ack',11.5,11.5,rid=90,sent=5.)
        trace.observe('read',12.,13.,thread_cpu=.1,process_cpu=.2)
        trace.observe('decode',13.1,13.3,thread_cpu=.1,process_cpu=.15)
        trace.observe('ack',13.4,13.4,rid=12,sent=12.)
        by_rid={item['request_id']:item for item in trace.snapshot()['ack_top']}
        self.assertEqual(by_rid[90]['read_containing_completion']['end'],11.)
        self.assertEqual(by_rid[12]['read_containing_completion']['end'],13.)
        self.assertEqual(by_rid[90]['decode_before_ack']['start'],11.1)
        self.assertAlmostEqual(by_rid[12]['read_completion_to_ack_seconds'],.4)
        for i in range(20):
            trace.observe('read',20.,20.+i,thread_cpu=.1,process_cpu=.3)
            trace.observe('ack',50.+i,50.+i,rid=100+i,sent=20.)
        snapshot=trace.snapshot()
        self.assertEqual(len(snapshot['ack_top']),8)
        self.assertEqual(len(snapshot['stages']['read']['top']),8)
        self.assertEqual(snapshot['ack_top'][0]['request_id'],119)

    def test_unchanged_relay_and_opt_in_child_arguments(self):
        validate_relay_digest(EXPECTED_RELAY)
        with self.assertRaises(ValueError):validate_relay_digest('0'*64)
        self.assertEqual(argument_parser().parse_args([]).runs,1)
        self.assertIn('--host-cpu-trace',trial_arguments(120))
        _,_,sources,_=certified_sources()
        self.assertTrue(all('adc8_a0_command_tails_v17/relay' in str(path) for path in sources))
