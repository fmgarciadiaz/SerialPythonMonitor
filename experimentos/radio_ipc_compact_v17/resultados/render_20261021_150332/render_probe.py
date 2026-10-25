"""Diagnostic FFT refresh ablation, independent of the compact codec.

No public UI change. Does not skip RF/audio batches or alter audio credits.
Uses the standard physical helper and its exclusive owner/restoration path.
"""
from datetime import datetime
from contextlib import ExitStack
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
    from monitor.v17.radio_output import RadioDacSource
    from monitor.v17 import spectral_analysis
    from experimentos.radio_ipc_compact_v17.adaptive_refresh import AdaptiveRefresh
    from diagnosticos.validar_generador_radio_v17 import main as validate
    hz = float(sys.argv[sys.argv.index('--probe-fft-hz')+1]) if '--probe-fft-hz' in sys.argv else 8.
    if hz != 0 and not 1 <= hz <= 60:
        raise ValueError('probe-fft-hz fuera de rango')
    adaptive = '--adaptive-refresh' in sys.argv
    stages = {}
    def measured(name, function):
        totals = stages[name] = dict(calls=0, thread_cpu_seconds=0., wall_seconds=0., max_wall_ms=0.)
        def call(*args, **kwargs):
            wall, cpu = time.perf_counter(), time.thread_time()
            totals['calls'] += 1
            try:
                return function(*args, **kwargs)
            finally:
                elapsed = time.perf_counter()-wall
                totals['thread_cpu_seconds'] += time.thread_time()-cpu
                totals['wall_seconds'] += elapsed
                totals['max_wall_ms'] = max(totals['max_wall_ms'],elapsed*1000)
        return call
    policy = AdaptiveRefresh()
    folder = Path(__file__).parent/'resultados'/datetime.now().strftime('render_%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    stats = dict(calls=0, skipped=0, executed=0, thread_cpu_seconds=0., wall_seconds=0., max_wall_ms=0.)
    original = SpectralDisplay.render
    original_ack = RadioDacSource.observe_transport

    def observe(source, stage, seconds):
        result = original_ack(source,stage,seconds)
        if adaptive and stage == 'send_to_ack':
            policy.observe_ack(source,seconds,time.monotonic())
        return result

    def render(view, single_owner=None):
        eligible = (single_owner is None and view.mode == 1
                    and not getattr(view.owner, 'single_shot_armed', False))
        now = time.monotonic()
        interval = 1/hz if hz else 0.
        if adaptive:
            worker = getattr(view.owner,'serial_worker',None)
            source = getattr(worker,'radio_output_source',None)
            if not (getattr(source,'radio_audio',False) and
                    not source.closed and not source.error):
                source = None
            interval = policy.interval(now,source,
                getattr(worker,'pending_batches',0),getattr(worker,'pending_dsp',0),eligible)
        if not eligible:
            return original(view, single_owner)
        stats['calls'] += 1
        if interval and now-getattr(view, '_probe_last_render', -1e9) < interval:
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
    policy_content = (Path(__file__).parent/'adaptive_refresh.py').read_bytes()
    (folder/'adaptive_refresh.py').write_bytes(policy_content)
    report = dict(ok=False, fft_hz=None if adaptive else hz, adaptive=adaptive, argv=sys.argv, stats=stats,
                  stages=stages,
                  policy_sha256=hashlib.sha256(policy_content).hexdigest(),
                  source_sha256=hashlib.sha256(content).hexdigest(),
                  limitation='Diagnostic refresh reduction, not a production fix or proof of GIL causality.')
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(SpectralDisplay,'render',render))
            stack.enter_context(patch.object(RadioDacSource,'observe_transport',observe))
            if '--stage-audit' in sys.argv:
                for target, attribute, name in ((SpectralDisplay,'_render_fft_analysis','analysis_pipeline'),
                        (SpectralDisplay,'_draw_fft_arrays','draw_submission'),
                        (spectral_analysis,'_fft','fft_numeric')):
                    stack.enter_context(patch.object(target,attribute,measured(name,getattr(target,attribute))))
                report['stage_limitation'] = 'Inclusive nested method timings; do not sum stages. Draw submission excludes later Qt painting. Counters span lifecycle.'
            physical, evidence = validate()
        report.update(ok=physical['ok'] and physical['restored'], physical_report=str(evidence/'report.json'))
    finally:
        if adaptive:
            policy.interval(time.monotonic(),None)
            report['policy'] = policy.snapshot(time.monotonic())
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('RENDER_REPORT',folder/'report.json',flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
