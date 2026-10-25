"""Private BatchArena same-app update/rollback rehearsal; plan unless --run.

Mutates only the explicit private app after exact stopped source/cache backup.
The production Scope V18 pair is restored by the outer Hardware transaction.
No production updater is enabled by this script's existence or partial result.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path, PurePosixPath
import signal
import shlex
import sys
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from experimentos.fs_max_v18.rehearsal_archive import APP, WORK_PREFIX, EXTRA, digest, source_files
from experimentos.fs_max_v18.run_probe import Hardware, EXP, CONTAINER, private_profiles, relay_configuration_equal
from experimentos.fs_max_v18.probe_journal import ProbeJournal, REMOTE_MANIFEST, source_manifest

NAME = 'Scope V18 Rate Probe BatchArena'
ANCHOR = 'halves[1].source==scope_batch2::Source::Idle) k_sleep(K_MSEC(1));'


def plan():
    return dict(private=True, recipe='batcharena', app=APP, name=NAME,
        default_action='print plan; no Q access', production_update=False,
        baseline=dict(bits=14, rate=40000, generator='OFF', wav='IDLE'),
        mutation=dict(source='sketch/sketch.ino', idle_ms_before=1, idle_ms_after=2,
                      added_file=EXTRA, removed_files=[]),
        steps=['Capture production identity/snapshot/CPU and own Q throughout.',
               'Hardware.prepare + restart once: private BatchArena app and relay.',
               'Confirm private low baseline; close receiver; stop relay before stopping app.',
               'Export exact sources; archive stopped full cache including ELF/BIN, metadata and venv; download and hash all backups.',
               'Change only private idle sleep 1->2 ms and add archivoextra.yml; start same private app once with relay stopped.',
               'Require changed firmware SHA256 and unchanged relay; restart retained relay and verify private acquisition.',
               'Stop relay/app; restore original sources/full cache and remove added file; verify original hashes BEFORE app start.',
               'Start same private app once; require original firmware SHA256 AFTER start and exact sources; restart retained relay.',
               'Restore private snapshot; verify 10 s integrity, identity, source hashes, relay inspect and CPU.',
               'Always Hardware.restore production after successful capture; verify original production identity.'])


def verify_export(path, expected):
    """Validate CLI-exported ZIP bytes without extracting any archive member."""
    with zipfile.ZipFile(path) as archive:
        files = {}
        for info in archive.infolist():
            name = info.filename.rstrip('/')
            member = PurePosixPath(name)
            if member.is_absolute() or '..' in member.parts or '\\' in name:
                raise ValueError('Unsafe exported archive path')
            if info.is_dir():
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Source export symlink is not accepted')
            if name in files:
                raise ValueError('Duplicate exported source file')
            files[name] = hashlib.sha256(archive.read(info)).hexdigest()
    for prefix in ('', Path(APP).name + '/'):
        normalized = {name[len(prefix):]: value for name, value in files.items() if name.startswith(prefix)}
        if len(normalized) == len(files) and normalized == expected:
            return dict(exact=True, sha256=digest(path), archive_prefix=prefix)
    raise ValueError('CLI source export differs from exact original source manifest')


class Rehearsal:
    def __init__(self, hardware):
        self.hw = hardware
        self.report = hardware.report
        if hardware.app != APP or hardware.app_name != NAME or hardware.recipe != 'batcharena':
            raise ValueError('Only the explicit private BatchArena target is allowed')
        token = uuid.uuid4().hex
        self.remote_folder = WORK_PREFIX + token
        self.helper = '/tmp/v18-rehearsal-' + token + '.py'
        self.remote_export = '/tmp/v18-rehearsal-' + token + '.zip'
        self.mutation_attempted = self.restoration_attempted = self.backup_ready = False
        self.report['private_paths'] = dict(app=APP, archive=self.remote_folder, helper=self.helper)

    def save(self):
        self.report['private_flags'] = dict(mutation_attempted=self.mutation_attempted,
            restoration_attempted=self.restoration_attempted, backup_ready=self.backup_ready)
        self.hw.persist()

    def action(self, name, fn):
        return self.hw.action('same_app_' + name, fn)

    def archive_command(self, action, **options):
        args = ['python3', self.helper, action, '--root', APP]
        for name, value in options.items():
            args.extend(['--' + name.replace('_', '-'), str(value)])
        return json.loads(self.hw.original.shell(*args, capture=True).stdout)

    def remote_sources(self):
        return json.loads(self.hw.original.shell('python3', '-c', REMOTE_MANIFEST, APP, capture=True).stdout)

    def identity(self):
        from monitor.v18.io.device_snapshot import DeviceIdentity
        actual = self.hw.candidate_identity()
        if actual['app'] != APP:
            raise ValueError('Candidate app identity path changed')
        return DeviceIdentity(self.hw.original.serial, self.hw.app_container,
                              actual['firmware_sha256'], actual['relay_sha256'])

    def inspect_relay(self):
        return json.loads(self.hw.original.shell('docker', 'inspect', CONTAINER, capture=True).stdout)[0]

    def check_stopped(self):
        relay = self.inspect_relay()
        app = json.loads(self.hw.original.shell('docker', 'inspect', self.hw.app_container, capture=True).stdout)[0]
        if relay['Id'] != self.relay_inspect['Id'] or relay['State']['Running'] or app['State']['Running']:
            raise RuntimeError('Private app and retained relay must both be stopped')

    def stop_pair(self):
        relay = self.inspect_relay()
        if relay['Id'] != self.relay_inspect['Id']:
            raise RuntimeError('Retained private relay ID changed; no stop attempted')
        self.action('stop_retained_relay', lambda: self.hw.original.shell('docker', 'stop', '--time', '3', relay['Id']))
        self.action('stop_private_app', self.hw.candidate.stop)
        self.check_stopped()

    def start_relay(self):
        relay = self.inspect_relay()
        if relay['Id'] != self.relay_inspect['Id'] or relay['State']['Running']:
            raise RuntimeError('Expected stopped retained private relay')
        self.action('start_retained_relay', lambda: self.hw.original.shell('docker', 'start', relay['Id']))
        # No Hardware.restart here: restarting the relay must not start/reset
        # the app a second time or hide the cache behavior being tested.
        started = self.inspect_relay()['State']['StartedAt']
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            state = self.inspect_relay()
            if not state['State']['Running']:
                raise RuntimeError('Retained private relay exited during startup')
            command = shlex.join(['docker', 'logs', '--since', started, relay['Id']]) + ' 2>&1'
            logs = self.hw.original.run('shell', command, capture=True).stdout
            if 'SPI ready: first verified frame' in logs:
                return
            time.sleep(.2)
        raise TimeoutError('Retained private relay did not verify a fresh SPI frame')

    def recover(self, identity, seconds):
        from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
        from monitor.v18.receiver.unoq_wav import State
        with self.hw.receiver() as receiver:
            lifecycle = ReceiverLifecycle(receiver, identity.__dict__, self.hw.folder / 'private_sessions')
            lifecycle.snapshot = replace(self.snapshot, identity=identity)
            result = lifecycle.restore(seconds)
            if receiver.wav_status is None or receiver.wav_status.state != State.IDLE:
                raise RuntimeError('Private recovery must end with WAV IDLE')
        if not result['hardware_restored']:
            raise RuntimeError('Private recovery failed: ' + repr(result))
        return result

    def capture_baseline(self):
        from monitor.v18.receiver.unoq_acquisition import Configuration
        from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
        from monitor.v18.receiver.unoq_wav import State
        self.original_identity = self.identity()
        with self.hw.receiver() as receiver:
            receiver.select(0)
            receiver.configure(Configuration(14, 40000))
            lifecycle = ReceiverLifecycle(receiver, self.original_identity.__dict__, self.hw.folder / 'private_sessions')
            self.snapshot = lifecycle.capture()
            if receiver.wav_status is None or receiver.wav_status.state != State.IDLE:
                raise RuntimeError('Rehearsal baseline requires WAV IDLE')
        self.relay_inspect = self.inspect_relay()
        self.private_cpu = self.hw.cpu_state(self.relay_inspect)
        self.private_governor = self.hw.original.shell('cat', self.hw.governor_path, capture=True).stdout.strip()
        self.original_sources = self.remote_sources()
        if self.original_sources != source_manifest(self.hw.folder / 'candidate_app'):
            raise ValueError('Installed private sources differ from original candidate copy')
        self.report['private_baseline'] = dict(identity=self.original_identity.__dict__,
            snapshot=self.snapshot.to_dict(), relay_inspect=self.relay_inspect,
            cpu=self.private_cpu, governor=self.private_governor, sources=self.original_sources)
        self.save()

    def backup(self):
        self.stop_pair()
        b = self.hw.original
        helper = EXP / 'rehearsal_archive.py'
        self.action('push_archive_helper', lambda: b.run('push', str(helper), self.helper))
        helper_hash = b.shell('sha256sum', self.helper, capture=True).stdout.split()[0]
        if helper_hash != digest(helper):
            raise ValueError('Remote archive helper SHA256 differs')
        self.action('export_private_app', lambda: b.cli('app', 'export', APP, self.remote_export))
        export = self.hw.folder / 'private_original_export.zip'
        self.action('download_private_export', lambda: b.run('pull', self.remote_export, str(export)))
        export_evidence = verify_export(export, self.original_sources)
        archives = self.action('archive_original_sources_and_full_cache',
            lambda: self.archive_command('backup', folder=self.remote_folder))
        if archives['source_files'] != self.original_sources:
            raise ValueError('Source archive differs from original private manifest')
        staging = archives.get('staging_verification', {})
        if any(staging.get(kind, {}).get('exact') is not True for kind in ('sources', 'cache')):
            raise ValueError('Exact source AND full-cache staging reconstruction required before mutation')
        for name, key in (('manifest.json', 'manifest_sha256'), ('sources.tar', 'sources_tar_sha256'), ('cache.tar', 'cache_tar_sha256')):
            local = self.hw.folder / ('private_original_' + name)
            self.action('download_' + name, lambda name=name, local=local: b.run('pull', self.remote_folder + '/' + name, str(local)))
            if digest(local) != archives[key]:
                raise ValueError('Downloaded original archive hash mismatch: ' + name)
        manifest = json.loads((self.hw.folder / 'private_original_manifest.json').read_text())
        if manifest.get('staging_verification') != staging:
            raise ValueError('Staging reconstruction evidence differs from original archive manifest')
        for kind in ('sources', 'cache'):
            name = 'verify_' + kind + '_manifest.json'
            local = self.hw.folder / ('private_original_' + name)
            self.action('download_' + name,
                lambda name=name, local=local: b.run('pull', self.remote_folder + '/' + name, str(local)))
            if (digest(local) != staging[kind]['manifest_sha256']
                    or staging[kind]['archive_sha256'] != archives[kind + '_tar_sha256']
                    or json.loads(local.read_text()) != manifest[kind]):
                raise ValueError('Exact staging reconstruction manifest/hash mismatch: ' + kind)
        artifacts = self.hw.folder / 'private_original_artifacts'
        artifacts.mkdir()
        cache_files = manifest['cache']
        primary = '.cache/sketch/sketch.ino.bin'
        elf_paths = [name for name, item in cache_files.items()
                     if name.startswith('.cache/sketch/') and item['kind'] == 'file' and name.endswith('.elf')]
        if primary not in cache_files or not elf_paths:
            raise ValueError('Full cache must contain original firmware BIN and ELF')
        hashes = {}
        for name in [primary] + elf_paths:
            local = artifacts / Path(name).name
            self.action('download_cache_artifact_' + local.name,
                lambda name=name, local=local: b.run('pull', APP + '/' + name, str(local)))
            hashes[name] = digest(local)
            if hashes[name] != cache_files[name]['sha256']:
                raise ValueError('Original cached artifact differs from archive')
        relay = artifacts / 'relay.bin'
        self.action('download_original_relay', lambda: b.run('pull', self.hw.relay + '/unoq_stream', str(relay)))
        if hashes[primary] != self.original_identity.firmware_sha256 or digest(relay) != self.original_identity.relay_sha256:
            raise ValueError('Original downloaded pair identity differs')
        self.manifest_sha256 = archives['manifest_sha256']
        self.report['private_backup'] = dict(export=export_evidence, archives=archives,
            artifact_hashes=hashes, relay_sha256=digest(relay), stopped=True,
            cli_version=b.cli('version', capture=True).stdout,
            app_start_help=b.cli('app', 'start', '--help', capture=True).stdout)
        self.backup_ready = True
        self.save()

    def mutate(self):
        if not self.backup_ready:
            raise RuntimeError('No private mutation without verified full backup')
        self.check_stopped()
        original = self.hw.folder / 'candidate_app/sketch/sketch.ino'
        text = original.read_text()
        if text.count(ANCHOR) != 1:
            raise ValueError('Expected one harmless idle-loop sleep anchor')
        mutated = self.hw.folder / 'mutated_sketch.ino'
        mutated.write_text(text.replace(ANCHOR, ANCHOR.replace('K_MSEC(1)', 'K_MSEC(2)'), 1))
        extra = self.hw.folder / EXTRA
        extra.write_text('private_same_app_rollback_rehearsal: true\n')
        expected = dict(self.original_sources)
        if EXTRA in expected:
            raise ValueError('Private added-file rehearsal path already exists')
        expected['sketch/sketch.ino'] = digest(mutated)
        expected[EXTRA] = digest(extra)
        self.mutation_attempted = True  # Before push, including uncertain failure.
        self.save()
        b = self.hw.original
        self.action('push_mutated_sketch', lambda: b.run('push', str(mutated), APP + '/sketch/sketch.ino'))
        self.action('push_added_file', lambda: b.run('push', str(extra), APP + '/' + EXTRA))
        if self.remote_sources() != expected:
            raise ValueError('Mutated source manifest differs from intended two-file change')
        self.report['private_mutated_sources'] = expected
        self.action('start_same_app_with_mutation', self.hw.candidate.start)
        actual = self.identity()
        self.report['private_mutated_identity'] = actual.__dict__
        if (actual.firmware_sha256 == self.original_identity.firmware_sha256
                or actual.relay_sha256 != self.original_identity.relay_sha256):
            raise ValueError('Rehearsal requires genuinely changed firmware and unchanged relay')
        self.start_relay()
        self.report['private_mutated_recovery'] = self.recover(actual, 1)
        self.report['private_mutation_ok'] = True
        self.save()

    def restore_once(self):
        if self.restoration_attempted:
            raise RuntimeError('Private source/cache restore is not retried')
        self.restoration_attempted = True
        self.save()
        self.stop_pair()
        material = self.action('restore_exact_sources_and_full_cache',
            lambda: self.archive_command('restore', folder=self.remote_folder, manifest_sha256=self.manifest_sha256))
        if not material.get('sources_exact') or not material.get('cache_exact') or material['source_files'] != self.original_sources:
            raise ValueError('Original material is not exact; no private app restart')
        before = self.identity()
        self.report['private_before_restart'] = dict(identity=before.__dict__, material=material)
        if before != self.original_identity or self.remote_sources() != self.original_sources:
            raise ValueError('Original identity/sources differ before restart; no private app restart')
        self.save()
        self.action('start_same_app_after_full_restore', self.hw.candidate.start)
        after = self.identity()
        self.report['private_after_restart_identity'] = after.__dict__
        self.save()
        if after != self.original_identity or self.remote_sources() != self.original_sources:
            raise ValueError('CLI start changed original firmware/source hashes; exact rollback not demonstrated')
        self.start_relay()
        recovery = self.recover(self.original_identity, 10)
        relay = self.inspect_relay()
        cpu = self.hw.cpu_state(relay)
        governor = self.hw.original.shell('cat', self.hw.governor_path, capture=True).stdout.strip()
        checks = dict(identity_equal=self.identity() == self.original_identity,
            sources_exact=self.remote_sources() == self.original_sources,
            relay_configuration_equal=relay_configuration_equal(relay, self.relay_inspect),
            relay_id_equal=relay['Id'] == self.relay_inspect['Id'], cpu_equal=cpu == self.private_cpu,
            governor_equal=governor == self.private_governor)
        return dict(ok=all(checks.values()), checks=checks, recovery=recovery,
                    identity=after.__dict__, cpu=cpu, governor=governor,
                    claim='Exact cached firmware identity before/after app start plus live acquisition; no MCU flash readback')


def orchestrate(hardware, report, save, rehearsal_factory=Rehearsal):
    captured = False
    private = None
    try:
        hardware.capture()
        captured = True
        save()
        hardware.prepare()
        hardware.restart()
        private = rehearsal_factory(hardware)
        hardware.action('same_app_capture_private_baseline', private.capture_baseline)
        hardware.action('same_app_create_verified_backup', private.backup)
        hardware.action('same_app_mutation_and_new_firmware_gate', private.mutate)
    except BaseException as exc:
        report['error'] = repr(exc)
    finally:
        if private is not None and private.mutation_attempted:
            try:
                report['private_restoration'] = hardware.action('same_app_exact_restore_and_recovery', private.restore_once)
            except BaseException as exc:
                report['private_restore_error'] = repr(exc)
        if captured:
            try:
                report['production_restoration'] = hardware.restore()
            except BaseException as exc:
                report['production_restore_error'] = repr(exc)
        report['ok'] = bool('error' not in report and report.get('private_mutation_ok') and report.get('private_restoration', {}).get('ok')
                            and report.get('production_restoration', {}).get('hardware_restored'))
        save()
    return report['ok']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    if not args.run:
        print(json.dumps(plan(), indent=2, ensure_ascii=False))
        return 0
    from monitor.v18.board_owner import board_owner
    folder = EXP / 'resultados' / ('same_app_restore_' + time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    (folder / 'runner.py').write_bytes(Path(__file__).read_bytes())
    (folder / 'archive_helper.py').write_bytes((EXP / 'rehearsal_archive.py').read_bytes())
    report = dict(ok=False, recipe='batcharena', private=True, plan=plan(),
                  runner_sha256=digest(Path(__file__)), archive_helper_sha256=digest(EXP / 'rehearsal_archive.py'))
    journal = ProbeJournal(folder / 'report.json', report)
    hardware = Hardware(folder, report)
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    with board_owner(hardware.original.serial, 'V18 private same-app rollback rehearsal'), private_profiles(hardware.source):
        ok = orchestrate(hardware, report, journal.save)
    print(folder / 'report.json')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
