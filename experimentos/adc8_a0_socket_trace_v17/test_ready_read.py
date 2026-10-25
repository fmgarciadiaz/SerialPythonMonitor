import socket
import unittest
from .ready_read import ReadyRead


class ReadyReadTests(unittest.TestCase):
    def test_connection_close_releases_peer_immediately(self):
        left, right = socket.socketpair()
        left.settimeout(.1)
        right.settimeout(.1)
        reader = ReadyRead()
        class Connection:
            socket = left
        connection = Connection()
        try:
            right.sendall(b'data')
            self.assertEqual(reader.read(connection, lambda c: b''), b'data')
            self.assertEqual(len(reader.handles), 1)
            reader.close_connection(connection, lambda c: c.socket.close())
            self.assertEqual(reader.handles, [])
            self.assertEqual(right.recv(1), b'')
        finally:
            reader.close(); left.close(); right.close()

    def test_immediate_fallback_order_timeout_and_independent_close(self):
        left, right = socket.socketpair()
        left.settimeout(.1)
        reader = ReadyRead()
        class Connection:
            socket = left
        connection = Connection()
        calls = []
        def fallback(c):
            calls.append(c)
            return b''
        try:
            right.sendall(b'first')
            self.assertEqual(reader.read(connection, fallback), b'first')
            self.assertEqual(calls, [])
            self.assertEqual(left.gettimeout(), .1)
            self.assertEqual(reader.read(connection, fallback), b'')
            self.assertEqual(len(calls), 1)
            right.sendall(b'second')
            self.assertEqual(reader.read(connection, fallback), b'second')
            left.sendall(b'command')
            self.assertEqual(right.recv(7), b'command')
            self.assertEqual((reader.immediate, reader.fallback), (2, 1))
            reader.close()
            left.sendall(b'open')
            self.assertEqual(right.recv(4), b'open')
        finally:
            reader.close(); left.close(); right.close()

    def test_eof_uses_original_error(self):
        left, right = socket.socketpair()
        left.settimeout(.1)
        reader = ReadyRead()
        class Connection:
            socket = left
        def original(c):
            self.assertEqual(c.socket.recv(1), b'')
            raise RuntimeError('original EOF')
        right.close()
        try:
            with self.assertRaisesRegex(RuntimeError, 'original EOF'):
                reader.read(Connection(), original)
        finally:
            reader.close(); left.close()
