import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from monitor.relay_identity import relay_digest, relay_sources
from monitor.v17.receiver.unoq_autoload import ensure_scope, ROOT


class RelayIdentityTests(unittest.TestCase):
    def test_installer_and_autoload_share_all_native_headers(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import usb_stream
        board=SimpleNamespace(config={'local_app':'arduino/v17/oscilloscope'},shell=MagicMock())
        expected='/home/arduino/.cache/serialmonitor/usb-stream-'+relay_digest(ROOT/'arduino/v17/relay')+'/unoq_stream'
        self.assertEqual(usb_stream.binary(board,p992=True,audio=True),expected)
        def run(args,*_):
            command=' '.join(args)
            if 'app list' in command:return json.dumps({'apps':[{'name':'Scope V17','status':'running'}]})
            if 'ps -a' in command:return 'serialmonitor-usb-stream\n'
            if 'inspect' in command:return json.dumps([{'State':{'Running':True},'Mounts':[{'Source':expected}]}])
            self.fail(command)
        with patch('monitor.v17.receiver.unoq_autoload.adb_path',return_value='adb'):
            started=Mock()
            self.assertEqual(ensure_scope('q',runner=run,on_started=started),'v17')
            started.assert_not_called()
        self.assertIn('native_profiles.h',[p.name for p in relay_sources(ROOT/'arduino/v17/relay')])

    def test_actual_start_is_reported_only_after_success(self):
        def run(args,*_):
            command=' '.join(args)
            if 'app list' in command:return json.dumps({'apps':[{'name':'Scope V17','status':'stopped'}]})
            if 'ps -a' in command:return ''
            return ''
        started=Mock()
        with patch('monitor.v17.receiver.unoq_autoload.adb_path',return_value='adb'):
            self.assertEqual(ensure_scope('q',runner=run,on_started=started),'v17')
        started.assert_called_once_with()

        def failed_start(args,*rest):
            if args[0]==sys.executable:raise RuntimeError('start failed')
            return run(args,*rest)
        started.reset_mock()
        with patch('monitor.v17.receiver.unoq_autoload.adb_path',return_value='adb'):
            with self.assertRaisesRegex(RuntimeError,'start failed'):
                ensure_scope('q',runner=failed_start,on_started=started)
        started.assert_not_called()

    def test_header_change_invalidates_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            for name in ('unoq_config_stream.c','base_verifier.c','config_relay_protocol.h','native_profiles.h'):
                (folder/name).write_text(name)
            previous=relay_digest(folder)
            (folder/'native_profiles.h').write_text('changed')
            self.assertNotEqual(previous,relay_digest(folder))
