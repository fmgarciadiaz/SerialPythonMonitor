"""Offline recovery contracts. Never contact Q or spawn an uploader."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from monitor.v20.q_support import recovery as mod

IDENTITY = dict(board_serial='fake', app='scope-v20-20261031-225916-main-1',
                firmware_sha256='a'*64, relay_sha256='b'*64)
BASE = dict(identity=IDENTITY, app_root='/home/arduino/ArduinoApps/scope-v20-20261031-225916',
            firmware='/firmware', relay_binary='/relay', app={'Id':'app-id'}, relay={'Id':'relay-id'})


class FakeBackend:
    def __init__(self):
        self.events=[]
        self.sleep=lambda _:None
        self.fail=None
    def preflight(self):
        self.events.append('preflight')
        if self.fail=='preflight': raise RuntimeError('wrong identity/source/reader')
        return BASE
    def evidence(self, baseline): self.events.append('evidence');return {'relay':'Exited 1'}
    def launch(self, baseline, folder):
        self.events.append('launch')
        if self.fail=='launch': raise TimeoutError('ADB query timed out')
    def wait(self, folder):
        self.events.append('wait')
        if self.fail=='wait': raise mod.RemoteJobFailed('upload failed')
    def finish(self, baseline):
        self.events.append('finish')
        if self.fail=='safe': raise RuntimeError('safe profile failed')
        return dict(continuous=True, dropped=0, fatal=0, crc_errors=0)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.marker=Path(self.tmp.name)/'pending.json'
        self.report=Path(self.tmp.name)/'report.json'
        self.patch=patch.object(mod,'pending_path',return_value=self.marker)
        self.patch.start();self.addCleanup(self.patch.stop)
        self.backend=FakeBackend()
    def run_recovery(self):
        return mod.recover('fake', self.report, backend=self.backend)
    def test_success_exact_order_and_explicit_safe_profile(self):
        result=self.run_recovery()
        self.assertTrue(result['ok'])
        self.assertEqual(self.backend.events,['preflight','evidence','launch','wait','finish'])
        self.assertFalse(self.marker.exists())
        self.assertFalse(result['restores_failed_profile'])
        self.assertTrue(result['recompiles_uploads_existing_sources'])
    def test_preflight_failure_has_no_mutations(self):
        self.backend.fail='preflight'
        self.assertFalse(self.run_recovery()['ok'])
        self.assertEqual(self.backend.events,['preflight'])
        self.assertFalse(self.marker.exists())
    def test_launch_timeout_blocks_connect_and_retry_reconciles_no_second_upload(self):
        self.backend.fail='launch'
        self.assertFalse(self.run_recovery()['ok'])
        with self.assertRaisesRegex(RuntimeError,'pendiente'):
            mod.assert_no_pending('fake')
        self.backend.fail=None;self.backend.events=[]
        self.assertTrue(self.run_recovery()['ok'])
        self.assertEqual(self.backend.events,['wait','preflight','finish'])
    def test_profile_failure_never_reports_success_and_retry_does_not_upload(self):
        self.backend.fail='safe'
        self.assertFalse(self.run_recovery()['ok'])
        self.assertTrue(self.marker.exists())
        self.backend.fail=None;self.backend.events=[]
        self.assertTrue(self.run_recovery()['ok'])
        self.assertNotIn('launch',self.backend.events)
    def test_terminal_job_failure_allows_explicit_retry(self):
        self.backend.fail='wait'
        self.assertFalse(self.run_recovery()['ok'])
        self.assertFalse(self.marker.exists())
        self.assertNotIn('finish',self.backend.events)
    def test_preflight_rejects_wrong_receipt_before_remote_queries(self):
        queries=[]
        def verify(*_): raise RuntimeError('receipt invalid')
        backend=mod.RecoveryBackend('fake',runner=lambda *a:queries.append(a),verifier=verify)
        with self.assertRaisesRegex(RuntimeError,'receipt invalid'): backend.preflight()
        self.assertEqual(queries,[])
    def test_preflight_guards_sources_hash_other_app_and_reader(self):
        def scenario(kind):
            queries=[]
            source={'sketch/sketch.ino':'c'*64}
            def runner(*args):
                command=args[-1];queries.append(command)
                if command.startswith('docker inspect'):
                    name=command.split()[-1]
                    info=dict(Name='/'+name,Id=name,Config=dict(Labels={'com.docker.compose.project.working_dir':BASE['app_root']+'/.cache'}),Mounts=[{'Destination':'/work/unoq_stream','Source':'/home/arduino/.cache/serialmonitor/relay'}])
                    return json.dumps([info])
                if command.startswith('docker ps'): return 'scope-v19-main-1' if kind=='other_scope' else ''
                if command.startswith('arduino-app-cli'): return json.dumps({'apps':[{'status':'running','name':'Other'}] if kind=='other_app' else []})
                if command.startswith('ss '): return 'ESTAB' if kind=='reader' else ''
                if command.startswith('python3'): return json.dumps({} if kind=='source' else source)
                if command.startswith('sha256sum'): return ('f'*64 if kind=='hash' else 'a'*64)+' file'
                self.fail('unexpected remote mutation: '+command)
            with patch.object(mod.RECEIPT.__class__,'read_text',return_value=json.dumps({'v20_sources':source})):
                backend=mod.RecoveryBackend('fake',runner=runner,verifier=lambda *_:IDENTITY)
                with self.assertRaises(RuntimeError):backend.preflight()
            self.assertFalse(any('docker stop' in q or 'app start' in q or 'gpioset' in q for q in queries))
        for kind in ('other_scope','other_app','reader','source','hash'):
            with self.subTest(kind=kind):scenario(kind)
    def test_missing_remote_status_returns_uncertain_and_preserves_marker(self):
        backend=mod.RecoveryBackend('fake',runner=lambda *_: (_ for _ in ()).throw(TimeoutError()),
                                    sleep=lambda _:None,progress=lambda *a,**kw:None)
        with patch.object(mod.time,'monotonic',side_effect=[0,0,0,16]):
            with self.assertRaisesRegex(RuntimeError,'incierto'):
                backend.wait('/tmp/job')
    def test_stale_running_pid_never_proves_completion(self):
        def runner(*args):
            if args[-1].startswith('cat '):return json.dumps(dict(state='running',pid=123))
            raise RuntimeError('no such process')
        backend=mod.RecoveryBackend('fake',runner=runner,sleep=lambda _:None)
        with self.assertRaisesRegex(RuntimeError,'no confirmado'):
            backend.wait('/tmp/job')
    def test_changed_firmware_prevents_relay_start(self):
        backend=mod.RecoveryBackend('fake',runner=lambda *_:self.fail('no mutation allowed'))
        backend.sha=lambda _: 'f'*64
        with self.assertRaisesRegex(RuntimeError,'BIN'):
            backend.finish(BASE)
    def test_final_identity_checked_after_safe_profile(self):
        events=[]
        backend=mod.RecoveryBackend('fake',runner=lambda *a:events.append(a[-1]) or '')
        backend.sha=lambda path: IDENTITY['firmware_sha256' if path=='/firmware' else 'relay_sha256']
        backend.inspect=lambda name:BASE['relay']
        backend.safe_profile=lambda identity:events.append('safe-profile') or dict(continuous=True)
        with patch('monitor.v20.io.live_connection.installed_identity',side_effect=[IDENTITY,dict(IDENTITY,firmware_sha256='f'*64)]) as identity:
            with self.assertRaisesRegex(RuntimeError,'durante'):
                backend.finish(BASE)
            self.assertEqual(identity.call_count,2)
            self.assertIn('safe-profile',events)

    def test_wait_retries_query_timeout_without_relaunch(self):
        events=[]
        def runner(*args):
            events.append(args)
            if len(events)==1: raise TimeoutError('query')
            return json.dumps(dict(state='done',exit_status=0))
        backend=mod.RecoveryBackend('fake',runner=runner,sleep=lambda _:None,progress=lambda *a,**kw:None)
        self.assertEqual(backend.wait('/tmp/job')['exit_status'],0)
        self.assertEqual(len(events),2)
        self.assertTrue(all('cat ' in args[-1] for args in events))


if __name__=='__main__':unittest.main()
