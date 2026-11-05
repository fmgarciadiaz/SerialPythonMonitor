import struct
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from monitor.v20.receiver.unoq_config_receiver import OutputReceiver
from monitor.v20.receiver.unoq_wav import State, Status


class WavResetConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.clock = patch('monitor.v20.receiver.unoq_config_receiver.time.monotonic',
                           side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.sent = []
        connection = SimpleNamespace(socket=Mock())
        self.receiver = OutputReceiver(connection, lambda rows: None)
        self.receiver.wav_candidate = True
        self.receiver.next_id = 0x80000010
        connection.socket.sendall.side_effect = self.sent.append

    def status(self, rid, state=State.PLAYING, reason=0):
        return Status(rid, 123, state, reason, 16, 100, 50, 100, 20000)

    def replies(self, query=None, stop=None):
        """Exercise the real ACK handler and timeout cleanup with a fake pump."""
        seen = set()

        def pump():
            self.now += 1.1
            frame = self.sent[-1]
            rid = struct.unpack_from('<I', frame, 8)[0]
            op = frame[20]
            reply = query if op == 0 else stop
            self.receiver.decoder.events = []
            if rid not in seen:
                seen.add(rid)
                if reply is not None:
                    self.receiver.decoder.events = [('wav', reply(rid))]
            self.receiver._process_decoder_events()
            self.receiver.service_wav()

        self.receiver.pump = pump

    def ops(self):
        return [frame[20] for frame in self.sent]

    def test_missing_query_ack_cannot_reuse_playing_status_after_timeout_cleanup(self):
        self.receiver.wav_status = self.status(0x80000001)
        self.replies()
        with self.assertRaises(TimeoutError):
            self.receiver.reset_wav_output()
        self.assertIsNone(self.receiver.wav_pending)
        self.assertEqual(self.ops(), [0])

    def test_missing_query_ack_cannot_reuse_idle_status(self):
        self.receiver.wav_status = self.status(0x80000001, State.IDLE)
        self.replies()
        with self.assertRaises(TimeoutError):
            self.receiver.reset_wav_output()

    def test_cached_query_status_with_reused_id_is_not_a_fresh_ack(self):
        self.receiver.wav_status = self.status(self.receiver.next_id, State.IDLE)
        self.replies()
        with self.assertRaises(TimeoutError):
            self.receiver.reset_wav_output()

    def test_uncorrelated_query_ack_does_not_confirm_reset(self):
        self.replies(query=lambda rid: self.status(rid + 100, State.IDLE))
        with self.assertRaises(TimeoutError):
            self.receiver.reset_wav_output()

    def test_ack_received_after_deadline_does_not_confirm_reset(self):
        self.replies(query=lambda rid: self.status(rid, State.IDLE))
        pump = self.receiver.pump

        def late_pump():
            self.now += 3.0
            pump()

        self.receiver.pump = late_pump
        with self.assertRaises(TimeoutError):
            self.receiver.reset_wav_output()

    def test_rejected_query_does_not_send_stop(self):
        self.replies(query=lambda rid: self.status(rid, reason=1))
        with self.assertRaises(RuntimeError):
            self.receiver.reset_wav_output()
        self.assertEqual(self.ops(), [0])

    def test_confirmed_idle_query_needs_no_stop(self):
        self.replies(query=lambda rid: self.status(rid, State.IDLE))
        self.receiver.reset_wav_output()
        self.assertEqual(self.ops(), [0])

    def test_missing_stop_ack_cannot_reuse_successful_query(self):
        self.replies(query=self.status)
        with self.assertRaises(TimeoutError):
            self.receiver.reset_wav_output()
        self.assertIsNone(self.receiver.wav_pending)
        self.assertEqual(self.ops(), [0, 3])

    def test_late_query_ack_does_not_confirm_stop(self):
        self.replies(query=self.status,
                     stop=lambda rid: self.status(rid - 1, State.IDLE))
        with self.assertRaises(TimeoutError):
            self.receiver.reset_wav_output()

    def test_rejected_stop_does_not_confirm_reset(self):
        self.replies(query=self.status,
                     stop=lambda rid: self.status(rid, State.IDLE, reason=1))
        with self.assertRaises(RuntimeError):
            self.receiver.reset_wav_output()

    def test_stop_requires_idle_or_done(self):
        for state in (State.PLAYING, State.BUFFERING, State.UNDERRUN, State.FAULT):
            with self.subTest(state=state):
                self.replies(query=self.status,
                             stop=lambda rid: self.status(rid, state))
                with self.assertRaises(RuntimeError):
                    self.receiver.reset_wav_output()

    def test_confirmed_stop_accepts_idle_and_done(self):
        for state in (State.IDLE, State.DONE):
            with self.subTest(state=state):
                self.sent.clear()
                self.replies(query=self.status,
                             stop=lambda rid: self.status(rid, state))
                self.receiver.reset_wav_output()
                self.assertEqual(self.ops(), [0, 3])
                self.assertEqual(struct.unpack_from('<I', self.sent[-1], 16)[0], 123)


if __name__ == '__main__':
    unittest.main()
