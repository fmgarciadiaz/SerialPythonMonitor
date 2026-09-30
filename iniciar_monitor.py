#!/usr/bin/env python3
"""Abre el monitor estable por defecto; V7 se elige explícitamente."""
import argparse
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent
MONITORS = {
    'v6': ('estable · firmware V4 · USB 2.000.000', ROOT / 'monitor/v6/app.py'),
    'v7': ('experimental · firmware V5 · USB 3.000.000', ROOT / 'monitor/v7/app.py'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=MONITORS, default='v6')
    parser.add_argument('--list', action='store_true', help='listar sin abrir Qt')
    args = parser.parse_args()
    if args.list:
        for version, (label, path) in MONITORS.items():
            print(f'{version}: {label} — {path.relative_to(ROOT)}')
        return
    label, path = MONITORS[args.version]
    print(f'SerialMonitor {args.version}: {label}', flush=True)
    runpy.run_path(str(path), run_name='__main__')


if __name__ == '__main__':
    main()
