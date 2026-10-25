"""Repeatable simulator acceptance; never imports a hardware connection."""
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def main():
    folder=Path(__file__).parent/'resultados'/datetime.now().strftime('%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    report=dict(ok=False,python=sys.version,parent_pid=os.getpid(),rounds=[],sources={},
        limitations=['Emulated device only: no Q, USB/ADB link, DSP, GUI or analog audio; TCP is local.',
                    'GIL-stall tests prove process separation in this model, not hardware stability.'])
    for name in ('prototype.py','test_prototype.py','validate_offline.py','wire_adapter.py','test_wire_adapter.py','audio_control.py','test_audio_control.py','audio_pump.py','test_audio_pump.py','local_transport.py','process_audio.py','test_process_audio.py','acquisition_path.py','test_acquisition_process.py','socket_transport.py','test_socket_transport.py','socket_model_peer.py','tcp_model_server.py','test_socket_process.py','adb_tunnel.py','test_adb_tunnel.py'):
        source=(Path(__file__).parent/name).read_bytes();(folder/name).write_bytes(source)
        report['sources'][name]=hashlib.sha256(source).hexdigest()
    # Freeze reused production validation and fixture dependencies as evidence.
    report['dependencies']={}
    paths=[*sorted((ROOT/'monitor/v17/receiver').glob('*.py')),
           *sorted((ROOT/'monitor/v17/receiver').glob('*.json')),
           ROOT/'tests/v17/test_compact_protocol.py']
    for path in paths:
        relative=path.relative_to(ROOT);source=path.read_bytes()
        target=folder/'dependencies'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source)
        report['dependencies'][str(relative)]=hashlib.sha256(source).hexdigest()
    for trial in range(5):
        suite=unittest.defaultTestLoader.loadTestsFromNames([
            'experimentos.radio_io_process_v17.test_prototype',
            'experimentos.radio_io_process_v17.test_wire_adapter',
            'experimentos.radio_io_process_v17.test_audio_control',
            'experimentos.radio_io_process_v17.test_audio_pump',
            'experimentos.radio_io_process_v17.test_process_audio',
            'experimentos.radio_io_process_v17.test_acquisition_process',
            'experimentos.radio_io_process_v17.test_socket_transport',
            'experimentos.radio_io_process_v17.test_socket_process',
            'experimentos.radio_io_process_v17.test_adb_tunnel'])
        stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        (folder/f'trial_{trial+1}.txt').write_text(stream.getvalue())
        report['rounds'].append(dict(trial=trial+1,tests=result.testsRun,ok=result.wasSuccessful()))
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        if not result.wasSuccessful():
            print(stream.getvalue());print(folder/'report.json');return 1
    report['ok']=True
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['rounds']));print(folder/'report.json')
    return 0


if __name__=='__main__':raise SystemExit(main())
