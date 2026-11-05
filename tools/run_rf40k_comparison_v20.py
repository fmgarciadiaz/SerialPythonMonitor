"""Run the native RF-only comparison as isolated sequential processes."""
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'tools/compare_rf40k_fps_v20.py'
env=os.environ.copy()
env['PYTHONPYCACHEPREFIX']='/tmp/arduscopio-v20-check-cache'
env.pop('QT_QPA_PLATFORM',None)
for pair in range(1,4):
    for version in (('v19','v20') if pair%2 else ('v20','v19')):
        command=[sys.executable,str(SCRIPT),'--version',version,'--run',str(pair),
                 '--warmup','3','--measure','10']
        print('RUN',pair,version,flush=True)
        subprocess.run(command,cwd=ROOT,env=env,check=True)
