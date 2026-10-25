"""Offline cost of the current RADIO DSP input; never connects to Q.

The reduced-column comparison is a byte-cost bound, not a valid DSP payload:
it deliberately omits continuity metadata and must never enter production.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import json
import hashlib
import multiprocessing as mp
from multiprocessing.reduction import ForkingPickler
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from monitor.v17.processing import ProcessingSettings
from monitor.v17.receiver.unoq_acquisition import Configuration


def inspect_input(batch, settings):
    """Consume input in the child, returning only a tiny validation result."""
    return len(batch.columns['CH1']), settings.generation, float(batch.columns['CH1'][-1])


def summarize(values):
    return dict(zip(('median_ms', 'p95_ms', 'max_ms'),
                    map(float, np.percentile(values, (50, 95, 100)))))


def measure(payload, settings, executor, repeats):
    expected = inspect_input(payload, settings)
    encoded = ForkingPickler.dumps((payload, settings))
    assert inspect_input(*ForkingPickler.loads(encoded)) == expected
    assert executor.submit(inspect_input, payload, settings).result() == expected
    dump_cpu, load_cpu, roundtrip = [], [], []
    for _ in range(repeats):
        started = time.thread_time()
        blob = ForkingPickler.dumps((payload, settings))
        dump_cpu.append((time.thread_time() - started) * 1000)
        started = time.thread_time()
        restored = ForkingPickler.loads(blob)
        load_cpu.append((time.thread_time() - started) * 1000)
        assert inspect_input(*restored) == expected
        started = time.perf_counter()
        assert executor.submit(inspect_input, payload, settings).result() == expected
        roundtrip.append((time.perf_counter() - started) * 1000)
    return dict(bytes=len(encoded), serialize_thread_cpu=summarize(dump_cpu),
                deserialize_thread_cpu=summarize(load_cpu),
                process_roundtrip_wall=summarize(roundtrip))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=200)
    args = parser.parse_args()
    if args.repeats < 20:
        parser.error('Se requieren al menos 20 repeticiones')
    if not hasattr(time, 'thread_time'):
        parser.error('Usar Python con time.thread_time (entorno Python 3.13)')
    config = Configuration(8, 1600000)
    settings = ProcessingSettings(acquisition=config, radio_enabled=True)
    rows = []
    with ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context('spawn')) as executor:
        for seconds in (.02, .04, .08, .16):
            count = int(config.actual_rate * seconds)
            indices = np.arange(count, dtype=np.uint32)
            columns = {'Muestra': indices, 'Tiempo (us)': indices.astype(float)*config.dt_us,
                       'CH1': 1.65 + .1*np.sin(indices * .37)}
            for name, selected in (('current', columns), ('ch1_only_lower_bound', {'CH1': columns['CH1']})):
                payload = SimpleNamespace(columns=selected, acquisition=config)
                result = measure(payload, settings, executor, args.repeats)
                rows.append(dict(samples=count, rf_seconds=seconds, variant=name, **result))
    folder = Path(__file__).resolve().parent/'resultados_v17'/datetime.now().strftime('radio_ipc_%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    source = Path(__file__).read_bytes()
    (folder/Path(__file__).name).write_bytes(source)
    report = dict(python=sys.version, numpy=np.__version__, repeats=args.repeats, rows=rows,
                  source_sha256=hashlib.sha256(source).hexdigest(),
                  limitations=['Offline, without GUI, receiver, DSP computation or Q.',
                                'Thread CPU is not GIL hold duration; roundtrip includes scheduling and pipe transport.',
                                'CH1-only omits mandatory continuity metadata: cost bound only, not a candidate implementation.',
                                'ProcessPool uses its actual ForkingPickler default protocol; no out-of-band buffers.',
                                'Variants run sequentially, current then lower bound; not an interleaved A/B qualification.'])
    (folder/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(folder/'report.json')
    for row in rows:
        print(row['samples'], row['variant'], row['bytes'], row['serialize_thread_cpu'], row['process_roundtrip_wall'])


if __name__ == '__main__':
    main()
