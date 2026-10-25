import unittest
from monitor.v18.io.live_connection import installed_connection, installed_identity

IDENTITY = dict(board_serial='v18-local-test', app='scope-v18-main-1', firmware_sha256='a'*64, relay_sha256='b'*64)

class Socket:
    def __init__(self): self.closed = False
    def setsockopt(self, *args): pass
    def settimeout(self, *args): pass
    def close(self): self.closed = True

class Adb:
    def __init__(self): self.rows = set(); self.calls = []
    def __call__(self, *args):
        self.calls.append(args)
        if args == ('devices', '-l'): return 'List of devices attached\nv18-local-test device usb:1'
        if args == ('forward', '--list'): return '\n'.join(' '.join(row) for row in sorted(self.rows))
        if args[-3:] == ('forward', 'tcp:0', 'tcp:8766'):
            self.rows.add(('v18-local-test', 'tcp:12345', 'tcp:8766')); return '12345'
        if args[-3:] == ('forward', '--remove', 'tcp:12345'):
            self.rows.remove(('v18-local-test', 'tcp:12345', 'tcp:8766')); return ''
        raise AssertionError(args)

class LiveConnectionTests(unittest.TestCase):
    def test_owner_closes_socket_and_only_owned_forward_on_error(self):
        adb = Adb(); peer = Socket()
        adb.rows.add(('other', 'tcp:54321', 'tcp:8766'))
        identities = []
        def identity(serial): identities.append(serial); return dict(IDENTITY)
        with self.assertRaisesRegex(ValueError, 'caller'):
            with installed_connection('v18-local-test', runner=adb, identity=identity,
                                      connect=lambda *a, **k: peer) as connection:
                self.assertEqual(connection.identity, IDENTITY)
                raise ValueError('caller')
        self.assertTrue(peer.closed)
        self.assertEqual(adb.rows, {('other', 'tcp:54321', 'tcp:8766')})
        self.assertGreaterEqual(len(identities), 3)
        self.assertFalse(any('start' in str(call) or 'push' in call for call in adb.calls))

    def test_setup_failure_releases_transferred_socket_and_forward(self):
        class BrokenSocket(Socket):
            def setsockopt(self, *args): raise OSError('socket setup')
        adb = Adb(); peer = BrokenSocket()
        with self.assertRaisesRegex(OSError, 'socket setup'):
            with installed_connection('v18-local-test', runner=adb,
                    identity=lambda serial: dict(IDENTITY), connect=lambda *a, **k: peer):
                self.fail('setup must fail')
        self.assertTrue(peer.closed)
        self.assertFalse(adb.rows)

    def test_experimental_identity_requires_explicit_exact_app(self):
        import json
        app='scope-v18-rate-probe-spi40-main-1'
        def runner(*args):
            command=args[-1]
            if command.startswith('docker ps '):return app+'\nserialmonitor-usb-stream-v18'
            if command=='docker inspect '+app:
                return json.dumps([{'Config':{'Labels':{'com.docker.compose.project.working_dir':
                    '/home/arduino/ArduinoApps/scope-v18-rate-probe-spi40/.cache'}}}])
            if command=='docker inspect serialmonitor-usb-stream-v18':
                return json.dumps([{'Mounts':[{'Destination':'/work/unoq_stream',
                    'Source':'/home/arduino/.cache/serialmonitor/probe/unoq_stream'}]}])
            if command.startswith('sha256sum '):return 'a'*64+' file'
            raise AssertionError(command)
        with self.assertRaises(RuntimeError):installed_identity('test',runner)
        result=installed_identity('test',runner,expected_app=app)
        self.assertEqual(result['app'],app)
        with self.assertRaises(RuntimeError):installed_identity('test',runner,expected_app='scope-v18-other-main-1')

    def test_absent_app_rejected_without_writes(self):
        calls = []
        def runner(*args): calls.append(args); return 'unrelated-main-1'
        with self.assertRaisesRegex(RuntimeError, 'ya activos'):
            installed_identity('v18-local-test', runner)
        self.assertEqual(len(calls), 1)
        self.assertIn('docker ps', calls[0][-1])

if __name__ == '__main__': unittest.main()
