"""Finish an interrupted campaign without replacing its original evidence."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experimentos.maxfreq_optimized_v17.run import OptimizedSweep, STAGES
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor


def main(path):
    source = Path(path).resolve()
    previous = json.loads(source.read_text())
    probe = OptimizedSweep()
    for relative, digest in previous['source_hashes'].items():
        if hashlib.sha256((source.parent.parent / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Experimental sources changed: {relative}')
    require_exclusive_monitor()
    if 'ESTAB' in probe.stable.shell('ss', '-tn', 'sport', '=', ':8766', capture=True).stdout:
        raise RuntimeError('Q has another reader')
    # Confirm that the interrupted deployment is still the isolated app.
    names = probe.stable.shell('docker', 'ps', '--format', '{{.Names}}', capture=True).stdout.splitlines()
    if 'scope-v16-send1400-experimental-main-1' not in names or 'scope-v17-main-1' in names:
        raise RuntimeError('Expected interrupted experimental deployment')
    remote = Path(probe.candidate.remote)
    paths = [str(remote / relative) for relative in previous['candidate_source_hashes']]
    hashes = probe.candidate.shell('sha256sum', *paths, capture=True).stdout.splitlines()
    actual = {line.split(maxsplit=1)[1].strip(): line.split()[0] for line in hashes}
    for relative, digest in previous['candidate_source_hashes'].items():
        if actual.get(str(remote / relative)) != digest:
            raise RuntimeError(f'Deployed sources changed: {relative}')
    probe.report = previous
    probe.report.update(resumed_from=str(source), restored=False, ok=False)
    probe.prior = previous['prior']
    probe.deployment = previous['deployment']
    probe.switched = True
    probe.save()
    try:
        winner = previous['winners']['14']['maximum_integrity']
        boundaries = [b for b in previous['boundaries'] if b['bits'] == 14 and b['criterion'] == 'headroom']
        starts = {b['node_pairs']: b['passing_ticks'] for b in boundaries}
        while min(starts.values()) <= 640:
            ticks = min(starts.values())
            for node in starts:
                if starts[node] != ticks:
                    continue
                rows = []
                for stage, seconds in STAGES:
                    evidence = [r for r in probe.report['cases'] if
                        (r['bits'], r['ticks'], r['node_pairs'], r['stage']) == (14, ticks, node, stage)]
                    row = evidence[-1] if evidence else probe.trial(14, ticks, node, seconds, stage, restart=True)
                    rows.append(row)
                    if not row['ok']:
                        break
                if len(rows) == 4 and all(r['ok'] and r.get('headroom_ok', False) for r in rows):
                    margin = dict(bits=14, ticks=ticks, node_pairs=node, actual_rate=160000000/ticks,
                        integrity_accepted=True, headroom_accepted=True,
                        acceptance_seconds=[60, 120, 120, 120])
                    probe.report['winners']['14'] = dict(maximum_integrity=winner, maximum_headroom=margin)
                    probe.report['ok'] = True
                    probe.save()
                    return
                starts[node] += 1
        raise RuntimeError('No headroom finalist passed')
    except BaseException as exc:
        probe.report['error'] = str(exc)
        raise
    finally:
        try:
            probe.restore()
        except Exception as exc:
            probe.report['restore_error'] = str(exc)
            raise
        finally:
            probe.save()
            print('REPORT', probe.folder / 'report.json', 'OK', probe.report['ok'],
                  'RESTORED', probe.report['restored'], flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
