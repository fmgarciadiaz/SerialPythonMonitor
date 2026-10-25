import socket
import unittest
from .socket_trace import SocketTrace, queued_bytes


class SocketTraceTests(unittest.TestCase):
    def test_nondestructive_and_bounded(self):
        left, right = socket.socketpair()
        try:
            probe = SocketTrace()
            class Connection:
                socket = left
            for _ in range(150):
                right.sendall(b'abc')
                self.assertEqual(queued_bytes(left)['bytes'], 3)
                self.assertEqual(probe.read(Connection(), lambda c: c.socket.recv(3)), b'abc')
            self.assertEqual(probe.count, 150)
            self.assertEqual(len(probe.recent), 128)
            self.assertEqual(len(probe.top), 8)
            self.assertEqual(probe.recent[-1]['before']['bytes'], 3)
            self.assertEqual(probe.recent[-1]['after']['bytes'], 0)
        finally:
            left.close(); right.close()

    def test_exception_preserved(self):
        left, right = socket.socketpair()
        try:
            class Connection:
                socket = left
            probe = SocketTrace()
            def fail(c):
                raise RuntimeError('original failure')
            with self.assertRaisesRegex(RuntimeError, 'original failure'):
                probe.read(Connection(), fail)
            self.assertEqual(probe.recent[-1]['error'], 'RuntimeError')
        finally:
            left.close(); right.close()
