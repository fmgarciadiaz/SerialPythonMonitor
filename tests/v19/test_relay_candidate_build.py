from pathlib import Path
import unittest
from tools.build_relay_candidate_v19 import execute_build
from tests.v19.test_q_update_transaction import Backend


class CandidateBuildTests(unittest.TestCase):
    def run_build(self,fail=False):
        backend=Backend();report={}
        capture=backend.capture
        identity=dict(firmware_sha256='b'*64,relay_sha256='c'*64)
        backend.capture=lambda:dict(capture(),identity=identity)
        def builder(*args):
            self.assertIn('stop_app',backend.calls)
            if fail:raise RuntimeError('compiler failed')
            return dict(path='private-candidate.bin',installed=False)
        execute_build(backend,dict(candidate_identity=identity),Path('.'),Path('.'),report,lambda:None,builder)
        return backend,report
    def test_successful_build_still_restores_original_pair(self):
        backend,report=self.run_build()
        self.assertTrue(report['ok']);self.assertTrue(report['restoration']['ok'])
        self.assertFalse(report['candidate_installed']);self.assertFalse(report['state_uncertain'])
        self.assertNotIn('install_sources',backend.calls)
        self.assertIn('verify_original',backend.calls)
    def test_failed_compiler_restores_before_returning_failure(self):
        backend,report=self.run_build(fail=True)
        self.assertFalse(report['ok']);self.assertIn('compiler failed',report['error'])
        self.assertTrue(report['restoration']['ok']);self.assertFalse(report['state_uncertain'])

    def test_unconfirmed_compiler_stop_never_restarts_acquisition(self):
        backend=Backend();report={}
        capture=backend.capture;identity=dict(firmware_sha256='b'*64,relay_sha256='c'*64)
        backend.capture=lambda:dict(capture(),identity=identity)
        def failed_builder(*args):
            backend._candidate_compile_cleared=False
            raise RuntimeError('compiler stop unknown')
        execute_build(backend,dict(candidate_identity=identity),Path('.'),Path('.'),report,lambda:None,failed_builder)
        self.assertFalse(report['ok']);self.assertTrue(report['state_uncertain'])
        self.assertFalse(report['restoration']['ok'])
        self.assertNotIn('start_original_app',backend.calls)

    def test_unaccepted_baseline_is_rejected_before_backup_or_stop(self):
        backend=Backend();report={}
        execute_build(backend,dict(candidate_identity={'firmware_sha256':'d'*64}),
                      Path('.'),Path('.'),report,lambda:None,lambda *_:self.fail('No build'))
        self.assertFalse(report['ok']);self.assertFalse(report['state_uncertain'])
        self.assertNotIn('backup',backend.calls);self.assertNotIn('quiesce',backend.calls)
