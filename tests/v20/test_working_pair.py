from contextlib import contextmanager
import json
from pathlib import Path
import shlex
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from monitor.v20.q_support import working_pair as pair
from monitor.v20.io.live_connection import installed_identity
from tools.activate_working_v20 import execute_working


class WorkflowTests(unittest.TestCase):
    def setup_case(self):
        baseline=dict(identity=dict(firmware_sha256='a'*64,relay_sha256='b'*64),
                      app_sources={'source':'c'*64},**{k:True for k in
                      ('generator_off','wav_idle','receiver_closed','identity_verified','source_manifest_verified')})
        backend=Mock();backend._board.return_value=SimpleNamespace(serial='board')
        backend.owner.return_value.__enter__=Mock();backend.owner.return_value.__exit__=Mock()
        backend.preflight.return_value={k:True for k in
            ('production_backend_qualified','rollback_rehearsal_verified','cached_launcher_verified')}
        backend.capture.return_value=baseline
        backend.backup.return_value={k:True for k in ('export_verified','source_archive_verified','full_cache_verified',
            'firmware_elf_bin_verified','relay_verified','paired_manifest_persisted')}
        candidate=dict(firmware_sha256='d'*64,relay_sha256='e'*64)
        backend._identity.return_value=dict(board_serial='board',app=pair.APP,**candidate)
        return backend,dict(candidate_identity=baseline['identity']),candidate,{k:True for k in pair.CHECKS}

    def test_verified_success_keeps_v20_running_and_publishes_only_after_saved_binding(self):
        backend,acceptance,candidate,verification=self.setup_case();report={};saves=[]
        publish=Mock(side_effect=lambda:self.assertTrue(saves[-1]['ok']))
        with patch('tools.activate_working_v20.rollback_once') as rollback:
            self.assertTrue(execute_working(backend,acceptance,candidate,report,
                lambda:saves.append(dict(report)),publish,activate_pair=Mock(return_value=verification)))
        rollback.assert_not_called();publish.assert_called_once()
        self.assertNotIn('restoration',report);self.assertTrue(report['private_firmware_activated'])
        self.assertEqual(report['source_changes'],dict(remove=[],added=[],replace=[]))
        self.assertFalse(report['promoted']);backend.owner.assert_called_once()

    def test_each_false_verification_and_cancellation_roll_back_before_publish(self):
        variants=[dict({k:True for k in pair.CHECKS},**{name:False}) for name in pair.CHECKS]+[KeyboardInterrupt()]
        for result in variants:
            with self.subTest(result=result):
                backend,acceptance,candidate,_=self.setup_case();report={};publish=Mock()
                activation=Mock(side_effect=result) if isinstance(result,BaseException) else Mock(return_value=result)
                with patch('tools.activate_working_v20.rollback_once',return_value=dict(ok=True)) as rollback:
                    self.assertFalse(execute_working(backend,acceptance,candidate,report,lambda:None,publish,activation))
                rollback.assert_called_once();publish.assert_not_called()
                self.assertTrue(report['restoration']['ok']);self.assertFalse(report['private_firmware_activated'])

    def test_preflight_failure_is_read_only_and_publish_failure_restores_v19(self):
        backend,acceptance,candidate,verification=self.setup_case();backend.preflight.side_effect=RuntimeError('busy')
        with patch('tools.activate_working_v20.rollback_once') as rollback:
            self.assertFalse(execute_working(backend,acceptance,candidate,{},lambda:None,Mock()))
        backend.quiesce.assert_not_called();rollback.assert_not_called()
        backend,acceptance,candidate,verification=self.setup_case()
        with patch('tools.activate_working_v20.rollback_once',return_value=dict(ok=True)) as rollback:
            self.assertFalse(execute_working(backend,acceptance,candidate,{},lambda:None,
                Mock(side_effect=OSError('receipt write failed')),Mock(return_value=verification)))
        rollback.assert_called_once()


class WorkingReceiptTests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();proof_path=root/pair.PROOF;proof_path.parent.mkdir(parents=True)
            for folder in ('oscilloscope','relay'):
                path=root/'arduino/v20'/folder;path.mkdir(parents=True);(path/'source').write_text(folder)
            (proof_path.parent/'relay.bin').write_bytes(b'relay')
            identity=dict(board_serial='board',app=pair.APP,firmware_sha256='a'*64,
                          relay_sha256=pair.digest(proof_path.parent/'relay.bin'))
            contract={'pinned':'bsp'}
            proof=dict(private=True,promoted=False,version=20,ok=True,restoration=dict(ok=True),
                       cases=[dict(state='complete',metrics=dict(integrity_pass=True))]*2,
                       baseline=dict(identity=dict(board_serial='board')),memory_contract=contract,
                       firmware_before=identity['firmware_sha256'],relay_sha256=identity['relay_sha256'],
                       v20_sources=pair.manifest(root/'arduino/v20/oscilloscope'),
                       relay_sources=pair.manifest(root/'arduino/v20/relay'))
            proof_path.write_text(json.dumps(proof))
            report_path=root/'diagnosticos/resultados_v20/activation/report.json';report_path.parent.mkdir()
            report=dict(private=True,promoted=False,ok=True,private_firmware_activated=True,private_identity=identity,
                        private_verification={k:True for k in pair.CHECKS},source_report=str(proof_path),
                        source_report_sha256=pair.digest(proof_path),memory_contract=contract,v20_sources=proof['v20_sources'])
            report_path.write_text(json.dumps(report));receipt_path=root/'working_pair.json'
            with patch.object(pair,'ROOT',root),patch.object(pair,'RECEIPT',receipt_path),patch.object(pair,'load_contract',return_value=contract),patch.object(pair,'verify_runner') as bsp:
                receipt=pair.receipt_from_report(report_path,'board');receipt_path.write_text(json.dumps(receipt))
                yield root,proof_path,report_path,receipt_path,receipt,identity,bsp

    def test_exact_receipt_and_bsp_with_no_deployment(self):
        with self.fixture() as (_,_,_,_,_,identity,bsp):
            commands=[]
            def runner(*args):
                command=shlex.split(args[-1]);commands.append(command)
                if command[:2]==['docker','ps']:return pair.APP+'\nserialmonitor-usb-stream-v20\n'
                if command[:2]==['docker','inspect']:
                    return json.dumps([dict(Config=dict(Labels={'com.docker.compose.project.working_dir':
                        '/home/arduino/ArduinoApps/'+pair.APP.removesuffix('-main-1')+'/.cache'}))] if command[-1]==pair.APP
                        else [dict(Mounts=[dict(Source='/home/arduino/.cache/serialmonitor/working/unoq_stream',Destination='/work/unoq_stream')])])
                if command[0]=='sha256sum':
                    key='firmware_sha256' if command[-1].endswith('.bin') else 'relay_sha256'
                    return identity[key]+'  '+command[-1]
                raise AssertionError(command)
            self.assertEqual(installed_identity('board',runner),identity)
            bsp.assert_called_once_with('board',runner)
            self.assertTrue(all(command[0]=='sha256sum' or command[:2] in (['docker','ps'],['docker','inspect']) for command in commands))

    def test_receipt_tampering_board_app_hash_and_contract_are_rejected(self):
        with self.fixture() as (_,_,_,path,receipt,identity,bsp):
            for changed in (dict(identity=dict(identity,board_serial='other')),dict(identity=dict(identity,app='scope-other-main-1')),
                            dict(identity=dict(identity,firmware_sha256='b'*64)),dict(promoted=True),
                            dict(source_report_sha256='0'*64),dict(memory_contract={})):
                path.write_text(json.dumps(dict(receipt,**changed)))
                with self.subTest(changed=changed),self.assertRaises(RuntimeError):pair.working_identity('board',Mock())
            bsp.assert_not_called()

    def test_changed_sources_proof_binary_and_activation_are_rejected(self):
        with self.fixture() as (root,proof,report,_,_,_,bsp):
            for path in (root/'arduino/v20/oscilloscope/source',root/'arduino/v20/relay/source',proof,
                         proof.parent/'relay.bin',report):
                original=path.read_bytes();path.write_bytes(original+b' ')
                with self.subTest(path=path),self.assertRaises(RuntimeError):pair.working_identity('board',Mock())
                path.write_bytes(original)
            bsp.assert_not_called()

    def test_explicit_private_identity_does_not_consume_working_receipt(self):
        with patch.object(pair,'working_identity',side_effect=AssertionError('must not use receipt')):
            with self.assertRaises(RuntimeError):installed_identity('board',lambda *args:'',expected_app=pair.APP,require_accepted=False)
