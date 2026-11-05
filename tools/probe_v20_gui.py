#!/usr/bin/env python3
"""Private V20 GUI/RADIO screen with V19 exact rollback and receiver-owned Q."""
import argparse
import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.private_v20_pair import checked_proof,reserve_screen,APP,APP_CONTAINER
from tools.probe_v20_sram3 import MANIFEST,CONTAINER
from tools.probe_relay_gui_v19 import execute_gui
from monitor.v19.q_support.backend import ProductionBackend,_relay_policy_equal,GOVERNOR
from monitor.v19.q_support.prepare import atomic_report,load_acceptance
from monitor.v19.q_support.service import RECEIPT


class TrialBackend(ProductionBackend):
    def __init__(self,*args,output,**kwargs):
        super().__init__(*args,**kwargs);self.output=output;self.v20_active=False
        self.v20_relay_id=None;self.v20board=None;self.selected=None
    def _identity(self):
        if not self.v20_active:return super()._identity()
        from monitor.v20.io.live_connection import installed_identity
        actual=installed_identity(self._board().serial,expected_app=APP_CONTAINER,require_accepted=False)
        expected=dict(board_serial=self._board().serial,app=APP_CONTAINER,
                      firmware_sha256=self.selected['firmware_sha256'],relay_sha256=self.selected['relay_sha256'])
        if actual!=expected:raise RuntimeError('Installed V20 candidate identity differs')
        return actual
    def stop_new_relay(self,baseline,prepared):
        if self.v20_relay_id is not None:
            info=self._inspect(CONTAINER)
            if info['Id']!=self.v20_relay_id:raise RuntimeError('V20 relay owner changed')
            (self.output/'v20_relay.log').write_text(self._output('sh','-c','docker logs '+CONTAINER+' 2>&1'))
            self._board().shell('docker','stop',CONTAINER)
            self._board().shell('docker','rename',CONTAINER,CONTAINER+'-evidence-'+self.token[:8])
            self.v20_relay_id=None
        super().stop_new_relay(baseline,prepared)
    def stop_app(self):
        if self.v20_active:
            self.v20board.stop();self.v20_active=False
        else:super().stop_app()


def activate(b,acceptance,candidate,baseline,journal):
    board=b._board();b.selected=candidate
    from monitor.v20.memory_contract import verify_board
    if verify_board(board)!=candidate['memory_contract']:raise RuntimeError('V20 memory BSP contract changed')
    actual=json.loads(board.shell('python3','-c',MANIFEST,APP,json.dumps(list(candidate['v20_sources'])),capture=True).stdout)
    if actual!=candidate['v20_sources']:raise RuntimeError('Imported V20 sources changed')
    if b._hash(APP+'/.cache/sketch/sketch.ino.bin')!=candidate['firmware_sha256']:
        raise RuntimeError('V20 firmware differs from measured proof')
    cfg=json.loads((ROOT/'arduino/v20/unoq.json').read_text());cfg['remote_app']=APP
    b.v20board=board.__class__(cfg);b.v20board.serial=board.serial
    b.v20_active=True;b.v20board.start()
    if b._hash(APP+'/.cache/sketch/sketch.ino.bin')!=candidate['firmware_sha256']:
        raise RuntimeError('Launcher changed V20 firmware')
    stage='/home/arduino/.cache/serialmonitor/v20-gui-'+b.token
    board.shell('mkdir','-p',stage);board.run('push',candidate['relay_path'],stage+'/unoq_stream')
    board.shell('chmod','0755',stage+'/unoq_stream')
    if b._hash(stage+'/unoq_stream')!=candidate['relay_sha256']:raise RuntimeError('V20 staged relay differs')
    if CONTAINER in b._output('docker','ps','-a','--format','{{.Names}}').splitlines():
        raise RuntimeError('Existing V20 relay cannot be overwritten')
    board.shell('docker','run','-d','--name',CONTAINER,'--network','host','--read-only',
        '--cap-drop','ALL','--cap-add','SYS_NICE','--security-opt','no-new-privileges','--user','0:0',
        '--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw',
        '--mount','type=bind,src='+stage+'/unoq_stream,dst=/work/unoq_stream,readonly',
        '--mount','type=bind,src='+GOVERNOR+',dst=/scope_cpu_governor',
        '--entrypoint','/work/unoq_stream','ghcr.io/arduino/app-bricks/python-apps-base:0.12.0')
    info=b._inspect(CONTAINER);b.v20_relay_id=info['Id']
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        if 'SPI ready: first verified frame' in b._output('sh','-c','docker logs '+CONTAINER+' 2>&1'):break
        time.sleep(.2)
    else:raise RuntimeError('V20 relay synchronization timeout')
    identity=b._identity()
    port=board.run('forward','tcp:0','tcp:8766',capture=True).stdout.strip()
    from monitor.v20.io.live_connection import LiveConnection
    from monitor.v20.receiver.unoq_config_receiver import OutputReceiver
    from monitor.v20.io.receiver_lifecycle import ReceiverLifecycle
    connection=None
    try:
        connection=LiveConnection(socket.create_connection(('127.0.0.1',int(port)),timeout=3),board.serial)
        receiver=OutputReceiver(connection,lambda _:None);receiver.decoder.numeric=True
        life=ReceiverLifecycle(receiver,identity,b.output/'private_load_sessions');snapshot=life.capture()
        recovery=life.restore(10)
    finally:
        if connection is not None:connection.close()
        board.run('forward','--remove','tcp:'+port)
    before=dict(baseline['snapshot']);after=snapshot.to_dict();before.pop('identity');after.pop('identity')
    info=b._inspect(CONTAINER)
    return dict(accepted_identity_equal=identity['firmware_sha256']==candidate['firmware_sha256'] and identity['relay_sha256']==candidate['relay_sha256'],
                sources_exact=actual==candidate['v20_sources'],snapshot_equal=before==after and recovery['hardware_restored'],
                continuous=recovery['recovery']['continuous'],integrity_ok=recovery['recovery']['dropped']==0 and recovery['recovery']['fatal']==0,
                cpu_equal=b._cpu(info)==baseline['cpu_state'] and b._output('cat',GOVERNOR)==baseline['governor'],
                relay_configuration_verified=_relay_policy_equal(baseline['relay_inspect'],info,
                    b._relay_bin(baseline['relay_inspect']),stage+'/unoq_stream'))


def queue_capacity(bits,rate):
    from monitor.v20.receiver.unoq_acquisition import Configuration
    return (Configuration(bits,rate)._native or {}).get('queue_slots',4)


def scenario_command(args,binding,output):
    cmd=[sys.executable,str(ROOT/'tools/gui_private_v20.py'),'--firmware-binding',str(binding),'--serial',args.serial,
         '--output',str(output/'gui.json'),'--bits',str(args.bits),'--rate',str(args.rate),
         '--frequency-khz','710','--no-retune','--duration',str(args.hold+5),
         '--hold-radio-seconds',str(0 if args.analysis_mode else args.hold)]
    if args.analysis_mode or not args.window_seconds:cmd+=['--fft-size','16384']
    if args.analysis_mode:cmd+=['--analysis-mode',args.analysis_mode,'--fft-only']
    if args.window_seconds:cmd+=['--window-seconds',str(args.window_seconds)]
    if args.detail_percent is not None:cmd+=['--detail-percent',str(args.detail_percent)]
    if args.us:cmd+=['--us']
    if args.scan_during_a0:cmd+=['--scan-during-a0']
    elif args.us:cmd+=['--scan']
    if args.wav:cmd+=['--wav']
    if args.fm:cmd+=['--fm','--voices',str(args.voices)]
    return cmd


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial',required=True);p.add_argument('--proof',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--hold',type=int,default=20,choices=(20,60,120))
    p.add_argument('--wav',action='store_true');p.add_argument('--fm',action='store_true')
    p.add_argument('--voices',type=int,choices=range(1,21),default=1)
    p.add_argument('--bits',type=int,choices=(8,10,12,14,16),default=8)
    p.add_argument('--rate',type=int,default=1860465)
    p.add_argument('--us',action='store_true')
    p.add_argument('--scan-during-a0',action='store_true')
    p.add_argument('--analysis-mode',choices=('vt','fft','heatmap','bode'))
    p.add_argument('--window-seconds',type=float,default=0)
    p.add_argument('--detail-percent',type=int,choices=range(1,101))
    p.add_argument('--raster-workers',type=int,choices=(1,2,4),default=1)
    p.add_argument('--raster-nice',type=int,choices=(0,10),default=0)
    p.add_argument('--raw-ack-latency',action='store_true')
    args=p.parse_args();output=args.output.resolve()
    if args.raster_nice and args.raster_workers==1:p.error('Priority experiment requires private strip workers')
    if args.raster_workers!=1 and not(args.analysis_mode in (None,'vt') and args.window_seconds>0 and args.detail_percent==100):
        p.error('Private tiles require a full-detail long V(t) window')
    if args.window_seconds<0 or (args.window_seconds and args.analysis_mode not in (None,'vt')):
        p.error('Long time windows require V(t) and a nonnegative duration')
    if args.raw_ack_latency and args.analysis_mode:p.error('Raw ACK capture requires an audio scenario')
    if args.analysis_mode and (args.us or args.scan_during_a0 or args.wav or args.fm):
        p.error('Raw analysis must be separate from audio/scan scenarios')
    from monitor.v20.receiver.unoq_acquisition import Configuration
    try:Configuration(args.bits,args.rate)
    except ValueError as exc:p.error(str(exc))
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v20'):p.error('New V20 diagnostic output required')
    candidate=checked_proof(args.proof);acceptance=load_acceptance(RECEIPT);output.mkdir(parents=True)
    report=dict(private=True,promoted=False,version=20,requested_tests=dict(radio=not bool(args.analysis_mode),wav=args.wav,fm=args.fm,voices=args.voices,us=args.us,scan_during_a0=args.scan_during_a0,analysis_mode=args.analysis_mode,bits=args.bits,rate=args.rate,window_seconds=args.window_seconds,detail_percent=args.detail_percent,raster_workers=args.raster_workers,raster_nice=args.raster_nice,raw_ack_latency=args.raw_ack_latency),**candidate);binding=output/'report.json'
    from monitor.v20.q_support.board import source_files
    monitor_root=ROOT/'monitor/v20'
    report['monitor_sources']={path.relative_to(monitor_root).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files(monitor_root)}
    report['tool_sources']={name:hashlib.sha256((ROOT/'tools'/name).read_bytes()).hexdigest() for name in ('probe_v20_gui.py','gui_private_v20.py','gui_live_smoke_v20.py','qt_timer_trace_v20.py','private_raster_tiles_v20.py','benchmark_raster_tiles_v20.py','process_resources_v20.py','reader_stages_v20.py','private_v20_pair.py','relay_wire_metrics_v19.py')}
    save=lambda:atomic_report(binding,report);save()
    b=TrialBackend(acceptance,output=output);b._board().serial=args.serial
    def gui():
        cmd=scenario_command(args,binding,output)
        report['gui_command']=cmd;save();guard=child=None;resources=None
        child_env=dict(os.environ,PYTHONFAULTHANDLER='1',ARDUSCOPIO_PRIVATE_RASTER_WORKERS=str(args.raster_workers),ARDUSCOPIO_PRIVATE_RASTER_NICE=str(args.raster_nice))
        if args.raw_ack_latency:child_env.update(ARDUSCOPIO_PRIVATE_RAW_ACK_LATENCY='1',MONITOR_V19_CHILD_STAGE_TIMING='1')
        try:
            if sys.platform=='darwin':guard=subprocess.Popen(['caffeinate','-du','-t',str(args.hold+180)])
            with (output/'gui.log').open('w') as log:
                child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=child_env)
                from tools.process_resources_v20 import ProcessResources
                resources=ProcessResources(child.pid,output/'process_resources.jsonl')
                deadline=time.monotonic()+args.hold+150
                while child.poll() is None:
                    if time.monotonic()>deadline:raise subprocess.TimeoutExpired(cmd,args.hold+150)
                    resources.sample()
                    try:child.wait(timeout=1)
                    except subprocess.TimeoutExpired:pass
        finally:
            if child is not None and child.poll() is None:
                child.send_signal(signal.SIGINT);child.wait(timeout=90)
            if guard is not None:guard.terminate();guard.wait(timeout=5)
        if not (output/'gui.json').exists():
            raise RuntimeError(f'GUI exited {child.returncode} without final evidence; see {output / "gui.log"}')
        evidence=json.loads((output/'gui.json').read_text())
        report['process_resources']=resources.summary()
        active=[s for s in evidence['stages'] if s['stage']=='periodic' and s.get('radio_playing_seconds') is not None]
        if active and evidence.get('monotonic_started') is not None:
            start=evidence['monotonic_started']+active[0]['elapsed']+10
            end=evidence['monotonic_started']+active[-1]['elapsed']
            report['steady_process_resources']=dict(resources.summary(start,end),start=start,end=end)
        rows=[s for s in evidence['stages'] if s['stage']=='periodic']
        exposed=sum(bool(s.get('exposed')) for s in rows)/max(1,len(rows))
        metrics=json.loads((output/'wire_metrics.json').read_text());radio=metrics['radio_playing']
        if args.raw_ack_latency:
            raw=metrics['raw_chunk_ack_latency']
            stages=json.loads((output/'reader_stages.json').read_text())
            complete=raw['enabled'] and raw['matched']>0 and raw['decoded']>0 and bool(stages['trackers'])
            evidence['assertions']['raw_ack_capture_observed_v20']=bool(complete)
            if not complete:evidence['errors'].append('V20 ACK arrival/processing capture incomplete')
        return dict(ok=child.returncode==0 and not evidence['errors'] and all(evidence['assertions'].values()),
                    errors=evidence['errors'],assertions=evidence['assertions'],exposed_fraction=exposed,
                    visible_gui_ok=exposed>=.9 and evidence['paint_events']>=args.hold*8 and evidence['display']['platform'] not in ('offscreen','minimal'),
                    display=evidence['display'],
                    paint_events=evidence['paint_events'],hold=evidence['radio_hold_seconds'],radio=radio,
                    scan=evidence['scan'],analysis_mode=args.analysis_mode,
                    raw_chunk_ack_latency=metrics['raw_chunk_ack_latency'],
                    analysis_synthetic=args.analysis_mode=='bode',
                    acquisition=metrics['all'],
                    reserve_screen=reserve_screen(radio,queue_capacity(args.bits,args.rate)),
                    scope='Functional V20 private screen; public acceptance remains false')
    previous={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def cancelled(*_):
        if not report.get('restoring') and not report.get('cancelling'):raise KeyboardInterrupt('Restoring V19 after V20 cancellation')
    for sig in previous:signal.signal(sig,cancelled)
    try:ok=execute_gui(b,acceptance,candidate,report,save,gui,activate_pair=activate)
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
    print(json.dumps(dict(ok=ok,error=report.get('error'),restored=report.get('restoration',{}).get('ok'))))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
