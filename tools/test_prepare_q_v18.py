"""Pure injected tests for V18 update/rollback ordering; never access Q."""
from contextlib import contextmanager
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import prepare_q_v18 as prepare


OLD = {'app.yaml': '1' * 64, 'sketch/old.h': '2' * 64}
NEW = {'app.yaml': '3' * 64, 'sketch/new.h': '4' * 64}
IDENTITY = {'firmware_sha256': 'a' * 64, 'relay_sha256': 'b' * 64}
ACCEPTANCE = {'sources': {'app': NEW}, 'candidate_identity': IDENTITY}


class FakeBackend:
    """Model source/cache changes and require original material before restart."""
    def __init__(self, fail=None, bad_material=False):
        self.events = []
        self.fail, self.bad_material = fail, bad_material
        self.owned = False
        self.sources = dict(OLD)
        self.cache = 'old full cache with ELF/BIN/metadata'
        self.saved_cache = self.cache
        self.original_verified = False

    @contextmanager
    def owner(self):
        self.owned = True
        self.events.append('owner_enter')
        try:
            yield
        finally:
            self.events.append('owner_exit')
            self.owned = False

    def event(self, name):
        assert self.owned
        self.events.append(name)
        if self.fail == name:
            self.fail = None
            raise RuntimeError('injected ' + name)

    def preflight(self, acceptance):
        self.event('preflight')
        return dict(production_backend_qualified=True, rollback_rehearsal_verified=True,
                    cached_launcher_verified=True)

    def capture(self):
        self.event('capture')
        return dict(generator_off=True, wav_idle=True, receiver_closed=True,
                    identity_verified=True, source_manifest_verified=True, app_sources=OLD)

    def backup(self, baseline):
        self.event('backup')
        return dict(export_verified=True, source_archive_verified=True, full_cache_verified=True,
                    firmware_elf_bin_verified=True, relay_verified=True, paired_manifest_persisted=True)

    def prepare(self, acceptance, baseline):
        self.event('prepare')
        return dict(source_hashes_equal=True, compiled_firmware_hash_equal=True,
                    precompiled_relay_hash_equal=True, fresh_cache_planned=True,
                    candidate_cache_policy='rebuild_in_production_app',
                    candidate_identity=dict(IDENTITY))

    def recheck(self, baseline, backup, prepared):
        self.event('recheck')
        return dict(baseline_unchanged=True, backups_verified=True, candidate_verified=True,
                    no_other_reader=True)

    def quiesce(self, baseline): self.event('quiesce')
    def stop_old_relay(self, baseline): self.event('stop_old_relay')
    def rename_old_relay(self, baseline): self.event('rename_old_relay')
    def stop_app(self): self.event('stop_app')

    def install_sources(self, acceptance, changes):
        self.sources = dict(NEW)  # Fail after partial/complete effect too.
        self.event('install_sources')

    def install_cache(self, prepared):
        self.cache = 'candidate cache'
        self.event('install_cache')

    def start_new_app(self, prepared):
        self.event('start_new_app')
        return dict(cache_layout_verified=True, compiled_firmware_hash_equal=True)
    def start_new_relay(self, baseline, prepared): self.event('start_new_relay')

    def verify_new(self, baseline, acceptance, prepared, seconds):
        self.event('verify_new')
        return dict(accepted_identity_equal=True, sources_exact=True, snapshot_equal=True,
                    continuous=True, integrity_ok=True, cpu_equal=True,
                    relay_configuration_verified=True, seconds=seconds)

    def stop_new_relay(self, baseline, prepared): self.event('stop_new_relay')

    def restore_sources(self, backup, changes):
        self.event('restore_sources')
        self.sources = dict(OLD)
        assert changes['added'] == ['sketch/new.h']
        assert changes['remove'] == ['sketch/old.h']

    def restore_cache(self, backup):
        self.event('restore_cache')
        self.cache = self.saved_cache

    def verify_original_material(self, baseline, backup):
        self.event('verify_original_material')
        self.original_verified = self.sources == OLD and self.cache == self.saved_cache and not self.bad_material
        return dict(sources_exact=self.original_verified, cache_exact=self.original_verified,
                    firmware_exact=self.original_verified, relay_exact=True)

    def start_original_app(self, baseline, backup):
        assert self.original_verified, 'Never start with uncertain original sources/cache'
        assert self.sources == OLD and self.cache == self.saved_cache
        self.event('start_original_app')

    def restore_old_relay(self, baseline): self.event('restore_old_relay')
    def restore_cpu(self, baseline): self.event('restore_cpu')

    def restore_snapshot(self, baseline, seconds):
        self.event('restore_snapshot')
        return dict(snapshot_equal=True, continuous=True, integrity_ok=True, seconds=seconds)

    def verify_original(self, baseline, backup):
        self.event('verify_original')
        return dict(identity_equal=True, sources_exact=True, relay_configuration_equal=True, cpu_equal=True)


class TransactionTests(unittest.TestCase):
    def run_backend(self, backend, removals=('sketch/old.h',)):
        report = {}
        snapshots = []
        ok = prepare.execute(backend, ACCEPTANCE, report,
                             lambda: snapshots.append(copy.deepcopy(report)), removals)
        return ok, report, snapshots

    def test_success_prepares_and_hashgates_before_any_production_mutation(self):
        backend = FakeBackend()
        ok, report, snapshots = self.run_backend(backend)
        self.assertTrue(ok)
        self.assertTrue(report['production_changed'])
        self.assertIsNone(report['rollback'])
        events = backend.events
        for name in ('backup', 'prepare', 'recheck'):
            self.assertLess(events.index(name), events.index('quiesce'))
        self.assertLess(events.index('stop_old_relay'), events.index('stop_app'))
        self.assertLess(events.index('rename_old_relay'), events.index('install_sources'))
        self.assertEqual(events[-1], 'owner_exit')
        for phase in report['journal']:
            self.assertEqual(phase['state'], 'completed')
            self.assertTrue(any(any(row['phase'] == phase['phase'] and row['state'] == 'intent'
                                    for row in saved['journal']) for saved in snapshots))

    def test_each_production_failure_attempts_one_exact_rollback(self):
        for failure in ('quiesce', 'stop_old_relay', 'rename_old_relay', 'stop_app',
                        'install_sources', 'install_cache', 'start_new_app', 'start_new_relay', 'verify_new'):
            with self.subTest(failure=failure):
                backend = FakeBackend(failure)
                # Each injected failure fires once. Rollback's stop_app is
                # independent of a forward stop_app that failed or timed out.
                ok, report, _ = self.run_backend(backend)
                self.assertFalse(ok)
                self.assertTrue(report['rollback']['ok'])
                self.assertFalse(report['production_changed'])
                self.assertEqual(backend.sources, OLD)
                self.assertEqual(backend.cache, backend.saved_cache)
                self.assertEqual(backend.events.count('start_original_app'), 1)
                self.assertEqual(backend.events.count('restore_sources'), 1)
                self.assertLess(backend.events.index('restore_sources'), backend.events.index('start_original_app'))
                self.assertLess(backend.events.index('restore_cache'), backend.events.index('start_original_app'))
                self.assertEqual(backend.events[-1], 'owner_exit')

    def test_preparation_failure_never_stops_production_or_rolls_it_back(self):
        for failure in ('preflight', 'capture', 'backup', 'prepare', 'recheck'):
            with self.subTest(failure=failure):
                backend = FakeBackend(failure)
                ok, report, _ = self.run_backend(backend)
                self.assertFalse(ok)
                self.assertIsNone(report['rollback'])
                self.assertNotIn('quiesce', backend.events)
                self.assertNotIn('stop_app', backend.events)

    def test_restore_material_failure_blocks_original_app_and_relay_start(self):
        backend = FakeBackend('verify_new', bad_material=True)
        ok, report, _ = self.run_backend(backend)
        self.assertFalse(ok)
        self.assertFalse(report['rollback']['ok'])
        self.assertTrue(report['production_changed'])
        self.assertNotIn('start_original_app', backend.events)
        self.assertNotIn('restore_old_relay', backend.events)
        self.assertEqual(backend.events.count('verify_original_material'), 1)

    def test_unlisted_source_deletion_stops_before_quiesce(self):
        backend = FakeBackend()
        ok, _, _ = self.run_backend(backend, removals=())
        self.assertFalse(ok)
        self.assertNotIn('quiesce', backend.events)

    def test_wrong_prepared_binary_identity_stops_before_quiesce(self):
        backend = FakeBackend()
        original = backend.prepare
        def prepare_wrong(*args):
            result = original(*args)
            result['candidate_identity']['firmware_sha256'] = 'c' * 64
            return result
        backend.prepare = prepare_wrong
        ok, _, _ = self.run_backend(backend)
        self.assertFalse(ok)
        self.assertNotIn('quiesce', backend.events)

    def test_live_adapter_is_closed_without_any_hardware_construction(self):
        report = {}
        ok = prepare.execute(prepare.UnqualifiedProductionBackend(), ACCEPTANCE, report, lambda: None)
        self.assertFalse(ok)
        self.assertIn('ProductionNotQualified', report['error'])
        self.assertEqual([e['phase'] for e in report['journal']], ['preflight'])
        self.assertFalse(report['production_changed'])

    def test_keyboard_interrupt_after_update_still_restores_before_owner_exit(self):
        backend = FakeBackend()
        def interrupted(*args):
            raise KeyboardInterrupt('signal 15')
        backend.verify_new = interrupted
        ok, report, _ = self.run_backend(backend)
        self.assertFalse(ok)
        self.assertTrue(report['rollback']['ok'])
        self.assertEqual(backend.events[-1], 'owner_exit')
        self.assertLess(backend.events.index('restore_cache'), backend.events.index('start_original_app'))


class AcceptanceTests(unittest.TestCase):
    def make_receipt(self, root):
        app, relay = root / 'app', root / 'relay'
        app.mkdir(); relay.mkdir()
        (app / 'app.yaml').write_text('name: Scope V18\n')
        (relay / 'relay.c').write_text('accepted relay\n')
        receipt = dict(schema=1, version=18, accepted=True, public_rates_changed=False,
                       sources=dict(app=prepare.source_manifest(app), relay=prepare.source_manifest(relay)))
        for kind in ('firmware', 'relay', 'evidence', 'rollback_rehearsal', 'prebuild_proof'):
            artifact = root / (kind + '.bin')
            artifact.write_bytes(kind.encode())
            receipt[kind] = dict(path=artifact.name, sha256=prepare.sha256(artifact))
        receipt['evidence'].update(physical_acceptance=True, restoration_verified=True)
        path = root / 'accepted.json'
        path.write_text(json.dumps(receipt))
        return path, app, relay, receipt

    def test_explicit_receipt_matches_all_sources_and_binary_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path, app, relay, _ = self.make_receipt(Path(directory))
            accepted = prepare.load_acceptance(path, app, relay)
            self.assertEqual(accepted['candidate_identity']['firmware_sha256'], prepare.sha256(path.parent / 'firmware.bin'))
            (path.parent / 'firmware.bin').write_bytes(b'changed but still exists')
            with self.assertRaisesRegex(ValueError, 'artifact missing or changed'):
                prepare.load_acceptance(path, app, relay)

    def test_missing_acceptance_hash_or_unaccepted_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path, app, relay, receipt = self.make_receipt(Path(directory))
            del receipt['firmware']['sha256']
            path.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):
                prepare.load_acceptance(path, app, relay)
            receipt['firmware']['sha256'] = prepare.sha256(path.parent / 'firmware.bin')
            path.write_text(json.dumps(receipt))
            (app / 'new.h').write_text('unaccepted')
            with self.assertRaisesRegex(ValueError, 'source hashes differ'):
                prepare.load_acceptance(path, app, relay)

    def test_no_traversal_cache_or_v17_source_deletions(self):
        for name in ('../v17/sketch.ino', '/scope-v17/sketch.ino', '.cache/sketch/a.bin', 'a/../b', 'a\\b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                prepare.source_name(name)

    def test_default_prints_plan_without_acceptance_or_hardware(self):
        with patch('sys.stdout', new=io.StringIO()) as output:
            self.assertEqual(prepare.main([]), 0)
            self.assertFalse(json.loads(output.getvalue())['production_adapter_qualified'])


if __name__ == '__main__':
    unittest.main()
