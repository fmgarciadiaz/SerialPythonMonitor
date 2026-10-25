"""Audit all preserved sustained trials, separating hidden windows from transport failures."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent

def audit(paths):
    adc = json.loads((EXP / 'qualification_summary.json').read_text())
    reference = json.loads((ROOT / adc['reports'][0]).read_text())
    result = dict(reports=[], cases=[], bits={}, restored=True)
    host_hashes = None
    for path in paths:
        parent = json.loads(path.read_text())
        assert parent['sustained'] and parent['restored'] and parent['recovery']['ok']
        assert parent['prior_identity'] == parent['final_identity']
        assert parent['candidate_identity'] == adc['candidate_identity']
        assert parent['source_hashes'] == reference['source_hashes']
        assert parent['candidate_relay_sha256'] == reference['candidate_relay_sha256']
        if host_hashes is None:
            host_hashes = parent['host_hashes']
        assert parent['host_hashes'] == host_hashes
        result['reports'].append(str(path.relative_to(ROOT)))
        for row in parent['cases']:
            if 'child' not in row:
                continue
            report = json.loads(Path(row['child']['report']).read_text())
            assert report['identity_before'] == adc['candidate_identity']
            assert report['adc']['bits'] == row['bits']
            assert report['output_input'] == 'FILTER' and row['view'] == 'fft'
            paint = report['paint_audit']
            stats = report['joint_send_statistics']
            audio = report['ok'] and report['restored'] and row['child_exit'] == 0
            visible = paint['exposed_fraction'] >= .9 and paint['fft_fps'] >= 5
            headroom = stats['mean_margin'] >= .1 and report['adc_queue_peak'] < 4 and stats['minimum_slack_ticks'] > 0
            result['cases'].append(dict(bits=row['bits'], stage=row['stage'], seconds=row['seconds'],
                report=str(Path(row['child']['report']).relative_to(ROOT)), audio_ok=audio,
                visual_ok=visible, headroom_ok=headroom, queue_peak=report['adc_queue_peak'],
                mean_margin=stats['mean_margin'], buffer_minimum=report['source_buffer_minimum'],
                exposed_fraction=paint['exposed_fraction'], fft_paints_per_second=paint['fft_fps']))
    for bits in (14, 16):
        rows = [r for r in result['cases'] if r['bits'] == bits]
        visible = [r for r in rows if r['visual_ok']]
        durations = sorted(r['seconds'] for r in visible)
        # Hidden runs remain listed; only a confirmed visibility issue can be excluded.
        audio_ok = bool(rows) and all(r['audio_ok'] for r in rows)
        audio_complete = sorted(r['seconds'] for r in rows) == [60, 120, 120, 120]
        if len({r['stage'] for r in rows}) != len(rows):
            raise ValueError('Repeated sustained stage; do not select successful repeats')
        complete = durations == [60, 120, 120, 120]
        result['bits'][str(bits)] = dict(complete=complete, audio_ok=audio_ok,
            audio_qualified=audio_complete and audio_ok and all(r['headroom_ok'] for r in rows),
            accepted=complete and audio_ok and all(r['headroom_ok'] for r in visible),
            hidden_cases=sum(not r['visual_ok'] for r in rows))
    result['scope'] = 'FILTER→A0 40kHz and visible FFT65536; windows include startup; no analog, Scan/US or other-mode acceptance'
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', type=Path, nargs='+')
    args = parser.parse_args()
    data = audit([p.resolve() for p in args.reports])
    (EXP / 'sustained_summary.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps(data['bits'], indent=2))
