"""Isolated physical runner; forwards normal RADIO validation CLI flags.

Default observes batch sizes only. --compact-ipc enables lossless metadata
packing for batches >=128000 samples. All ownership/restoration stays with
the existing validation helper. No public code or Q firmware is modified.
"""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    from monitor.v17.qt_environment import prepare_platform_plugins
    prepare_platform_plugins()
    from monitor.v17 import app
    from diagnosticos.validar_generador_radio_v17 import main as validate
    from experimentos.radio_ipc_compact_v17.codec import compact, RegularRadioBatch, process_compact
    enabled = '--compact-ipc' in sys.argv
    minimum = int(sys.argv[sys.argv.index('--compact-min-samples')+1]) if '--compact-min-samples' in sys.argv else 128000
    if minimum < 1:
        raise ValueError('compact-min-samples debe ser positivo')
    folder = Path(__file__).parent/'resultados'/datetime.now().strftime('physical_%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    stats = dict(enabled=enabled, minimum_samples=minimum, batches=0, compacted=0,
                 fallback=0, max_samples=0, pack_cpu_seconds=0., pack_wall_seconds=0.)
    histogram = Counter()
    original = app.OutputWorker._process_separately

    def process(worker, batch, settings):
        size = len(batch.columns['CH1'])
        stats['batches'] += 1
        stats['max_samples'] = max(stats['max_samples'], size)
        # Fixed histogram bins: no unbounded per-batch trace.
        histogram[next((limit for limit in (32000,64000,128000,256000,512000,1600000) if size <= limit), 'larger')] += 1
        if not enabled or size < stats['minimum_samples']:
            return original(worker, batch, settings)
        worker._ensure_process().result()
        required = {'Muestra','Tiempo (us)'}
        if settings.radio_enabled: required.add('CH1')
        if settings.filter.source in ('CH1','CH2'): required.add(settings.filter.source)
        payload = SimpleNamespace(columns={k:v for k,v in batch.columns.items() if k in required},
                                  acquisition=getattr(batch,'acquisition',settings.acquisition))
        wall, cpu = time.perf_counter(), time.thread_time()
        payload = compact(payload, settings)
        stats['pack_cpu_seconds'] += time.thread_time()-cpu
        stats['pack_wall_seconds'] += time.perf_counter()-wall
        stats['compacted' if isinstance(payload, RegularRadioBatch) else 'fallback'] += 1
        batch.processing, filtered = worker._processing_process.submit(process_compact,payload,settings).result()
        if filtered is None: batch.columns.pop('FILTER',None)
        else: batch.columns['FILTER'] = filtered
        return batch

    report = dict(ok=False, argv=sys.argv, stats=stats)
    for name in ('codec.py','run.py'):
        content = (Path(__file__).parent/name).read_bytes()
        (folder/name).write_bytes(content)
        report.setdefault('source_hashes',{})[name] = hashlib.sha256(content).hexdigest()
    try:
        with patch.object(app.OutputWorker, '_process_separately', process):
            physical, evidence = validate()
        report.update(ok=physical['ok'] and physical['restored'], physical_report=str(evidence/'report.json'))
    finally:
        stats['size_upper_bound_histogram'] = dict(histogram)
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('IPC_REPORT', folder/'report.json', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
