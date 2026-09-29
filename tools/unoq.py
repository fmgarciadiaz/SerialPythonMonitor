#!/usr/bin/env python3
"""Desarrollo del UNO Q por USB usando las herramientas instaladas en la placa."""
import argparse
import ast
from datetime import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'arduino' / 'unoq.json'


def source_files(folder):
    excluded = {'.git', '.cache', '__pycache__', 'data', '.venv'}
    return sorted(p for p in folder.rglob('*') if p.is_file()
                  and not p.is_symlink()
                  and not any(part in excluded for part in p.relative_to(folder).parts)
                  and p.name != '.DS_Store' and p.suffix != '.pyc')


class Board:
    def __init__(self, config):
        self.config = config
        bundled = Path.home() / 'Library/Arduino15/packages/arduino/tools/adb'
        candidates = sorted(bundled.glob('*/adb')) if bundled.exists() else []
        self.adb = os.environ.get('UNOQ_ADB') or shutil.which('adb') or (str(candidates[-1]) if candidates else None)
        if not self.adb:
            raise RuntimeError('No se encontró ADB. Definí UNOQ_ADB con la ruta del ejecutable.')
        self.serial = os.environ.get('UNOQ_SERIAL', config['serial'])
        self.remote = config['remote_app']
        self.local = ROOT / config['local_app']

    def run(self, *args, capture=False):
        return subprocess.run([self.adb, '-s', self.serial, *args], check=True,
                              text=True, stdout=subprocess.PIPE if capture else None)

    def shell(self, *args, capture=False):
        return self.run('shell', shlex.join(str(a) for a in args), capture=capture)

    def cli(self, *args, capture=False):
        return self.shell('arduino-app-cli', *args, capture=capture)

    def status(self):
        self.run('get-state')
        self.cli('version')
        result = json.loads(self.cli('app', 'list', '--format', 'json', capture=True).stdout)
        matches = [app for app in result.get('apps', []) if app.get('name') == self.config['name']]
        if not matches:
            raise RuntimeError('La aplicación configurada no figura en la placa.')
        print(json.dumps(matches, ensure_ascii=False, indent=2))

    def check_sources(self):
        for relative in ('app.yaml', 'python/main.py', 'sketch/sketch.ino', 'sketch/sketch.yaml'):
            if not (self.local / relative).is_file():
                raise RuntimeError(f'Falta {self.local / relative}')
        files = source_files(self.local)
        for path in files:
            if path.suffix == '.py':
                ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        return files

    def push_sources(self, files, destination):
        for path in files:
            target = destination + '/' + path.relative_to(self.local).as_posix()
            self.shell('mkdir', '-p', target.rsplit('/', 1)[0])
            self.run('push', str(path), target)

    def compile(self):
        files = self.check_sources()
        stage = '/tmp/serialmonitor-build-' + uuid.uuid4().hex
        try:
            self.push_sources(files, stage)
            # Validar con el Python de destino, sin importar App ni ejecutar main.py.
            self.shell('python3', '-c',
                       'import ast,pathlib,sys; root=pathlib.Path(sys.argv[1]); '
                       '[ast.parse(p.read_text(), filename=str(p)) for p in root.rglob("*.py")]', stage)
            self.shell('arduino-cli', 'compile', '--fqbn', self.config['fqbn'],
                       '--profile', 'default', '--build-path', stage + '/build', stage + '/sketch')
        finally:
            # Sólo eliminar la carpeta temporal creada por esta invocación.
            self.shell('python3', '-c',
                       'import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)', stage)
        print('Python validado y sketch compilado. No se cargó firmware.')

    def backup(self):
        folder = ROOT / 'respaldos' / 'unoq'
        folder.mkdir(parents=True, exist_ok=True)
        name = 'osciloscopio_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.zip'
        temporary = '/tmp/' + name
        try:
            self.cli('app', 'export', self.remote, temporary)
            self.run('pull', temporary, str(folder / name))
        finally:
            self.shell('python3', '-c', 'import pathlib,sys; pathlib.Path(sys.argv[1]).unlink(missing_ok=True)', temporary)
        print(f'Respaldo: {folder / name}')
        return folder / name

    def deploy(self):
        self.compile()
        self.backup()
        self.cli('app', 'stop', self.remote)
        self.push_sources(self.check_sources(), self.remote)
        self.cli('app', 'start', self.remote)
        print('Código transferido y aplicación iniciada con App CLI.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('status', 'compile', 'backup', 'deploy', 'start', 'stop', 'logs'))
    parser.add_argument('--follow', action='store_true', help='Seguir logs hasta Ctrl+C')
    args = parser.parse_args()
    try:
        board = Board(json.loads(CONFIG.read_text()))
        if args.command == 'logs':
            opts = ['--follow'] if args.follow else ['--tail', '50']
            board.cli('app', 'logs', board.remote, *opts)
        elif args.command in ('start', 'stop'):
            board.cli('app', args.command, board.remote)
        else:
            getattr(board, args.command)()
    except (OSError, RuntimeError, SyntaxError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
