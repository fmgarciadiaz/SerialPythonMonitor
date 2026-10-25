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
        limitations=['Synthetic device only: no Q, real transport, DSP, GUI or analog audio.',
                    'GIL-stall tests prove process separation in this model, not hardware stability.'])
    for name in ('prototype.py','test_prototype.py','validate_offline.py'):
        source=(Path(__file__).parent/name).read_bytes();(folder/name).write_bytes(source)
        report['sources'][name]=hashlib.sha256(source).hexdigest()
    for trial in range(5):
        suite=unittest.defaultTestLoader.loadTestsFromName('experimentos.radio_io_process_v17.test_prototype')
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
