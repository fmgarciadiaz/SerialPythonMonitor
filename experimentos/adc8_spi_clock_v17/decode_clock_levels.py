"""Decode saved read-only DFS evidence; no board access."""
import json
from pathlib import Path


def decode(data):
    snapshots = data['snapshots']
    if not all(s == snapshots[0] for s in snapshots):
        raise ValueError('Clock snapshots changed')
    snapshot = snapshots[0]
    if not snapshot['dfs_control'] & 1:
        raise ValueError('DFS is not enabled')
    # QCM2290 gcc_parent_map_1: selector 0=XO, 1=GPLL0, 2=AUX2, 4=GPLL6.
    parents = {0: 'bi_tcxo', 1: 'gpll0', 2: 'gpll0_out_aux2', 4: 'gpll6'}
    levels = []
    for index, level in enumerate(snapshot['levels']):
        cfg = level['cfg']
        source = parents[(cfg >> 8) & 7]
        rate = int(data['clocks'][source]['clk_rate'])
        hid = cfg & 31
        if hid:
            rate = rate * 2 // (hid + 1)
        if (cfg >> 12) & 3:
            m = level['m'] & 65535
            n = ((~level['n']) & 65535) + m
            rate = rate * m // n
        levels.append({'index': index, 'source_hz': rate})
    requests = []
    for req in [38000000, 38500000, 39000000, 40000000, 41500000]:
        candidates = []
        for entry in levels:
            source = entry['source_hz']
            div = (source + req - 1) // req
            candidates.append((req - source // div, entry['index'], source, div))
        _, index, source, div = min(candidates)
        requests.append({'requested_hz': req, 'index': index,
                         'source_hz': source, 'divisor': div,
                         'configured_hz_model': source / div})
    return {'dfs_enabled': True, 'levels': levels,
            'requests_upstream_selection_model': requests,
            'not_electrical_measurement': True}


if __name__ == '__main__':
    folder = Path(__file__).resolve().parent
    result = decode(json.loads((folder / 'clock_levels_live.json').read_text()))
    text = json.dumps(result, indent=2) + '\n'
    (folder / 'clock_levels_decoded.json').write_text(text)
    print(text)
