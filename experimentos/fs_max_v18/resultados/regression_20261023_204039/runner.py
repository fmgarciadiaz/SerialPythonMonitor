"""Screen current public native maxima with BatchFast before transport promotion.

Uses the existing exclusive-owner transaction and restores the production pair.
This is regression screening, not qualification of new rates or analog accuracy.
"""
import argparse
import json
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experimentos.fs_max_v18.run_probe import Hardware,orchestrate,private_profiles
from experimentos.fs_max_v18.probe_journal import ProbeJournal

def regression_plan(seconds=15):
    from monitor.v18.receiver.unoq_native import PROFILES
    if not 0<seconds<=120:raise ValueError('seconds must be in (0,120]')
    rows=[]
    for bits in (8,10,12,14,16):
        for channels in (1,2):
            eligible=[p for p in PROFILES if p['bits']==bits and p['channels']==channels
                      and not p.get('internal_only') and not p.get('integration_pending')]
            if not eligible:continue
            p=min(eligible,key=lambda p:p['ticks'])
            rows.append(dict(p,seconds=seconds,rate=160000000/p['ticks'],
                             repetition=1,regression_only=True))
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true')
    p.add_argument('--seconds',type=float,default=15)
    args=p.parse_args();rows=regression_plan(args.seconds)
    if not args.run:print(json.dumps(rows,indent=2));return 0
    from monitor.v18.board_owner import board_owner
    folder=Path(__file__).resolve().parent/'resultados'/time.strftime('regression_%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    (folder/'runner.py').write_bytes(Path(__file__).read_bytes())
    report=dict(ok=False,cases=[],plan=rows,recipe='batchfast',scope='public native maxima regression')
    journal=ProbeJournal(folder/'report.json',report);hw=Hardware(folder,report)
    def interrupted(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,interrupted)
    with board_owner(hw.original.serial,'V18 BatchFast regression'),private_profiles(hw.source):
        ok=orchestrate(hw,rows,report,journal.save)
    print(folder/'report.json');return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
