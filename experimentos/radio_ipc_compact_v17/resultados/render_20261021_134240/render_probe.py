"""Diagnostic FFT refresh ablation, independent of the compact codec.

No public UI change. Does not skip RF/audio batches or alter audio credits.
Uses the standard physical helper and its exclusive owner/restoration path.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    from monitor.v17.qt_environment import prepare_platform_plugins
    prepare_platform_plugins()
    from monitor.v17.spectrum import SpectralDisplay
    from diagnosticos.validar_generador_radio_v17 import main as validate
    hz = float(sys.argv[sys.argv.index('--probe-fft-hz')+1]) if '--probe-fft-hz' in sys.argv else 8.
    if hz != 0 and not 1 <= hz <= 60:
        raise ValueError('probe-fft-hz fuera de rango')
    folder = Path(__file__).parent/'resultados'/datetime.now().strftime('render_%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    stats = dict(calls=0, skipped=0, executed=0, thread_cpu_seconds=0., wall_seconds=0., max_wall_ms=0.)
    original = SpectralDisplay.render

    def render(view, single_owner=None):
        eligible = (single_owner is None and view.mode == 1
                    and not getattr(view.owner, 'single_shot_armed', False))
        if not eligible:
            return original(view, single_owner)
        stats['calls'] += 1
        now = time.monotonic()
        if hz and now-getattr(view, '_probe_last_render', -1e9) < 1/hz:
            stats['skipped'] += 1
            return
        view._probe_last_render = now
        stats['executed'] += 1
        wall, cpu = time.perf_counter(), time.thread_time()
        try:
            return original(view, single_owner)
        finally:
            elapsed = time.perf_counter()-wall
            stats['thread_cpu_seconds'] += time.thread_time()-cpu
            stats['wall_seconds'] += elapsed
            stats['max_wall_ms'] = max(stats['max_wall_ms'], elapsed*1000)

    content = Path(__file__).read_bytes()
    (folder/Path(__file__).name).write_bytes(content)
    report = dict(ok=False, fft_hz=hz, argv=sys.argv, stats=stats,
                  source_sha256=hashlib.sha256(content).hexdigest(),
                  limitation='Diagnostic refresh reduction, not a production fix or proof of GIL causality.')
    try:
        with patch.object(SpectralDisplay, 'render', render):
            physical, evidence = validate()
        report.update(ok=physical['ok'] and physical['restored'], physical_report=str(evidence/'report.json'))
    finally:
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('RENDER_REPORT',folder/'report.json',flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
