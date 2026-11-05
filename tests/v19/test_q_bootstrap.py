"""Initial-install routing, ownership boundaries and failure handling, offline."""
from contextlib import nullcontext
from contextlib import redirect_stdout
import io
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch,call

from monitor.v19.q_support import bootstrap,service
from monitor.v19.q_support.prepare import source_manifest
from monitor.v19.q_support.backend import APP,APP_CONTAINER,CONTAINER,HELPER

EMPTY=dict(apps=[],containers=[],running=[],path_exists=False)


class BootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]
        reference=root/'monitor/v19/q_support/v18_reference'
        proof=reference/'prebuild_proof.json'
        cls.acceptance=dict(
            receipt_path=str(reference/'acceptance.json'),
            sources=dict(app=source_manifest(root/'arduino/v19/oscilloscope'),
                         relay=source_manifest(root/'arduino/v19/relay')),
            candidate_identity=dict(firmware_sha256='a'*64,relay_sha256='b'*64),
            artifacts=dict(prebuild_proof=dict(path=str(proof),
                sha256=hashlib.sha256(proof.read_bytes()).hexdigest())))

    def backend(self):
        b=Mock();b.acceptance=self.acceptance;b.remote_folder='/tmp/new-v19';b.helper='/tmp/helper.py'
        b.new_relay_id='new-relay'
        b._board.return_value.create.return_value=None
        b.prepare.return_value=dict(source_hashes_equal=True,compiled_firmware_hash_equal=True,
                                   precompiled_relay_hash_equal=True)
        b._sources.return_value=self.acceptance['sources']['app']
        b._identity.return_value=dict(board_serial='new-q',app=APP_CONTAINER,**self.acceptance['candidate_identity'])
        b.capture.return_value=dict(app_sources=self.acceptance['sources']['app'])
        b._recover.return_value=dict(snapshot_equal=True,continuous=True,integrity_ok=True,seconds=10)
        b._output.return_value=APP_CONTAINER+'\n'+CONTAINER
        b._inspect.return_value={'Id':'new-relay'}
        b.new_app_id='scope-v19-id'
        b._json.return_value={'apps':[{'name':'Scope V19','id':'scope-v19-id'}]}
        return b

    def install(self,b,report):
        listings={'count':0}
        app_paths={'count':0}
        def json_response(*args):
            if args[:2]==('arduino-app-cli','app'):
                listings['count']+=1
                rows=[{'name':'Scope V19','id':'scope-v19-id'}] if listings['count']<3 else []
                return {'apps':rows}
            if args[0]=='python3' and args[-1]==APP:
                app_paths['count']+=1
                return app_paths['count']==1
            return False
        b._json.side_effect=json_response
        with patch.object(bootstrap,'preflight',return_value=EMPTY),patch.object(bootstrap,'inventory',return_value=EMPTY):
            bootstrap.install_empty(b,self.acceptance,report,lambda:None)

    def test_empty_and_inactive_v17_are_allowed(self):
        bootstrap.require_empty(EMPTY)
        state=dict(EMPTY,apps=[dict(name='Scope V17',status='stopped')],containers=['scope-v17-main-1'])
        bootstrap.require_empty(state)

    def test_existing_or_partial_v19_is_never_overwritten(self):
        for change in (dict(path_exists=True),dict(containers=[APP_CONTAINER]),
                       dict(containers=[CONTAINER]),dict(apps=[dict(name='Scope V19')])):
            with self.subTest(change=change),self.assertRaisesRegex(RuntimeError,'no se sobrescribe'):
                bootstrap.require_empty(dict(EMPTY,**change))

    def test_other_running_apps_and_relays_are_not_stopped(self):
        for change in (dict(apps=[dict(name='Factory demo',status='running')]),
                       dict(running=['scope-v17-main-1']),dict(running=['serialmonitor-usb-stream'])):
            with self.subTest(change=change),self.assertRaises(RuntimeError):
                bootstrap.require_empty(dict(EMPTY,**change))

    def test_install_checks_acquisition_and_marks_success(self):
        b=self.backend();report={'ok':False};self.install(b,report)
        self.assertTrue(report['ok']);self.assertEqual(report['action'],'installed_initial')
        phases=[row['phase'] for row in report['journal']]
        self.assertLess(phases.index('initial_stage'),phases.index('initial_import'))
        self.assertLess(phases.index('initial_start_app'),phases.index('initial_start_relay'))
        b._recover.assert_called_once_with(b._identity.return_value,10)
        self.assertNotIn('initial_cleanup',report)

    def test_binary_failure_cannot_import_or_start(self):
        b=self.backend();b.prepare.return_value['compiled_firmware_hash_equal']=False
        report={'ok':False}
        with self.assertRaisesRegex(RuntimeError,'binarios'):self.install(b,report)
        b._board.return_value.create.assert_not_called();b.start_new_app.assert_not_called()
        self.assertFalse(report['ok'])

    def test_bad_sources_never_start_firmware(self):
        b=self.backend();b._sources.return_value={};report={'ok':False}
        with self.assertRaisesRegex(RuntimeError,'fuentes importadas'):self.install(b,report)
        b.start_new_app.assert_not_called()
        self.assertTrue(report['initial_cleanup']['errors']==[])
        b._board.return_value.stop.assert_not_called()

    def test_acquisition_failure_destroys_only_new_app(self):
        b=self.backend();b._recover.return_value['continuous']=False;report={'ok':False}
        with self.assertRaisesRegex(RuntimeError,'continua'):self.install(b,report)
        self.assertFalse(report['ok']);b._board.return_value.stop.assert_called_once()
        self.assertIn(('mv',APP,'/tmp/new-v19/failed_initial_app'),
                      [call.args for call in b._board.return_value.shell.call_args_list])
        self.assertFalse(report['initial_cleanup']['previous_firmware_restored'])

    def test_cleanup_never_stops_a_relay_with_different_identity(self):
        b=self.backend();b._inspect.return_value={'Id':'foreign-relay'}
        bootstrap.cleanup(b,True)
        commands=[call.args for call in b._board.return_value.shell.call_args_list]
        self.assertFalse(any('foreign-relay' in row or CONTAINER in row for row in commands))

    def test_cleanup_cannot_move_app_after_stop_failure(self):
        b=self.backend();b._board.return_value.stop.side_effect=RuntimeError('stop failed')
        result=bootstrap.cleanup(b,True)
        self.assertTrue(result['errors'])
        self.assertFalse(any(call.args[0]=='mv' for call in b._board.return_value.shell.call_args_list))

    def test_preflight_rejects_launcher_before_pushing_or_compiling(self):
        b=self.backend();b._output.return_value='different CLI'
        with patch.object(bootstrap,'inventory',return_value=EMPTY),self.assertRaisesRegex(RuntimeError,'App CLI'):
            bootstrap.preflight(b,self.acceptance)
        b._board.return_value.run.assert_not_called();b.prepare.assert_not_called()

    def test_preflight_verifies_transferred_helper(self):
        b=self.backend()
        proof=json.loads(Path(self.acceptance['artifacts']['prebuild_proof']['path']).read_text())
        b._output.return_value=proof['launcher']['version'].strip()
        b._hash.side_effect=[proof['launcher']['sha256'],'0'*64]
        with patch.object(bootstrap,'inventory',return_value=EMPTY),self.assertRaisesRegex(RuntimeError,'verificador transferido'):
            bootstrap.preflight(b,self.acceptance)

    def test_inventory_refuses_unknown_listing(self):
        b=self.backend();b._json.return_value={}
        with self.assertRaisesRegex(RuntimeError,'inventario'):bootstrap.inventory(b)

    def test_source_manifest_does_not_require_cache(self):
        from monitor.v19.q_support import archive
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'main.py').write_text('ok')
            with patch.object(archive,'APP',str(root)),patch.object(archive,'PRODUCTION_APP',str(root)):
                output=io.StringIO()
                with redirect_stdout(output):archive.main(['source-manifest','--root',str(root)])
                self.assertEqual(json.loads(output.getvalue()),{'source_files':{'main.py':hashlib.sha256(b'ok').hexdigest()}})

    def test_cleanup_quarantines_exact_import_without_cache(self):
        b=self.backend()
        listings={'count':0}
        app_paths={'count':0}
        def json_response(*args):
            if args[:2]==('arduino-app-cli','app'):
                listings['count']+=1
                return {'apps':[{'name':'Scope V19','id':'scope-v19-id'}]} if listings['count']==1 else {'apps':[]}
            if args[0]=='python3' and args[-1]==APP:
                app_paths['count']+=1
                return app_paths['count']==1
            return args[-1]==APP
        b._json.side_effect=json_response
        result=bootstrap.cleanup(b,True)
        self.assertEqual(result['errors'],[])
        b._board.return_value.cli.assert_not_called()
        self.assertIn(('mv',APP,'/tmp/new-v19/failed_initial_app'),
                      [call.args for call in b._board.return_value.shell.call_args_list])

    def test_service_routes_missing_pair_to_initial_install_under_owner(self):
        b=self.backend();b.owner.side_effect=nullcontext
        def installed(backend,acceptance,report,save):
            report.update(ok=True,action='installed_initial');save()
        with tempfile.TemporaryDirectory() as folder,patch.object(service,'load_acceptance',return_value=self.acceptance),\
             patch.object(service,'ProductionBackend',return_value=b),\
             patch.object(service,'installed_identity',side_effect=RuntimeError('not installed')),\
             patch.object(service,'wake_accepted_pair',side_effect=service.MissingScopePair()),\
             patch.object(bootstrap,'install_empty',side_effect=installed) as install,patch.object(service,'execute') as update:
            target=Path(folder)/'report.json';result=service.prepare('new-q',target)
            self.assertTrue(result['ok']);self.assertEqual(json.loads(target.read_text())['action'],'installed_initial')
            install.assert_called_once();update.assert_not_called();b.owner.assert_called_once()

    def test_service_does_not_treat_unrelated_wake_failure_as_blank(self):
        b=self.backend();b.owner.side_effect=nullcontext
        with tempfile.TemporaryDirectory() as folder,patch.object(service,'load_acceptance',return_value=self.acceptance),\
             patch.object(service,'ProductionBackend',return_value=b),\
             patch.object(service,'installed_identity',side_effect=RuntimeError('not running')),\
             patch.object(service,'wake_accepted_pair',side_effect=RuntimeError('another app')),\
             patch.object(bootstrap,'install_empty') as install:
            result=service.prepare('new-q',Path(folder)/'report.json')
            self.assertFalse(result['ok']);install.assert_not_called()

if __name__=='__main__':unittest.main()
