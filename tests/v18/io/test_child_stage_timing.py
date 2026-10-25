import unittest
from types import SimpleNamespace
from unittest.mock import patch

from monitor.v18.io.receiver_process import RemotePcmSource
from monitor.v18.receiver import unoq_config_receiver as receiver_module
from monitor.v18.receiver import unoq_wav as wav


class Clock:
    def __init__(self):
        self.wall = 100.
        self.cpu = 10.

    def advance(self, wall, cpu):
        self.wall += wall
        self.cpu += cpu


class ChildStageTimingTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.wall_patch = patch.object(receiver_module.time, 'monotonic', lambda: self.clock.wall)
        self.cpu_patch = patch.object(receiver_module.time, 'thread_time', lambda: self.clock.cpu, create=True)
        self.wall_patch.start()
        self.cpu_patch.start()
        self.addCleanup(self.wall_patch.stop)
        self.addCleanup(self.cpu_patch.stop)

    def receiver(self):
        connection = SimpleNamespace(read=lambda: b'', socket=SimpleNamespace(sendall=lambda frame: None))
        receiver = receiver_module.OutputReceiver(connection, lambda samples: None)
        receiver.service_wav = lambda: None
        return receiver

    def test_wall_pause_is_distinct_from_thread_cpu_and_pump_gap(self):
        timing = receiver_module._ChildStageTiming()
        def pump():
            timing.call('decoder_events', lambda: self.clock.advance(.2, .002))
        timing.pump('pump_global', lambda: timing.pump('pump', pump))
        self.clock.advance(.15, .001)
        timing.pump('pump_global', lambda: None)
        snapshot = timing.snapshot(detail=True)
        self.assertAlmostEqual(snapshot['max_ms']['decoder_events']['wall'], 200)
        self.assertAlmostEqual(snapshot['max_ms']['decoder_events']['cpu'], 2)
        self.assertAlmostEqual(snapshot['max_ms']['pump_gap']['wall'], 150)
        self.assertAlmostEqual(snapshot['max_ms']['pump_gap']['cpu'], 1)
        self.assertEqual(sum(row['stage'] == 'pump_gap' for row in snapshot['events']), 1)
        self.assertEqual(snapshot['active'], [])

    def test_ring_is_bounded_recent_and_scalar(self):
        timing = receiver_module._ChildStageTiming()
        for rid in range(1100):
            timing._observe('send', self.clock.wall, self.clock.wall, 0., rid=rid, kind=13)
            self.clock.advance(.001, 0.)
        events = timing.snapshot(detail=True)['events']
        self.assertEqual(len(events), 1024)
        self.assertEqual(events[0]['rid'], 76)
        self.assertEqual(events[-1]['rid'], 1099)
        self.assertTrue(all(isinstance(value, (str, int, float, type(None)))
                            for row in events for value in row.values()))
        self.clock.advance(3.01, 0.)
        self.assertEqual(timing.snapshot(detail=True)['events'], [])
        self.assertIn('send', timing.snapshot()['max_ms'])

    def test_short_stage_is_omitted_but_send_and_ack_are_retained(self):
        timing = receiver_module._ChildStageTiming()
        timing._observe('collect', 99.999, 100., .001)
        timing._observe('read', 99.99, 100., .002, bytes_read=992)
        timing._observe('read', 99.999, 100., .001, bytes_read=64)
        receiver = self.receiver()
        receiver.child_stage_timing = timing
        receiver.wav_inflight = {123: (99.8, 13)}
        receiver._trace_transport('send', 100., 100., 123, kind=13)
        receiver._trace_transport('ack', 100., 100., 123)
        snapshot = timing.snapshot(detail=True)
        self.assertEqual([row['stage'] for row in snapshot['events']], ['read', 'send', 'ack'])
        self.assertEqual(snapshot['bytes_read'], 1056)
        self.assertEqual(snapshot['read_bytes_max'], 992)
        self.assertEqual(snapshot['events'][-1]['rid'], 123)
        self.assertEqual(snapshot['events'][-1]['kind'], 13)
        self.assertAlmostEqual(snapshot['events'][-1]['send_to_ack_ms'], 200)

    def test_underrun_snapshot_in_callback_sees_unfinished_events_and_pump(self):
        receiver = self.receiver()
        timing = receiver.child_stage_timing = receiver_module._ChildStageTiming()
        source = receiver.wav_codes = RemotePcmSource(dict(session=1), lambda event: None)
        status = SimpleNamespace(request_id=123, session=1, rate=20000,
                                 state=wav.State.UNDERRUN, reason=0)
        receiver.wav_session = 1
        receiver.wav_inflight = {123: (99.8, 13)}
        receiver.decoder = SimpleNamespace(events=[('wav', status)], statuses=[], config=None,
                                           feed=lambda data, **options: None)
        snapshots = []
        def on_wav(status):
            self.clock.advance(.2, .002)
            snapshots.append(source.transport_snapshot(child_timing=timing, detail=True))
        receiver.on_wav = on_wav
        receiver.pump()
        active = snapshots[0]['child_stages']['active']
        self.assertEqual([row['stage'] for row in active], ['pump', 'decoder_events'])
        self.assertAlmostEqual(active[-1]['wall_ms'], 200)
        self.assertAlmostEqual(active[-1]['cpu_ms'], 2)
        self.assertEqual(timing.active, [])
        self.assertIsNone(receiver.wav_codes)

    def test_normal_snapshot_has_no_ring_or_active_stage_and_api_remains_compatible(self):
        timing = receiver_module._ChildStageTiming()
        source = RemotePcmSource(dict(session=1), lambda event: None)
        source.observe_transport('socket_send', .01)
        row = source.transport_snapshot(child_timing=timing)
        self.assertNotIn('events', row['child_stages'])
        self.assertNotIn('active', row['child_stages'])
        self.assertEqual(row['delivery_max_ms']['socket_send'], 10.)
        self.assertNotIn('child_stages', source.transport_snapshot())

    def test_flag_off_allocates_no_ring_and_calls_no_thread_clock(self):
        with patch.object(receiver_module, '_child_stage_timing_enabled', False), \
                patch.object(receiver_module, '_ChildStageTiming') as helper, \
                patch.object(receiver_module.time, 'thread_time', side_effect=AssertionError('unexpected CPU clock')):
            receiver = self.receiver()
            receiver.pump()
            self.assertIsNone(receiver.child_stage_timing)
            helper.assert_not_called()
            source = RemotePcmSource(dict(session=1), lambda event: None)
            self.assertNotIn('child_stages', source.transport_snapshot())
        with patch.object(receiver_module, 'time', SimpleNamespace()):
            with self.assertRaisesRegex(RuntimeError, 'requiere Python con time.thread_time'):
                receiver_module._ChildStageTiming()

    def test_exception_finishes_stage_without_masking_original_error(self):
        timing = receiver_module._ChildStageTiming()
        def fail():
            self.clock.advance(.01, .001)
            raise ValueError('test error')
        with self.assertRaisesRegex(ValueError, 'test error'):
            timing.pump('pump', lambda: timing.call('collect', fail))
        self.assertEqual(timing.active, [])
        self.assertEqual(timing._pump_depth, 0)
        self.assertAlmostEqual(timing.max_ms['collect']['wall'], 10.)


if __name__ == '__main__':
    unittest.main()
