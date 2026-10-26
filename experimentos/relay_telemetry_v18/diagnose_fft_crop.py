"""Exclusive relay-only A/B. Preserve original container and MCU; always restore."""
import json,time,socket,contextlib,subprocess,shlex,sys
from pathlib import Path
from experimentos.relay_telemetry_v18.prepare import HERE
from experimentos.fs_max_v18.run_probe import FrameMetrics,relay_configuration_equal
from monitor.v18.q_support.board import Board,CONFIG
from monitor.v18.board_owner import board_owner
from monitor.v18.io.live_connection import installed_identity,LiveConnection
from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
from monitor.v18.receiver.unoq_acquisition import Configuration
NAME='serialmonitor-usb-stream-v18'

@contextlib.contextmanager
def receive(b):
    port=b.run('forward','tcp:0','tcp:8766',capture=True).stdout.strip();connection=None
    try:
        connection=LiveConnection(socket.create_connection(('127.0.0.1',int(port)),timeout=3),b.serial)
        receiver=OutputReceiver(connection,lambda records:None);receiver.decoder.numeric=True
        yield receiver
    finally:
        if connection:connection.close()
        b.run('forward','--remove','tcp:'+port)

class Lease:
    def __init__(self,serial):self.serial=serial;self.context=None
    def acquire(self):
        if self.context is not None:raise RuntimeError('Lease already held')
        context=board_owner(self.serial,'V18 relay A/B coordinator')
        context.__enter__();self.context=context
    def release(self):
        if self.context is not None:
            context,self.context=self.context,None
            context.__exit__(None,None,None)
    def __enter__(self):self.acquire();return self
    def __exit__(self,*args):self.release()

def main():
    builds=sorted(HERE.glob('build_*/report.json'));build=json.loads(builds[-1].read_text());assert build['ok']
    folder=HERE/time.strftime('fft_crop_diagnosis_%Y%m%d_%H%M%S');folder.mkdir()
    report=dict(ok=False,firmware_changed=False,cases=[],build=str(builds[-1]),restoration={})
    def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    b=Board(json.loads(CONFIG.read_text()));renamed=False;stopped=False;snapshot=None;identity=None;inspect=None
    saved=NAME+'-saved-telemetry-'+str(int(time.time()))
    def logs(label):
        r=subprocess.run([b.adb,'-s',b.serial,'shell',shlex.join(['docker','logs','--timestamps','--tail','100',NAME])],capture_output=True,text=True)
        (folder/(label+'.log')).write_text(r.stdout+r.stderr)
    def measure(variant):
        before=set((HERE.parents[1]/'diagnosticos/resultados_v18').glob('radio_rate_check_*'))
        # The GUI child owns the actual Q lock throughout I/O and restoration.
        lease.release()
        try:
            command=[sys.executable,str(HERE.parents[1]/'tools/probe_radio_rate_v18.py'),
                '--bits','8','--ticks','86','--hold','120','--frequency-khz','550','--keep-display-awake',
                '--fft-size','65536','--crop-radios']
            with (folder/(variant+'_gui.log')).open('w') as log:
                result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        finally:
            lease.acquire()
        added=set((HERE.parents[1]/'diagnosticos/resultados_v18').glob('radio_rate_check_*'))-before
        if len(added)!=1:raise RuntimeError('Missing unique GUI evidence')
        evidence=added.pop();outer=json.loads((evidence/'report.json').read_text())
        gui=json.loads((evidence/'gui.json').read_text())
        expected_relay=identity['relay_sha256'] if variant=='accepted' else build['relay_sha256']
        exact=outer['identity']['firmware_sha256']==identity['firmware_sha256'] and outer['identity']['relay_sha256']==expected_relay
        functional=not gui['errors'] and all(gui['assertions'].values()) and gui['radio_hold_seconds']>=120
        restored=outer.get('restoration',{}).get('hardware_restored') and outer.get('identity_unchanged')
        row=dict(variant=variant,bits=8,ticks=86,seconds=120,ok=bool(exact and functional and restored),
            visible_gui_ok=outer.get('visible_gui_ok'),evidence=str(evidence),exit_code=result.returncode)
        report['cases'].append(row);save();print('AUDIO',row,flush=True)
        if not row['ok']:raise RuntimeError('Combined RADIO/A0 test failed')
    save();print(folder,flush=True)
    with Lease(b.serial) as lease:
        try:
            if 'ESTAB' in b.shell('ss','-tn','sport','=',':8766',capture=True).stdout:raise RuntimeError('Another Q reader active')
            identity=installed_identity(b.serial)
            if identity!=build['identity']:raise RuntimeError('Baseline differs from build baseline')
            receipt=json.loads((HERE.parents[1]/'monitor/v18/q_support/accepted/acceptance.json').read_text())
            if not receipt['accepted'] or any(identity[k]!=receipt[name]['sha256'] for k,name in (('firmware_sha256','firmware'),('relay_sha256','relay'))):raise RuntimeError('Baseline is not the accepted pair')
            report['identity']=identity
            inspect=json.loads(b.shell('docker','inspect',NAME,capture=True).stdout)[0];report['original_relay']=inspect
            binary=build['remote']+'/unoq_stream'
            assert b.shell('sha256sum',binary,capture=True).stdout.split()[0]==build['relay_sha256']
            with receive(b) as receiver:
                life=ReceiverLifecycle(receiver,identity,folder/'initial');snapshot=life.capture()
                report['snapshot']=snapshot.to_dict();save()
                if snapshot.generator.enabled:raise RuntimeError('Generator active; leave state untouched')
            report['baseline_reference']='diagnosticos/resultados_v18/radio_rate_check_20261026_182606/report.json'
            report['scope']='Dedicated instrumented FFT crop diagnosis, not performance A/B'
            b.shell('docker','stop','--time','3',NAME);stopped=True
            b.shell('docker','rename',NAME,saved);renamed=True;save()
            # A fresh checker requires the MCU startup epoch; restart the unchanged accepted app.
            b.start()
            firmware=b.shell('sha256sum',b.remote+'/.cache/sketch/sketch.ino.bin',capture=True).stdout.split()[0]
            if firmware!=identity['firmware_sha256']:raise RuntimeError('Firmware drift after app restart')
            governor=next(m['Source'] for m in inspect['Mounts'] if m['Destination']=='/scope_cpu_governor')
            b.shell('docker','run','-d','--name',NAME,'--network','host','--read-only','--cap-drop','ALL','--cap-add','SYS_NICE',
                '--security-opt','no-new-privileges','--user','0:0','--device','/dev/spidev0.0:/dev/spidev0.0:rw',
                '--device','/dev/gpiochip1:/dev/gpiochip1:rw','--mount',f'type=bind,src={binary},dst=/work/unoq_stream,readonly',
                '--mount',f'type=bind,src={governor},dst=/scope_cpu_governor','--entrypoint','/work/unoq_stream',inspect['Config']['Image'])
            deadline=time.monotonic()+15
            while True:
                try:
                    current=installed_identity(b.serial)
                    if current['firmware_sha256']!=identity['firmware_sha256'] or current['relay_sha256']!=build['relay_sha256']:raise RuntimeError('Unexpected candidate identity')
                    with receive(b) as receiver:receiver.pump()
                    break
                except (OSError,RuntimeError):
                    if time.monotonic()>deadline:raise
                    time.sleep(.2)
            measure('instrumented')
            report['measurement_ok']=True
        except BaseException as exc:report['error']=repr(exc)
        finally:
            cleanup_errors=[]
            def attempt(label,operation):
                try:return operation()
                except BaseException as exc:
                    cleanup_errors.append(label+': '+repr(exc));return None
            names=attempt('list containers',lambda:b.shell('docker','ps','-a','--format','{{.Names}}',capture=True).stdout.splitlines())
            if renamed:
                if names is not None and NAME in names:
                    attempt('stop candidate',lambda:b.shell('docker','stop','--time','3',NAME))
                    attempt('candidate logs',lambda:logs('instrumented_exit'))
                    info=attempt('inspect candidate',lambda:json.loads(b.shell('docker','inspect',NAME,capture=True).stdout)[0])
                    if info is not None and not info['State']['Running']:
                        attempt('remove stopped candidate',lambda:b.shell('docker','rm',NAME))
                names=attempt('list before rename',lambda:b.shell('docker','ps','-a','--format','{{.Names}}',capture=True).stdout.splitlines())
                if names is not None and NAME not in names and saved in names:
                    attempt('rename original',lambda:b.shell('docker','rename',saved,NAME))
            after=attempt('inspect original',lambda:json.loads(b.shell('docker','inspect',NAME,capture=True).stdout)[0])
            original_present=after is not None and inspect is not None and after['Id']==inspect['Id']
            if original_present and (renamed or not after['State']['Running']):
                attempt('stop original for synchronized restart',lambda:b.shell('docker','stop','--time','3',NAME))
                attempt('restart unchanged original app',b.start)
                attempt('start original',lambda:b.shell('docker','start',NAME))
            if snapshot is not None and original_present:
                def restore_snapshot():
                    deadline=time.monotonic()+15
                    while True:
                        try:
                            with receive(b) as receiver:
                                life=ReceiverLifecycle(receiver,identity,folder/'restore');life.snapshot=snapshot
                                report['restoration']=life.restore(10)
                            return
                        except OSError:
                            if time.monotonic()>deadline:raise
                            time.sleep(.2)
                attempt('restore snapshot',restore_snapshot)
                actual=attempt('verify identity',lambda:installed_identity(b.serial))
                report['identity_restored']=actual==identity
                after=attempt('verify original container',lambda:json.loads(b.shell('docker','inspect',NAME,capture=True).stdout)[0])
                report['original_container_restored']=after is not None and after['Id']==inspect['Id'] and relay_configuration_equal(after,inspect)
            attempt('original logs',lambda:logs('accepted_final'))
            report['cleanup_errors']=cleanup_errors
            report['ok']=bool(report.get('measurement_ok') and not cleanup_errors and report['restoration'].get('hardware_restored') and report.get('identity_restored') and report.get('original_container_restored'))
            save();print('FINAL',report['ok'],folder,flush=True)
    return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
