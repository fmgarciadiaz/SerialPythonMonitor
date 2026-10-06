#!/usr/bin/env python3
"""Install the monitor's complete V12 Audio stack on the selected UNO Q."""
import argparse
import json
import os
import subprocess
import sys
from unoq import Board, config_path
from usb_stream import binary, stop


def prepare(serial):
    os.environ['UNOQ_SERIAL'] = serial
    board = Board(json.loads(config_path('v12_audio').read_text()))
    print('Comprobando Q y aplicaciones…', flush=True)
    board.run('get-state')
    apps = json.loads(board.cli('app', 'list', '--format', 'json', capture=True).stdout).get('apps', [])
    if any(a.get('status') == 'running' and a.get('name') != board.config['name'] for a in apps):
        raise RuntimeError('Hay otra aplicación activa en el Q; detenerla antes de preparar el monitor.')
    existing = any(a.get('name') == board.config['name'] for a in apps)
    print('Validando y compilando firmware MCU…', flush=True)
    board.compile()
    if existing:
        print('Guardando respaldo de la aplicación instalada…', flush=True)
        board.backup()
    print('Compilando relay en el Q…', flush=True)
    binary(board, build=True, p992=True, audio=True)
    stop(board)
    if existing:
        print('Actualizando app y firmware MCU…', flush=True)
        board.stop()
        board.push_sources(board.check_sources(), board.remote)
    else:
        print('Instalando app y firmware MCU…', flush=True)
        board.create()
    print('Cargando MCU y comprobando relay…', flush=True)
    subprocess.run([sys.executable, str(config_path('v12_audio').parents[2] / 'tools' / 'usb_stream.py'),
                    'start', '--firmware', 'v12_audio'], check=True)
    print('Q preparado: MCU, app y relay activos.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    args = parser.parse_args()
    try:
        prepare(args.serial)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
