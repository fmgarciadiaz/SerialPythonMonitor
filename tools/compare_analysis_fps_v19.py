#!/usr/bin/env python3
"""Measure installed V19 visible FPS; optionally compare with an archived V18 report."""
import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.validate_v19 import run_case
MODES = [('vt', 'Spectre', 86, None), ('fft', 'Spectre', 86, None),
         ('fft', 'Power', 86, None), ('fft', 'Distort', 86, None),
         ('fft', 'Transfer', 253, None), ('fft', 'Radio', 86, None),
         ('heatmap', 'Spectre', 253, None), ('bode', 'Spectre', 86, 0),
         ('bode', 'Spectre', 86, 1), ('bode', 'Spectre', 86, 2),
         ('vt', 'Spectre', 86, None, 4)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default='1060031107')
    parser.add_argument('--bits', type=int, default=8)
    parser.add_argument('--ticks', type=int, default=86)
    parser.add_argument('--hold', type=int, default=20)
    parser.add_argument('--keep-display-awake', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--reference-report',type=Path,
                        help='Archived comparison report; never starts a historical monitor')
    args = parser.parse_args()
    if not 5 <= args.hold <= 120:
        parser.error('--hold must be between 5 and 120 seconds')
    folder = args.output or ROOT / 'diagnosticos/resultados_v19' / time.strftime('fps_compare_%Y%m%d_%H%M%S')
    folder.mkdir(parents=True, exist_ok=True)
    report = dict(ok=False, firmware_deployment=False, profile=dict(bits=args.bits, ticks=args.ticks),
                  hold_seconds=args.hold, cases=[])
    report_path = folder / 'report.json'
    references=[]
    if args.reference_report:
        references=[row for row in json.loads(args.reference_report.read_text()).get('cases',[])
                    if row.get('version')=='v18']
        report['reference_report']=str(args.reference_report)

    def save():
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')

    save()
    for mode_spec in MODES:
        mode, fft_view, ticks, *extra = mode_spec
        bode_method = extra[0] if extra else None
        window_seconds = extra[1] if len(extra)>1 else 0
        for version in ('v19',):
            suffix=f'_bode{bode_method}' if bode_method is not None else ''
            suffix += f'_window{window_seconds}s' if window_seconds else ''
            name = f'{version}_{mode}_{fft_view.lower()}{suffix}'
            command = [sys.executable, str(ROOT / f'tools/probe_radio_rate_{version}.py'),
                       '--serial', args.serial, '--bits', str(args.bits), '--ticks', str(ticks),
                       '--hold', str(args.hold), '--frequency-khz', '400',
                       '--analysis-mode', mode, '--fft-view', fft_view, '--fft-size', '16384']
            if bode_method is not None:
                command += ['--bode-method', str(bode_method)]
            if window_seconds:
                command += ['--window-seconds', str(window_seconds)]
            if args.keep_display_awake:
                command.append('--keep-display-awake')
            print('START', name, flush=True)
            log_path = folder / f'{name}.log'
            try:
                with log_path.open('w') as log:
                    exit_code=run_case(command,log,args.hold+180)
            except Exception as exc:
                report['cases'].append(dict(name=name,ok=False,error=str(exc)));save();return 1
            lines = log_path.read_text(errors='replace').splitlines()
            run_folder = next((Path(line) for line in lines if line.startswith(str(ROOT / 'diagnosticos'))), None)
            evidence = json.loads((run_folder / 'report.json').read_text()) if run_folder else {}
            periodic = evidence.get('paint_fps', [])
            row = dict(name=name, version=version, mode=mode, fft_view=fft_view,
                       command=command, log=str(log_path), evidence=str(run_folder) if run_folder else None,
                       exit_code=exit_code, ok=bool(exit_code == 0 and evidence.get('ok')),
                       fps_samples=periodic,
                       mean_paint_fps=(sum(periodic) / len(periodic) if periodic else None),
                       median_paint_fps=(statistics.median(periodic) if periodic else None),
                       p95_paint_fps=(sorted(periodic)[min(len(periodic)-1, int(.95*len(periodic)))] if periodic else None),
                       synthetic_bode_updates=evidence.get('synthetic_bode_updates'),
                       exposed_fraction=evidence.get('exposed_fraction'),
                       restored=bool(evidence.get('restoration', {}).get('hardware_restored')))
            report['cases'].append(row)
            save()
            print('RESULT', json.dumps(row, ensure_ascii=False), flush=True)
            if not row['ok']:
                print('STOP: failed case; inspect evidence and restoration before continuing.', flush=True)
                return 1
    by_mode = {}
    for mode_spec in MODES:
        mode, fft_view, _ticks, *extra = mode_spec
        bode_method = extra[0] if extra else None
        window_seconds = extra[1] if len(extra)>1 else 0
        suffix=f'_bode{bode_method}' if bode_method is not None else ''
        suffix += f'_window{window_seconds}s' if window_seconds else ''
        key = f'{mode}_{fft_view.lower()}{suffix}'
        pair = {row['version']: row['median_paint_fps'] for row in references+report['cases'] if row['name'].endswith(key)}
        if pair.get('v18') is not None and pair.get('v19') is not None:
            base, candidate = pair['v18'], pair['v19']
            by_mode[key] = dict(metric='median visible paint FPS',v18_fps=base, v19_fps=candidate,
                                difference_fps=candidate-base,
                                difference_percent=(100*(candidate-base)/base if base else None))
    report['comparison'] = by_mode
    report['ok'] = len(report['cases']) == len(MODES) and all(row['ok'] for row in report['cases'])
    save()
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
