"""Pure tests; no Q, subprocesses, C compilation, or physical acceptance."""
from contextlib import contextmanager
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experimentos.fs_max_v18 import transition_batchstack as probe
from experimentos.fs_max_v18.run_probe import private_profiles
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.receiver.unoq_switch import Phase, Reason


class FakeReceiver:
    def __init__(self):
        self.decoder = SimpleNamespace(status=None, statuses=[], pairs=0)

    def select(self, mode):
        assert mode == 0

    def generator(self):
        pass


class FakeBackend:
    def __init__(self, fail=None):
        self.events = []
        self.fail = fail
        self.identity = {'app': 'Scope V18', 'firmware_sha256': 'original'}
        self.open = False

    def event(self, name):
        self.events.append(name)
        if self.fail == name:
            raise RuntimeError(name)

    def capture(self):
        self.event('capture')

    def prepare(self):
        self.event('prepare')

    def restart(self):
        self.event('restart')

    def candidate_identity(self):
        assert not self.open, 'Q admin with measurement socket open'
        self.event('candidate_identity')
        return {'firmware_sha256': 'candidate', 'relay_sha256': 'private'}

    @contextmanager
    def receiver(self):
        self.event('open')
        self.open = True
        try:
            yield FakeReceiver()
        finally:
            self.open = False
            self.event('close')

    def restore(self):
        assert not self.open, 'restore with measurement socket open'
        self.event('restore')
        return dict(hardware_restored=True, identity_equal=True)

    def final_identity(self):
        self.event('final_identity')
        return self.identity


class PlanTests(unittest.TestCase):
    def test_fixed_wire_sequence_and_duration(self):
        rows = probe.plan()
        self.assertEqual(len(rows), 15)
        self.assertEqual(sum(r['seconds'] for r in rows), 75)
        expected = [(8, 1, 88, 3488), (8, 2, 253, 3888), (14, 2, None, 2048),
                    (10, 2, 308, 4176), (8, 1, 88, 3488)]
        with private_profiles(probe.EXP / 'batchstack'):
            for cycle in range(3):
                group = rows[cycle * 5:(cycle + 1) * 5]
                self.assertEqual([(r['bits'], r['channels'], r['ticks'], r['node_pairs']) for r in group], expected)
                for row in group:
                    config = Configuration.from_wire(row['bits'], row['wire_period'])
                    self.assertEqual(config.channels, row['channels'])
                    self.assertAlmostEqual(config.actual_rate, row['rate'])
                    self.assertEqual(row['cycle'], cycle + 1)

    def test_default_has_no_hardware_construction(self):
        with patch.object(probe, 'TransitionHardware', side_effect=AssertionError('hardware')), patch('sys.stdout', new=io.StringIO()):
            self.assertEqual(probe.main([]), 0)


class TransactionTests(unittest.TestCase):
    def run_transaction(self, backend, measure):
        report = {'stages': [], 'measurement_ok': False}
        saves = []
        ok = probe.orchestrate(backend, probe.plan(), report, lambda: saves.append(len(report['stages'])), measure)
        return ok, report, saves

    def test_one_setup_restart_connection_restore_and_full_sequence(self):
        backend = FakeBackend()
        seen = []
        def measure(receiver, profile, row, save):
            self.assertTrue(backend.open)
            seen.append((profile['cycle'], profile['position']))
            row['ok'] = True
        ok, report, saves = self.run_transaction(backend, measure)
        self.assertTrue(ok)
        self.assertEqual(len(seen), 15)
        for name in ('capture', 'prepare', 'restart', 'open', 'close', 'restore'):
            self.assertEqual(backend.events.count(name), 1)
        self.assertLess(backend.events.index('close'), backend.events.index('restore'))
        self.assertEqual(report['identity_start'], report['identity_final'])
        self.assertTrue(saves)

    def test_first_failed_stage_aborts_and_closes_before_restore(self):
        backend = FakeBackend()
        def measure(receiver, profile, row, save):
            if profile['position'] == 2:
                raise ValueError('integrity')
            row['ok'] = True
        ok, report, _ = self.run_transaction(backend, measure)
        self.assertFalse(ok)
        self.assertEqual(len(report['stages']), 2)
        self.assertIn('integrity', report['stages'][-1]['error'])
        self.assertEqual(backend.events[-2:], ['restore', 'final_identity'])

    def test_prepare_and_restart_failures_restore_captured_snapshot(self):
        for failure in ('prepare', 'restart'):
            with self.subTest(failure=failure):
                backend = FakeBackend(failure)
                ok, report, _ = self.run_transaction(backend, lambda *a: self.fail('measure'))
                self.assertFalse(ok)
                self.assertEqual(backend.events.count('restore'), 1)
                self.assertEqual(report['stages'], [])

    def test_capture_failure_does_not_restore_without_snapshot(self):
        backend = FakeBackend('capture')
        ok, _, _ = self.run_transaction(backend, lambda *a: self.fail('measure'))
        self.assertFalse(ok)
        self.assertNotIn('restore', backend.events)

    def test_keyboard_interrupt_still_closes_and_restores(self):
        backend = FakeBackend()
        def measure(*args):
            raise KeyboardInterrupt('signal')
        ok, report, _ = self.run_transaction(backend, measure)
        self.assertFalse(ok)
        self.assertIn('KeyboardInterrupt', report['error'])
        self.assertIn('close', backend.events)
        self.assertIn('restore', backend.events)

    def test_failed_exact_restoration_prevents_success(self):
        backend = FakeBackend()
        backend.restore = lambda: {'hardware_restored': False}
        def measure(receiver, profile, row, save):
            row['ok'] = True
        ok, report, _ = self.run_transaction(backend, measure)
        self.assertFalse(ok)
        self.assertTrue(report['measurement_ok'])


class StageTests(unittest.TestCase):
    def test_stale_status_after_ack_waits_for_current_epoch(self):
        profile = probe.plan()[2]  # Normal profile: no native send/queue metrics.
        config = Configuration.from_wire(14, 32)
        receiver = FakeReceiver()
        receiver.config = config
        receiver.decoder.config = config
        receiver.decoder.epoch = 7
        receiver.decoder.status = dict(epoch=6, bits=8, rate=1000, dropped=0, fatal=0)
        receiver.config_applied = SimpleNamespace(phase=Phase.APPLIED, reason=Reason.OK,
            active=config, requested_bits=14, requested_period=32, request_id=123, epoch=7)
        receiver.configure = lambda wanted: True
        now = [0.0]
        calls = [0]
        def pump():
            calls[0] += 1
            now[0] += 1
            receiver.decoder.pairs += 31250
            receiver.decoder.status = dict(epoch=7, bits=14, rate=31250, dropped=0, fatal=0)
            receiver.decoder.statuses = [receiver.decoder.status]
        receiver.pump = pump
        row = {'ok': False}
        probe.measure_stage(receiver, profile, row, lambda: None, clock=lambda: now[0])
        self.assertTrue(row['ok'])
        self.assertEqual(calls[0], 6)  # One first-status pump plus five measured.
        self.assertEqual(row['pairs_before'], 31250)
        self.assertEqual(row['pairs_delta'], 156250)
        self.assertEqual(row['elapsed'], 5)
        self.assertNotIn('native_metrics', row)

    def test_noop_reuses_only_matching_applied_ack(self):
        config = Configuration(14, 31250)
        receiver = FakeReceiver()
        receiver.configure = lambda wanted: False
        receiver.config = receiver.decoder.config = config
        receiver.decoder.epoch = 9
        receiver.config_applied = SimpleNamespace(phase=Phase.APPLIED, reason=Reason.OK,
            active=config, requested_bits=14, requested_period=32, request_id=456, epoch=9)
        self.assertTrue(probe.configure_confirmed(receiver, config)['reused_ack'])
        receiver.config_applied.requested_period = 25
        with self.assertRaisesRegex(ValueError, 'APPLIED'):
            probe.configure_confirmed(receiver, config)

    def test_counter_failure_or_stale_epoch_is_rejected(self):
        config = Configuration(14, 31250)
        for status in (None, dict(epoch=1, bits=14, rate=31250, dropped=0, fatal=0),
                       dict(epoch=2, bits=14, rate=31250, dropped=1, fatal=0),
                       dict(epoch=2, bits=14, rate=31250, dropped=0, fatal=1)):
            with self.subTest(status=status), self.assertRaises(ValueError):
                probe.validate_status(status, config, 2)


if __name__ == '__main__':
    unittest.main()
