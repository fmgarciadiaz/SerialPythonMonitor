"""Run three sequential native V20 adaptive/fixed timer pairs."""
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'tools/compare_rf40k_fixed_timer_v20.py'
env=os.environ.copy()
env['PYTHONPYCACHEPREFIX']='/tmp/arduscopio-v20-check-cache'
env.pop('QT_QPA_PLATFORM',None)
for pair in range(1,4):
    for fixed in ((False,True) if pair%2 else (True,False)):
        command=[sys.executable,str(SCRIPT),'--run',str(pair),'--warmup','3','--measure','10']
        if fixed:command.append('--fixed-timer')
        print('RUN',pair,'fixed' if fixed else 'adaptive',flush=True)
        subprocess.run(command,cwd=ROOT,env=env,check=True)
