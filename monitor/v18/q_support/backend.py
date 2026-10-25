"""Bounded Scope V18 same-app backend. Constructing it never contacts the Q.

The accepted receipt and the engine in prepare_q_v18 are mandatory. This
adapter has no entry point of its own and never imports a private app cache.
"""
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import shlex
import socket
import subprocess
import time
import uuid

from monitor.v18.q_support import prepare as contract

ROOT = contract.ROOT
APP = contract.APP
CONTAINER = contract.CONTAINER
APP_CONTAINER = 'scope-v18-main-1'
GOVERNOR = '/sys/devices/system/cpu/cpufreq/policy0/scaling_governor'
HELPER = Path(__file__).with_name('archive.py')
FQBN = 'arduino:zephyr:unoq'
PROFILE = 'default'
ADDED = frozenset(('sketch/batch2_ownership.h', 'sketch/batch_command.h',
                   'sketch/spi16_geometry.h'))


def _digest(path):
    return contract.sha256(path)


def _verified_file(receipt, key):
    item = receipt.get('artifacts', {}).get(key)
    if not isinstance(item, dict) or not contract.valid_hash(item.get('sha256')):
        raise ValueError(key + ' requires SHA256')
    path = (Path(receipt['receipt_path']).parent / item.get('path', '')).resolve()
    if not path.is_file() or _digest(path) != item['sha256']:
        raise ValueError(key + ' bytes differ from receipt')
    return path


def _relay_policy_equal(original, candidate, old_binary, new_binary):
    """Compare the relay launch contract while allowing its accepted BIN mount."""
    if original.get('Image') != candidate.get('Image'):
        return False
    for key in ('NetworkMode', 'ReadonlyRootfs', 'CapAdd', 'CapDrop',
                'SecurityOpt', 'Devices', 'Binds'):
        if original.get('HostConfig', {}).get(key) != candidate.get('HostConfig', {}).get(key):
            return False
    for key in ('Env', 'Entrypoint', 'User'):
        if original.get('Config', {}).get(key) != candidate.get('Config', {}).get(key):
            return False
    def mounts(info, replace=False):
        rows = []
        for mount in info.get('Mounts', []):
            row = dict(mount)
            if replace and row.get('Source') == old_binary:
                row['Source'] = new_binary
            rows.append(row)
        return sorted(rows, key=lambda row: row.get('Destination', ''))
    return mounts(original, True) == mounts(candidate)


class ProductionBackend:
    def __init__(self, acceptance, *, board=None):
        self.acceptance = acceptance
        self.board = board
        self.token = uuid.uuid4().hex
        self.remote_folder = '/home/arduino/.cache/serialmonitor/v18-production-' + self.token
        self.helper = '/tmp/v18-production-archive-' + self.token + '.py'
        self.stage = '/tmp/v18-production-build-' + self.token
        self.export = '/tmp/v18-production-export-' + self.token + '.zip'
        self.local = ROOT / 'respaldos/parejas' / ('v18_production_' + self.token)
        self.saved_relay = CONTAINER + '-saved-' + self.token[:10]
        self.new_relay = '/home/arduino/.cache/serialmonitor/v18-relay-' + self.token
        self.original_sources = None
        self.archive_hash = None
        self.original_relay_id = None
        self.new_relay_id = None
        self.relay_renamed = False
        self.material_restored = False

    def _board(self):
        if self.board is None:
            from monitor.v18.q_support.board import Board
            cfg = json.loads((ROOT / 'arduino/v18/unoq.json').read_text())
            if cfg['remote_app'] != APP or cfg['name'] != contract.NAME or cfg['container'] != CONTAINER:
                raise RuntimeError('V18 board target changed')
            class BoundedBoard(Board):
                def run(self, *args, capture=False):
                    timeout = 600 if any('compile' in str(arg) or 'app start' in str(arg)
                                         for arg in args) else 60
                    return subprocess.run([self.adb, '-s', self.serial, *args], check=True,
                                          text=True, stdout=subprocess.PIPE if capture else None,
                                          timeout=timeout)
            self.board = BoundedBoard(cfg)
        return self.board

    @contextmanager
    def owner(self):
        from monitor.v18.board_owner import board_owner
        with board_owner(self._board().serial, 'Scope V18 production update'):
            yield

    def _output(self, *args):
        return self._board().shell(*args, capture=True).stdout.strip()

    def _json(self, *args):
        return json.loads(self._output(*args))

    def _hash(self, remote):
        value = self._output('sha256sum', remote).split()[0]
        if not contract.valid_hash(value):
            raise RuntimeError('Invalid remote SHA256: ' + remote)
        return value

    def _inspect(self, name):
        values = self._json('docker', 'inspect', name)
        if len(values) != 1:
            raise RuntimeError('Ambiguous container: ' + name)
        return values[0]

    def _app_bin(self):
        info = self._inspect(APP_CONTAINER)
        root = (info.get('Config', {}).get('Labels') or {}).get('com.docker.compose.project.working_dir')
        if root != APP + '/.cache':
            raise RuntimeError('Scope V18 cache root changed')
        return root + '/sketch/sketch.ino.bin'

    def _relay_bin(self, info):
        mounts = [m['Source'] for m in info.get('Mounts', [])
                  if m.get('Destination') == '/work/unoq_stream']
        if len(mounts) != 1 or not mounts[0].startswith('/home/arduino/.cache/serialmonitor/'):
            raise RuntimeError('Unexpected V18 relay mount')
        return mounts[0]

    def _identity(self):
        app = self._inspect(APP_CONTAINER)
        relay = self._inspect(CONTAINER)
        if not app['State']['Running'] or not relay['State']['Running']:
            raise RuntimeError('Scope V18 pair is not running')
        return dict(board_serial=self._board().serial, app=APP_CONTAINER,
                    firmware_sha256=self._hash(self._app_bin()),
                    relay_sha256=self._hash(self._relay_bin(relay)))

    def _archive(self, action, **options):
        args = ['python3', self.helper, action, '--root', APP]
        for key, value in options.items():
            args += ['--' + key.replace('_', '-'), str(value)]
        return self._json(*args)

    def _sources(self):
        return self._archive('snapshot')['source_files']

    def _cache(self):
        return self._archive('snapshot')['cache']

    def _cpu(self, info):
        script = ('import json,os,sys;p=int(sys.argv[1]);'
                  'print(json.dumps(dict(policy=os.sched_getscheduler(p),'
                  'priority=os.sched_getparam(p).sched_priority,'
                  'cpus=sorted(os.sched_getaffinity(p)))))')
        return self._json('python3', '-c', script, str(info['State']['Pid']))

    @contextmanager
    def _receiver(self):
        from monitor.v18.io.live_connection import LiveConnection
        from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
        port = None
        connection = None
        try:
            port = self._board().run('forward', 'tcp:0', 'tcp:8766', capture=True).stdout.strip()
            connection = LiveConnection(socket.create_connection(('127.0.0.1', int(port)), timeout=3),
                                        self._board().serial)
            receiver = OutputReceiver(connection, lambda _: None)
            receiver.decoder.numeric = True
            yield receiver
        finally:
            if connection is not None:
                connection.close()
            if port:
                self._board().run('forward', '--remove', 'tcp:' + port)

    def _no_reader(self):
        if 'ESTAB' in self._output('ss', '-tn', 'sport', '=', ':8766'):
            raise RuntimeError('Another V18 TCP reader is active')
        return True

    def preflight(self, acceptance):
        receipt = json.loads(Path(acceptance['receipt_path']).read_text())
        rehearsal = _verified_file(acceptance, 'rollback_rehearsal')
        trial = json.loads(rehearsal.read_text())
        if not (trial.get('ok') is True and trial.get('private') is True and
                trial.get('recipe') == 'batcharena' and
                trial.get('private_mutation_ok') is True and
                trial.get('private_restoration', {}).get('ok') is True and
                trial['private_restoration'].get('recovery', {}).get('hardware_restored') is True and
                trial.get('production_restoration', {}).get('hardware_restored') is True):
            raise RuntimeError('Same-app full-cache rollback rehearsal is not verified')
        if (trial.get('private_restoration', {}).get('identity', {}).get('firmware_sha256') !=
                acceptance['candidate_identity']['firmware_sha256'] or
                trial.get('private_restoration', {}).get('identity', {}).get('relay_sha256') !=
                acceptance['candidate_identity']['relay_sha256']):
            raise RuntimeError('Rollback rehearsal tested another binary pair')
        proof = json.loads(_verified_file(acceptance, 'prebuild_proof').read_text())
        if (proof.get('compile', {}).get('fqbn') != FQBN or
                proof.get('compile', {}).get('profile') != PROFILE or
                proof.get('firmware_sha256') != acceptance['candidate_identity']['firmware_sha256'] or
                proof.get('relay_sha256') != acceptance['candidate_identity']['relay_sha256'] or
                proof.get('sources') != acceptance['sources']):
            raise RuntimeError('Exact production-stage compile proof missing')
        self._board().run('get-state')
        running = self._output('docker', 'ps', '--format', '{{.Names}}').splitlines()
        active_apps = [name for name in running if name.startswith('scope-') and name.endswith('-main-1')]
        if active_apps != [APP_CONTAINER] or CONTAINER not in running:
            raise RuntimeError('Only the Scope V18 production pair may be active')
        apps=self._json('arduino-app-cli','app','list','--format','json').get('apps',[])
        if any(app.get('status')=='running' and app.get('name')!='Scope V18' for app in apps):
            raise RuntimeError('Otra app del Q está activa; no se modificará')
        cli = self._output('arduino-app-cli', 'version')
        cli_path = proof.get('launcher', {}).get('path')
        if (cli_path != '/usr/bin/arduino-app-cli' or
                cli != proof['launcher']['version'].strip() or
                self._hash(cli_path) != proof['launcher']['sha256']):
            raise RuntimeError('Installed app CLI differs from accepted rehearsal evidence')
        self._board().run('push', str(HELPER), self.helper)
        if self._hash(self.helper) != _digest(HELPER):
            raise RuntimeError('Remote archive helper differs')
        self._no_reader()
        return dict(production_backend_qualified=True, rollback_rehearsal_verified=True,
                    cached_launcher_verified=True, cli_version=cli,
                    cli_sha256=proof['launcher']['sha256'])

    def capture(self):
        from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
        from monitor.v18.receiver.unoq_wav import State
        self._no_reader()
        identity = self._identity()
        relay = self._inspect(CONTAINER)
        self.original_relay_id = relay['Id']
        governor = self._output('cat', GOVERNOR)
        cpu = self._cpu(relay)
        with self._receiver() as receiver:
            lifecycle = ReceiverLifecycle(receiver, identity, self.local / 'sessions')
            self.snapshot = lifecycle.capture()
            if receiver.wav_status is None or receiver.wav_status.state != State.IDLE:
                raise RuntimeError('WAV must be idle')
        self._no_reader()
        sources = self._sources()
        self.original_sources = sources
        return dict(generator_off=True, wav_idle=True, receiver_closed=True,
                    identity_verified=True, source_manifest_verified=True,
                    identity=identity, snapshot=self.snapshot.to_dict(), relay_inspect=relay,
                    cpu_state=cpu, governor=governor, app_sources=sources)

    def backup(self, baseline):
        from monitor.v18.q_support.verification import verify_export
        self.local.mkdir(parents=True, exist_ok=True)
        b = self._board()
        b.cli('app', 'export', APP, self.export)
        exported = self.local / 'original_export.zip'
        b.run('pull', self.export, str(exported))
        verify_export(exported, baseline['app_sources'], app=APP)
        archived = self._archive('backup', folder=self.remote_folder)
        if archived['source_files'] != baseline['app_sources']:
            raise RuntimeError('Live source archive changed during backup')
        staging = archived.get('staging_verification', {})
        if any(staging.get(kind, {}).get('exact') is not True for kind in ('sources', 'cache')):
            raise RuntimeError('Full-cache staging reconstruction failed')
        for name, key in (('manifest.json', 'manifest_sha256'),
                          ('sources.tar', 'sources_tar_sha256'), ('cache.tar', 'cache_tar_sha256')):
            local = self.local / name
            b.run('pull', self.remote_folder + '/' + name, str(local))
            if _digest(local) != archived[key]:
                raise RuntimeError('Downloaded backup differs: ' + name)
        for kind in ('sources', 'cache'):
            name = 'verify_' + kind + '_manifest.json'
            local = self.local / name
            b.run('pull', self.remote_folder + '/' + name, str(local))
            if _digest(local) != staging[kind]['manifest_sha256']:
                raise RuntimeError('Downloaded staging proof differs: ' + kind)
        manifest = json.loads((self.local / 'manifest.json').read_text())
        cache = manifest['cache']
        bin_key = '.cache/sketch/sketch.ino.bin'
        elf_keys = [key for key in cache if key.startswith('.cache/sketch/') and key.endswith('.elf')]
        if bin_key not in cache or not elf_keys:
            raise RuntimeError('Original full cache lacks BIN/ELF')
        for remote, name in ((self._app_bin(), 'original_firmware.bin'),
                             (self._relay_bin(baseline['relay_inspect']), 'original_relay.bin')):
            local = self.local / name
            b.run('pull', remote, str(local))
        if (_digest(self.local / 'original_firmware.bin') != baseline['identity']['firmware_sha256'] or
                _digest(self.local / 'original_relay.bin') != baseline['identity']['relay_sha256'] or
                cache[bin_key]['sha256'] != baseline['identity']['firmware_sha256']):
            raise RuntimeError('Paired backup binary identity mismatch')
        for key in elf_keys:
            local = self.local / Path(key).name
            b.run('pull', APP + '/' + key, str(local))
            if _digest(local) != cache[key]['sha256']:
                raise RuntimeError('Original ELF differs')
        self.archive_hash = archived['manifest_sha256']
        pair = dict(schema=1, version=18, app=APP, original_identity=baseline['identity'],
                    source_archive_sha256=archived['sources_tar_sha256'],
                    cache_archive_sha256=archived['cache_tar_sha256'],
                    archive_manifest_sha256=self.archive_hash,
                    export_sha256=_digest(exported),
                    original_firmware_sha256=_digest(self.local / 'original_firmware.bin'),
                    original_relay_sha256=_digest(self.local / 'original_relay.bin'))
        (self.local / 'pair_manifest.json').write_text(json.dumps(pair, indent=2) + '\n')
        self._no_reader()
        return dict(export_verified=True, source_archive_verified=True, full_cache_verified=True,
                    firmware_elf_bin_verified=True, relay_verified=True,
                    paired_manifest_persisted=True, folder=str(self.local),
                    archive_manifest_sha256=self.archive_hash)

    def prepare(self, acceptance, baseline):
        from monitor.v18.relay_identity import relay_sources
        b = self._board()
        app_sources = contract.APP_SOURCES
        if contract.source_manifest(app_sources) != acceptance['sources']['app']:
            raise RuntimeError('Accepted app source changed')
        b.shell('mkdir', '-p', self.stage, self.stage + '/sketch')
        for source in sorted(app_sources.rglob('*')):
            if not source.is_file() or source.is_symlink():
                continue
            relative = source.relative_to(app_sources).as_posix()
            if relative not in acceptance['sources']['app']:
                continue
            target = self.stage + '/' + relative
            b.shell('mkdir', '-p', target.rsplit('/', 1)[0])
            b.run('push', str(source), target)
        # Compiling a staging tree cannot overwrite the running production cache.
        b.shell('arduino-cli', 'compile', '--fqbn', FQBN, '--profile', PROFILE,
                '--build-path', self.stage + '/build', self.stage + '/sketch')
        compiled = self.stage + '/build/sketch.ino.bin'
        expected = acceptance['candidate_identity']
        if self._hash(compiled) != expected['firmware_sha256']:
            raise RuntimeError('Production-stage firmware hash differs from accepted BIN')
        if _digest(acceptance['artifacts']['firmware']['path']) != expected['firmware_sha256']:
            raise RuntimeError('Local accepted firmware differs')
        relay = Path(acceptance['artifacts']['relay']['path'])
        if _digest(relay) != expected['relay_sha256']:
            raise RuntimeError('Precompiled accepted relay differs')
        b.shell('mkdir', '-p', self.new_relay)
        b.run('push', str(relay), self.new_relay + '/unoq_stream')
        b.shell('chmod', '0755', self.new_relay + '/unoq_stream')
        if self._hash(self.new_relay + '/unoq_stream') != expected['relay_sha256']:
            raise RuntimeError('Staged relay differs')
        return dict(source_hashes_equal=True, compiled_firmware_hash_equal=True,
                    precompiled_relay_hash_equal=True, fresh_cache_planned=True,
                    candidate_cache_policy='rebuild_in_production_app',
                    candidate_identity=expected, staging_build=compiled)

    def recheck(self, baseline, backup, prepared):
        current = self._identity()
        manifest = json.loads((self.local / 'manifest.json').read_text())
        if (current != baseline['identity'] or self._sources() != baseline['app_sources'] or
                contract.source_manifest(contract.APP_SOURCES) != self.acceptance['sources']['app'] or
                contract.source_manifest(contract.RELAY_SOURCES) != self.acceptance['sources']['relay'] or
                self._hash(prepared['staging_build']) != prepared['candidate_identity']['firmware_sha256'] or
                self._hash(self.new_relay + '/unoq_stream') != prepared['candidate_identity']['relay_sha256'] or
                _digest(self.local / 'manifest.json') != self.archive_hash or
                _digest(self.local / 'sources.tar') != manifest['sources_tar_sha256'] or
                _digest(self.local / 'cache.tar') != manifest['cache_tar_sha256'] or
                self._hash(self.remote_folder + '/manifest.json') != self.archive_hash or
                self._hash(APP + '/.cache/sketch/sketch.ino.bin') != baseline['identity']['firmware_sha256']):
            raise RuntimeError('Baseline, backup or staged candidate changed')
        self._no_reader()
        return dict(baseline_unchanged=True, backups_verified=True,
                    candidate_verified=True, no_other_reader=True)

    def quiesce(self, baseline):
        from monitor.v18.receiver.unoq_acquisition import Configuration
        self._no_reader()
        if self._identity() != baseline['identity']:
            raise RuntimeError('Identity changed before stop')
        with self._receiver() as receiver:
            receiver.select(0)
            receiver.configure(Configuration(14, 40000))
        self._no_reader()
        self.inactive_cpu = self._cpu(self._inspect(CONTAINER))
        self.inactive_governor = self._output('cat', GOVERNOR)

    def stop_old_relay(self, baseline):
        if self._inspect(CONTAINER)['Id'] != self.original_relay_id:
            raise RuntimeError('Original relay ID changed')
        self._board().shell('docker', 'stop', '--time', '3', self.original_relay_id)

    def rename_old_relay(self, baseline):
        if self._inspect(CONTAINER)['Id'] != self.original_relay_id:
            raise RuntimeError('Original relay ID changed before rename')
        self._board().shell('docker', 'rename', CONTAINER, self.saved_relay)
        self.relay_renamed = True

    def stop_app(self):
        self._board().stop()

    def install_sources(self, acceptance, changes):
        if set(changes['added']) != set(ADDED) or changes['remove']:
            raise RuntimeError('Only three reviewed V18 source additions are allowed')
        b = self._board()
        for name in changes['replace'] + changes['added']:
            source = contract.APP_SOURCES / name
            target = APP + '/' + name
            b.shell('mkdir', '-p', target.rsplit('/', 1)[0])
            b.run('push', str(source), target)
            if self._hash(target) != acceptance['sources']['app'][name]:
                raise RuntimeError('Installed source differs: ' + name)
        if self._sources() != acceptance['sources']['app']:
            raise RuntimeError('Installed app source manifest differs')

    def install_cache(self, prepared):
        # Full original cache is already archived. No private cache is copied.
        self._board().shell('mv', APP + '/.cache', self.remote_folder + '/quarantined_original_cache')
        self._board().shell('mkdir', APP + '/.cache')

    def start_new_app(self, prepared):
        self._board().start()
        actual = self._hash(self._app_bin())
        if actual != prepared['candidate_identity']['firmware_sha256']:
            raise RuntimeError('Scope V18 launcher produced an unexpected firmware BIN')
        cache = self._cache()
        if '.cache/sketch/sketch.ino.bin' not in cache:
            raise RuntimeError('Scope V18 fresh cache layout changed')
        return dict(cache_layout_verified=True, compiled_firmware_hash_equal=True,
                    firmware_sha256=actual)

    def start_new_relay(self, baseline, prepared):
        IMAGE = 'ghcr.io/arduino/app-bricks/python-apps-base:0.12.0'
        b = self._board()
        b.shell('docker', 'run', '-d', '--name', CONTAINER, '--network', 'host', '--read-only',
                '--cap-drop', 'ALL', '--cap-add', 'SYS_NICE',
                '--security-opt', 'no-new-privileges', '--user', '0:0',
                '--device', '/dev/spidev0.0:/dev/spidev0.0:rw',
                '--device', '/dev/gpiochip1:/dev/gpiochip1:rw',
                '--mount', 'type=bind,src=' + self.new_relay + '/unoq_stream,dst=/work/unoq_stream,readonly',
                '--mount', 'type=bind,src=' + GOVERNOR + ',dst=/scope_cpu_governor',
                '--entrypoint', '/work/unoq_stream', IMAGE)
        info = self._inspect(CONTAINER)
        self.new_relay_id = info['Id']
        if self._hash(self._relay_bin(info)) != prepared['candidate_identity']['relay_sha256']:
            raise RuntimeError('Running relay BIN differs')
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if 'SPI ready: first verified frame' in self._output('sh', '-c',
                    'docker logs ' + shlex.quote(self.new_relay_id) + ' 2>&1'):
                return
            time.sleep(.2)
        raise TimeoutError('New V18 relay did not verify SPI startup')

    def _recover(self, identity, seconds):
        from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
        from monitor.v18.io.device_snapshot import DeviceIdentity
        with self._receiver() as receiver:
            lifecycle = ReceiverLifecycle(receiver, identity, self.local / 'sessions')
            lifecycle.snapshot = replace(self.snapshot, identity=DeviceIdentity(**identity))
            result = lifecycle.restore(seconds)
        recovery = result.get('recovery') or {}
        return dict(snapshot_equal=result.get('hardware_restored') is True,
                    continuous=recovery.get('continuous') is True,
                    integrity_ok=recovery.get('dropped') == 0 and recovery.get('fatal') == 0,
                    seconds=recovery.get('seconds', 0), detail=result)

    def verify_new(self, baseline, acceptance, prepared, seconds):
        identity = self._identity()
        expected = dict(baseline['identity'], **acceptance['candidate_identity'])
        if identity != expected:
            raise RuntimeError('Installed Scope V18 pair identity differs')
        recovery = self._recover(identity, seconds)
        info = self._inspect(CONTAINER)
        current_cpu = self._cpu(info)
        if current_cpu != baseline['cpu_state']:
            raise RuntimeError('Relay CPU state differs from original configuration')
        policy = _relay_policy_equal(baseline['relay_inspect'], info,
                                     self._relay_bin(baseline['relay_inspect']),
                                     self.new_relay + '/unoq_stream')
        return dict(accepted_identity_equal=True,
                    sources_exact=self._sources() == acceptance['sources']['app'],
                    cpu_equal=True, relay_configuration_verified=policy,
                    **recovery)

    def stop_new_relay(self, baseline, prepared):
        names = self._output('docker', 'ps', '-a', '--format', '{{.Names}}').splitlines()
        if CONTAINER in names:
            info = self._inspect(CONTAINER)
            if info['Id'] == self.original_relay_id:
                if info['State']['Running']:
                    self._board().shell('docker', 'stop', '--time', '3', info['Id'])
                return
            if (self._relay_bin(info) != self.new_relay + '/unoq_stream' or
                    (self.new_relay_id is not None and info['Id'] != self.new_relay_id)):
                raise RuntimeError('Unowned relay now uses production name')
            self._board().shell('docker', 'rm', '-f', info['Id'])

    def restore_sources(self, backup, changes):
        if self.archive_hash is None:
            raise RuntimeError('No verified original archive')
        result = self._archive('restore', folder=self.remote_folder,
                               manifest_sha256=self.archive_hash)
        if result.get('sources_exact') is not True or result.get('cache_exact') is not True:
            raise RuntimeError('Exact source/cache restore failed')
        self.material_restored = True

    def restore_cache(self, backup):
        if not self.material_restored or self._sources() != self.original_sources:
            raise RuntimeError('Original sources/cache not restored')

    def verify_original_material(self, baseline, backup):
        source_ok = self._sources() == baseline['app_sources']
        cache = self._cache()
        original = json.loads((self.local / 'manifest.json').read_text())['cache']
        cache_ok = cache == original
        firmware_ok = self._hash(APP + '/.cache/sketch/sketch.ino.bin') == baseline['identity']['firmware_sha256']
        relay_ok = self._hash(self._relay_bin(baseline['relay_inspect'])) == baseline['identity']['relay_sha256']
        return dict(sources_exact=source_ok, cache_exact=cache_ok,
                    firmware_exact=firmware_ok, relay_exact=relay_ok)

    def start_original_app(self, baseline, backup):
        material = self.verify_original_material(baseline, backup)
        if not all(material.values()):
            raise RuntimeError('Original material changed before launcher')
        self._board().start()
        if self._hash(self._app_bin()) != baseline['identity']['firmware_sha256']:
            raise RuntimeError('Original Scope V18 BIN changed after launcher')

    def restore_old_relay(self, baseline):
        names = self._output('docker', 'ps', '-a', '--format', '{{.Names}}').splitlines()
        if self.saved_relay in names:
            if self._inspect(self.saved_relay)['Id'] != self.original_relay_id:
                raise RuntimeError('Saved original relay ID changed')
            self._board().shell('docker', 'rename', self.saved_relay, CONTAINER)
        if self._inspect(CONTAINER)['Id'] != self.original_relay_id:
            raise RuntimeError('Original relay name now refers to different container')
        self._board().shell('docker', 'start', CONTAINER)

    def restore_cpu(self, baseline):
        from monitor.v18.q_support.verification import relay_configuration_equal
        relay = self._inspect(CONTAINER)
        if not relay_configuration_equal(relay, baseline['relay_inspect']):
            raise RuntimeError('Original relay configuration differs')
        if (self._cpu(relay) != getattr(self, 'inactive_cpu', baseline['cpu_state']) or
                self._output('cat', GOVERNOR) != getattr(self, 'inactive_governor', baseline['governor'])):
            raise RuntimeError('Original relay CPU state differs')

    def restore_snapshot(self, baseline, seconds):
        identity = self._identity()
        if identity != baseline['identity']:
            raise RuntimeError('Original identity differs before snapshot restore')
        return self._recover(identity, seconds)

    def verify_original(self, baseline, backup):
        from monitor.v18.q_support.verification import relay_configuration_equal
        relay = self._inspect(CONTAINER)
        return dict(identity_equal=self._identity() == baseline['identity'],
                    sources_exact=self._sources() == baseline['app_sources'],
                    relay_configuration_equal=relay_configuration_equal(relay, baseline['relay_inspect']),
                    cpu_equal=self._cpu(relay) == baseline['cpu_state'] and
                              self._output('cat', GOVERNOR) == baseline['governor'])
