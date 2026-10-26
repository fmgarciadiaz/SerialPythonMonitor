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
import tempfile
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / 'arduino' / 'v18' / 'unoq.json'


def config_path(version):
    if version != "v18": raise ValueError("Only V18 is supported")
    for folder in (ROOT / 'arduino' / version,):
        path = folder / 'unoq.json'
        if path.is_file():
            return path
    raise FileNotFoundError(f'Versión Arduino desconocida: {version}')


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

    def compile(self, artifacts=None):
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
            if artifacts is not None:
                artifacts = Path(artifacts)
                artifacts.mkdir(parents=True, exist_ok=True)
                for name in ('sketch.ino.bin','sketch.ino_debug.elf','sketch.ino.elf','sketch.ino.map'):
                    self.run('pull',stage+'/build/'+name,str(artifacts/name))
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

    def stop(self):
        self.cli('app', 'stop', self.remote)
        boot = self.config.get('ready_boot')
        if boot:
            # PG13/MPU70 primero habilita el loader y luego pasa a READY SPI.
            # Mantener MCU en reset al cambiar la dirección del GPIO del MPU.
            self.shell('gpioset', '-c', boot['chip'], '-t0', f"{boot['reset_line']}=0")
            try:
                self.shell('gpioset', '-c', boot['chip'], '-t0', f"{boot['ready_line']}=1")
            finally:
                self.shell('gpioset', '-c', boot['chip'], '-t0', f"{boot['reset_line']}=1")

    def start(self):
        if self.config.get('ready_boot'):
            self.stop()
        self.cli('app', 'start', self.remote)

    def deploy(self):
        self.compile()
        self.backup()
        self.stop()
        self.push_sources(self.check_sources(), self.remote)
        self.start()
        print('Código transferido y aplicación iniciada con App CLI.')

    def create(self):
        """Importa una aplicación independiente sin arrancar ni cargar firmware."""
        files = self.check_sources()
        app_folder = self.remote.rsplit('/', 1)[-1]
        remote_zip = '/tmp/serialmonitor-import-' + uuid.uuid4().hex + '.zip'
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'app.zip'
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as out:
                for path in files:
                    out.write(path, app_folder + '/' + path.relative_to(self.local).as_posix())
            try:
                self.run('push', str(archive), remote_zip)
                self.cli('app', 'import', remote_zip)
            finally:
                self.shell('python3', '-c',
                           'import pathlib,sys; pathlib.Path(sys.argv[1]).unlink(missing_ok=True)', remote_zip)
        print('Aplicación importada. No se inició ni se cargó firmware.')

