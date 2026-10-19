#!/usr/bin/env python3
"""Install the selected monitor stack on the selected UNO Q."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from unoq import Board, config_path
from usb_stream import binary, stop


def prepare(serial, firmware='v16'):
    os.environ['UNOQ_SERIAL'] = serial
    board = Board(json.loads(config_path(firmware).read_text()))
    print('Comprobando Q y aplicaciones…', flush=True)
    board.run('get-state')
    apps = json.loads(board.cli('app', 'list', '--format', 'json', capture=True).stdout).get('apps', [])
    compatible = {'Scope V17':'v17','Scope V16':'v16','Scope WAV V12 Audio':'v12_audio','Scope Pulse US V13 Experimental':'v13_pulse','Scope Acquisition P992 V11':'v11_p992'}
    if any(a.get('status') == 'running' and a.get('name') != board.config['name'] and a.get('name') not in compatible for a in apps):
        raise RuntimeError('Hay otra aplicación activa en el Q; detenerla antes de preparar el monitor.')
    existing = any(a.get('name') == board.config['name'] for a in apps)
    print('Validando y compilando firmware MCU…', flush=True)
    board.compile()
    backup = None
    if existing:
        print('Guardando respaldo de la aplicación instalada…', flush=True)
        backup = board.backup()
    print('Comprobando relay compilado en el Q…', flush=True)
    try:
        binary(board, p992=True, audio=True)
        print('Reutilizando relay: las fuentes no cambiaron.', flush=True)
    except subprocess.CalledProcessError:
        print('Compilando relay en el Q…', flush=True)
        binary(board, build=True, p992=True, audio=True)
    try:
        # Release READY ownership before Board.stop reconfigures its GPIO.
        stop(board)
        for app in apps:
            if app.get('status') == 'running' and app.get('name') != board.config['name']:
                print('Deteniendo la aplicación anterior del monitor…', flush=True)
                previous = Board(json.loads(config_path(compatible[app['name']]).read_text()))
                previous.stop()
        if existing:
            print('Actualizando app y firmware MCU…', flush=True)
            board.stop()
            board.push_sources(board.check_sources(), board.remote)
        else:
            print('Instalando app y firmware MCU…', flush=True)
            board.create()
        print('Cargando MCU y comprobando relay…', flush=True)
        subprocess.run([sys.executable, str(Path(__file__).resolve().with_name('usb_stream.py')),
                        'start', '--firmware', firmware], check=True, timeout=600)
    except Exception:
        print('Preparación incompleta: estado de MCU/app/relay sin confirmar.', flush=True)
        if backup: print(f'Respaldo recuperable: {backup}', flush=True)
        print('Mantener el Q conectado, revisar el log y volver a Preparar Q antes de usar la salida.', flush=True)
        raise
    print('Q preparado: MCU, app y relay activos.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--firmware', choices=('v12_audio','v13_pulse','v16', 'v17'), default='v16')
    args = parser.parse_args()
    try:
        prepare(args.serial,args.firmware)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
