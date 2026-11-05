from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from tools import private_v20_pair as pair
from monitor.v20.memory_contract import load_contract
from tools.probe_v20_gui import TrialBackend
from monitor.v19.q_support.backend import ProductionBackend


class PrivateV20Tests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();out=root/'diagnosticos/resultados_v20/proof';out.mkdir(parents=True)
            digest=lambda b:hashlib.sha256(b).hexdigest();sources={}
            for field,folder in [('v20_sources','oscilloscope'),('relay_sources','relay')]:
                p=root/'arduino/v20'/folder;p.mkdir(parents=True);(p/'source').write_bytes(b'original')
                sources[field]={'source':digest(b'original')}
            (out/'relay.bin').write_bytes(b'relay')
            report=dict(private=True,promoted=False,ok=True,restoration=dict(ok=True),ready_no_yield=False,
                        cases=[dict(state='complete',metrics=dict(integrity_pass=True))]*2,
                        firmware_before='a'*64,relay_sha256=digest(b'relay'),memory_contract=load_contract(),**sources)
            path=out/'report.json';path.write_text(json.dumps(report))
            binding=root/'diagnosticos/resultados_v20/gui/report.json';binding.parent.mkdir()
            expected=dict(board_serial='test',app=pair.APP_CONTAINER,firmware_sha256='a'*64,relay_sha256=report['relay_sha256'])
            active=dict(private=True,promoted=False,private_firmware_activated=True,private_identity=expected,
                        source_report=str(path),source_report_sha256=digest(path.read_bytes()))
            binding.write_text(json.dumps(active))
            with patch.object(pair,'ROOT',root),patch.dict(os.environ,{pair.ENV:str(binding)}):
                yield root,path,binding,active,expected

    def test_private_reserve_preserves_legacy_result_and_requires_margin(self):
        metrics=dict(mean_send_margin=.12,mcu_queue_peak=4,min_slack_ticks=100,headroom_pass=False)
        value=pair.reserve_screen(metrics,16)
        self.assertTrue(value['passes']);self.assertFalse(value['legacy_headroom_pass'])
        self.assertFalse(value['publicly_accepted']);self.assertEqual(value['free_at_peak'],12)
        for change in (dict(mean_send_margin=.099),dict(mcu_queue_peak=8),dict(min_slack_ticks=0),dict(mcu_queue_peak=17)):
            self.assertFalse(pair.reserve_screen(dict(metrics,**change),16)['passes'])

    def test_binding_exact_sources_binary_and_installed_pair(self):
        with self.fixture() as (root,proof,binding,active,expected):
            self.assertEqual(pair.expected_identity('test'),expected)
            with patch('monitor.v20.memory_contract.verify_runner'),patch.object(pair,'installed_identity',return_value=expected):
                self.assertEqual(pair.private_identity('test'),expected)
            with patch('monitor.v20.memory_contract.verify_runner'),patch.object(pair,'installed_identity',return_value=dict(expected,firmware_sha256='b'*64)):
                with self.assertRaises(RuntimeError):pair.private_identity('test')
            for p in (root/'arduino/v20/relay/source',proof.parent/'relay.bin'):
                before=p.read_bytes();p.write_bytes(b'changed')
                with self.assertRaises(ValueError):pair.expected_identity('test')
                p.write_bytes(before)
            with self.assertRaises(RuntimeError):pair.expected_identity('wrong-board')

    def test_private_queue_proof_requires_exact_candidate_and_archive(self):
        with self.fixture() as (root,proof,_,active,expected):
            candidate=root/'experiments/v20/tcp_queue_recovery/frame_send_queue.h'
            candidate.parent.mkdir(parents=True);candidate.write_bytes(b'candidate')
            archived=proof.parent/'private_frame_send_queue.h';archived.write_bytes(b'candidate')
            report=json.loads(proof.read_text());report['tcp_queue_recovery']=True
            report['relay_sources']['frame_send_queue.h']=hashlib.sha256(b'candidate').hexdigest()
            proof.write_text(json.dumps(report));pair.checked_proof(proof)
            archived.write_bytes(b'wrong')
            with self.assertRaises(ValueError):pair.checked_proof(proof)
            archived.write_bytes(b'candidate');candidate.write_bytes(b'changed')
            with self.assertRaises(ValueError):pair.checked_proof(proof)

    def test_inactive_or_restoring_binding_rejected_without_board_operations(self):
        with self.fixture() as (_,proof,path,active,expected):
            for change in (dict(promoted=True),dict(restoring=True),dict(cancelling=True),
                           dict(private_firmware_activated=False),dict(error='failed'),
                           dict(restoration=dict(ok=True)),dict(private_identity=dict(expected,app='scope-v19-main-1'))):
                path.write_text(json.dumps(dict(active,**change)))
                with self.subTest(change=change),self.assertRaises(RuntimeError):pair.expected_identity('test')
            path.write_text(json.dumps(active));proof.write_text(proof.read_text()+' ')
            with self.assertRaises(RuntimeError):pair.expected_identity('test')

    def test_unrestored_or_nonoriginal_proof_rejected(self):
        with self.fixture() as (_,proof,path,active,expected):
            original=json.loads(proof.read_text())
            for change in (dict(ready_no_yield=True),dict(ok=False),dict(restoration=dict(ok=False)),dict(cases=[])):
                proof.write_text(json.dumps(dict(original,**change)))
                with self.assertRaises(ValueError):pair.checked_proof(proof)

    def test_rollback_stops_only_owned_v20_relay_and_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            b=object.__new__(TrialBackend);b.output=Path(temp);b.token='1234567890';b.v20_relay_id='owned'
            b._inspect=Mock(return_value={'Id':'foreign'});b._board=Mock();b._output=Mock(return_value='raw log')
            with patch.object(ProductionBackend,'stop_new_relay') as original:
                with self.assertRaises(RuntimeError):b.stop_new_relay({},None)
                b._board().shell.assert_not_called();original.assert_not_called()
                b._inspect.return_value={'Id':'owned'};b.stop_new_relay({},None)
                b._board().shell.assert_any_call('docker','stop','serialmonitor-usb-stream-v20')
                self.assertEqual((b.output/'v20_relay.log').read_text(),'raw log')
                self.assertIsNone(b.v20_relay_id);original.assert_called_once()

    def test_private_app_stop_restores_identity_selection_before_v19_restart(self):
        b=object.__new__(TrialBackend);b.v20_active=True;b.v20board=Mock();b._board=Mock()
        b.stop_app();b.v20board.stop.assert_called_once();self.assertFalse(b.v20_active)
        b._board().stop.assert_not_called()
        b.stop_app();b._board().stop.assert_called_once()
