"""Pure archive and injected rehearsal tests; no Q, compiler or subprocess."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from experimentos.fs_max_v18 import rehearsal_archive as archive
from experimentos.fs_max_v18 import rehearse_same_app_restore as rehearsal


class ArchiveTests(unittest.TestCase):
    def fixture(self, folder):
        root = folder / 'app'
        (root / 'sketch').mkdir(parents=True)
        (root / '.cache/sketch').mkdir(parents=True)
        (root / '.cache/.venv/bin').mkdir(parents=True)
        (root / 'app.yaml').write_text('name: Scope V18 Rate Probe BatchArena\n')
        (root / 'sketch/sketch.ino').write_text('original idle(1);\n')
        (root / '.cache/sketch/sketch.ino.bin').write_bytes(b'original firmware')
        (root / '.cache/sketch/_debug.elf').write_bytes(b'original ELF')
        (root / '.cache/sketch/build.options.json').write_text('{"original": true}')
        outside = folder / 'outside'
        outside.write_bytes(b'outside sentinel')
        (root / '.cache/.venv/bin/python3').symlink_to(outside)
        os.utime(root / 'sketch/sketch.ino', ns=(1700000000123456789, 1700000000987654321))
        return root, outside

    def test_full_cache_and_source_roundtrip_with_metadata_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            root, outside = self.fixture(folder)
            original_sources = archive.snapshot(root, 'sources')
            original_cache = archive.snapshot(root, 'cache')
            backup = folder / 'backup'
            result = archive.backup(root, backup)
            for kind in ('sources', 'cache'):
                proof = result['staging_verification'][kind]
                self.assertTrue(proof['exact'])
                self.assertEqual(proof['stage'], 'verify_' + kind)
                self.assertEqual(archive.snapshot(backup / ('verify_' + kind), kind),
                                 original_sources if kind == 'sources' else original_cache)
                self.assertEqual(archive.digest(backup / ('verify_' + kind + '_manifest.json')),
                                 proof['manifest_sha256'])
            (root / 'sketch/sketch.ino').write_text('mutated idle(2);\n')
            (root / archive.EXTRA).write_text('new: true\n')
            (root / '.cache/sketch/sketch.ino.bin').write_bytes(b'new firmware')
            (root / '.cache/sketch/build.options.json').write_text('{"original": false}')
            (root / '.cache/new_build_metadata').write_bytes(b'new')
            restored = archive.restore(root, backup, result['manifest_sha256'])
            self.assertTrue(restored['sources_exact'])
            self.assertTrue(restored['cache_exact'])
            self.assertEqual(archive.snapshot(root, 'sources'), original_sources)
            self.assertEqual(archive.snapshot(root, 'cache'), original_cache)
            self.assertFalse((root / archive.EXTRA).exists())
            self.assertTrue((backup / 'mutated_cache/new_build_metadata').is_file())
            self.assertEqual(outside.read_bytes(), b'outside sentinel')
            self.assertEqual(os.readlink(root / '.cache/.venv/bin/python3'), str(outside))

    def test_unknown_added_source_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            root, _ = self.fixture(folder)
            result = archive.backup(root, folder / 'backup')
            unknown = root / 'unowned.yml'
            unknown.write_text('must remain')
            with self.assertRaisesRegex(ValueError, 'Unowned'):
                archive.restore(root, folder / 'backup', result['manifest_sha256'])
            self.assertEqual(unknown.read_text(), 'must remain')
            self.assertFalse((folder / 'backup/mutated_cache').exists())

    def test_metadata_permission_failure_aborts_backup_before_source_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            root, _ = self.fixture(folder)
            original_sources = archive.snapshot(root, 'sources')
            original_cache = archive.snapshot(root, 'cache')
            with patch.object(archive, 'metadata', side_effect=PermissionError('os.chown denied')):
                with self.assertRaisesRegex(PermissionError, 'chown denied'):
                    archive.backup(root, folder / 'backup')
            self.assertEqual(archive.snapshot(root, 'sources'), original_sources)
            self.assertEqual(archive.snapshot(root, 'cache'), original_cache)
            self.assertFalse((root / archive.EXTRA).exists())
            self.assertFalse((folder / 'backup/manifest.json').exists())
            self.assertFalse((folder / 'backup/restore_sources').exists())

    def test_corrupted_cache_archive_prevents_any_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            root, _ = self.fixture(folder)
            result = archive.backup(root, folder / 'backup')
            (folder / 'backup/cache.tar').write_bytes(b'changed archive')
            (root / 'sketch/sketch.ino').write_text('mutated source')
            with self.assertRaisesRegex(ValueError, 'archive changed'):
                archive.restore(root, folder / 'backup', result['manifest_sha256'])
            self.assertEqual((root / 'sketch/sketch.ino').read_text(), 'mutated source')
            self.assertFalse((folder / 'backup/mutated_cache').exists())

    def test_source_symlink_or_unsafe_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            root, outside = self.fixture(folder)
            (root / 'source_alias').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'Source symlink'):
                archive.snapshot(root, 'sources')
            with self.assertRaisesRegex(ValueError, 'explicit private'):
                archive.main(['restore', '--root', str(root), '--folder', str(folder)])

    def test_unpack_rejects_traversal_and_symlink_parents(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with tarfile.open(folder / 'empty.tar', 'w'):
                pass
            records = {'../escape': dict(kind='directory')}
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                archive.unpack(folder / 'empty.tar', records, folder / 'out')
            records = {'link': dict(kind='symlink'), 'link/escape': dict(kind='file')}
            with self.assertRaisesRegex(ValueError, 'non-directory parent'):
                archive.unpack(folder / 'empty.tar', records, folder / 'out2')


class FakeHardware:
    def __init__(self, report, events, fail=None):
        self.report, self.events, self.fail = report, events, fail

    def event(self, name):
        self.events.append(name)
        if name == self.fail:
            raise RuntimeError(name)

    def capture(self): self.event('production_capture')
    def prepare(self): self.event('production_prepare_private')
    def restart(self): self.event('initial_private_restart')

    def action(self, name, operation):
        return operation()

    def restore(self):
        self.event('production_restore')
        return dict(hardware_restored=True)


class FakeRehearsal:
    def __init__(self, hardware, fail=None):
        self.hw, self.fail = hardware, fail
        self.mutation_attempted = False

    def capture_baseline(self): self.hw.event('private_baseline')
    def backup(self):
        self.hw.event('private_exact_backup')
        if self.fail == 'backup_metadata':
            raise PermissionError('staging metadata reconstruction denied')

    def mutate(self):
        self.mutation_attempted = True
        self.hw.event('private_mutate')
        if self.fail == 'mutate':
            raise RuntimeError('mutating push failed after effect')
        self.hw.report['private_mutation_ok'] = True

    def restore_once(self):
        self.hw.event('private_exact_restore')
        if self.fail == 'restore':
            raise RuntimeError('private restore failed')
        return dict(ok=True)


class RehearsalTests(unittest.TestCase):
    def transaction(self, failure=None, hardware_failure=None):
        report, events = {}, []
        hardware = FakeHardware(report, events, hardware_failure)
        ok = rehearsal.orchestrate(hardware, report, lambda: None,
                                    lambda hw: FakeRehearsal(hw, failure))
        return ok, report, events

    def test_private_recovery_precedes_production_restore(self):
        ok, report, events = self.transaction()
        self.assertTrue(ok)
        self.assertLess(events.index('private_exact_backup'), events.index('private_mutate'))
        self.assertLess(events.index('private_exact_restore'), events.index('production_restore'))
        self.assertEqual(events.count('initial_private_restart'), 1)

    def test_mutating_failure_still_attempts_private_restore_then_production(self):
        ok, report, events = self.transaction('mutate')
        self.assertFalse(ok)
        self.assertTrue(report['private_restoration']['ok'])
        self.assertEqual(events.count('private_exact_restore'), 1)
        self.assertEqual(events[-1], 'production_restore')

    def test_private_restore_failure_never_blocks_production_restore(self):
        ok, report, events = self.transaction('restore')
        self.assertFalse(ok)
        self.assertIn('private_restore_error', report)
        self.assertTrue(report['production_restoration']['hardware_restored'])
        self.assertEqual(events.count('private_exact_restore'), 1)
        self.assertEqual(events[-1], 'production_restore')

    def test_backup_metadata_failure_prevents_mutation_and_restores_production(self):
        ok, report, events = self.transaction('backup_metadata')
        self.assertFalse(ok)
        self.assertIn('PermissionError', report['error'])
        self.assertNotIn('private_mutate', events)
        self.assertNotIn('private_exact_restore', events)
        self.assertTrue(report['production_restoration']['hardware_restored'])
        self.assertEqual(events[-1], 'production_restore')

    def test_setup_failure_restores_production_after_capture_only(self):
        for name in ('production_capture', 'production_prepare_private', 'initial_private_restart'):
            with self.subTest(failure=name):
                ok, report, events = self.transaction(hardware_failure=name)
                self.assertFalse(ok)
                self.assertEqual('production_restore' in events, name != 'production_capture')

    def test_export_is_exact_with_known_prefix_and_rejects_extra_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'export.zip'
            with zipfile.ZipFile(path, 'w') as output:
                output.writestr(Path(rehearsal.APP).name + '/app.yaml', b'name: private\n')
            expected = {'app.yaml': hashlib.sha256(b'name: private\n').hexdigest()}
            self.assertTrue(rehearsal.verify_export(path, expected)['exact'])
            with zipfile.ZipFile(path, 'a') as output:
                output.writestr(Path(rehearsal.APP).name + '/unowned', b'extra')
            with self.assertRaisesRegex(ValueError, 'differs'):
                rehearsal.verify_export(path, expected)

    def test_plan_constructs_no_hardware(self):
        with patch.object(rehearsal, 'Hardware', side_effect=AssertionError('hardware')), patch('sys.stdout', new=io.StringIO()) as output:
            self.assertEqual(rehearsal.main([]), 0)
            self.assertEqual(json.loads(output.getvalue())['app'], archive.APP)


if __name__ == '__main__':
    unittest.main()
