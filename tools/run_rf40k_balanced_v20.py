"""Sequential native A/B for the bounded RF cadence. No device access."""
import os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
env=dict(os.environ,PYTHONPYCACHEPREFIX='/tmp/arduscopio-v20-check-cache')
env.pop('QT_QPA_PLATFORM',None)
for pair in range(1,4):
    for legacy in ((True,False) if pair%2 else (False,True)):
        path=ROOT/f'diagnosticos/resultados_v20/rf40k_balanced_20261103/{pair:02d}_{"legacy" if legacy else "balanced"}_w9000_ch1.json'
        if path.exists():raise RuntimeError('Do not overwrite '+str(path))
        cmd=[sys.executable,str(ROOT/'tools/benchmark_rf40k_balanced_v20.py'),
             '--run',str(pair),'--warmup','3','--measure','10']
        if legacy:cmd.append('--legacy-policy')
        subprocess.run(cmd,cwd=ROOT,env=env,check=True)
