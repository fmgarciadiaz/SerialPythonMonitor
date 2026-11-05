"""Fault injection for the update transaction; no board or subprocess I/O."""
from contextlib import nullcontext
import unittest
from monitor.v19.q_support.prepare import execute

FLAGS=('production_backend_qualified rollback_rehearsal_verified cached_launcher_verified '
       'generator_off wav_idle receiver_closed identity_verified source_manifest_verified '
       'export_verified source_archive_verified full_cache_verified firmware_elf_bin_verified '
       'relay_verified paired_manifest_persisted source_hashes_equal compiled_firmware_hash_equal '
       'precompiled_relay_hash_equal fresh_cache_planned baseline_unchanged backups_verified '
       'candidate_verified no_other_reader cache_layout_verified accepted_identity_equal '
       'sources_exact snapshot_equal continuous integrity_ok cpu_equal relay_configuration_verified '
       'cache_exact firmware_exact relay_exact identity_equal relay_configuration_equal').split()


class Backend:
    def __init__(self,fail=None,rollback_fail=False):
        self.calls=[];self.fail=fail;self.rollback_fail=rollback_fail
    def owner(self):return nullcontext()
    def __getattr__(self,name):
        def operation(*args):
            self.calls.append(name)
            if name==self.fail or (self.rollback_fail and name=='restore_cache'):
                self.fail=None
                raise RuntimeError('injected '+name)
            result=dict.fromkeys(FLAGS,True)
            result.update(app_sources={'sketch/a.h':'a'*64},seconds=10,
                candidate_identity={'firmware_sha256':'b'*64,'relay_sha256':'c'*64},
                candidate_cache_policy='rebuild_in_production_app')
            return result
        return operation


class UpdateTransactionTests(unittest.TestCase):
    def run_update(self,backend):
        report={};acceptance=dict(sources=dict(app={'sketch/a.h':'a'*64}),
            candidate_identity={'firmware_sha256':'b'*64,'relay_sha256':'c'*64})
        execute(backend,acceptance,report,lambda:None)
        return report
    def test_compile_and_recheck_failures_restore_original_pair(self):
        for failure in ('quiesce','stop_old_relay','rename_old_relay','stop_app','prepare','recheck'):
            with self.subTest(failure=failure):
                backend=Backend(failure);report=self.run_update(backend)
                self.assertFalse(report['ok']);self.assertTrue(report['rollback']['ok'])
                self.assertFalse(report['production_changed']);self.assertFalse(report['state_uncertain'])
                self.assertNotIn('install_sources',backend.calls)
                self.assertIn('verify_original',backend.calls)
    def test_failed_rollback_is_explicitly_uncertain(self):
        report=self.run_update(Backend('prepare',rollback_fail=True))
        self.assertFalse(report['ok']);self.assertFalse(report['rollback']['ok'])
        self.assertTrue(report['production_changed']);self.assertTrue(report['state_uncertain'])
    def test_build_occurs_only_after_both_app_and_relay_stopped(self):
        backend=Backend();report=self.run_update(backend)
        self.assertTrue(report['ok'])
        for operation in ('backup','quiesce','stop_old_relay','rename_old_relay','stop_app'):
            self.assertLess(backend.calls.index(operation),backend.calls.index('prepare'))
        self.assertLess(backend.calls.index('recheck'),backend.calls.index('install_sources'))
        self.assertFalse(report['state_uncertain'])

    def test_live_relay_guard_rejects_build_before_any_stage_write(self):
        from unittest.mock import Mock
        from monitor.v19.q_support.backend import ProductionBackend
        backend=ProductionBackend({})
        backend.original_relay_id='original'
        backend._inspect=Mock(return_value={'Id':'original','State':{'Running':True}})
        backend._output=Mock(return_value='scope-v19-main-1')
        backend._board=Mock()
        with self.assertRaisesRegex(RuntimeError,'must be stopped'):
            backend.prepare({}, {'captured':True})
        backend._board.assert_not_called()
