"""No Q: private profiles and failure/rollback transaction contract."""
import unittest
from experimentos.fs_max_v18.run_probe import plan,private_profiles,orchestrate
class RunnerTests(unittest.TestCase):
    def test_mount_order_does_not_hide_configuration_changes(self):
        from experimentos.fs_max_v18.run_probe import relay_configuration_equal
        from copy import deepcopy
        first={'Config':{},'HostConfig':{},'Mounts':[
            {'Destination':'/a','Source':'/original','RW':False},
            {'Destination':'/b','Source':'/cpu','RW':True}]}
        second=deepcopy(first);second['Mounts'].reverse()
        self.assertTrue(relay_configuration_equal(first,second))
        second['Mounts'][0]['RW']=False
        self.assertFalse(relay_configuration_equal(first,second))

    def test_metrics_preserve_frame_weighting_across_batches_without_retention(self):
        from experimentos.fs_max_v18.run_probe import FrameMetrics
        metrics=FrameMetrics()
        self.assertIsNone(metrics.margin(100))
        a={'send_ticks':20,'queue_peak':2,'slack_ticks':50}
        b={'send_ticks':80,'queue_peak':3,'slack_ticks':10}
        metrics.observe([a,a]);metrics.observe([b,dict(b,send_ticks=0)])
        self.assertEqual(metrics.frames,4)
        self.assertEqual(metrics.send_count,3)
        self.assertAlmostEqual(metrics.margin(100),.6)
        self.assertEqual((metrics.queue_peak,metrics.min_slack),(3,10))
        self.assertFalse(any(isinstance(value,(list,dict)) for value in vars(metrics).values()))

    def test_plan(self):
        self.assertEqual([p['ticks'] for p in plan([8])],[98,96,94,92,90,89,88])
        self.assertTrue(all(p['seconds']==15 for p in plan([8,10,12,14,16])))
        with self.assertRaises(ValueError):plan([9])
    def test_wide_recipe_keeps_total_sample_capacity_and_private_lookup(self):
        from pathlib import Path
        from monitor.v18.receiver.unoq_acquisition import Configuration
        rows=plan([8],60,[88],recipe='wide8')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['node_pairs']*rows[0]['queue_slots'],3456*8)
        source=Path(__file__).resolve().parent/'wide8'
        with private_profiles(source):
            self.assertEqual(Configuration.from_wire(8,6912<<16|88).node_pairs,6912)
        with self.assertRaises(ValueError):plan([12],recipe='wide8')

    def test_private_profiles_scoped(self):
        from monitor.v18.receiver import unoq_native
        from monitor.v18.receiver.unoq_acquisition import Configuration
        before=unoq_native.PROFILES
        with private_profiles():
            self.assertEqual(Configuration.from_wire(8,3456<<16|88).node_pairs,3456)
        self.assertIs(unoq_native.PROFILES,before)
    def test_transaction(self):
        class Fake:
            def __init__(self,fail):self.events=[];self.fail=fail
            def capture(self):self.events.append('capture')
            def prepare(self):
                self.events.append('prepare')
                if self.fail=='prepare':raise RuntimeError('setup')
            def measure(self,p):self.events.append('measure');return {'ok':self.fail!='measure'}
            def restore(self):self.events.append('restore');return {'hardware_restored':True}
        for fail in ('prepare','measure',None):
            backend=Fake(fail);report={'cases':[]};saved=[]
            ok=orchestrate(backend,[{},{}],report,lambda:saved.append(True))
            self.assertEqual(backend.events[-1],'restore');self.assertEqual(ok,fail is None)
            self.assertEqual(backend.events.count('measure'),0 if fail=='prepare' else 1 if fail=='measure' else 2)
            self.assertTrue(saved)
    def test_every_setup_boundary_restores_without_retry(self):
        boundaries=['low','backup','relay_stop','relay_rename','original_stop','compile','import','relay_build']
        for boundary in boundaries:
            class Fake:
                def __init__(self):self.calls=[]
                def capture(self):self.calls.append('capture')
                def prepare(self):
                    for stage in boundaries:
                        self.calls.append(stage)
                        if stage==boundary:raise RuntimeError(stage)
                def measure(self,p):raise AssertionError('must not measure')
                def restore(self):self.calls.append('restore');return {'hardware_restored':True}
            fake=Fake();report={'cases':[]}
            self.assertFalse(orchestrate(fake,[{}],report,lambda:None))
            self.assertEqual(fake.calls[-1],'restore')
            self.assertEqual(fake.calls.count(boundary),1)
            self.assertIn(boundary,report['error'])
    def test_capture_failure_does_not_mutate(self):
        class Fake:
            def capture(self):raise RuntimeError('snapshot')
            def prepare(self):raise AssertionError('mutation')
            def restore(self):raise AssertionError('mutation')
        report={'cases':[]}
        self.assertFalse(orchestrate(Fake(),[{}],report,lambda:None))
        self.assertIn('snapshot',report['error'])
    def test_restore_uses_normal_governor_before_restoring_active_profile(self):
        from contextlib import contextmanager
        from types import SimpleNamespace
        from unittest.mock import patch,Mock
        from experimentos.fs_max_v18.run_probe import Hardware
        calls=[];phase={'restored':False}
        info={'State':{'Pid':42},'Config':{},'HostConfig':{},
              'Mounts':[{'Source':'/governor','Destination':'/scope_cpu_governor','RW':True}]}
        def shell(*args,**kwargs):
            calls.append(args)
            if args[:2]==('docker','inspect'):
                import json
                return SimpleNamespace(stdout=json.dumps([info]))
            if args[0]=='cat':return SimpleNamespace(stdout='performance')
            return SimpleNamespace(stdout='')
        hw=Hardware.__new__(Hardware)
        hw.original=SimpleNamespace(shell=shell,serial='test')
        hw.renamed=hw.relay_stopped=hw.app_touched=hw.candidate_started=False
        hw.governor='performance';hw.governor_path='/governor';hw.inspect=info
        hw.identity={'identity':1};hw.snapshot=None;hw.folder='/tmp'
        normal={'policy':0,'priority':0,'cpus':[0,1,2,3]}
        active={'policy':1,'priority':10,'cpus':[2]}
        hw.report={'normal_cpu_governor':'schedutil','normal_cpu_state':normal,'cpu_state':active}
        hw.cpu_state=lambda _:active if phase['restored'] else normal
        @contextmanager
        def receiver():yield None
        hw.receiver=receiver
        lifecycle=Mock()
        def restore(_):
            phase['restored']=True
            return {'hardware_restored':True}
        lifecycle.return_value.restore.side_effect=restore
        with patch('monitor.v18.io.live_connection.installed_identity',return_value=hw.identity),patch.dict('sys.modules',{'monitor.v18.io.receiver_lifecycle':SimpleNamespace(ReceiverLifecycle=lifecycle)}):
            result=hw.restore()
        writes=[args for args in calls if args[:2]==('docker','exec')]
        self.assertEqual(len(writes),1)
        self.assertIn('schedutil',writes[0][-1])
        self.assertTrue(result['normal_cpu_state_equal'])
        self.assertTrue(result['cpu_state_equal'])
        self.assertTrue(result['hardware_restored'])

    def test_cleanup_continues_after_each_admin_failure(self):
        from contextlib import contextmanager
        from types import SimpleNamespace
        from unittest.mock import patch,Mock
        from experimentos.fs_max_v18.run_probe import Hardware,CONTAINER
        for broken in ('rm','candidate_stop','original_start','rename','start','cat'):
            events=[]
            def shell(*args,**kw):
                events.append(args)
                action=args[1] if args[0]=='docker' else args[0]
                if action==broken:raise RuntimeError(broken)
                if action=='ps':return SimpleNamespace(stdout=CONTAINER)
                if action=='inspect':return SimpleNamespace(stdout='[{"Config":{},"HostConfig":{},"Mounts":[]}]')
                return SimpleNamespace(stdout='performance')
            def action(name):
                events.append((name,))
                if name==broken:raise RuntimeError(name)
            hw=Hardware.__new__(Hardware)
            hw.original=SimpleNamespace(shell=shell,start=lambda:action('original_start'),serial='test')
            hw.candidate=SimpleNamespace(stop=lambda:action('candidate_stop'))
            hw.renamed=hw.relay_stopped=hw.app_touched=hw.candidate_started=True
            hw.saved_name='saved';hw.governor='performance';hw.governor_path='/fake';hw.folder='/tmp'
            hw.identity={'a':1};hw.snapshot=None;hw.report={'cpu_state':{}}
            hw.inspect={'Config':{},'HostConfig':{},'Mounts':[]};hw.cpu_state=lambda info:{}
            @contextmanager
            def receiver():yield None
            hw.receiver=receiver
            lifecycle=Mock();lifecycle.return_value.restore.return_value={'hardware_restored':True}
            with patch('monitor.v18.io.live_connection.installed_identity',return_value=hw.identity),patch.dict('sys.modules',{'monitor.v18.io.receiver_lifecycle':SimpleNamespace(ReceiverLifecycle=lifecycle)}):
                result=hw.restore()
            self.assertFalse(result['hardware_restored'])
            self.assertTrue(result['rollback_errors'])
            self.assertIn(('original_start',),events)
            self.assertTrue(any(e[:2]==('docker','rename') for e in events))
            self.assertTrue(any(e[:2]==('docker','start') for e in events))
            self.assertTrue(any(e[0]=='cat' for e in events))
if __name__=='__main__':unittest.main()
