#!/usr/bin/env python3
"""Desarrollo del UNO Q por USB usando las herramientas instaladas en la placa."""
import argparse
import ast
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONFIG = ROOT / 'arduino' / 'v19' / 'unoq.json'


def config_path(version):
    for folder in (ROOT / 'arduino' / version, ROOT / 'arduino' / 'historico' / version):
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


V19_SERIALS_VARIANT_PATCH = r'''import pathlib,shutil,sys
src,dst=sys.argv[1:]
shutil.copytree(src,dst,symlinks=True)
(pathlib.Path(dst).parent/'common').symlink_to(pathlib.Path(src).parent/'common',target_is_directory=True)
header=pathlib.Path(dst)/'llext-edk/include/zephyr/include/generated/zephyr/devicetree_generated.h'
text=header.read_text()
start=text.index('#define DT_N_S_zephyr_user_P_serials_IDX_0 ')
end=text.index('#define DT_N_S_zephyr_user_P_cans ',start)
block='\n'.join([
'#define DT_N_S_zephyr_user_P_serials_IDX_0 DT_N_S_soc_S_serial_40013800',
'#define DT_N_S_zephyr_user_P_serials_IDX_0_PH DT_N_S_soc_S_serial_40013800',
'#define DT_N_S_zephyr_user_P_serials_IDX_0_EXISTS 1',
'#define DT_N_S_zephyr_user_P_serials_IDX_1 DT_N_S_soc_S_serial_46002400',
'#define DT_N_S_zephyr_user_P_serials_IDX_1_PH DT_N_S_soc_S_serial_46002400',
'#define DT_N_S_zephyr_user_P_serials_IDX_1_EXISTS 1',
'#define DT_N_S_zephyr_user_P_serials_FOREACH_PROP_ELEM(fn) fn(DT_N_S_zephyr_user, serials, 0) \\\n\tfn(DT_N_S_zephyr_user, serials, 1)',
'#define DT_N_S_zephyr_user_P_serials_FOREACH_PROP_ELEM_SEP(fn, sep) fn(DT_N_S_zephyr_user, serials, 0) DT_DEBRACKET_INTERNAL sep \\\n\tfn(DT_N_S_zephyr_user, serials, 1)',
'#define DT_N_S_zephyr_user_P_serials_FOREACH_PROP_ELEM_VARGS(fn, ...) fn(DT_N_S_zephyr_user, serials, 0, __VA_ARGS__) \\\n\tfn(DT_N_S_zephyr_user, serials, 1, __VA_ARGS__)',
'#define DT_N_S_zephyr_user_P_serials_FOREACH_PROP_ELEM_SEP_VARGS(fn, sep, ...) fn(DT_N_S_zephyr_user, serials, 0, __VA_ARGS__) DT_DEBRACKET_INTERNAL sep \\\n\tfn(DT_N_S_zephyr_user, serials, 1, __VA_ARGS__)',
'#define DT_N_S_zephyr_user_P_serials_LEN 2',
'#define DT_N_S_zephyr_user_P_serials_EXISTS 1',
])+'\n'
header.write_text(text[:start]+block+text[end:])
overlay=pathlib.Path(dst)/'arduino_uno_q_stm32u585xx.overlay'
text=overlay.read_text()
old='serials = <&usart1>, <&lpuart1>, <&usart3>;'
if old not in text:
    raise SystemExit('Unexpected UNO Q serials list; refusing variant override')
overlay.write_text(text.replace(old,'serials = <&usart1>, <&lpuart1>;'))
print('Prepared isolated V19 variant: USART1 + LPUART1, USART3 omitted')
'''

V19_STACK_DIAGNOSTIC_PATCH = r'''import hashlib,json,pathlib,sys
sketch_path,variant_path=sys.argv[1:]
sketch=pathlib.Path(sketch_path)
text=sketch.read_text()
if '#define SCOPE_STACK_DIAGNOSTICS 1' in text:
    raise SystemExit('Stack diagnostic marker already exists')
if '#include "acquisition.h"' not in text:
    raise SystemExit('Unexpected V19 sketch layout')
sketch.write_text('#define SCOPE_STACK_DIAGNOSTICS 1\n'+text)
conf=pathlib.Path(variant_path)/'arduino_uno_q_stm32u585xx.conf'
config=conf.read_text()
if 'CONFIG_THREAD_STACK_INFO=y' not in config:
    raise SystemExit('The UNO Q variant does not expose thread stack metadata')
print(json.dumps({'patched_sketch_sha256':hashlib.sha256(sketch.read_bytes()).hexdigest(),
                  'variant_conf_sha256':hashlib.sha256(conf.read_bytes()).hexdigest()}))
'''


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

    def run(self, *args, capture=False, merge_stderr=False):
        return subprocess.run([self.adb, '-s', self.serial, *args], check=True,
                              text=True, stdout=subprocess.PIPE if capture else None,
                              stderr=subprocess.STDOUT if capture and merge_stderr else None)

    def shell(self, *args, capture=False, merge_stderr=False):
        return self.run('shell', shlex.join(str(a) for a in args), capture=capture,
                        merge_stderr=merge_stderr)

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

    def inventory(self):
        """Show app/relay state for every supported Scope pair without mutation."""
        from monitor.v19.board_owner import board_owner
        with board_owner(self.serial, 'read-only app/relay inventory'):
            self.run('get-state', capture=True)
            listing = json.loads(self.cli('app', 'list', '--format', 'json', capture=True).stdout)
            apps = listing.get('apps', [])
            all_containers = set(self.shell('docker', 'ps', '-a', '--format', '{{.Names}}', capture=True).stdout.splitlines())
            running_containers = set(self.shell('docker', 'ps', '--format', '{{.Names}}', capture=True).stdout.splitlines())
            pairs = []
            active_components = []
            for version in ('v17', 'v18', 'v19', 'v20'):
                config = json.loads(config_path(version).read_text(encoding='utf-8'))
                app = next((row for row in apps if row.get('name') == config['name']), None)
                app_status = app.get('status', 'unknown') if app else 'absent'
                app_container = f"scope-{version}-main-1"
                app_container_status = ('running' if app_container in running_containers else
                                        'stopped' if app_container in all_containers else 'absent')
                relay_name = config['container']
                relay_status = ('running' if relay_name in running_containers else
                                'stopped' if relay_name in all_containers else 'absent')
                coherent = (app_status == 'running' and app_container_status == 'running'
                            and relay_status == 'running')
                if app_status == 'running':
                    active_components.append(f'{version}:app')
                if app_container_status == 'running':
                    active_components.append(f'{version}:app_container')
                if relay_status == 'running':
                    active_components.append(f'{version}:relay')
                pairs.append(dict(version=version, app=config['name'], app_status=app_status,
                                  app_container=app_container,
                                  app_container_status=app_container_status,
                                  relay=relay_name, relay_status=relay_status,
                                  coherent_active_pair=coherent))
            running_apps = [row.get('name') for row in apps if row.get('status') == 'running']
            known_containers = {row['app_container'] for row in pairs} | {row['relay'] for row in pairs}
            unpaired_running = sorted(running_containers - known_containers)
            coherent_versions = [row['version'] for row in pairs if row['coherent_active_pair']]
            result = dict(board_serial=self.serial, pairs=pairs,
                          active_components=active_components,
                          coherent_active_pair_versions=coherent_versions,
                          exactly_one_coherent_pair=(len(coherent_versions) == 1 and
                                                     len(active_components) == 3 and
                                                     not [row for row in apps
                                                          if row.get('status') == 'running'
                                                          and row.get('name') not in {p['app'] for p in pairs}] and
                                                     not unpaired_running),
                          other_running_apps=[name for name in running_apps
                                              if name not in {row['app'] for row in pairs}],
                          unpaired_running_containers=unpaired_running,
                          retained_saved_relays=sorted(name for name in all_containers
                                                       if name.startswith('serialmonitor-usb-stream-')
                                                       and '-saved-' in name))
            print(json.dumps(result, ensure_ascii=False, indent=2))

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

    def _v19_variant_source(self):
        if self.config.get('name') != 'Scope V19':
            raise RuntimeError('La variante diagnóstica sólo se permite para Scope V19.')
        sketch_yaml = (self.local / 'sketch/sketch.yaml').read_text(encoding='utf-8')
        match = re.search(r'platform: arduino:zephyr \(([^)]+)\)', sketch_yaml)
        if not match:
            raise RuntimeError('No se pudo leer la versión de Arduino Core de V19.')
        data_dir = self.shell('arduino-cli', 'config', 'get', 'directories.data', capture=True).stdout.strip()
        return (Path(data_dir) / 'packages/arduino/hardware/zephyr' / match.group(1) /
                'variants/arduino_uno_q_stm32u585xx').as_posix()

    def _v19_serial_variant(self, stage):
        source = self._v19_variant_source()
        destination = stage + '/v19-variant-serial3-off'
        self.shell('python3', '-c', V19_SERIALS_VARIANT_PATCH, source, destination)
        return destination

    @staticmethod
    def _serial_variant_metadata():
        return {'kind': 'temporary UNO Q variant copy',
                'base_variant': 'arduino_uno_q_stm32u585xx',
                'serials_property_before': ['usart1', 'lpuart1', 'usart3'],
                'serials_property_after': ['usart1', 'lpuart1'],
                'omitted': ['usart3'],
                'reason': 'Keep Serial1 UART fallback and Serial2 for RouterBridge; omit unused Serial3',
                'original_variant_unchanged': True,
                'hardware_tested': False,
                'not_installed': True}

    def _v19_stack_diagnostic(self, stage, variant_path):
        result = self.shell('python3', '-c', V19_STACK_DIAGNOSTIC_PATCH,
                            stage + '/sketch/sketch.ino', variant_path,
                            capture=True).stdout.strip()
        try:
            metadata = json.loads(result)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f'No se pudo verificar el parche diagnóstico: {result}') from exc
        metadata.update({'config': 'existing CONFIG_THREAD_STACK_INFO=y',
                         'method': 'fill stack storage with 0xA5 before thread creation; scan intact prefix',
                         'sample_period_ms': 250,
                         'reported_values': ['producer_stack_free_bytes', 'output_stack_free_bytes'],
                         'frame_kind': 21, 'candidate_only': True, 'not_installed': True,
                         'variant': 'serial3-off' if variant_path != self._v19_variant_source()
                                    else 'UNO Q default'})
        return metadata

    def compile(self, artifacts=None, omit_serial3=False):
        if omit_serial3 and self.config.get('name') != 'Scope V19':
            raise RuntimeError('--omit-serial3 sólo se permite para Scope V19.')
        if self.config.get('name') == 'Scope V19':
            self.run('get-state')
            listing = json.loads(self.cli('app', 'list', '--format', 'json', capture=True).stdout)
            active_apps = [app.get('name') for app in listing.get('apps', [])
                           if app.get('status') == 'running']
            active_containers = self.shell('docker', 'ps', '--format', '{{.Names}}', capture=True).stdout.splitlines()
            if active_apps or any(name.startswith('scope-') and name.endswith('-main-1')
                                  or name.startswith('serialmonitor-usb-stream')
                                  for name in active_containers):
                raise RuntimeError('No compilo Scope V19 mientras haya una app o relay activo en el Q.')
        files = self.check_sources()
        stage = '/tmp/serialmonitor-build-' + uuid.uuid4().hex
        try:
            self.push_sources(files, stage)
            # Validar con el Python de destino, sin importar App ni ejecutar main.py.
            self.shell('python3', '-c',
                       'import ast,pathlib,sys; root=pathlib.Path(sys.argv[1]); '
                       '[ast.parse(p.read_text(), filename=str(p)) for p in root.rglob("*.py")]', stage)
            compile_args = ['arduino-cli', 'compile', '--fqbn', self.config['fqbn'],
                            '--profile', 'default', '--build-path', stage + '/build']
            if omit_serial3:
                variant_path = self._v19_serial_variant(stage)
                compile_args += ['--build-property', f'build.variant.path={variant_path}']
            compile_args.append(stage + '/sketch')
            self.shell(*compile_args)
            if artifacts is not None:
                artifacts = Path(artifacts)
                artifacts.mkdir(parents=True, exist_ok=True)
                for name in ('sketch.ino.bin','sketch.ino_debug.elf','sketch.ino.elf','sketch.ino.map'):
                    self.run('pull',stage+'/build/'+name,str(artifacts/name))
                if omit_serial3:
                    (artifacts / 'v19-variant-override.json').write_text(
                        json.dumps(self._serial_variant_metadata(), indent=2, ensure_ascii=False) + '\n',
                        encoding='utf-8')
        finally:
            # Sólo eliminar la carpeta temporal creada por esta invocación.
            self.shell('python3', '-c',
                       'import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)', stage)
        print('Python validado y sketch compilado. No se cargó firmware.')

    def compile_pair(self, artifacts, omit_serial3=False, stack_diagnostic=False):
        """Build the V19 STM32 firmware and Linux relay together; never install either."""
        if self.config.get('name') != 'Scope V19':
            raise RuntimeError('compile-pair sólo está definido para Scope V19.')
        from monitor.v19.board_owner import board_owner
        app_files = self.check_sources()
        relay_folder = ROOT / 'arduino/v19/relay'
        relay_files = source_files(relay_folder)
        main_c = relay_folder / 'unoq_config_stream.c'
        if main_c not in relay_files:
            raise RuntimeError('Falta el punto de entrada arduino/v19/relay/unoq_config_stream.c')
        artifacts = Path(artifacts).expanduser().resolve()
        if any(folder == artifacts or folder in artifacts.parents
               for folder in (ROOT / 'arduino/v19', ROOT / 'monitor/v19')):
            raise RuntimeError('Los artefactos no se guardan dentro de las fuentes V19.')
        stage = '/tmp/scope-v19-pair-build-' + uuid.uuid4().hex
        with board_owner(self.serial, 'Scope V19 paired build'):
            self.run('get-state')
            listing = json.loads(self.cli('app', 'list', '--format', 'json', capture=True).stdout)
            active_apps = [app.get('name') for app in listing.get('apps', [])
                           if app.get('status') == 'running']
            active_containers = self.shell('docker', 'ps', '--format', '{{.Names}}', capture=True).stdout.splitlines()
            if active_apps or active_containers:
                raise RuntimeError('Compilación V19 requiere todas las apps y contenedores del Q detenidos.')
            try:
                for folder, files in ((self.local, app_files), (relay_folder, relay_files)):
                    for path in files:
                        target = stage + '/' + ('app/' if folder == self.local else 'relay/') + path.relative_to(folder).as_posix()
                        self.shell('mkdir', '-p', target.rsplit('/', 1)[0])
                        self.run('push', str(path), target)
                compile_args = ['arduino-cli', 'compile', '--fqbn', self.config['fqbn'],
                                '--profile', 'default', '--build-path', stage + '/app/build']
                stack_metadata = None
                variant_path = None
                if omit_serial3:
                    variant_path = self._v19_serial_variant(stage + '/app')
                    compile_args += ['--build-property', f'build.variant.path={variant_path}']
                elif stack_diagnostic:
                    variant_path = self._v19_variant_source()
                if stack_diagnostic:
                    stack_metadata = self._v19_stack_diagnostic(stage + '/app', variant_path)
                compile_args.append(stage + '/app/sketch')
                try:
                    compile_output = self.shell(*compile_args, capture=True,
                                                merge_stderr=True).stdout
                except subprocess.CalledProcessError as exc:
                    if exc.stdout:
                        print(exc.stdout, end='', flush=True)
                    raise
                print(compile_output, end='', flush=True)
                flash = re.search(r'Sketch uses ([\d,]+) bytes \((\d+)%\).*?Maximum is ([\d,]+) bytes',
                                  compile_output)
                ram = re.search(r'Global variables use ([\d,]+) bytes \((\d+)%\).*?leaving ([\d,]+) bytes.*?Maximum is ([\d,]+) bytes',
                                compile_output)
                # Build the ARM64 relay inside an ephemeral compiler container on the Q.
                tools_dir = str(ROOT / 'tools')
                if tools_dir not in sys.path:
                    sys.path.insert(0, tools_dir)
                from spi_benchmark import BUILD_IMAGE
                self.shell('docker', 'run', '--rm', '--user', '0:0', '--security-opt',
                           'no-new-privileges', '--mount', f'type=bind,src={stage},dst=/build',
                           '--entrypoint', 'sh', BUILD_IMAGE, '-c',
                           'apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev '
                           '&& cc -O2 -std=c11 -Wall -Wextra -Werror '
                           '/build/relay/unoq_config_stream.c -lm -o /build/relay/unoq_stream')
                artifacts.mkdir(parents=True, exist_ok=True)
                outputs = {'firmware': ('app/build/sketch.ino.bin', 'firmware-v19.bin'),
                           'firmware_elf': ('app/build/sketch.ino.elf', 'firmware-v19.elf'),
                           'relay': ('relay/unoq_stream', 'relay-v19-unoq_stream')}
                hashes = {}
                for key, (remote, filename) in outputs.items():
                    destination = artifacts / filename
                    self.run('pull', stage + '/' + remote, str(destination))
                    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
                    hashes[key] = {'path': filename, 'sha256': digest}
                manifest = {'schema': 1, 'version': 19, 'candidate_only': True,
                            'installed': False, 'sources': {
                                'firmware': {p.relative_to(self.local).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in app_files},
                                'relay': {p.relative_to(relay_folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in relay_files}},
                            'artifacts': hashes,
                            'firmware_memory': {
                                'flash': ({'used_bytes': int(flash.group(1).replace(',', '')),
                                           'used_percent': int(flash.group(2)),
                                           'maximum_bytes': int(flash.group(3).replace(',', ''))}
                                          if flash else None),
                                'static_ram': ({'used_bytes': int(ram.group(1).replace(',', '')),
                                               'used_percent': int(ram.group(2)),
                                               'free_bytes': int(ram.group(3).replace(',', '')),
                                               'maximum_bytes': int(ram.group(4).replace(',', ''))}
                                              if ram else None),
                                'warnings': [line.strip() for line in compile_output.splitlines()
                                             if 'Low memory available' in line]},
                            'acceptance': 'pending physical validation and review'}
                if omit_serial3:
                    manifest['experimental_build_override'] = self._serial_variant_metadata()
                    manifest['build_tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
                if stack_diagnostic:
                    if omit_serial3:
                        manifest['experimental_build_override'] = self._serial_variant_metadata()
                    manifest['stack_diagnostic'] = stack_metadata
                    manifest['build_tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
                (artifacts / 'build-v19-pair.json').write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            finally:
                self.shell('python3', '-c',
                           'import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)', stage)
        print(f'Pareja V19 compilada en {artifacts}. No se cargó firmware, app ni relay.')

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('status', 'inventory', 'compile', 'compile-pair', 'backup', 'deploy', 'start', 'stop', 'logs', 'create'))
    parser.add_argument('--version', choices=('v4', 'v5', 'v6', 'v6_polling', 'v6_dma', 'v6_irq', 'v6_adc', 'v7_dual', 'v8_config', 'v9_fast', 'v10_diag', 'v11_p992', 'v12_audio', 'v13_pulse', 'v16', 'v17', 'v18', 'v19', 'v20'), default='v19',
                        help='v19 predeterminado; anteriores seleccionables explícitamente')
    parser.add_argument('--follow', action='store_true', help='Seguir logs hasta Ctrl+C')
    parser.add_argument('--artifacts', type=Path,
                        help='Directorio de salida requerido por compile-pair; guarda BIN, ELF, relay y manifiesto SHA256')
    parser.add_argument('--omit-serial3', action='store_true',
                        help='Compilación experimental V19: omite USART3 en una copia temporal de la variante UNO Q')
    parser.add_argument('--stack-diagnostic', action='store_true',
                        help='Build diagnóstico V19 de pilas con la variante predeterminada; nunca se instala')
    args = parser.parse_args()
    if args.version == 'v19' and args.command not in ('compile', 'compile-pair', 'inventory', 'status', 'logs'):
        print('Error: Scope V19 es candidato sin aceptación física; se permiten inventario, estado, logs y compilación, pero no mutaciones.', file=sys.stderr)
        return 2
    if args.command == 'compile-pair' and (args.version != 'v19' or args.artifacts is None):
        print('Error: compile-pair requiere --version v19 y --artifacts RUTA.', file=sys.stderr)
        return 2
    if args.omit_serial3 and (args.version != 'v19' or args.command not in ('compile', 'compile-pair')):
        print('Error: --omit-serial3 sólo se permite en compile/compile-pair de V19.', file=sys.stderr)
        return 2
    if args.stack_diagnostic and (args.version != 'v19' or args.command != 'compile-pair'):
        print('Error: --stack-diagnostic sólo se permite en compile-pair de V19.', file=sys.stderr)
        return 2
    try:
        board = Board(json.loads(config_path(args.version).read_text()))
        print(f"Destino: {board.config['name']} ({board.local})", flush=True)
        if args.command == 'logs':
            opts = ['--follow'] if args.follow else ['--tail', '50']
            board.cli('app', 'logs', board.remote, *opts)
        elif args.command == 'compile-pair':
            board.compile_pair(args.artifacts, omit_serial3=args.omit_serial3,
                               stack_diagnostic=args.stack_diagnostic)
        elif args.command == 'compile':
            board.compile(artifacts=args.artifacts, omit_serial3=args.omit_serial3)
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
