"""Resume a completed grid after owner loss; never reuse partial acceptances.

Firmware/core hashes are checked by AwakeSweep --resume. Complete winners pass
the existing physical evidence gate before being retained. Other candidates
repeat the entire acceptance, with fresh starts, and finally restore production.
"""
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experimentos.maxfreq_dual_v16.awake import AwakeSweep
from experimentos.maxfreq_dual_v16.sweep import NODES, EXP
from experimentos.maxfreq_v16.accepted import accepted_profiles

STAGES = [('finalist', 60), ('acceptance_1', 120), ('acceptance_2', 120),
          ('acceptance_3', 120), ('endurance', 600)]


def completed_bits(report):
    completed = set()
    for bits, winners in report['winners'].items():
        if not all(winners.get(name) for name in ('maximum_integrity', 'maximum_headroom')):
            continue
        evidence = copy.deepcopy(report)
        # Only evaluate the acceptance evidence here; run() performs restoration.
        evidence.update(ok=True, restored=True, winners={bits: winners})
        profiles = accepted_profiles(evidence)
        if not profiles or any(p.channels != 2 for p in profiles):
            raise ValueError('Invalid dual winner')
        completed.add(int(bits))
    return completed


class ResumeFinalists(AwakeSweep):
    def __init__(self):
        if '--resume' not in sys.argv:
            raise RuntimeError('This runner requires --resume')
        previous = json.loads((EXP/'sweep.json').read_text())
        super().__init__()
        self.completed = completed_bits(self.report)
        self.report['interruption'] = previous.get('interruption')
        self.report['interim_restoration'] = {
            k: previous.get(k) for k in ('restored', 'restore_integrity_ok',
                                         'restore_integrity_error', 'final_adc', 'final_generator')
        }
        self.report['resume_runner'] = {
            'file': str(Path(__file__).relative_to(ROOT)),
            'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'utc': datetime.now(timezone.utc).isoformat(),
            'retained_complete_bits': sorted(self.completed),
            'partial_acceptances_reused': False,
        }

    def screen(self):
        # The previous campaign reached finalists: keep its exact bounded grid.
        if not any(r['stage'] == 'finalist' for r in self.report['cases']):
            raise RuntimeError('Grid/refinement completion not established')

    def finalists(self):
        for bits in NODES:
            if bits in self.completed:
                print(f'RETAIN complete ADC{bits} controlled winners', flush=True)
                continue
            cases = [r for r in self.report['cases'] if r['bits'] == bits]
            passed = [r for r in cases if r['ok']]
            profiles = sorted({(r['ticks'], r['node_pairs']) for r in passed},
                              key=lambda p: (p[0], -p[1]))
            # Previous controlled long failures remain exclusions. Missing rows
            # (the interrupted run) are not failures and are never acceptances.
            long_rows = [r for r in cases if r['stage'] in dict(STAGES)
                         and r.get('host_awake_control')
                         and abs(r.get('wall_monotonic_drift_seconds', 999)) <= 2]
            rejected = {(r['ticks'], r['node_pairs']) for r in long_rows if not r['ok']}
            rejected_margin = {(r['ticks'], r['node_pairs']) for r in long_rows
                               if not r.get('headroom_ok')}
            accepted = {}

            def validate(ticks, n, margin=False):
                key = (ticks, n)
                if key in accepted:
                    return accepted[key]
                if key in rejected or (margin and key in rejected_margin):
                    return None
                rows = []
                for stage, seconds in STAGES:
                    row = self.trial(bits, ticks, n, seconds, stage, restart=True)
                    rows.append(row)
                    if not row['ok']:
                        rejected.add(key)
                        return None
                    if margin and not row.get('headroom_ok'):
                        rejected_margin.add(key)
                        return None
                result = dict(channels=2, bits=bits, ticks=ticks, node_pairs=n,
                              actual_rate=160000000/ticks, integrity_accepted=True,
                              headroom_accepted=all(r.get('headroom_ok', False) for r in rows))
                accepted[key] = result
                return result

            winner = None
            for ticks, n in profiles:
                winner = validate(ticks, n)
                if winner:
                    break
            self.report['winners'][str(bits)] = dict(maximum_integrity=winner,
                                                     maximum_headroom=None)
            self.save()
            for ticks, n in profiles:
                if not any(r['ticks'] == ticks and r['node_pairs'] == n
                           and r.get('headroom_ok') for r in passed):
                    continue
                result = validate(ticks, n, margin=True)
                if result and result['headroom_accepted']:
                    self.report['winners'][str(bits)]['maximum_headroom'] = result
                    break
            if winner is None:
                self.report.setdefault('unaccepted_bits', []).append(bits)
            self.save()


if __name__ == '__main__':
    sweep = ResumeFinalists()
    sweep.run()
    raise SystemExit(0 if sweep.report['ok'] and sweep.report['restored'] else 1)
