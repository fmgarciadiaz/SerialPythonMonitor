#!/usr/bin/env python3
"""Install the selected monitor stack on the selected UNO Q."""
import argparse
import json
import os
import subprocess
import sys
from unoq import Board, config_path
from usb_stream import binary, stop


def prepare(serial, firmware='v12_audio'):
    os.environ['UNOQ_SERIAL'] = serial
    board = Board(json.loads(config_path(firmware).read_text()))
    print('Comprobando Q y aplicaciones…', flush=True)
    board.run('get-state')
    apps = json.loads(board.cli('app', 'list', '--format', 'json', capture=True).stdout).get('apps', [])
    compatible = {'Scope WAV V12 Audio':'v12_audio','Scope Pulse US V13 Experimental':'v13_pulse'}
    if any(a.get('status') == 'running' and a.get('name') != board.config['name'] and a.get('name') not in compatible for a in apps):
        raise RuntimeError('Hay otra aplicación activa en el Q; detenerla antes de preparar el monitor.')
    existing = any(a.get('name') == board.config['name'] for a in apps)
    print('Validando y compilando firmware MCU…', flush=True)
    board.compile()
    if existing:
        print('Guardando respaldo de la aplicación instalada…', flush=True)
        board.backup()
    for app in apps:
        if app.get('status') == 'running' and app.get('name') != board.config['name']:
            print('Deteniendo la aplicación anterior del monitor…', flush=True)
            previous = Board(json.loads(config_path(compatible[app['name']]).read_text()))
            previous.stop()
    print('Comprobando relay compilado en el Q…', flush=True)
    try:
        binary(board, p992=True, audio=True)
        print('Reutilizando relay: las fuentes no cambiaron.', flush=True)
    except subprocess.CalledProcessError:
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
    subprocess.run([sys.executable, str(config_path(firmware).parents[2] / 'tools' / 'usb_stream.py'),
                    'start', '--firmware', firmware], check=True)
    print('Q preparado: MCU, app y relay activos.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--firmware', choices=('v12_audio','v13_pulse'), default='v12_audio')
    args = parser.parse_args()
    try:
        prepare(args.serial,args.firmware)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
