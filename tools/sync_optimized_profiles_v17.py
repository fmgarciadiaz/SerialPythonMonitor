"""Synchronize the six accepted CH1 profiles into V17 only."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ('finalist', 'acceptance_1', 'acceptance_2', 'acceptance_3')


def synchronize(report_path):
    report = json.loads(report_path.read_text())
    if not all(report.get(key) for key in ('ok', 'restored', 'restore_integrity_ok')):
        raise ValueError('Incomplete or unrestored physical campaign')
    profiles_path = ROOT / 'monitor/v17/receiver/native_profiles.json'
    profiles = json.loads(profiles_path.read_text())
    added = []
    for bits in (10, 12, 14):
        for criterion in ('maximum_integrity', 'maximum_headroom'):
            winner = report['winners'][str(bits)][criterion]
            rows = []
            for stage, seconds in zip(STAGES, (60, 120, 120, 120)):
                matches = [row for row in report['cases'] if
                    (row['bits'], row['ticks'], row['node_pairs'], row['stage']) ==
                    (bits, winner['ticks'], winner['node_pairs'], stage)]
                if not matches:
                    raise ValueError(f'Missing {bits}/{criterion}/{stage}')
                row = matches[-1]
                if not row['ok'] or row.get('seconds', 0) < seconds or any(
                        row['status'][key] for key in ('dropped', 'fatal')):
                    raise ValueError(f'Invalid {bits}/{criterion}/{stage}')
                rows.append(row)
            margin = all(row.get('headroom_ok', False) for row in rows)
            if criterion == 'maximum_headroom' and not margin:
                raise ValueError('Headroom finalist did not pass every stage')
            profile = dict(bits=bits, ticks=winner['ticks'], node_pairs=winner['node_pairs'],
                channels=1, headroom=False, isolated_headroom=margin,
                optimized_transport=True, integration_pending=True, validation='isolated_60s_3x120s',
                acceptance_seconds=[60, 120, 120, 120],
                evidence=str(report_path.relative_to(ROOT)))
            key = (bits, profile['ticks'], profile['node_pairs'], 1)
            existing = next((p for p in profiles if
                (p['bits'], p['ticks'], p['node_pairs'], p['channels']) == key), None)
            if existing:
                # Do not erase subsequent production acceptance on a re-sync.
                if existing.get('validation') != 'production_60s_3x120s':
                    existing.update(profile)
                profile = existing
            else:
                profiles.append(profile)
            added.append(profile)
    profiles_path.write_text(json.dumps(profiles, indent=2) + '\n')
    rows = ''.join(f'    {{{p["bits"]}, {p["channels"]}, {p["ticks"]}, {p["node_pairs"]}}},\n'
                   for p in profiles)
    for folder in ('arduino/v17/oscilloscope/sketch', 'arduino/v17/relay'):
        path = ROOT / folder / 'native_profiles.h'
        content = path.read_text()
        start = content.index('static const ScopeNativeProfile scope_native_profiles[] = {')
        end = content.index('\n};', start) + 3
        content = content[:start] + 'static const ScopeNativeProfile scope_native_profiles[] = {\n' + rows + '};' + content[end:]
        path.write_text(content)
        fast = [(8, 114, 3456)] + [(p['bits'], p['ticks'], p['node_pairs']) for p in profiles if p.get('optimized_transport')]
        clauses = ' ||\n        '.join(f'(bits=={bits} && ticks=={ticks} && pairs=={pairs})'
                                     for bits, ticks, pairs in fast)
        (ROOT / folder / 'high_rate_profile.h').write_text(
            '#pragma once\n#include <stdint.h>\n'
            '// Exact CH1 profiles with the validated SPI38/FIFO10 pipeline.\n'
            'static inline int scope_high_rate(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {\n'
            f'    return channels==1 && ({clauses});\n}}\n'
            'static inline int scope_spi40(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {\n'
            '    return bits==8 && channels==1 && (ticks==100 || ticks==112) && pairs==3456;\n}\n'
            'static inline unsigned scope_queue_capacity(unsigned bits,unsigned channels,uint32_t ticks,unsigned pairs) {\n'
            '    return scope_spi40(bits,channels,ticks,pairs)?8U:4U;\n}\n')
    return added


def publish_integration(report_path):
    report=json.loads(report_path.read_text())
    if not (report.get('ok') and report.get('restored') and report.get('recovery',{}).get('ok')):
        raise ValueError('Incomplete production integration or restoration')
    if report.get('final_identity',{}).get('app')!='scope-v17-main-1':
        raise ValueError('Production V17 identity missing')
    path=ROOT/'monitor/v17/receiver/native_profiles.json'
    profiles=json.loads(path.read_text())
    accepted=[]
    for profile in profiles:
        if not profile.get('optimized_transport'):
            continue
        rows=[]
        for stage,seconds in zip(STAGES,(60,120,120,120)):
            matches=[r for r in report['cases'] if r['adc']==dict(bits=profile['bits'],rate=160000000//profile['ticks'])
                and r['stage']==stage and r['node_pairs']==profile['node_pairs']]
            if not matches:
                break
            row=matches[-1]
            if not row['ok'] or row.get('seconds',0)<seconds or row['status']['dropped'] or row['status']['fatal']:
                raise ValueError('Invalid production acceptance stage')
            if row.get('scheduler')!=dict(policy=1,priority=10):
                raise ValueError('Fast scheduler unverified')
            rows.append(row)
        if len(rows)!=4:
            continue
        margin=all(r['metrics']['mean_send_headroom']>=.1 and
            r['metrics']['maxima']['queue_peak']<4 and r['metrics']['maxima']['slack_ticks']>0 for r in rows)
        profile.update(headroom=margin,
            integration_pending=False,validation='production_60s_3x120s',
            integrated_evidence=str(report_path.relative_to(ROOT)),
            firmware_sha256=report['final_identity']['firmware_sha256'])
        accepted.append(profile)
    if not accepted:
        raise ValueError('No profile has four accepted production stages')
    path.write_text(json.dumps(profiles,indent=2)+'\n')
    return accepted


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--integration',action='store_true')
    args = parser.parse_args()
    print(json.dumps((publish_integration if args.integration else synchronize)(args.report.resolve()), indent=2))
