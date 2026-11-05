#!/usr/bin/env python3
"""Private GUI/RADIO/A0 relay check with receiver-owned lease and final rollback."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.probe_relay_transport_v19 import checked_artifact
from monitor.v19.q_support.prepare import Journal,_require,atomic_report,load_acceptance,rollback_once,source_changes
from monitor.v19.q_support.backend import ProductionBackend
from monitor.v19.q_support.service import RECEIPT


def relay_cpu_snapshot(backend):
    """Only before/after the GUI owner, never during high-rate acquisition."""
    pid=backend._inspect('serialmonitor-usb-stream-v19')['State']['Pid']
    script=('import json,os,time;'
            f'p={int(pid)};'
            's=open("/proc/%d/stat"%p).read().rsplit(")",1)[1].split();'
            'print(json.dumps(dict(pid=p,start_ticks=int(s[19]),'
            'cpu_ticks=int(s[11])+int(s[12]),hz=os.sysconf("SC_CLK_TCK"),'
            'monotonic=time.monotonic())))')
    return json.loads(backend._output('python3','-c',script))


def relay_cpu_cost(before,after):
    if any(before[k]!=after[k] for k in ('pid','start_ticks','hz')):
        raise ValueError('Relay process identity changed')
    wall=after['monotonic']-before['monotonic'];ticks=after['cpu_ticks']-before['cpu_ticks']
    if wall<=0 or ticks<0:raise ValueError('Invalid CPU observation interval')
    return dict(wall_seconds=wall,cpu_seconds=ticks/before['hz'],
                fraction_of_one_core=ticks/before['hz']/wall,
                caveat='Whole GUI lifetime including startup/restoration, not PLAY-only utilization')


@contextmanager
def restore_owner(backend,timeout=90):
    deadline=time.monotonic()+timeout
    while True:
        lease=backend.owner()
        try:
            lease.__enter__();break
        except RuntimeError as exc:
            if 'Q ocupado' not in str(exc) or time.monotonic()>=deadline:raise
            time.sleep(.1)
    try:yield
    finally:lease.__exit__(None,None,None)


def execute_gui(backend,acceptance,artifact,report,save,gui,activate_pair=None):
    journal=Journal(report,save);baseline=backup=changes=None;dirty=False
    report.update(ok=False,private=True,promoted=False,state_uncertain=False)
    try:
        with backend.owner():
            qualified=journal.step('preflight',lambda:backend.preflight(acceptance))
            _require(qualified,('production_backend_qualified','rollback_rehearsal_verified',
                                'cached_launcher_verified'),'Qualified backend')
            baseline=journal.step('capture',backend.capture);report['baseline']=baseline
            _require(baseline,('generator_off','wav_idle','receiver_closed','identity_verified',
                              'source_manifest_verified'),'Accepted baseline')
            if any(baseline.get('identity',{}).get(k)!=v for k,v in acceptance['candidate_identity'].items()):
                raise RuntimeError('Accepted original pair required')
            backup=journal.step('backup',lambda:backend.backup(baseline));report['backup']=backup
            _require(backup,('export_verified','source_archive_verified','full_cache_verified',
                            'firmware_elf_bin_verified','relay_verified','paired_manifest_persisted'),'Paired backup')
            changes=source_changes(baseline['app_sources'],baseline['app_sources'])
            dirty=True;report['state_uncertain']=True
            for name,args in (('quiesce',(baseline,)),('stop_old_relay',(baseline,)),
                              ('rename_old_relay',(baseline,)),('stop_app',())):
                journal.step(name,lambda name=name,args=args:getattr(backend,name)(*args))
            if activate_pair is None:
                b=backend._board();b.shell('mkdir','-p',backend.new_relay)
                b.run('push',artifact['path'],backend.new_relay+'/unoq_stream')
                b.shell('chmod','0755',backend.new_relay+'/unoq_stream')
                if backend._hash(backend.new_relay+'/unoq_stream')!=artifact['sha256']:
                    raise RuntimeError('Staged candidate hash differs')
                prepared=dict(candidate_identity=dict(acceptance['candidate_identity'],relay_sha256=artifact['sha256']))
                journal.step('start_accepted_firmware',lambda:backend.start_new_app(prepared))
                journal.step('start_private_relay',lambda:backend.start_new_relay(baseline,prepared))
                report['private_candidate_activated']=True
                verification=journal.step('verify_private_pair',lambda:backend.verify_new(
                    baseline,dict(acceptance,candidate_identity=prepared['candidate_identity']),prepared,10))
            else:
                # Transaction/lease mechanics only. The supplied private adapter
                # must validate its own artifact and exact pair before returning.
                verification=activate_pair(backend,acceptance,artifact,baseline,journal)
                report['private_firmware_activated']=True
            _require(verification,('accepted_identity_equal','sources_exact','snapshot_equal',
                'continuous','integrity_ok','cpu_equal','relay_configuration_verified'),'Private pair')
            report['private_verification']=verification;report['private_identity']=backend._identity()
            save()
        # Administrative owner releases its lease. The GUI receiver child must
        # acquire its own lease; it retains it even if this coordinator dies.
        report['gui']=journal.step('gui_radio_a0',gui)
        if not report['gui'].get('ok'):raise RuntimeError('Private GUI/audio check failed')
    except BaseException as exc:
        report['error']=repr(exc)
    finally:
        if dirty:
            report['cancelling']=True
            try:
                with restore_owner(backend):
                    report['restoring']=True
                    backend._no_reader()
                    if backend.new_relay_id is not None:
                        try:
                            report['candidate_relay_log']=backend._output('sh','-c',
                                'docker logs '+shlex.quote(backend.new_relay_id)+' 2>&1')
                        except Exception as exc:report['candidate_log_error']=repr(exc)
                    report['restoration']=rollback_once(backend,baseline,backup,None,changes,journal)
            except BaseException as exc:
                # A live receiver/foreign owner prevents administrative takeover.
                report['restoration']=dict(ok=False,errors=[repr(exc)],blocked=True)
            report['state_uncertain']=not report['restoration']['ok']
            report['restoring']=report['cancelling']=False
        report['ok']=bool(report.get('gui',{}).get('ok') and report.get('restoration',{}).get('ok')
                          and not report.get('error'))
        save()
    return report['ok']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--build-report',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--hold',type=float,default=60)
    parser.add_argument('--fft-size',type=int,choices=(16384,32768,65536),default=16384)
    parser.add_argument('--wav',action='store_true');parser.add_argument('--fm',action='store_true')
    parser.add_argument('--metrics',action='store_true',help='Observe existing MCU counters in the host receiver child')
    parser.add_argument('--keep-display-awake',action='store_true')
    parser.add_argument('--private-ack-refresh',action='store_true')
    parser.add_argument('--process-cost',action='store_true',help='Read relay CPU before/after the GUI, never during it')
    parser.add_argument('--inline-burst',type=int,choices=(1,4,8))
    parser.add_argument('--inline-interval-ms',type=int,choices=(6,8,10))
    parser.add_argument('--startup-only',action='store_true')
    args=parser.parse_args();output=args.output.resolve()
    if (args.inline_interval_ms is not None or args.startup_only) and args.inline_burst is None:
        parser.error('Explicit inline burst required')
    if args.inline_burst is not None and args.private_ack_refresh:parser.error('Inline arm cannot replay legacy ACK')
    if args.inline_burst==1 and not args.startup_only:parser.error('Burst1 is prefill-only; explicit startup-only required')
    if not 0<args.hold<=120:parser.error('hold must be in (0,120]')
    if args.keep_display_awake and sys.platform!='darwin':parser.error('Display guard requires macOS')
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('Use a new directory under diagnosticos/resultados_v19')
    artifact=checked_artifact(args.build_report);acceptance=load_acceptance(RECEIPT)
    output.mkdir(parents=True);binding=output/'report.json'
    report=dict(schema=1,version=19,source_build_report=str(args.build_report.resolve()),private=True,promoted=False)
    report['host_cadence']=dict(burst=args.inline_burst,interval_ms=args.inline_interval_ms,startup_only=args.startup_only)
    save=lambda:atomic_report(binding,report);save()
    backend=ProductionBackend(acceptance);backend._board().serial=args.serial
    def gui():
        cpu_before=relay_cpu_snapshot(backend) if args.process_cost else None
        if cpu_before is not None:report['relay_cpu_before']=cpu_before;save()
        command=[sys.executable,str(ROOT/'tools/gui_relay_candidate_v19.py'),'--binding',str(binding),
            '--serial',args.serial,'--output',str(output/'gui.json'),'--bits','8','--rate','1860465',
            '--duration',str(args.hold+5),'--hold-radio-seconds',str(args.hold),
            '--fft-size',str(args.fft_size),'--frequency-khz','710','--voices','20']
        if args.wav:command.append('--wav')
        if args.fm:command.append('--fm')
        if args.metrics:command.append('--metrics')
        if args.private_ack_refresh:command.append('--private-ack-refresh')
        if args.inline_burst is not None:command+=['--inline-burst',str(args.inline_burst)]
        if args.inline_interval_ms is not None:command+=['--inline-interval-ms',str(args.inline_interval_ms)]
        if args.startup_only:command+=['--startup-only']
        report['gui_command']=command;save()
        child=guard=None
        try:
            if args.keep_display_awake:
                guard=subprocess.Popen(['/usr/bin/caffeinate','-du','-t',str(int(args.hold+180))])
                report['display_guard']=dict(pid=guard.pid,scoped=True);save()
            with (output/'gui.log').open('w') as log:
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
                report['gui_pid']=child.pid;save()
                try:child.wait(timeout=args.hold+150)
                except subprocess.TimeoutExpired:raise RuntimeError('GUI deadline exceeded')
        finally:
            if child is not None and child.poll() is None:
                report['cancelling']=True
                child.send_signal(signal.SIGINT)
                try:child.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    report['gui_owner_still_active']=True
                report['cancelling']=False;save()
            if guard is not None:
                guard.terminate();guard.wait(timeout=5)
                report['display_guard']['released']=True;save()
        evidence=json.loads((output/'gui.json').read_text())
        if cpu_before is not None:
            report['relay_cpu_after']=relay_cpu_snapshot(backend)
            report['relay_cpu_cost']=relay_cpu_cost(cpu_before,report['relay_cpu_after']);save()
        periodic=[s for s in evidence['stages'] if s['stage']=='periodic']
        radio_rows=[s for s in periodic if s.get('radio_playing_seconds') is not None]
        fft_progress=any(a.get('spectral_last_end') is not None and
            b.get('spectral_last_end')!=a.get('spectral_last_end') for a,b in zip(radio_rows,radio_rows[1:]))
        fft_data_ok=bool(radio_rows) and fft_progress and any(radio_rows[-1].get('fft_finite_points',()))
        profile_ok=bool(radio_rows) and all(s.get('applied_configuration')==
            dict(bits=8,rate=1860465,channels=1) for s in radio_rows)
        reserves=[s['radio_a0_diagnostics'].get('buffer_minimum') for s in evidence['stages']
                  if s.get('radio_playing_seconds') is not None and s.get('radio_a0_diagnostics')]
        reserves=[value for value in reserves if value is not None]
        exposed=sum(bool(s['exposed']) for s in periodic)/max(1,len(periodic))
        visible=exposed>=.9 and evidence['paint_events']>=args.hold*8 and evidence.get('display',{}).get('platform')=='cocoa'
        if args.metrics:
            metrics=json.loads((output/'wire_metrics.json').read_text())
            if not metrics.get('radio_playing',{}).get('send_nodes'):
                raise RuntimeError('No native send observations during RADIO PLAYING')
            report['wire_metrics']=metrics;save()
        return dict(ok=child.returncode==0 and not evidence['errors'] and all(evidence['assertions'].values())
                        and visible and fft_data_ok and profile_ok,
            errors=evidence['errors'],assertions=evidence['assertions'],visible_gui_ok=visible,
            fft_data_ok=bool(fft_data_ok),radio_profile_ok=profile_ok,
            exposed_fraction=exposed,paint_events=evidence['paint_events'],
            radio_hold_seconds=evidence['radio_hold_seconds'],radio_played_samples=evidence['radio_played_samples'],
            audio_source_min_samples=min(reserves,default=None),
            pending_gui_peak=max((s['pending_gui_peak'] for s in evidence['stages']),default=0),
            pending_dsp_peak=max((s['pending_dsp_peak'] for s in evidence['stages']),default=0))
    previous={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def interrupted(*_):
        if report.get('restoring') or report.get('cancelling'):return
        raise KeyboardInterrupt('GUI campaign cancelled; restoring accepted pair')
    for s in previous:signal.signal(s,interrupted)
    try:ok=execute_gui(backend,acceptance,artifact,report,save,gui)
    finally:
        for s,handler in previous.items():signal.signal(s,handler)
    print(json.dumps(dict(ok=ok,error=report.get('error'),restored=report.get('restoration',{}).get('ok'),output=str(output))))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
