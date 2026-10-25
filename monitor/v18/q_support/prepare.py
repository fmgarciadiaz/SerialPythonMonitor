#!/usr/bin/env python3
"""Receipt-gated Scope V18 update with exact paired backup and rollback.

The hardware backend checks physical acceptance, the same-app rollback record,
source and binary hashes before any production mutation. Default action prints
its plan; --run requires the accepted receipt.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import tempfile

ROOT = Path(__file__).resolve().parents[3]
APP = '/home/arduino/ArduinoApps/scope-v18'
NAME = 'Scope V18'
CONTAINER = 'serialmonitor-usb-stream-v18'
APP_SOURCES = ROOT / 'arduino/v18/oscilloscope'
RELAY_SOURCES = ROOT / 'arduino/v18/relay'
EXCLUDED = {'.git', '.cache', '__pycache__', 'data', '.venv'}
QUALIFICATION_REQUIRED = (
    'Installed CLI binary/version and its actual start/cache behavior must be recorded.',
    'A private same-app rehearsal must restore source archive AND full original cache, '
    'including ELF/BIN and build metadata, before starting the original app.',
    'That rehearsal must remove new source files, restore deleted old files, and verify '
    'old firmware/relay hashes, source hashes, relay config, CPU state and 10 s recovery.',
    'A reviewed hardware adapter tied to that proven behavior must implement this engine.',
)


class ProductionNotQualified(RuntimeError):
    pass


def plan():
    return dict(app=NAME, remote_app=APP, relay_container=CONTAINER,
        local_app='arduino/v18/oscilloscope', local_relay='arduino/v18/relay',
        production_adapter_qualified=False, public_rate_promotion=False,
        guard_requirements=list(QUALIFICATION_REQUIRED),
        preparation=[
            'Acquire V18 board_owner for all Q I/O; verify only Scope V18 and its relay are active.',
            'Capture SPI, generator OFF and WAV IDLE snapshot, firmware/relay identities, '
            'container inspect and active/inactive CPU state.',
            'Export original app; verify an exact original-source archive and full cache archive; '
            'download original firmware ELF/BIN and mounted relay; persist paired backup manifest.',
            'Stage only accepted arduino/v18 sources; compile firmware before stopping production; '
            'hash-gate sources, compiled firmware and already compiled accepted relay.',
            'Copy accepted relay into a new standard digest cache; reject cache collisions; '
            'recheck production identity/sources/snapshot and all rollback material.',
        ],
        deployment=[
            'Quiesce acquisition; close receiver before Q administrative operations.',
            'Stop and retain old relay container under a unique saved name; stop Scope V18.',
            'Push exact V18 sources; remove only explicitly enumerated obsolete source files; '
            'install the proven prepared-cache layout with accepted firmware.',
            'Start SAME Scope V18 app through the qualified launcher; start new named relay.',
            'Verify accepted binaries/sources, snapshot settings, CPU/relay configuration and '
            '10 s continuous recovery; retain original container and paired backup.',
        ],
        rollback=[
            'One attempt: stop/remove only the transaction-owned new relay; stop Scope V18.',
            'Restore exact original source archive and remove explicitly recorded added sources.',
            'Restore full original cache and metadata, including original ELF/BIN; '
            'verify exact original sources/cache/binary hashes BEFORE original app restart.',
            'Start original Scope V18 once; recover retained original relay name/container once.',
            'Restore original CPU baseline and acquisition/generator snapshot; verify original '
            'identity, source hashes, relay inspect, CPU state and 10 s recovery.',
            'If source/cache verification fails, do not start any app/relay with uncertain firmware.',
        ])


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def valid_hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def source_name(name):
    if not isinstance(name, str):
        raise ValueError('Source names must be relative strings')
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or path.as_posix() != name
            or any(part in ('.', '..') or part in EXCLUDED for part in path.parts)
            or '\\' in name):
        raise ValueError(f'Unsafe source name: {name!r}')
    return name


def checked_manifest(manifest):
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError('Nonempty exact source manifest required')
    for name, digest in manifest.items():
        source_name(name)
        if not valid_hash(digest):
            raise ValueError(f'Invalid source SHA256: {name!r}')
    return dict(manifest)


def source_manifest(folder):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('Regular source directory required')
    result = {}
    for path in sorted(folder.rglob('*')):
        relative = path.relative_to(folder)
        if any(part in EXCLUDED for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f'Source symlink is not accepted: {relative}')
        if path.is_file() and path.name != '.DS_Store' and path.suffix != '.pyc':
            result[source_name(relative.as_posix())] = sha256(path)
    return checked_manifest(result)


def source_changes(original, candidate, allowed_removals=()):
    """Only exact enumerated files may be deleted in apply or rollback."""
    original, candidate = checked_manifest(original), checked_manifest(candidate)
    allowed = {source_name(name) for name in allowed_removals}
    removed = set(original) - set(candidate)
    if removed != allowed:
        raise ValueError('Explicit --remove-source list must equal obsolete original sources')
    return dict(remove=sorted(removed), added=sorted(set(candidate) - set(original)),
                replace=sorted(name for name in set(candidate) & set(original)
                               if candidate[name] != original[name]))


def load_acceptance(path, app_sources=APP_SOURCES, relay_sources=RELAY_SOURCES):
    """An existing binary is never acceptance; all bytes must match a receipt."""
    path = Path(path).resolve()
    receipt = json.loads(path.read_text())
    if (receipt.get('schema') != 1 or receipt.get('version') != 18
            or receipt.get('accepted') is not True or receipt.get('public_rates_changed') is not False):
        raise ValueError('Explicit accepted V18 receipt without public-rate promotion required')
    expected = receipt.get('sources', {})
    for key, folder in (('app', app_sources), ('relay', relay_sources)):
        if checked_manifest(expected.get(key)) != source_manifest(folder):
            raise ValueError(f'Accepted {key} source hashes differ from current V18 sources')
    if not any(line.strip() == 'name: Scope V18' for line in (Path(app_sources) / 'app.yaml').read_text().splitlines()):
        raise ValueError('Only production app name Scope V18 is accepted')
    artifacts = {}
    for key in ('firmware', 'relay', 'evidence', 'rollback_rehearsal', 'prebuild_proof'):
        item = receipt.get(key, {})
        if not isinstance(item, dict) or not valid_hash(item.get('sha256')) or not isinstance(item.get('path'), str):
            raise ValueError(f'Explicit {key} path and SHA256 required')
        artifact = (path.parent / item['path']).resolve()
        if not artifact.is_file() or sha256(artifact) != item['sha256']:
            raise ValueError(f'Accepted {key} artifact missing or changed')
        artifacts[key] = dict(path=str(artifact), sha256=item['sha256'])
    evidence = receipt['evidence']
    if evidence.get('physical_acceptance') is not True or evidence.get('restoration_verified') is not True:
        raise ValueError('Physical acceptance with verified restoration required')
    return dict(receipt_path=str(path), receipt_sha256=sha256(path),
                sources=expected, artifacts=artifacts,
                candidate_identity={key + '_sha256': artifacts[key]['sha256'] for key in ('firmware', 'relay')})


class Journal:
    """Durable intent before each bounded operation; no mutating retry."""
    def __init__(self, report, save):
        self.report, self.save = report, save

    def step(self, name, operation):
        entry = dict(phase=name, state='intent')
        self.report.setdefault('journal', []).append(entry)
        self.save()
        try:
            result = operation()
        except BaseException as exc:
            entry.update(state='failed', error=repr(exc))
            self.save()
            raise
        entry['state'] = 'completed'
        self.save()
        return result


def _require(mapping, names, label):
    if not isinstance(mapping, dict) or any(mapping.get(name) is not True for name in names):
        raise RuntimeError(f'{label} evidence incomplete')


def rollback_once(backend, baseline, backup, prepared, changes, journal):
    """Do not start original app until BOTH exact sources and cache pass."""
    result = dict(ok=False, attempted=True, errors=[])
    def step(name, *args):
        return journal.step('rollback_' + name, lambda: getattr(backend, name)(*args))
    try:
        step('stop_new_relay', baseline, prepared)
        step('stop_app')
        step('restore_sources', backup, changes)
        step('restore_cache', backup)
        material = step('verify_original_material', baseline, backup)
        _require(material, ('sources_exact', 'cache_exact', 'firmware_exact', 'relay_exact'), 'Original restart material')
        result['material'] = material
        step('start_original_app', baseline, backup)
        step('restore_old_relay', baseline)
        step('restore_cpu', baseline)
        recovery = step('restore_snapshot', baseline, 10)
        _require(recovery, ('snapshot_equal', 'continuous', 'integrity_ok'), 'Rollback recovery')
        if recovery.get('seconds', 0) < 10:
            raise RuntimeError('Rollback needs at least ten real recovery seconds')
        final = step('verify_original', baseline, backup)
        _require(final, ('identity_equal', 'sources_exact', 'relay_configuration_equal', 'cpu_equal'), 'Original final verification')
        result.update(ok=True, recovery=recovery, final=final)
    except BaseException as exc:
        result['errors'].append(repr(exc))
    return result


def execute(backend, acceptance, report, save, allowed_removals=()):
    """Backend owns bounded Q I/O; it must close every receiver before admin.

    The live adapter verifies its receipt at runtime. Injected backends test
    the same operation order without Q. All backups and preparation are completed before quiescence.
    'dirty' is set BEFORE the first production mutation, including failed intent.
    """
    journal = Journal(report, save)
    baseline = backup = prepared = changes = None
    dirty = committed = False
    report.update(ok=False, production_changed=False, rollback=None)
    with backend.owner():
        try:
            qualification = journal.step('preflight', lambda: backend.preflight(acceptance))
            _require(qualification, ('production_backend_qualified', 'rollback_rehearsal_verified',
                                      'cached_launcher_verified'), 'Production qualification')
            baseline = journal.step('capture', backend.capture)
            _require(baseline, ('generator_off', 'wav_idle', 'receiver_closed',
                               'identity_verified', 'source_manifest_verified'), 'Baseline capture')
            report['baseline'] = baseline
            backup = journal.step('backup', lambda: backend.backup(baseline))
            _require(backup, ('export_verified', 'source_archive_verified', 'full_cache_verified',
                             'firmware_elf_bin_verified', 'relay_verified', 'paired_manifest_persisted'), 'Rollback backup')
            report['backup'] = backup
            prepared = journal.step('prepare', lambda: backend.prepare(acceptance, baseline))
            _require(prepared, ('source_hashes_equal', 'compiled_firmware_hash_equal',
                               'precompiled_relay_hash_equal', 'fresh_cache_planned'), 'Accepted candidate')
            if prepared.get('candidate_cache_policy') != 'rebuild_in_production_app':
                raise RuntimeError('Private candidate cache cannot be installed in production')
            if prepared.get('candidate_identity') != acceptance['candidate_identity']:
                raise RuntimeError('Compiled candidate identity differs from acceptance')
            report['prepared'] = prepared
            changes = source_changes(baseline['app_sources'], acceptance['sources']['app'], allowed_removals)
            report['source_changes'] = changes
            recheck = journal.step('recheck', lambda: backend.recheck(baseline, backup, prepared))
            _require(recheck, ('baseline_unchanged', 'backups_verified', 'candidate_verified',
                              'no_other_reader'), 'Pre-stop recheck')
            save()
            dirty = True
            for name, args in (
                ('quiesce', (baseline,)), ('stop_old_relay', (baseline,)),
                ('rename_old_relay', (baseline,)), ('stop_app', ()),
                ('install_sources', (acceptance, changes)), ('install_cache', (prepared,)),
                ('start_new_app', (prepared,)), ('start_new_relay', (baseline, prepared)),
            ):
                result = journal.step(name, lambda name=name, args=args: getattr(backend, name)(*args))
                if name == 'start_new_app':
                    _require(result, ('cache_layout_verified', 'compiled_firmware_hash_equal'),
                             'Production app cache after start')
            recovery = journal.step('verify_new', lambda: backend.verify_new(baseline, acceptance, prepared, 10))
            report['verification'] = recovery
            save()
            _require(recovery, ('accepted_identity_equal', 'sources_exact', 'snapshot_equal',
                               'continuous', 'integrity_ok', 'cpu_equal', 'relay_configuration_verified'), 'Installed candidate')
            if recovery.get('seconds', 0) < 10:
                raise RuntimeError('Installed candidate needs at least ten real recovery seconds')
            report.update(verification=recovery, production_changed=True, ok=True)
            save()
            committed = True
        except BaseException as exc:
            report.update(error=repr(exc), ok=False)
        finally:
            if dirty and not committed:
                report['rollback'] = rollback_once(backend, baseline, backup, prepared, changes, journal)
                report['production_changed'] = not report['rollback']['ok']
            save()
    return report['ok']


class UnqualifiedProductionBackend:
    """No Board, ADB, launcher, cache mutation or deployment is constructed."""
    @contextmanager
    def owner(self):
        # No Q I/O exists here. The future adapter must replace this with the
        # interoperable monitor.v18.board_owner lock spanning capture/rollback.
        yield

    def preflight(self, acceptance):
        raise ProductionNotQualified('V18 production adapter closed: exact same-app source/full-cache '
            'rollback and cached launcher are not yet physically demonstrated. '
            'See docs/PREPARAR_Q_V18_TRANSACCIONAL.md. No Q operation attempted.')


def atomic_report(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--acceptance', type=Path)
    parser.add_argument('--remove-source', action='append', default=[])
    parser.add_argument('--report', type=Path, default=ROOT / 'diagnosticos/resultados_v18/prepare_q_review.json')
    args = parser.parse_args(argv)
    if not args.run:
        print(json.dumps(plan(), indent=2, ensure_ascii=False))
        return 0
    report = dict(schema=1, version=18, plan=plan())
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.acceptance is None:
            raise ValueError('--run requires an explicit accepted source/binary/evidence receipt')
        acceptance = load_acceptance(args.acceptance)
        report['acceptance'] = acceptance
        from monitor.v18.q_support.backend import ProductionBackend
        ok = execute(ProductionBackend(acceptance), acceptance, report,
                     lambda: atomic_report(args.report, report), args.remove_source)
    except BaseException as exc:
        report.update(ok=False, error=repr(exc), production_changed=False)
        atomic_report(args.report, report)
        ok = False
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
    print(args.report)
    if not ok:
        print(report.get('error', 'Preparation failed'))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
