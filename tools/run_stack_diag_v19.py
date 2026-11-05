#!/usr/bin/env python3
"""Run a private V19 stack probe, then restore the exact cached V17 firmware.

The temporary diagnostic app has a unique App Lab identity. It never starts,
imports over, or edits Scope V17, Scope V18, or production Scope V19. The final
restore app is also temporary and is built from a copy of the Q's V17 sources.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import struct
import sys
import tempfile
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from monitor.v19.board_owner import board_owner
from monitor.v19.receiver.unoq_usb import Connection
from tools.read_stack_diag_v19 import FrameReader, read_stack_diagnostic
from tools.unoq import source_files

ADB_BUNDLE = Path.home() / 'Library/Arduino15/packages/arduino/tools/adb'
EXCLUDED = {'.git', '.cache', '__pycache__', 'data', '.venv'}
V17_APP = '/home/arduino/ArduinoApps/scope-v17'
V18_APP = '/home/arduino/ArduinoApps/scope-v18'
V19_APP_NAME = 'Scope V19'
Q_APPS_ROOT = '/home/arduino/ArduinoApps'
BOOT_GPIO = {'chip': 'gpiochip1', 'ready_line': 70, 'reset_line': 38}
V17_BACKUP_BIN = ROOT / 'respaldos/parejas/v17_20261023_000325/firmware_v17.bin'
V17_BACKUP_RELAY = ROOT / 'respaldos/parejas/v17_20261023_000325/relay_v17.bin'
V18_RECEIPT = ROOT / 'monitor/v18/q_support/accepted/acceptance.json'
V19_DIAG_BUILD = ROOT / 'diagnosticos/resultados_v19/probes/stack_diagnostic_stock_variant_20261027'
V19_DIAG_MANIFEST = V19_DIAG_BUILD / 'build-v19-pair.json'
V18_ACCEPTED_RELAY = ROOT / 'monitor/v18/q_support/accepted/relay.bin'
GOVERNOR = '/sys/devices/system/cpu/cpufreq/policy0/scaling_governor'
RELAY_IMAGE = 'ghcr.io/arduino/app-bricks/python-apps-base:0.12.0'
REMOTE_SOURCE_MANIFEST = r'''import pathlib,hashlib,json,sys
r=pathlib.Path(sys.argv[1]); ex={'.git','.cache','__pycache__','data','.venv'}; d={}
for p in sorted(r.rglob('*')):
 if p.is_file() and not p.is_symlink() and not any(x in ex for x in p.relative_to(r).parts) and p.name!='.DS_Store' and p.suffix!='.pyc':
  d[p.relative_to(r).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps(d,sort_keys=True))
'''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_manifest(folder):
    folder = Path(folder)
    result = {}
    for path in sorted(folder.rglob('*')):
        relative = path.relative_to(folder)
        if (path.is_file() and not path.is_symlink()
                and not any(part in EXCLUDED for part in relative.parts)
                and path.name != '.DS_Store' and path.suffix != '.pyc'):
            result[relative.as_posix()] = digest(path)
    return result


def load_v18_restore_reference():
    """Validate the archived V18 receipt without importing any V18 code."""
    receipt = json.loads(V18_RECEIPT.read_text(encoding='utf-8'))
    if not (receipt.get('schema') == 1 and receipt.get('version') == 18
            and receipt.get('accepted') is True and receipt.get('public_rates_changed') is False):
        raise RuntimeError('No hay recibo de restauración V18 aceptado')
    for key, source_folder in (('app', ROOT / 'arduino/v18/oscilloscope'),
                               ('relay', ROOT / 'arduino/v18/relay')):
        if source_manifest(source_folder) != receipt.get('sources', {}).get(key):
            raise RuntimeError('Las fuentes V18 locales difieren del recibo aceptado')
    hashes = {}
    for key in ('firmware', 'relay'):
        item = receipt.get(key, {})
        path = (V18_RECEIPT.parent / item.get('path', '')).resolve()
        if not path.is_file() or digest(path) != item.get('sha256'):
            raise RuntimeError('Artefacto V18 aceptado no coincide: ' + key)
        hashes[key] = item['sha256']
    receipt['candidate_identity'] = {'firmware_sha256': hashes['firmware'],
                                     'relay_sha256': hashes['relay']}
    return receipt


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(temporary, path)


class Q:
    def __init__(self, serial):
        candidates = sorted(ADB_BUNDLE.glob('*/adb')) if ADB_BUNDLE.exists() else []
        self.adb = os.environ.get('UNOQ_ADB') or shutil.which('adb') or (str(candidates[-1]) if candidates else None)
        if not self.adb:
            raise RuntimeError('No se encontró ADB')
        self.serial = serial

    def run(self, *args, timeout=60):
        return subprocess.run([self.adb, '-s', self.serial, *map(str, args)],
                              text=True, capture_output=True, check=True, timeout=timeout)

    def shell(self, *args, timeout=60):
        return self.run('shell', shlex.join(map(str, args)), timeout=timeout)

    def output(self, *args, timeout=60):
        return self.shell(*args, timeout=timeout).stdout.strip()

    def cli(self, *args, timeout=60):
        return self.shell('arduino-app-cli', *args, timeout=timeout)

    def pulse_loader(self):
        boot = BOOT_GPIO
        self.shell('gpioset', '-c', boot['chip'], '-t0', f"{boot['reset_line']}=0")
        try:
            self.shell('gpioset', '-c', boot['chip'], '-t0', f"{boot['ready_line']}=1")
        finally:
            self.shell('gpioset', '-c', boot['chip'], '-t0', f"{boot['reset_line']}=1")

    def apps(self):
        return json.loads(self.cli('app', 'list', '--format', 'json').stdout).get('apps', [])

    def containers(self, all_=True):
        args = ['docker', 'ps'] + (['-a'] if all_ else []) + ['--format', '{{.Names}}']
        return sorted(filter(None, self.output(*args).splitlines()))

    def remote_manifest(self, folder):
        return json.loads(self.output('python3', '-c', REMOTE_SOURCE_MANIFEST, folder))

    def sha(self, path):
        return self.output('sha256sum', path).split()[0]

    def exists(self, path):
        return self.output('python3', '-c',
                           'import os,sys; print("yes" if os.path.exists(sys.argv[1]) else "no")',
                           path) == 'yes'

    def inspect(self, name):
        return json.loads(self.output('docker', 'inspect', name))[0]

    def prove_v17_rebuild(self, expected_sha):
        script = r'''import pathlib,tempfile,shutil,subprocess,hashlib,sys
src=pathlib.Path(sys.argv[1]); tmp=pathlib.Path(tempfile.mkdtemp(prefix='scope-v17-restore-proof-'))
try:
 dst=tmp/'sketch'; shutil.copytree(src,dst,ignore=shutil.ignore_patterns('.cache','__pycache__'))
 p=subprocess.run(['arduino-cli','compile','--fqbn','arduino:zephyr:unoq','--profile','default','--build-path',str(tmp/'build'),str(dst)],text=True,capture_output=True,timeout=240)
 if p.returncode:
  print(p.stdout); print(p.stderr,file=sys.stderr); raise SystemExit(p.returncode)
 print(hashlib.sha256((tmp/'build/sketch.ino.bin').read_bytes()).hexdigest())
finally: shutil.rmtree(tmp,ignore_errors=True)
'''
        result = self.output('python3', '-c', script, V17_APP + '/sketch', timeout=300)
        actual = result.splitlines()[-1].strip()
        if actual != expected_sha:
            raise RuntimeError('Build V17 desde las fuentes Q no reproduce su BIN cacheado')
        return actual

    def app_path(self, row):
        identity = base64.urlsafe_b64decode(row['id'] + '=' * (-len(row['id']) % 4)).decode()
        if not identity.startswith('user:'):
            raise RuntimeError('La app temporal no tiene identidad user: verificable')
        return '/home/arduino/ArduinoApps/' + identity.split(':', 1)[1]


def write_app_yaml(path, name):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    changed = 0
    for i, line in enumerate(lines):
        if line.startswith('name:'):
            lines[i] = 'name: ' + json.dumps(name, ensure_ascii=False)
            changed += 1
            break
    if changed != 1:
        raise RuntimeError('No se encontró exactamente un nombre de app')
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def import_app(q, folder, slug, name):
    files = source_files(folder)
    with tempfile.TemporaryDirectory(prefix='arduscopio-q-app-') as local_tmp:
        archive = Path(local_tmp) / (slug + '.zip')
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as out:
            for path in files:
                out.write(path, slug + '/' + path.relative_to(folder).as_posix())
        remote_zip = '/tmp/' + slug + '.zip'
        q.run('push', str(archive), remote_zip)
        try:
            q.cli('app', 'import', remote_zip, timeout=90)
        finally:
            q.shell('python3', '-c',
                    'import pathlib,sys; pathlib.Path(sys.argv[1]).unlink(missing_ok=True)', remote_zip)
    matches = [row for row in q.apps() if row.get('name') == name]
    if len(matches) != 1:
        raise RuntimeError(f'App import no produjo una identidad única para {name!r}')
    app_path = q.app_path(matches[0])
    if Path(app_path).name != slug:
        raise RuntimeError(f'Ruta de App Lab inesperada: {app_path}')
    return app_path, matches[0]['id']


def verify_baseline(q, v19_manifest, v18_acceptance):
    apps = q.apps()
    if any(row.get('status') == 'running' for row in apps):
        raise RuntimeError('Hay una app activa en el Q; no se iniciará el diagnóstico')
    running = q.containers(all_=False)
    if running:
        raise RuntimeError('Hay contenedores activos en el Q: ' + ', '.join(running))
    if any(row.get('name') == V19_APP_NAME for row in apps):
        raise RuntimeError('Scope V19 ya existe; esta rutina privada no la usa ni sobrescribe')

    v17_remote = q.remote_manifest(V17_APP)
    v17_local = source_manifest(ROOT / 'arduino/v17/oscilloscope')
    extras = set(v17_remote) - set(v17_local)
    if (set(v17_local) - set(v17_remote) or
            any(v17_remote[name] != v17_local[name] for name in v17_local) or
            extras != {'sketch/radio_test_stream.h'}):
        raise RuntimeError('Fuentes Q de Scope V17 cambiaron; no se puede preparar restauración temporal exacta')
    v17_cached = V17_APP + '/.cache/sketch/sketch.ino.bin'
    if q.sha(v17_cached) != digest(V17_BACKUP_BIN):
        raise RuntimeError('BIN cacheado de V17 no coincide con el respaldo pareado')
    v17_relay = q.inspect('serialmonitor-usb-stream')
    v17_mounts = [m['Source'] for m in v17_relay.get('Mounts', [])
                  if m.get('Destination') == '/work/unoq_stream']
    if (v17_relay.get('State', {}).get('Running') or len(v17_mounts) != 1 or
            q.sha(v17_mounts[0]) != digest(V17_BACKUP_RELAY)):
        raise RuntimeError('El relay V17 detenido no coincide con la pareja archivada')

    v18_remote = q.remote_manifest(V18_APP)
    if v18_remote != v18_acceptance['sources']['app']:
        raise RuntimeError('Fuentes Scope V18 del Q no coinciden con su recibo aceptado')
    if q.exists(V18_APP + '/.cache/sketch/sketch.ino.bin'):
        raise RuntimeError('Cambió el estado cacheado V18 desde la inspección; revisar antes de seguir')

    relay = q.inspect('serialmonitor-usb-stream-v18')
    relay_mounts = [m['Source'] for m in relay.get('Mounts', [])
                    if m.get('Destination') == '/work/unoq_stream']
    if len(relay_mounts) != 1 or q.sha(relay_mounts[0]) != v18_acceptance['candidate_identity']['relay_sha256']:
        raise RuntimeError('El relay V18 detenido no coincide con el par aceptado')
    if digest(V18_ACCEPTED_RELAY) != v18_acceptance['candidate_identity']['relay_sha256']:
        raise RuntimeError('El relay aceptado local cambió')

    firmware = V19_DIAG_BUILD / 'firmware-v19.bin'
    relay_bin = V19_DIAG_BUILD / 'relay-v19-unoq_stream'
    if (v19_manifest.get('installed') is not False or
            v19_manifest.get('candidate_only') is not True or
            digest(firmware) != v19_manifest['artifacts']['firmware']['sha256'] or
            digest(relay_bin) != v19_manifest['artifacts']['relay']['sha256']):
        raise RuntimeError('Artefactos V19 diagnósticos no coinciden con el manifiesto')
    source_hashes = v19_manifest['sources']['firmware']
    for relative, expected in source_hashes.items():
        if digest(ROOT / 'arduino/v19/oscilloscope' / relative) != expected:
            raise RuntimeError('Fuente V19 cambió desde el build: ' + relative)

    container_ids = {}
    for name in q.containers(all_=True):
        container_ids[name] = q.inspect(name)['Id']
    return dict(apps=[{k: row.get(k) for k in ('id', 'name', 'status', 'default')}
                      for row in apps], containers=container_ids,
                v17_source_manifest=v17_remote, v18_source_manifest=v18_remote,
                v17_source_files=len(v17_remote), v17_cached_firmware_sha256=q.sha(v17_cached),
                v17_cached_relay_sha256=digest(V17_BACKUP_RELAY),
                v18_source_files=len(v18_remote), v18_accepted_firmware_sha256=v18_acceptance['candidate_identity']['firmware_sha256'],
                v18_accepted_relay_sha256=v18_acceptance['candidate_identity']['relay_sha256'],
                v18_cached_firmware_present=False,
                stack_diag_firmware_sha256=digest(firmware),
                stack_diag_relay_sha256=digest(relay_bin))


def install_v17_restore_copy(q, token, temp_root, baseline):
    local = Path(temp_root) / ('v17-restore-' + token)
    shutil.copytree(ROOT / 'arduino/v17/oscilloscope', local)
    extra = local / 'sketch/radio_test_stream.h'
    q.run('pull', V17_APP + '/sketch/radio_test_stream.h', str(extra))
    copied_sources = source_manifest(local)
    original_sources = baseline['v17_source_manifest']
    if (set(copied_sources) != set(original_sources) or
            any(copied_sources[name] != original_sources[name]
                for name in copied_sources if name != 'app.yaml')):
        raise RuntimeError('La copia temporal no coincide con las fuentes Q V17 fuera del nombre de app')
    write_app_yaml(local / 'app.yaml', 'Scope V17 Restore ' + token)
    restore_slug = 'scope-v17-restore-' + token
    restore_name = 'Scope V17 Restore ' + token
    app_path, app_id = import_app(q, local, restore_slug, restore_name)
    expected_bin = baseline['v17_cached_firmware_sha256']
    return app_path, app_id, expected_bin


def start_restore(q, app_path, app_id, expected_bin):
    q.cli('app', 'stop', app_path, timeout=120)
    q.pulse_loader()
    q.cli('app', 'start', app_path, timeout=600)
    actual = q.sha(app_path + '/.cache/sketch/sketch.ino.bin')
    if actual != expected_bin:
        raise RuntimeError('El firmware reconstruido para restaurar V17 difiere del BIN inicial')
    return actual


def restore_v17_original_pair(q, baseline, serial):
    """Restore and prove V17 through its original paired app and relay."""
    app_id = next((row['id'] for row in q.apps() if row.get('name') == 'Scope V17'), None)
    if app_id is None:
        raise RuntimeError('No está la app original Scope V17 para rollback')
    relay_name = 'serialmonitor-usb-stream'
    expected_relay_id = baseline['containers'].get(relay_name)
    relay_id = q.inspect(relay_name)['Id']
    if not expected_relay_id or relay_id != expected_relay_id:
        raise RuntimeError('El relay original V17 cambió de identidad; no se inicia')
    connection = None
    try:
        q.cli('app', 'stop', V17_APP, timeout=120)
        q.pulse_loader()
        q.cli('app', 'start', V17_APP, timeout=600)
        firmware_sha = q.sha(V17_APP + '/.cache/sketch/sketch.ino.bin')
        if firmware_sha != baseline['v17_cached_firmware_sha256']:
            raise RuntimeError('El BIN compilado de V17 difiere del cache verificado')
        q.shell('docker', 'start', relay_name)
        connection = open_connection_when_ready(serial)
        packet, kind = FrameReader(connection).next_packet()
        if kind not in (3, 15):
            raise RuntimeError(f'Primer frame de V17 inesperado: {kind}')
        return firmware_sha, dict(relay_id=relay_id,
                                  firmware_sha256=firmware_sha,
                                  first_verified_frame=True,
                                  first_frame_kind=kind,
                                  first_frame_sequence=struct.unpack_from('<I', packet, 8)[0])
    finally:
        if connection is not None:
            connection.close()
        try:
            info = q.inspect(relay_name)
            if info.get('Id') == expected_relay_id and info.get('State', {}).get('Running'):
                q.shell('docker', 'stop', '--time', '3', relay_name)
        finally:
            q.cli('app', 'stop', V17_APP, timeout=120)
            q.pulse_loader()


def stop_destroy_app(q, app_path, name, expected_manifest, *, keep_on_mismatch=False):
    errors = []
    try:
        rows = [row for row in q.apps() if row.get('name') == name]
        if not rows:
            return errors
        row = rows[0]
        if row.get('status') == 'running':
            q.cli('app', 'stop', app_path, timeout=120)
        if expected_manifest is not None:
            actual = q.remote_manifest(app_path)
            if actual != expected_manifest:
                if keep_on_mismatch:
                    return ['Fuentes de app temporal cambiaron; se conserva para inspección']
                raise RuntimeError('App temporal modificada; se conserva en el Q')
        q.cli('app', 'destroy', app_path, timeout=120)
        # App Lab destroy stops/removes the runtime but can retain the imported
        # source directory. Delete only this uniquely named temporary app.
        slug = Path(app_path).name
        if 'Scope V19 Stack Diagnostic ' in name:
            expected_prefix = 'scope-v19-stack-diagnostic-'
        elif 'Scope V19 Normal Pair Probe ' in name:
            expected_prefix = 'scope-v19-normal-probe-'
        else:
            expected_prefix = 'scope-v17-restore-'
        if not slug.startswith(expected_prefix):
            raise RuntimeError('Ruta temporal fuera de los slugs permitidos; no se elimina')
        script = r'''import pathlib,shutil,sys
p=pathlib.Path(sys.argv[1]); root=pathlib.Path('/home/arduino/ArduinoApps')
expected=sys.argv[2]; slug=sys.argv[3]
if p.parent != root or p.name != slug or p.is_symlink(): raise SystemExit('ruta temporal no valida')
f=p/'app.yaml'
if not f.is_file() or expected not in f.read_text(): raise SystemExit('nombre temporal no coincide')
shutil.rmtree(p)
if p.exists(): raise SystemExit('no se pudo retirar carpeta temporal')
'''
        q.shell('python3', '-c', script, app_path, name, slug)
        if any(row.get('name') == name for row in q.apps()):
            raise RuntimeError('La app temporal sigue registrada tras limpieza')
    except Exception as exc:
        errors.append(str(exc))
    return errors


def relay_up(q, name, remote_bin, expected_hash):
    q.shell('mkdir', '-p', remote_bin.rsplit('/', 1)[0])
    local_bin = V19_DIAG_BUILD / 'relay-v19-unoq_stream'
    q.run('push', str(local_bin), remote_bin)
    q.shell('chmod', '0755', remote_bin)
    if q.sha(remote_bin) != expected_hash:
        raise RuntimeError('Relay V19 temporal cambió al copiarse al Q')
    q.shell('docker', 'run', '-d', '--name', name,
            '--label', 'arduscopio.scope.stack-diagnostic=true',
            '--network', 'host', '--read-only', '--cap-drop', 'ALL', '--cap-add', 'SYS_NICE',
            '--security-opt', 'no-new-privileges', '--user', '0:0',
            '--device', '/dev/spidev0.0:/dev/spidev0.0:rw',
            '--device', '/dev/gpiochip1:/dev/gpiochip1:rw',
            '--mount', 'type=bind,src=' + remote_bin + ',dst=/work/unoq_stream,readonly',
            '--mount', 'type=bind,src=' + GOVERNOR + ',dst=/scope_cpu_governor',
            '--entrypoint', '/work/unoq_stream', RELAY_IMAGE, timeout=60)
    info = q.inspect(name)
    mounts = [m['Source'] for m in info.get('Mounts', [])
              if m.get('Destination') == '/work/unoq_stream']
    if len(mounts) != 1 or q.sha(mounts[0]) != expected_hash:
        raise RuntimeError('Relay temporal activo con identidad distinta')
    if not info.get('State', {}).get('Running'):
        raise RuntimeError('El relay temporal no quedó en ejecución')
    return info['Id']


def open_connection_when_ready(serial, timeout=20):
    """Retry the real USB/TCP path; container logs are not transport evidence."""
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        connection = Connection(serial)
        try:
            connection.open()
            return connection
        except Exception as exc:
            last_error = exc
            connection.close()
            time.sleep(.25)
    raise TimeoutError(f'No abrió el transporte USB/TCP en {timeout}s: {last_error}')


def relay_up_v17(q, name, remote_bin, expected_hash):
    q.shell('mkdir', '-p', remote_bin.rsplit('/', 1)[0])
    q.run('push', str(V17_BACKUP_BIN), remote_bin)
    q.shell('chmod', '0755', remote_bin)
    if q.sha(remote_bin) != expected_hash:
        raise RuntimeError('Relay V17 temporal no coincide con el BIN pareado')
    q.shell('docker', 'run', '-d', '--name', name,
            '--label', 'arduscopio.scope.stack-diagnostic=true',
            '--network', 'host', '--read-only', '--cap-drop', 'ALL', '--cap-add', 'SYS_NICE',
            '--security-opt', 'no-new-privileges', '--user', '0:0',
            '--device', '/dev/spidev0.0:/dev/spidev0.0:rw',
            '--device', '/dev/gpiochip1:/dev/gpiochip1:rw',
            '--mount', 'type=bind,src=' + remote_bin + ',dst=/work/unoq_stream,readonly',
            '--mount', 'type=bind,src=' + GOVERNOR + ',dst=/scope_cpu_governor',
            '--entrypoint', '/work/unoq_stream', RELAY_IMAGE, timeout=60)
    info = q.inspect(name)
    mounts = [m['Source'] for m in info.get('Mounts', [])
              if m.get('Destination') == '/work/unoq_stream']
    if len(mounts) != 1 or q.sha(mounts[0]) != expected_hash:
        raise RuntimeError('Relay V17 temporal activo con identidad distinta')
    if not info.get('State', {}).get('Running'):
        raise RuntimeError('El relay V17 temporal no quedó en ejecución')
    return info['Id']


def cleanup_relay(q, name, expected_id):
    errors = []
    try:
        info = q.inspect(name)
        labels = info.get('Config', {}).get('Labels') or {}
        if labels.get('arduscopio.scope.stack-diagnostic') != 'true':
            raise RuntimeError('Contenedor con nombre temporal pero sin etiqueta de propiedad; no se modifica')
        if expected_id is not None and info.get('Id') != expected_id:
            raise RuntimeError('El nombre del relay temporal apunta a otro ID; no se modifica')
        expected_id = info['Id']
        if info.get('State', {}).get('Running'):
            q.shell('docker', 'stop', '--time', '3', expected_id)
        q.shell('docker', 'rm', expected_id)
    except Exception as exc:
        errors.append(str(exc))
    return errors


def run(args):
    raise RuntimeError('Herramienta histórica retirada: restauraba V17. '
                       'Usar tools/probe_radio_rate_v19.py para la pareja V19 instalada.')


def _historical_run(args):
    token = uuid.uuid4().hex[:8]
    q = Q(args.serial)
    output = args.output.expanduser().resolve()
    v19_manifest = json.loads(V19_DIAG_MANIFEST.read_text(encoding='utf-8'))
    v18_acceptance = load_v18_restore_reference()
    report = dict(schema=1, version=19, purpose='private stack measurement; not production acceptance',
                  started_utc=datetime.now(timezone.utc).isoformat(), serial=args.serial,
                  temporary_apps=[], temporary_relay=None, physical_acceptance=False,
                  restored=False, errors=[])
    atomic_json(output, report)
    with board_owner(args.serial, 'private V19 stack diagnostic with V17 firmware restore'):
        baseline = verify_baseline(q, v19_manifest, v18_acceptance)
        # Rollback identity is checked against the accepted archived BIN and
        # the exact Q source manifest above. Recompiling the same V17 sources
        # on every private diagnostic adds minutes but no new safety evidence.
        report['baseline'] = baseline
        atomic_json(output, report)
        if 'ESTAB' in q.output('ss', '-tn', 'sport', '=', ':8766'):
            raise RuntimeError('Hay un lector TCP activo en el relay; no se inicia la captura')

        diag_app = restore_app = None
        diag_app_manifest = restore_app_manifest = None
        relay_name = 'serialmonitor-usb-stream-v19-stackdiag-' + token
        relay_id = None
        firmware_may_have_changed = False
        restore_verified = False
        capture_result = None
        try:
            with tempfile.TemporaryDirectory(prefix='arduscopio-stack-run-') as local_tmp:
                temp_root = Path(local_tmp)
                diag_src = temp_root / 'v19-stack-diagnostic'
                shutil.copytree(ROOT / 'arduino/v19/oscilloscope', diag_src)
                write_app_yaml(diag_src / 'app.yaml', 'Scope V19 Stack Diagnostic ' + token)
                sketch = diag_src / 'sketch/sketch.ino'
                sketch.write_text('#define SCOPE_STACK_DIAGNOSTICS 1\n' +
                                  sketch.read_text(encoding='utf-8'), encoding='utf-8')
                if digest(sketch) != v19_manifest['stack_diagnostic']['patched_sketch_sha256']:
                    raise RuntimeError('Sketch temporal no coincide con el hash del build diagnóstico')
                diag_source_manifest = source_manifest(diag_src)
                base_manifest = v19_manifest['sources']['firmware']
                if (set(diag_source_manifest) != set(base_manifest) or
                        diag_source_manifest['sketch/sketch.ino'] != v19_manifest['stack_diagnostic']['patched_sketch_sha256'] or
                        any(diag_source_manifest[name] != expected for name, expected in base_manifest.items()
                            if name not in ('app.yaml', 'sketch/sketch.ino'))):
                    raise RuntimeError('Fuentes temporales de la app diagnóstica no coinciden con el build')
                diag_slug = 'scope-v19-stack-diagnostic-' + token
                diag_name = 'Scope V19 Stack Diagnostic ' + token
                diag_app, diag_id = import_app(q, diag_src, diag_slug, diag_name)
                diag_app_manifest = diag_source_manifest
                imported_manifest = q.remote_manifest(diag_app)
                if imported_manifest != diag_app_manifest:
                    raise RuntimeError('Las fuentes importadas de la app diagnóstica no coinciden')
                report['temporary_apps'].append({'role': 'diagnostic', 'id': diag_id, 'path': diag_app})
                atomic_json(output, report)

                firmware_may_have_changed = True
                q.cli('app', 'stop', diag_app, timeout=120)
                q.pulse_loader()
                q.cli('app', 'start', diag_app, timeout=600)
                actual_firmware = q.sha(diag_app + '/.cache/sketch/sketch.ino.bin')
                expected_firmware = v19_manifest['artifacts']['firmware']['sha256']
                if actual_firmware != expected_firmware:
                    raise RuntimeError('App Lab generó un BIN distinto al build diagnóstico verificado')
                report['diagnostic_firmware_sha256'] = actual_firmware
                atomic_json(output, report)

                relay_remote = '/home/arduino/.cache/serialmonitor/' + relay_name + '/unoq_stream'
                relay_id = relay_up(q, relay_name, relay_remote,
                                    v19_manifest['artifacts']['relay']['sha256'])
                report['temporary_relay'] = {'name': relay_name, 'id': relay_id,
                                             'sha256': v19_manifest['artifacts']['relay']['sha256']}
                atomic_json(output, report)
                connection = open_connection_when_ready(args.serial)
                try:
                    reader = FrameReader(connection)
                    first_packet, first_kind = reader.next_packet()
                    if first_kind not in (3, 15, 16, 19, 20, 21):
                        raise RuntimeError(f'Primer frame V19 de tipo inválido: {first_kind}')
                    report['temporary_relay']['first_verified_frame'] = True
                    report['temporary_relay']['first_frame_kind'] = first_kind
                    report['temporary_relay']['first_frame_sequence'] = struct.unpack_from('<I', first_packet, 8)[0]
                    atomic_json(output, report)
                    capture_result = read_stack_diagnostic(
                        connection, reader, args.duration, args.capture_output,
                        args.bits, args.rate)
                    report['capture'] = {key: capture_result.get(key) for key in
                                         ('duration_seconds', 'diagnostic_frames', 'tested_configuration',
                                          'minimum_free_bytes', 'adc_configuration_restored', 'capture_error')}
                    atomic_json(output, report)
                finally:
                    connection.close()
        except Exception as exc:
            report['errors'].append(str(exc))
        finally:
            report['cleanup_relay_errors'] = cleanup_relay(q, relay_name, relay_id)
            if diag_app:
                report['cleanup_diagnostic_app_errors'] = stop_destroy_app(
                    q, diag_app, 'Scope V19 Stack Diagnostic ' + token, diag_app_manifest)
            if firmware_may_have_changed:
                try:
                    restored_hash, restore_proof = restore_v17_original_pair(
                        q, baseline, args.serial)
                    report['restore_firmware_sha256'] = restored_hash
                    report['restore_spi_proof'] = restore_proof
                    restore_verified = True
                except Exception as exc:
                    report['errors'].append('Restauración V17: ' + str(exc))
                    report['restore_error'] = str(exc)

            try:
                final_apps = q.apps()
                final_running = q.containers(all_=False)
                final_v17_cache = q.sha(V17_APP + '/.cache/sketch/sketch.ino.bin')
                final_v18_sources = q.remote_manifest(V18_APP)
                final_v17_sources = q.remote_manifest(V17_APP)
                original_app_keys = {(row.get('id'), row.get('name'), row.get('status'), row.get('default'))
                                     for row in baseline['apps']}
                final_app_keys = {(row.get('id'), row.get('name'), row.get('status'), row.get('default'))
                                  for row in final_apps}
                final_containers = {name: q.inspect(name)['Id'] for name in q.containers(all_=True)}
                report['final_state'] = dict(running_apps=[row.get('name') for row in final_apps
                                                           if row.get('status') == 'running'],
                    running_containers=final_running,
                    original_app_inventory_equal=original_app_keys == final_app_keys,
                    original_container_ids_equal=baseline['containers'] == final_containers,
                    v17_source_manifest_equal=final_v17_sources == baseline['v17_source_manifest'],
                    v18_source_manifest_equal=final_v18_sources == v18_acceptance['sources']['app'],
                    v17_cached_firmware_unchanged=final_v17_cache == baseline['v17_cached_firmware_sha256'],
                    v18_cached_firmware_absent=not q.exists(V18_APP + '/.cache/sketch/sketch.ino.bin'),
                    v19_production_absent=not any(row.get('name') == V19_APP_NAME for row in final_apps),
                    v17_firmware_restored=restore_verified)
                report['restored'] = (restore_verified and not final_running and
                    report['final_state']['original_app_inventory_equal'] and
                    report['final_state']['original_container_ids_equal'] and
                    report['final_state']['v17_source_manifest_equal'] and
                    report['final_state']['v17_cached_firmware_unchanged'] and
                    report['final_state']['v18_source_manifest_equal'] and
                    report['final_state']['v18_cached_firmware_absent'] and
                    report['final_state']['v19_production_absent'] and
                    report['final_state']['original_app_inventory_equal'] and
                    report.get('restore_spi_proof', {}).get('first_verified_frame') is True and
                    not report.get('cleanup_restore_relay_errors') and
                    not report.get('cleanup_restore_app_errors'))
            except Exception as exc:
                report['errors'].append('Verificación final: ' + str(exc))
                report['final_state_error'] = str(exc)
            report['finished_utc'] = datetime.now(timezone.utc).isoformat()
            atomic_json(output, report)

    success = (report.get('restored') is True and not report['errors'] and
               report.get('capture', {}).get('capture_error') is None and
               report.get('capture', {}).get('adc_configuration_restored') is True)
    print(json.dumps({'restored': report.get('restored'), 'capture': report.get('capture'),
                      'errors': report['errors'], 'report': str(output)}, indent=2, ensure_ascii=False))
    return 0 if success else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default='1060031107')
    parser.add_argument('--duration', type=float, default=120)
    parser.add_argument('--bits', type=int, default=8, choices=(8, 10, 12, 14, 16))
    parser.add_argument('--rate', type=int, default=1860465)
    parser.add_argument('--output', type=Path, default=ROOT / 'diagnosticos/resultados_v19/stack_diagnostic_20261027/physical_run.json')
    parser.add_argument('--capture-output', type=Path, default=ROOT / 'diagnosticos/resultados_v19/stack_diagnostic_20261027/stack_usage_8bit_1860.json')
    args = parser.parse_args()
    if not 5 <= args.duration <= 3600:
        parser.error('--duration debe estar entre 5 y 3600 s')
    if args.rate != 1860465 or args.bits != 8:
        parser.error('El build diagnóstico privado actual sólo está preparado para ADC8/1.860 MS/s')
    try:
        return run(args)
    except Exception as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
