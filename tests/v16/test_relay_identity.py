import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from monitor.relay_identity import relay_digest, relay_sources
from monitor.v16.receiver.unoq_autoload import ensure_scope, ROOT


class RelayIdentityTests(unittest.TestCase):
    def test_installer_and_autoload_share_all_native_headers(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import usb_stream
        board=SimpleNamespace(config={'local_app':'arduino/v16/oscilloscope'},shell=MagicMock())
        expected='/home/arduino/.cache/serialmonitor/usb-stream-'+relay_digest(ROOT/'arduino/v16/relay')+'/unoq_stream'
        self.assertEqual(usb_stream.binary(board,p992=True,audio=True),expected)
        def run(args,*_):
            command=' '.join(args)
            if 'app list' in command:return json.dumps({'apps':[{'name':'Scope V16','status':'running'}]})
            if 'ps -a' in command:return 'serialmonitor-usb-stream\n'
            if 'inspect' in command:return json.dumps([{'State':{'Running':True},'Mounts':[{'Source':expected}]}])
            self.fail(command)
        with patch('monitor.v16.receiver.unoq_autoload.adb_path',return_value='adb'):
            self.assertEqual(ensure_scope('q',runner=run),'v16')
        self.assertIn('native_profiles.h',[p.name for p in relay_sources(ROOT/'arduino/v16/relay')])

    def test_header_change_invalidates_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            for name in ('unoq_config_stream.c','base_verifier.c','config_relay_protocol.h','native_profiles.h'):
                (folder/name).write_text(name)
            previous=relay_digest(folder)
            (folder/'native_profiles.h').write_text('changed')
            self.assertNotEqual(previous,relay_digest(folder))
