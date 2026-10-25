"""Private SPI screening. Default prints plan; --run owns Q through rollback."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
EXP=Path(__file__).resolve().parent
CONTAINER='serialmonitor-usb-stream-v18'
APP='/home/arduino/ArduinoApps/scope-v18-rate-probe'
from experimentos.fs_max_v18.probe_journal import ProbeJournal,source_manifest,REMOTE_MANIFEST,adoption_decision

def relay_configuration_equal(left,right):
    # Docker may enumerate equivalent bind mounts in a different order.
    return (left['Config']==right['Config'] and left['HostConfig']==right['HostConfig'] and
            sorted(left['Mounts'],key=lambda m:m['Destination'])==
            sorted(right['Mounts'],key=lambda m:m['Destination']))

class FrameMetrics:
    """Preserve frame weighting without retaining hundreds of thousands of dicts."""
    def __init__(self):
        self.frames=self.send_count=self.send_total=self.queue_peak=0
        self.min_slack=None
    def observe(self,statuses):
        for status in statuses:
            self.frames+=1
            ticks=status.get('send_ticks',0)
            if ticks:self.send_count+=1;self.send_total+=ticks
            self.queue_peak=max(self.queue_peak,status.get('queue_peak',0))
            slack=status.get('slack_ticks',0)
            self.min_slack=slack if self.min_slack is None else min(self.min_slack,slack)
    def margin(self,budget):
        return 1-self.send_total/self.send_count/budget if self.send_count else None

def plan(bits,seconds=15,target_ticks=None,recipe="baseline"):
    source=EXP if recipe=='baseline' else EXP/recipe
    profiles=json.loads((source/'candidate_profiles.json').read_text())
    if not set(bits)<= {8,10,12,14,16} or not bits:raise ValueError('Invalid bits')
    if not 0<seconds<=120:raise ValueError('seconds must be in (0,120]')
    selected=[p for p in profiles if p['bits'] in bits and 'purpose' not in p]
    if target_ticks is not None:
        selected=[p for p in selected if p['ticks'] in target_ticks]
        if not selected or set(target_ticks)-{p['ticks'] for p in selected}:raise ValueError('Unknown selected ticks')
    if not selected:raise ValueError('No profiles for selected recipe and bits')
    return [dict(p,seconds=seconds,rate=160000000/p['ticks']) for p in selected]

@contextmanager
def private_profiles(source=EXP):
    from monitor.v18.receiver import unoq_native
    prior=unoq_native.PROFILES
    unoq_native.PROFILES=tuple(prior)+tuple(json.loads((source/'candidate_profiles.json').read_text()))
    try:yield
    finally:unoq_native.PROFILES=prior

def orchestrate(backend,rows,report,save):
    """Injected transaction: a setup failure still restores once snapshot exists."""
    captured=False
    try:
        backend.capture();captured=True;save()
        backend.prepare()
        for profile in rows:
            row=backend.measure(profile);report['cases'].append(row);save()
            if not row['ok']:
                report['stopped_on_integrity_failure']=row.get('failure_stage')=='integrity'
                report['stopped_on_failure']=True
                break
        report['ok']=len(report['cases'])==len(rows) and all(r['ok'] for r in report['cases'])
    except BaseException as exc:
        report['error']=repr(exc)
    finally:
        if captured:
            try:report['restoration']=backend.restore()
            except BaseException as exc:report['restore_error']=repr(exc)
        save()
    report['measurement_ok']=report.get('ok',False)
    report['ok']=report['measurement_ok'] and report.get('restoration',{}).get('hardware_restored',False)
    save()
    return report['ok']

class Hardware:
    def __init__(self,folder,report):
        from tools.unoq import Board
        from spi_benchmark import IMAGE,BUILD_IMAGE
        class BoundedBoard(Board):
            def run(self,*args,capture=False):
                timeout=240 if any('compile' in str(a) or 'apt-get' in str(a) or 'app start' in str(a) for a in args) else 60
                return subprocess.run([self.adb,'-s',self.serial,*args],check=True,text=True,
                    stdout=subprocess.PIPE if capture else None,timeout=timeout)
        cfg=json.loads((ROOT/'arduino/v18/unoq.json').read_text())
        self.original=BoundedBoard(cfg);self.folder=folder;self.report=report
        self.recipe=report.get('recipe','baseline')
        self.source=EXP if self.recipe=='baseline' else EXP/self.recipe
        suffix={'baseline':'','spin100':'','spi40_10_12':'-spi40','wide8':'-wide8','txclean':'-txclean','word14':'-word14','full8':'-full8','crc8':'-full8','wordping':'-wordping','spi16':'-spi16','batch2':'-batch2','batchfast':'-batchfast','batchnative':'-batchnative','batchstack':'-batchstack','batcharena':'-batcharena','batchquickack':'-batcharena','trace8':'-wordping','trace8time':'-wordping','alignedping':'-alignedping'}[self.recipe]
        self.app=APP+suffix
        from experimentos.fs_max_v18.probe_journal import RECIPES
        self.app_name=RECIPES[self.app]
        self.app_container=Path(self.app).name+'-main-1'
        self.IMAGE,self.BUILD_IMAGE=IMAGE,BUILD_IMAGE
        self.renamed=False;self.relay_stopped=False;self.app_touched=False;self.candidate=None;self.candidate_started=False;self.low=False
        self.saved_name=CONTAINER+'-saved-'+uuid.uuid4().hex[:10]
        self.journal=ProbeJournal(folder/'report.json',report)
        self.report['saved_relay_name']=self.saved_name
        self.governor_path='/sys/devices/system/cpu/cpufreq/policy0/scaling_governor'

    def persist(self):
        self.report['setup_flags']={key:getattr(self,key) for key in ('low','relay_stopped','renamed','app_touched','candidate_started')}
        self.journal.save()

    def action(self,name,fn):
        def operation():
            try:return fn()
            finally:self.report['setup_flags']={key:getattr(self,key) for key in ('low','relay_stopped','renamed','app_touched','candidate_started')}
        return self.journal.mutate(name,operation)

    @contextmanager
    def receiver(self):
        from monitor.v18.io.live_connection import LiveConnection
        from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
        b=self.original;port=None;c=None
        try:
            port=b.run('forward','tcp:0','tcp:8766',capture=True).stdout.strip()
            c=LiveConnection(socket.create_connection(('127.0.0.1',int(port)),timeout=3),b.serial)
            r=OutputReceiver(c,lambda records:None);r.decoder.numeric=True
            yield r
        finally:
            if c:c.close()
            if port:b.run('forward','--remove','tcp:'+port)

    def capture(self):
        from monitor.v18.io.live_connection import installed_identity
        from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
        b=self.original
        if 'ESTAB' in b.shell('ss','-tn','sport','=',':8766',capture=True).stdout:raise RuntimeError('Q has another reader')
        self.identity=installed_identity(b.serial)
        self.inspect=json.loads(b.shell('docker','inspect',CONTAINER,capture=True).stdout)[0]
        if not self.inspect['State']['Running']:raise RuntimeError('Original relay not running')
        self.governor=b.shell('cat',self.governor_path,capture=True).stdout.strip()
        self.report['cpu_state']=self.cpu_state(self.inspect)
        with self.receiver() as r:
            lifecycle=ReceiverLifecycle(r,self.identity,self.folder)
            self.snapshot=lifecycle.capture()
            if self.snapshot.generator.enabled:raise RuntimeError('Generator must be OFF')
        self.report.update(identity=self.identity,snapshot=self.snapshot.to_dict(),original_relay=self.inspect,cpu_governor=self.governor)

    def prepare(self):
        from monitor.v18.receiver.unoq_acquisition import Configuration
        from monitor.relay_identity import relay_sources,relay_digest
        b=self.original
        def low():
            with self.receiver() as r:r.select(0);r.configure(Configuration(14,40000));self.low=True
        self.action('configure_low',low)
        # Save the inactive baseline separately: restoring an active governor
        # before re-enabling a fast profile would corrupt the relay's baseline.
        self.report['normal_cpu_governor']=b.shell('cat',self.governor_path,capture=True).stdout.strip()
        self.report['normal_cpu_state']=self.cpu_state(self.inspect)
        self.persist()
        self.report['backup']=str(self.action('backup_original',b.backup));self.persist()
        # Retain the entire stopped container: exact mounts/env/caps/cpuset survive.
        self.action('stop_original_relay',lambda:b.shell('docker','stop','--time','3',CONTAINER));self.relay_stopped=True;self.persist()
        self.action('save_original_relay',lambda:b.shell('docker','rename',CONTAINER,self.saved_name));self.renamed=True;self.persist()
        self.app_touched=True;self.action('stop_original_app',b.stop)
        local=self.folder/'candidate_app';shutil.copytree(self.source/'oscilloscope',local)
        yaml=local/'app.yaml';yaml.write_text('name: '+self.app_name+'\n'+'\n'.join(yaml.read_text().splitlines()[1:])+'\n')
        cfg=dict(b.config,name=self.app_name,remote_app=self.app,local_app=str(local))
        self.candidate=type(b)(cfg)
        apps=json.loads(b.cli('app','list','--format','json',capture=True).stdout)['apps']
        self.report['app_list_before_candidate']=apps;self.persist()
        matches=[a for a in apps if a.get('name')==cfg['name']]
        if matches:
            ids=b.shell('docker','ps','-aq',capture=True).stdout.split()
            containers=json.loads(b.shell('docker','inspect',*ids,capture=True).stdout) if ids else []
            remote=json.loads(b.shell('python3','-c',REMOTE_MANIFEST,self.app,capture=True).stdout)
            normalized=[]
            for a in matches:
                import base64
                expected_id=base64.b64encode(('user:'+Path(self.app).name).encode()).decode().rstrip('=')
                if a.get('id')!=expected_id or a.get('status') not in ('stopped','uninitialized'):
                    raise RuntimeError('Candidate identity/state not confirmed')
                normalized.append(dict(name=a['name'],path=self.app,running=False))
            decision=adoption_decision(normalized,containers,source_manifest(local),remote,remote_app=self.app)
        else:decision='create'
        self.report['candidate_app_action']=decision;self.persist()
        if decision=='create':
            self.action('compile_candidate',self.candidate.compile)
            self.action('import_candidate',self.candidate.create)
        self.relay='/home/arduino/.cache/serialmonitor/v18-rate-probe-'+relay_digest(self.source/'relay')
        self.action('mkdir_private_relay',lambda:b.shell('mkdir','-p',self.relay))
        for p in relay_sources(self.source/'relay'):self.action('push_private_relay_'+p.name,lambda p=p:b.run('push',str(p),self.relay+'/'+p.name))
        self.action('build_private_relay',lambda:b.shell('docker','run','--rm','--user','0:0','--security-opt','no-new-privileges',
            '--mount',f'type=bind,src={self.relay},dst=/build','--entrypoint','sh',self.BUILD_IMAGE,'-c',
            'apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && cc -O2 -std=c11 -Wall -Wextra -Werror /build/unoq_config_stream.c -lm -o /build/unoq_stream'))
        self.report['candidate_relay']=self.relay

    def restart(self):
        b=self.original
        names=b.shell('docker','ps','-a','--format','{{.Names}}',capture=True).stdout.splitlines()
        if CONTAINER in names:self.action('remove_previous_candidate_relay',lambda:b.shell('docker','rm','-f',CONTAINER))
        self.candidate_started=True
        self.action('start_candidate_app',self.candidate.start)
        self.action('start_candidate_relay',lambda:b.shell('docker','run','-d','--name',CONTAINER,'--network','host','--read-only','--cap-drop','ALL',
            '--cap-add','SYS_NICE','--env','SCOPE_EXPERIMENT_RT=1','--security-opt','no-new-privileges','--user','0:0',
            '--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw',
            '--mount',f'type=bind,src={self.relay}/unoq_stream,dst=/work/unoq_stream,readonly',
            '--mount',f'type=bind,src={self.governor_path},dst=/scope_cpu_governor',
            '--entrypoint','/work/unoq_stream',self.IMAGE))
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            logs=b.run('shell','docker logs '+CONTAINER+' 2>&1',capture=True).stdout
            if 'SPI ready: first verified frame' in logs:return
            time.sleep(.2)
        raise TimeoutError('Candidate relay startup')

    def candidate_identity(self):
        b=self.original
        info=json.loads(b.shell('docker','inspect',self.app_container,capture=True).stdout)[0]
        root=info['Config']['Labels']['com.docker.compose.project.working_dir']
        if root!=self.app+'/.cache':raise RuntimeError('Candidate firmware location changed')
        relay=json.loads(b.shell('docker','inspect',CONTAINER,capture=True).stdout)[0]
        mounts=[m['Source'] for m in relay['Mounts'] if m['Destination']=='/work/unoq_stream']
        if mounts!=[self.relay+'/unoq_stream']:raise RuntimeError('Candidate relay mount mismatch')
        paths=[root+'/sketch/sketch.ino.bin',mounts[0]]
        hashes=b.shell('sha256sum',*paths,capture=True).stdout.splitlines()
        values=[line.split()[0] for line in hashes]
        if len(values)!=2 or any(len(value)!=64 or any(c not in '0123456789abcdef' for c in value) for value in values):
            raise RuntimeError('Candidate SHA256 invalid')
        return dict(firmware_sha256=values[0],relay_sha256=values[1],app=self.app)

    def measure(self,p):
        from monitor.v18.receiver.unoq_acquisition import Configuration
        row=dict(p,ok=False,measured=False);metrics=FrameMetrics();stage='startup'
        try:
            self.restart()
            with self.receiver() as r:
                r.select(0);r.generator()
                r.configure(Configuration(14,40000))
                actual=self.candidate_identity()
                expected=self.report.setdefault('candidate_identity_expected',actual)
                if actual!=expected:raise RuntimeError('Candidate identity changed between independent runs')
                row['candidate_identity']=actual;self.persist()
                stage='warmup'
                if p['bits']==8:
                    r.configure(Configuration.from_wire(8,3456<<16|112))
                    warm_end=time.monotonic()+2
                    while time.monotonic()<warm_end:r.pump()
                    row['warmup']={'bits':8,'ticks':112,'seconds':2}
                stage='integrity'
                encoded=(p['node_pairs']<<16)|p['ticks']|(0x80000000 if p.get('channels',1)==2 else 0)
                r.configure(Configuration.from_wire(p['bits'],encoded))
                end=time.monotonic()+1
                while time.monotonic()<end:r.pump()
                before=r.decoder.pairs;start=time.monotonic();row['measured']=True
                while time.monotonic()-start<p['seconds']:
                    r.pump();metrics.observe(r.decoder.statuses)
                elapsed=time.monotonic()-start;samples=r.decoder.pairs-before
                if abs(samples/elapsed/p['rate']-1)>.02:raise ValueError('Observed rate mismatch')
                if not metrics.frames:raise ValueError('Missing metrics')
                budget=p['node_pairs']*p['ticks'];margin=metrics.margin(budget)
                peak=metrics.queue_peak;slack=metrics.min_slack
                row.update(ok=True,samples=samples,elapsed=elapsed,status=r.decoder.status,queue_peak=peak,
                    min_slack_ticks=slack,mean_send_margin=margin,send_margin_weighting="frames",
                    metric_frames=metrics.frames,
                    headroom_ok=margin is not None and margin>=.1 and peak<4 and slack>0)
        except Exception as exc:
            row.update(error=repr(exc),failure_stage=stage)
            if row['measured']:
                row.update(elapsed=time.monotonic()-start,samples=r.decoder.pairs-before,
                           last_valid_status=r.decoder.status)
        finally:
            try:
                logs=self.original.run('shell','docker logs '+CONTAINER+' 2>&1',capture=True).stdout
                (self.folder/f'case_{p["bits"]}_{p["ticks"]}_run{p.get("repetition",1)}.log').write_text(logs)
            except Exception as exc:row['log_error']=repr(exc)
        return row

    def cpu_state(self,info):
        pid=str(info['State']['Pid'])
        code="import json,os,sys; p=int(sys.argv[1]); print(json.dumps(dict(policy=os.sched_getscheduler(p),priority=os.sched_getparam(p).sched_priority,cpus=sorted(os.sched_getaffinity(p)))))"
        return json.loads(self.original.shell('python3','-c',code,pid,capture=True).stdout)

    def restore(self):
        from monitor.v18.io.live_connection import installed_identity
        from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
        b=self.original;errors=[];result={'hardware_restored':False}
        def attempt(name,fn):
            try:return self.action('rollback_'+name,fn) if hasattr(self,'journal') else fn()
            except BaseException as exc:errors.append(name+': '+repr(exc))
        if self.renamed:
            def remove_candidate_relay():
                names=b.shell('docker','ps','-a','--format','{{.Names}}',capture=True).stdout.splitlines()
                if CONTAINER in names:b.shell('docker','rm','-f',CONTAINER)
            attempt('remove_candidate_relay',remove_candidate_relay)
        if self.app_touched:
            if self.candidate_started:attempt('stop_candidate_app',self.candidate.stop)
            attempt('start_original_app',b.start)
        if self.renamed:attempt('rename_original_relay',lambda:b.shell('docker','rename',self.saved_name,CONTAINER))
        if self.relay_stopped:attempt('start_original_relay',lambda:b.shell('docker','start',CONTAINER))
        def restore_governor():
            target=self.report.get('normal_cpu_governor',self.governor)
            current=b.shell('cat',self.governor_path,capture=True).stdout.strip()
            if current==target:return
            mounts=[m for m in self.inspect.get('Mounts',[]) if m.get('Source')==self.governor_path and m.get('RW')]
            if len(mounts)!=1:raise RuntimeError('No writable original governor mount')
            b.shell('docker','exec','--user','0:0',CONTAINER,'sh','-c',
                'printf %s '+shlex.quote(target)+' > '+shlex.quote(mounts[0]['Destination']))
        attempt('restore_governor',restore_governor)
        def verify_normal_cpu():
            if 'normal_cpu_state' not in self.report:return
            info=json.loads(b.shell('docker','inspect',CONTAINER,capture=True).stdout)[0]
            actual=self.cpu_state(info)
            result['normal_cpu_state_equal']=actual==self.report['normal_cpu_state']
            if not result['normal_cpu_state_equal']:
                raise RuntimeError('Inactive CPU baseline differs before profile restoration')
        attempt('verify_normal_cpu',verify_normal_cpu)
        def recover():
            # Only connection startup may wait; recovery itself is attempted once.
            deadline=time.monotonic()+15
            while True:
                try:
                    with self.receiver() as r:
                        lifecycle=ReceiverLifecycle(r,self.identity,self.folder);lifecycle.snapshot=self.snapshot
                        return lifecycle.restore(10)
                except OSError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.2)
        recovered=attempt('snapshot_recovery',recover)
        if recovered:result.update(recovered)
        actual=attempt('identity',lambda:installed_identity(b.serial))
        result['identity_equal']=actual==self.identity
        restored=attempt('inspect_original_relay',lambda:json.loads(b.shell('docker','inspect',CONTAINER,capture=True).stdout)[0])
        result['restored_relay_inspect']=restored
        result['relay_configuration_equal']=bool(restored) and relay_configuration_equal(restored,self.inspect)
        governor=attempt('readback_governor',lambda:b.shell('cat',self.governor_path,capture=True).stdout.strip())
        result['cpu_governor_equal']=governor==self.governor
        cpu=attempt('readback_cpu',lambda:self.cpu_state(restored)) if restored else None
        result['cpu_state_equal']=cpu==self.report.get('cpu_state')
        result['rollback_errors']=errors
        result['hardware_restored']=bool(result.get('hardware_restored') and result['identity_equal'] and
            result['relay_configuration_equal'] and result['cpu_governor_equal'] and result['cpu_state_equal'] and not errors)
        return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true');parser.add_argument('--bits',nargs='+',type=int,default=[8,10,12,14,16])
    parser.add_argument('--seconds',type=float,default=15)
    parser.add_argument('--target-ticks',nargs='+',type=int)
    parser.add_argument('--repeats',type=int,choices=range(1,4),default=1)
    parser.add_argument('--recipe',choices=('baseline','spi40_10_12','wide8','spin100','txclean','word14','full8','crc8','wordping','spi16','batch2','batchfast','batchnative','batchstack','batcharena','batchquickack','trace8','trace8time','alignedping'),default='baseline')
    args=parser.parse_args(argv);rows=[dict(row,repetition=repetition)
        for repetition in range(1,args.repeats+1)
        for row in plan(args.bits,args.seconds,args.target_ticks,args.recipe)]
    if not args.run:print(json.dumps(dict(private=True,transport='SPI',cases=rows),indent=2));return 0
    from monitor.v18.board_owner import board_owner
    folder=EXP/'resultados'/time.strftime('%Y%m%d_%H%M%S');folder.mkdir(parents=True)
    (folder/'runner.py').write_bytes(Path(__file__).read_bytes())
    report=dict(ok=False,cases=[],plan=rows,recipe=args.recipe,runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    journal=ProbeJournal(folder/'report.json',report)
    save=journal.save
    backend=Hardware(folder,report)
    def interrupted(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,interrupted)
    with board_owner(backend.original.serial,'V18 isolated rate probe'),private_profiles(backend.source):
        ok=orchestrate(backend,rows,report,save)
    print(folder/'report.json');return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
