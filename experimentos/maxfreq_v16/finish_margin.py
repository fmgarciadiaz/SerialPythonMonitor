"""Reuse complete awake acceptances and refine the remaining margin boundary."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experimentos.maxfreq_v16.awake import AwakeSweep
from experimentos.maxfreq_v16.accepted import accepted_profiles
from experimentos.maxfreq_v16.sweep import EXP

STAGES = [('finalist',60),('acceptance_1',120),('acceptance_2',120),
          ('acceptance_3',120),('endurance',600)]


class FinishMargin(AwakeSweep):
    def __init__(self):
        previous = json.loads((EXP/'sweep.json').read_text())
        if not previous.get('restored'):
            raise RuntimeError('Wait for the previous owner to restore the board')
        super().__init__()
        evidence = dict(self.report, ok=True, restored=True)
        accepted_profiles(evidence)  # Existing winners must already have complete awake evidence.
        self.report['acceptance_driver'] = {
            'file': __file__,
            'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'reuse': 'Only complete controlled acceptances; stop margin-only cases at first failed criterion',
        }
        self.report.pop('error',None)

    def screen(self):
        # Fine refinement of the gap left by the coarse headroom grid.
        for ticks in range(225,242):
            if not any(r['bits']==14 and r['ticks']==ticks and r['node_pairs']==7936
                       and r['stage']=='margin_refine' and r.get('host_awake_control')
                       for r in self.report['cases']):
                self.trial(14,ticks,7936,10,'margin_refine')

    def finalists(self):
        for bits, winners in self.report['winners'].items():
            if winners.get('maximum_headroom'):
                continue
            bits=int(bits)
            profiles=sorted({(r['ticks'],r['node_pairs']) for r in self.report['cases']
                             if r['bits']==bits and r['ok'] and r.get('headroom_ok')},
                            key=lambda p:(p[0],-p[1]))
            for ticks,n in profiles:
                relevant=[r for r in self.report['cases'] if r['bits']==bits and
                          r['ticks']==ticks and r['node_pairs']==n and r.get('host_awake_control')]
                if any(r['stage'] in dict(STAGES) and
                       (not r['ok'] or not r.get('headroom_ok')) for r in relevant):
                    continue
                complete=True
                for stage,seconds in STAGES:
                    rows=[r for r in relevant if r['stage']==stage]
                    row=rows[-1] if rows else self.trial(bits,ticks,n,seconds,stage,restart=True)
                    if not row['ok'] or not row.get('headroom_ok'):
                        complete=False
                        break
                if complete:
                    winners['maximum_headroom']=dict(bits=bits,ticks=ticks,node_pairs=n,
                        actual_rate=160000000/ticks,integrity_accepted=True,headroom_accepted=True)
                    self.save()
                    break


if __name__=='__main__':
    sweep=FinishMargin()
    sweep.run()
    raise SystemExit(0 if sweep.report['ok'] and sweep.report['restored'] else 1)
