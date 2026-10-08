import hashlib
import json
import unittest
from unittest.mock import patch
from monitor.historico.v13.receiver.unoq_autoload import ensure_scope,ROOT,run_command

class AutoloadTests(unittest.TestCase):
    def runner(self,active=True,other=False,relay=True):
        commands=[]
        source=[ROOT/f'arduino/v12_audio/relay/{n}' for n in ('unoq_config_stream.c','base_verifier.c','config_relay_protocol.h')]
        digest=hashlib.sha256(b''.join(p.read_bytes() for p in source)).hexdigest()[:20]
        binary=f'/home/arduino/.cache/serialmonitor/usb-stream-{digest}/unoq_stream'
        def run(args,running,timeout):
            commands.append(args)
            command=args[-1]
            if 'app list' in command:
                return json.dumps({'apps':[{'name':'Other' if other else 'Scope WAV V12 Audio','status':'running' if active else 'stopped'}]})
            if 'docker ps' in command:return 'serialmonitor-usb-stream' if relay else ''
            if 'docker inspect' in command:return json.dumps([{'State':{'Running':relay},'Mounts':[{'Source':binary}]}])
            return ''
        return run,commands
    def test_active_pair_is_reused(self):
        run,calls=self.runner()
        with patch('monitor.historico.v13.receiver.unoq_autoload.adb_path',return_value='adb'):
            self.assertEqual(ensure_scope('selected',runner=run),'v12_audio')
        self.assertFalse(any('-c' in args for args in calls))
    def test_stopped_pair_starts_selected_device_without_build(self):
        run,calls=self.runner(active=False,relay=False)
        with patch('monitor.historico.v13.receiver.unoq_autoload.adb_path',return_value='adb'):
            ensure_scope('selected',runner=run)
        launch=calls[-1]
        self.assertIn('selected',launch)
        self.assertEqual(launch[-3:],['start','--firmware','v12_audio'])
        self.assertNotIn('--build-native',launch)
        # Exercise the real launcher/imports with --help, without board access.
        output=run_command(launch[:-3]+['--help'])
        self.assertIn('start',output)
    def test_other_application_is_not_stopped(self):
        run,calls=self.runner(other=True)
        with patch('monitor.historico.v13.receiver.unoq_autoload.adb_path',return_value='adb'):
            with self.assertRaisesRegex(RuntimeError,'otra aplicación'):ensure_scope('selected',runner=run)
        self.assertEqual(len(calls),1)
    def test_ready_failure_reports_cause_and_keeps_log(self):
        import sys
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder, patch('monitor.historico.v13.receiver.unoq_autoload.ROOT', Path(folder)):
            with self.assertRaisesRegex(RuntimeError, 'MCU no entrega READY'):
                run_command([sys.executable, '-c',
                             "import sys; print('READY wait: Connection timed out'); print('RuntimeError: El relay no quedó en ejecución.'); sys.exit(1)"])
            logs = list((Path(folder) / 'diagnosticos/resultados_autoload').glob('*.log'))
            self.assertEqual(len(logs), 1)
            self.assertIn('READY wait', logs[0].read_text())

    def test_cancel_before_start(self):
        with self.assertRaises(InterruptedError):run_command(['unused'],running=lambda:False)


class ConnectScopeTests(unittest.TestCase):
    def test_live_connection_does_not_start_app(self):
        from monitor.historico.v13.receiver.unoq_autoload import connect_scope
        with patch('monitor.historico.v13.receiver.unoq_autoload.Connection') as factory, patch('monitor.historico.v13.receiver.unoq_autoload.ensure_scope') as start:
            with connect_scope('q') as connection:
                self.assertIs(connection, factory.return_value)
            start.assert_not_called()
            factory.return_value.open.assert_called_once()
            factory.return_value.close.assert_called_once()

    def test_missing_transport_starts_and_retries(self):
        from monitor.historico.v13.receiver.unoq_autoload import connect_scope
        with patch('monitor.historico.v13.receiver.unoq_autoload.Connection') as factory, patch('monitor.historico.v13.receiver.unoq_autoload.ensure_scope') as start:
            factory.return_value.open.side_effect = [ConnectionRefusedError(), None]
            with connect_scope('selected'): pass
            self.assertEqual(start.call_args.args[0], 'selected')
            self.assertEqual(factory.return_value.open.call_count, 2)
            self.assertEqual(factory.return_value.close.call_count, 2)

    def test_failed_start_closes_transport(self):
        from monitor.historico.v13.receiver.unoq_autoload import connect_scope
        with patch('monitor.historico.v13.receiver.unoq_autoload.Connection') as factory, patch('monitor.historico.v13.receiver.unoq_autoload.ensure_scope', side_effect=RuntimeError('READY')):
            factory.return_value.open.side_effect = ConnectionRefusedError()
            with self.assertRaisesRegex(RuntimeError, 'READY'):
                with connect_scope('q'): pass
            self.assertEqual(factory.return_value.open.call_count, 1)
            self.assertEqual(factory.return_value.close.call_count, 2)

    def test_adb_tunnel_opens_but_remote_relay_is_down(self):
        from monitor.historico.v13.receiver.unoq_autoload import connect_scope
        with patch('monitor.historico.v13.receiver.unoq_autoload.Connection') as factory, patch('monitor.historico.v13.receiver.unoq_autoload.ensure_scope') as start:
            factory.return_value.socket.recv.side_effect = [b'', b'S']
            with connect_scope('q'): pass
            start.assert_called_once()
            self.assertEqual(factory.return_value.open.call_count, 2)
            self.assertEqual(factory.return_value.socket.recv.call_count, 2)
