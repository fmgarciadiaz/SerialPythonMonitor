"""Offline checks for the private V20 RADIO priming cadence."""

import struct
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from monitor.v20.receiver import unoq_config_receiver as core
from tools.private_radio_priming_v20 import realtime_radio_priming


class Source:
    live = True
    radio_audio = True
    credit_window = 30
    target_blocks = 30
    maximum_blocks = 30
    chunk_burst = 8
    chunk_interval = .006

    def __len__(self):
        return 480 * 100

    def try_codes(self, start, end):
        return np.zeros(end - start, dtype=np.uint16)


class PrivateRadioPrimingTests(unittest.TestCase):
    def make_receiver(self, **changes):
        config = dict(bits=8, rate=2000000, channels=1, period=80, node_pairs=3488)
        config.update(changes)
        receiver = core.OutputReceiver(SimpleNamespace(socket=Mock()), lambda _: None)
        receiver.config = SimpleNamespace(**config)
        receiver.wav_codes = Source()
        receiver.wav_rate = 40000
        receiver.wav_session = 9
        receiver.next_id = 0x80000001
        receiver.wav_status = SimpleNamespace(session=9, queue_slots=30,
                                              free_blocks=30, accepted=0)
        receiver.wav_chunk_tokens = 1.
        receiver.wav_chunk_token_at = 10.
        return receiver

    @staticmethod
    def frames(receiver):
        return [call.args[0] for call in receiver.connection.socket.sendall.call_args_list]

    @staticmethod
    def kinds(receiver):
        return [struct.unpack_from('<H', frame, 6)[0]
                for frame in PrivateRadioPrimingTests.frames(receiver)]

    def test_priming_uses_12ms_and_restores_source_after_every_call(self):
        clock = [10.]
        receiver = self.make_receiver()
        source = receiver.wav_codes
        original = core.OutputReceiver.service_wav
        with patch.object(core.time, 'monotonic', side_effect=lambda: clock[0]):
            with realtime_radio_priming():
                receiver.service_wav()
                self.assertEqual(self.kinds(receiver), [13])
                self.assertEqual(source.chunk_interval, .006)
                clock[0] = 10.0061
                receiver.service_wav()
                self.assertEqual(self.kinds(receiver), [13])
                clock[0] = 10.0121
                receiver.service_wav()
                self.assertEqual(self.kinds(receiver), [13, 13])
                self.assertEqual(source.chunk_interval, .006)
        self.assertIs(core.OutputReceiver.service_wav, original)
        self.assertEqual(source.chunk_burst, 8)
        self.assertEqual([struct.unpack_from('<I', f, 20)[0] for f in self.frames(receiver)], [0, 480])

    def test_normal_started_cadence_is_6ms_and_restart_uses_12ms_again(self):
        clock = [10.]
        receiver = self.make_receiver()
        receiver.wav_started = True
        original = core.OutputReceiver.service_wav
        with patch.object(core.time, 'monotonic', side_effect=lambda: clock[0]):
            with realtime_radio_priming():
                receiver.service_wav()
                clock[0] = 10.0061
                receiver.service_wav()
                self.assertEqual(self.kinds(receiver), [13, 13])
                receiver.wav_started = False
                receiver.wav_inflight.clear()
                receiver.wav_pending = None
                receiver.wav_status.free_blocks = 30
                receiver.wav_status.accepted = receiver.wav_next_offset
                receiver.wav_chunk_tokens = 0.
                receiver.wav_chunk_token_at = clock[0]
                clock[0] += .0061
                receiver.service_wav()
                self.assertEqual(self.kinds(receiver), [13, 13])
                clock[0] += .0061
                receiver.service_wav()
                self.assertEqual(self.kinds(receiver), [13, 13, 13])
                self.assertEqual(receiver.wav_codes.chunk_interval, .006)
        self.assertIs(core.OutputReceiver.service_wav, original)

    def test_play_waits_for_all_30_chunk_acks(self):
        clock = [10.]
        receiver = self.make_receiver()
        with patch.object(core.time, 'monotonic', side_effect=lambda: clock[0]):
            with realtime_radio_priming():
                for index in range(30):
                    clock[0] = 10. + index * .0121
                    receiver.service_wav()
                    self.assertEqual(len(self.frames(receiver)), index + 1)
                    self.assertFalse(receiver.wav_started)
                    self.assertLessEqual(len(receiver.wav_inflight), 1)
                    if index < 29:
                        receiver.wav_inflight.clear()
                        receiver.wav_pending = None
                        receiver.wav_status.accepted = (index + 1) * 480
                        receiver.wav_status.free_blocks = 29 - index
                receiver.service_wav()
                self.assertEqual(self.kinds(receiver), [13] * 30)
                self.assertFalse(receiver.wav_started)
                receiver.wav_inflight.clear()
                receiver.wav_pending = None
                receiver.wav_status.accepted = 30 * 480
                receiver.wav_status.free_blocks = 0
                receiver.service_wav()
                self.assertEqual(self.kinds(receiver), [13] * 30 + [11])
                self.assertTrue(receiver.wav_started)
        self.assertEqual(receiver.wav_codes.chunk_interval, .006)

    def test_other_profiles_and_sources_are_byte_identical(self):
        cases = [dict(rate=1860465, period=86), dict(bits=10),
                 dict(channels=2), dict(period=81), dict(node_pairs=3456)]
        for changes in cases + [dict(radio_audio=False), dict(wav_rate=20000)]:
            with self.subTest(changes=changes):
                actual = self.make_receiver(**{k: v for k, v in changes.items()
                                               if k not in ('radio_audio', 'wav_rate')})
                baseline = self.make_receiver(**{k: v for k, v in changes.items()
                                                 if k not in ('radio_audio', 'wav_rate')})
                for receiver in (actual, baseline):
                    if 'radio_audio' in changes:
                        receiver.wav_codes.radio_audio = changes['radio_audio']
                    if 'wav_rate' in changes:
                        receiver.wav_rate = changes['wav_rate']
                with patch.object(core.time, 'monotonic', return_value=10.0061):
                    baseline.service_wav()
                    with realtime_radio_priming():
                        actual.service_wav()
                self.assertEqual(self.frames(actual), self.frames(baseline))
                self.assertEqual(actual.wav_next_offset, baseline.wav_next_offset)
                self.assertEqual(actual.wav_codes.chunk_interval, .006)

    def test_exception_restores_interval_and_exact_method(self):
        receiver = self.make_receiver()
        original = core.OutputReceiver.service_wav
        with self.assertRaisesRegex(RuntimeError, 'injected'):
            with realtime_radio_priming():
                with patch.object(receiver, '_wav_chunk_codes', side_effect=RuntimeError('injected')):
                    receiver.service_wav()
        self.assertEqual(receiver.wav_codes.chunk_interval, .006)
        self.assertIs(core.OutputReceiver.service_wav, original)


if __name__ == '__main__':
    unittest.main()
