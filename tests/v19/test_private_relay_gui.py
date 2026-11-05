from contextlib import contextmanager,nullcontext
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from tests.v19.test_q_update_transaction import Backend
from tools.probe_relay_gui_v19 import execute_gui,restore_owner
from tools import private_relay_gui_v19 as binding


ACCEPTED=dict(firmware_sha256='b'*64,relay_sha256='c'*64)
PRIVATE=dict(board_serial='test',app='scope-v19-main-1',firmware_sha256='b'*64,relay_sha256='d'*64)


class PrivateGuiTests(unittest.TestCase):
    def test_restore_waits_for_receiver_lease_without_taking_it_over(self):
        class Busy:
            def __enter__(self):raise RuntimeError('Q ocupado por receptor')
        backend=Mock();backend.owner.side_effect=[Busy(),nullcontext()]
        with patch('tools.probe_relay_gui_v19.time.sleep'):
            with restore_owner(backend):self.assertEqual(backend.owner.call_count,2)
        backend.stop_app.assert_not_called()

    def test_restore_timeout_preserves_foreign_lease(self):
        class Busy:
            def __enter__(self):raise RuntimeError('Q ocupado por receptor')
        backend=Mock();backend.owner.return_value=Busy()
        with self.assertRaisesRegex(RuntimeError,'Q ocupado'):
            with restore_owner(backend,timeout=0):self.fail('No lease acquired')
        backend.stop_app.assert_not_called()

    def backend(self):
        backend=Backend();backend.depth=0
        @contextmanager
        def owner():
            backend.depth+=1
            try:yield
            finally:backend.depth-=1
        backend.owner=owner
        capture=backend.capture
        backend.capture=lambda:dict(capture(),identity=dict(PRIVATE,**ACCEPTED))
        backend.new_relay='/private/relay';backend.new_relay_id='candidate-id'
        backend._board=Mock();backend._hash=Mock(return_value='d'*64)
        backend._identity=Mock(return_value=PRIVATE);backend._output=Mock(return_value='relay log')
        return backend

    def test_gui_child_owns_lease_and_original_is_restored_after_failure(self):
        for passes in (True,False):
            with self.subTest(passes=passes):
                backend=self.backend();report={}
                def gui():
                    self.assertEqual(backend.depth,0)
                    self.assertEqual(report['private_identity'],PRIVATE)
                    return dict(ok=passes)
                execute_gui(backend,dict(candidate_identity=ACCEPTED),
                            dict(path='candidate.bin',sha256='d'*64),report,lambda:None,gui)
                self.assertEqual(report['ok'],passes)
                self.assertTrue(report['restoration']['ok']);self.assertFalse(report['state_uncertain'])
                self.assertIn('verify_original',backend.calls)

    def test_foreign_reader_blocks_rollback_before_any_takeover(self):
        backend=self.backend();backend._no_reader=Mock(side_effect=RuntimeError('foreign reader'))
        report={}
        execute_gui(backend,dict(candidate_identity=ACCEPTED),
                    dict(path='candidate.bin',sha256='d'*64),report,lambda:None,lambda:dict(ok=True))
        self.assertFalse(report['ok']);self.assertTrue(report['state_uncertain'])
        self.assertTrue(report['restoration']['blocked'])
        self.assertNotIn('stop_new_relay',backend.calls)

    def test_exact_binding_rejects_wrong_board_and_wrong_installed_pair(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'binding.json'
            report=dict(private=True,promoted=False,private_candidate_activated=True,
                source_build_report='build.json',private_identity=PRIVATE,
                baseline=dict(identity=dict(PRIVATE,**ACCEPTED)))
            path.write_text(json.dumps(report))
            with patch.dict(os.environ,{binding.ENV:str(path)}), \
                 patch.object(binding,'checked_artifact',return_value=dict(sha256='d'*64)), \
                 patch.object(binding,'accepted_identity',return_value=ACCEPTED), \
                 patch.object(binding,'installed_identity',return_value=PRIVATE) as identity:
                self.assertEqual(binding.private_identity('test'),PRIVATE)
                identity.assert_called_with('test',require_accepted=False)
                with self.assertRaisesRegex(RuntimeError,'identity differs'):binding.binding_identity('other')
                identity.return_value=dict(PRIVATE,relay_sha256='e'*64)
                with self.assertRaisesRegex(RuntimeError,'exact private'):binding.private_identity('test')
                report['restoring']=True;path.write_text(json.dumps(report))
                with self.assertRaisesRegex(RuntimeError,'not active'):binding.binding_identity('test')
