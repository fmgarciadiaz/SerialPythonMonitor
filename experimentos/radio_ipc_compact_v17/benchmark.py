"""Alternating offline A/B including packing and child reconstruction costs."""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import hashlib
import json
import multiprocessing as mp
from multiprocessing.reduction import ForkingPickler
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from experimentos.radio_ipc_compact_v17.codec import compact, expand
from experimentos.radio_ipc_compact_v17.test_codec import batch, SETTINGS
from diagnosticos.medir_ipc_radio_v17 import summarize


def consume(payload):
    started = time.thread_time()
    restored = expand(payload)
    return (len(restored.columns['CH1']), float(restored.columns['Tiempo (us)'][-1]),
            (time.thread_time()-started)*1000)


def main():
    folder = Path(__file__).parent/'resultados'/datetime.now().strftime('%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    results = []
    with ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context('spawn')) as pool:
        pool.submit(consume, batch()).result()
        for count in (32000, 64000, 128000, 256000):
            original = batch(count=count)
            expected = consume(original)[:2]
            measurements = {name:dict(pack=[], wall=[], rebuild=[]) for name in ('current','compact')}
            for repeat in range(100):
                order = ('current','compact') if repeat % 2 == 0 else ('compact','current')
                for name in order:
                    started = time.perf_counter()
                    cpu = time.thread_time()
                    payload = compact(original, SETTINGS) if name == 'compact' else original
                    pack_cpu = (time.thread_time()-cpu)*1000
                    answer = pool.submit(consume, payload).result()
                    wall = (time.perf_counter()-started)*1000
                    assert answer[:2] == expected
                    measurements[name]['pack'].append(pack_cpu)
                    measurements[name]['wall'].append(wall)
                    measurements[name]['rebuild'].append(answer[2])
            for name, values in measurements.items():
                payload = compact(original, SETTINGS) if name == 'compact' else original
                results.append(dict(samples=count, variant=name,
                    bytes=len(ForkingPickler.dumps(payload)),
                    pack_thread_cpu=summarize(values['pack']),
                    child_rebuild_thread_cpu=summarize(values['rebuild']),
                    total_roundtrip_wall=summarize(values['wall'])))
    hashes = {}
    for filename in ('codec.py', 'test_codec.py', 'benchmark.py'):
        content = (Path(__file__).parent/filename).read_bytes()
        (folder/filename).write_bytes(content)
        hashes[filename] = hashlib.sha256(content).hexdigest()
    report = dict(python=sys.version, numpy=np.__version__, repetitions=100,
        order='alternating current/compact then compact/current', rows=results, source_hashes=hashes,
        limitations=['Offline, no GUI, Q or demodulation. Includes packing, pipe, scheduling and child reconstruction.',
                     'No proof of underrun correction or physical acceptance.'])
    (folder/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(folder/'report.json')
    for row in results:
        print(row['samples'], row['variant'], row['bytes'], row['total_roundtrip_wall'])


if __name__ == '__main__':
    main()
