#!/usr/bin/env python3
"""Audio screen on installed working V20; optional WAV/Synth, no deployment or V19 rollback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from monitor.v20.board_owner import board_owner
from monitor.v20.io.live_connection import installed_identity
from monitor.v20.q_support.prepare import atomic_report
from monitor.v20.q_support.working_pair import RECEIPT,digest


def command(serial,binding,hold,*,wav=False,fm=False,voices=1,synth_hold=5,synth_rate=20000,synth_profile='panel',radio_rate=1860465,radio_bits=8,stall_trace=False,trace_numpy_any=False,window_seconds=0,detail_percent=None,synth_early_play=False,scan=False,us=False,scan_during_a0=False,restart_a0=False):
    cmd=[sys.executable,str(ROOT/'tools/gui_private_v20.py'),'--firmware-binding',str(binding),
            '--serial',serial,'--output',str(binding.parent/'gui.json'),'--bits',str(radio_bits),'--rate',str(radio_rate),
            '--fft-size','16384','--no-retune','--frequency-khz',str(10 if radio_rate==40000 else 710 if radio_rate>=1500000 else 530),
            '--hold-radio-seconds',str(hold),'--duration',str(hold+5)]
    if stall_trace:cmd.append('--stall-trace')
    if trace_numpy_any:cmd.append('--trace-numpy-any')
    if window_seconds:cmd+=['--window-seconds',str(window_seconds),'--radio-time-view']
    if detail_percent is not None:cmd+=['--detail-percent',str(detail_percent)]
    if wav:cmd.append('--wav')
    if fm:cmd+=['--fm','--voices',str(voices),'--synth-hold',str(synth_hold),'--synth-rate',str(synth_rate),'--synth-profile',synth_profile]
    if synth_early_play:cmd.append('--synth-early-play')
    if (radio_bits,radio_rate)==(8,2000000):cmd.append('--allow-internal-2m')
    if radio_bits!=8:cmd.append('--allow-private-adc')
    for enabled,flag in ((scan,'--scan'),(us,'--us'),(scan_during_a0,'--scan-during-a0'),(restart_a0,'--restart-a0')):
        if enabled:cmd.append(flag)
    return cmd



def execution_budget(hold,*,fm=False,synth_hold=5):
    # Audio adds 120 s prepare, 10 s STOP, 10 s recovery and 60 s startup/WAV/shutdown.
    return hold+synth_hold+200 if fm else hold+180


def identity(serial):
    with board_owner(serial,'working V20 screen identity check'):
        return installed_identity(serial)


def run_child(cmd,output,hold,report,save):
    env=dict(os.environ,PYTHONFAULTHANDLER='1',MONITOR_V19_CHILD_STAGE_TIMING='1',
             ARDUSCOPIO_PRIVATE_RAW_ACK_LATENCY='1',ARDUSCOPIO_PRIVATE_RASTER_WORKERS='1',
             ARDUSCOPIO_PRIVATE_RASTER_NICE='0',ARDUSCOPIO_PRIVATE_RECOVERY_SECONDS='10')
    if report.get('requested_tests',{}).get('diagnostics_mode')=='native-only':
        env.update(MONITOR_V19_CHILD_STAGE_TIMING='0',ARDUSCOPIO_PRIVATE_RAW_ACK_LATENCY='0')
    with (output/'gui.log').open('w') as log:
        child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
        requested=report.get('requested_tests',{})
        budget=execution_budget(hold,fm=requested.get('fm',False),synth_hold=requested.get('synth_confirmed_hold_seconds') or 5)
        report.update(child_pid=child.pid,execution_budget_seconds=budget);save();deadline=time.monotonic()+budget
        try:
            while child.poll() is None:
                if time.monotonic()>=deadline:
                    report['timeout']=True;break
                try:child.wait(timeout=1)
                except subprocess.TimeoutExpired:pass
        except KeyboardInterrupt:
            report['cancelled']=True
        finally:
            if child.poll() is None:
                report['graceful_interrupt_sent']=True;save();child.send_signal(signal.SIGINT)
                try:child.wait(timeout=60)
                except subprocess.TimeoutExpired:report['child_still_running']=True
        report['child_returncode']=child.returncode
        save()
    return not report.get('child_still_running',False)


def wait_for_receiver_close(output,timeout=30):
    """After a GUI crash, let its still-owned receiver finish exact restoration."""
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        paths=list((output/'private_gui_sessions').glob('session_*.json'))
        if paths:
            try:
                sessions=[json.loads(path.read_text()) for path in paths]
            except (OSError,json.JSONDecodeError):
                sessions=[]
            if sessions and all(s.get('state')=='closed' and
                                s.get('receiver_activity',{}).get('released') is True
                                for s in sessions):return True
        time.sleep(.2)
    return False


def collect(output,report,before):
    gui_path=output/'gui.json'
    gui=json.loads(gui_path.read_text()) if gui_path.exists() else {}
    report['gui']=dict(errors=gui.get('errors',[]),assertions=gui.get('assertions',{}),
                       display=gui.get('display'),paint_events=gui.get('paint_events'),
                       radio_hold_seconds=gui.get('radio_hold_seconds'),scan=gui.get('scan'),
                       synth_transition=gui.get('synth_transition'),synth_remote_voice_peak=gui.get('synth_remote_voice_peak'))
    phase_names={'radio_a0_playing_confirmed','before_stop','wav_configure','wav_play_requested',
                 'wav_playing_confirmed','wav_before_stop','fm_configure','fm_play_requested',
                 'fm_playing_confirmed','fm_stop_confirmed','fm_before_stop','before_close'}
    report['audio_phases']=[{k:row.get(k) for k in ('stage','elapsed','applied_configuration',
        'requested_voices','wav_active','radio_a0','radio_status','samples','exposed',
        'synth_transition','synth_preparation','synth_source')}
        for row in gui.get('stages',[]) if row.get('stage') in phase_names]
    periodic=[row for row in gui.get('stages',[]) if row.get('stage')=='periodic']
    fraction=sum(bool(row.get('exposed')) for row in periodic)/len(periodic) if periodic else 0.
    report['exposure']=dict(periodic_samples=len(periodic),exposed_fraction=fraction,
        exposure_sufficient=fraction>=.9 and bool(periodic),
        note='Exposure only; no visible FPS or analog acceptance inferred.')
    metrics_path=output/'wire_metrics.json';stages_path=output/'reader_stages.json'
    metrics=json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
    stages=json.loads(stages_path.read_text()) if stages_path.exists() else {}
    report['metrics']=metrics
    report['service_diagnostics']=[t['wav_service'] for t in stages.get('trackers',[]) if 'wav_service' in t]
    sessions=[]
    for path in sorted((output/'private_gui_sessions').glob('session_*.json')):
        session=json.loads(path.read_text());recovery=session.get('recovery') or {}
        restored=(session.get('state')=='closed' and session.get('hardware_restored') is True
                  and not session.get('errors') and session.get('snapshot',{}).get('identity')==before
                  and recovery.get('continuous') is True and recovery.get('dropped')==0 and recovery.get('fatal')==0
                  and recovery.get('seconds',0)>=10)
        sessions.append(dict(path=str(path),ok=restored,detail=session))
    report['v20_snapshot_restore']=dict(ok=bool(sessions) and all(s['ok'] for s in sessions),sessions=sessions)
    raw=metrics.get('raw_chunk_ack_latency',{})
    report['diagnostics_complete']=bool(raw.get('enabled') and raw.get('matched',0)>0 and raw.get('decoded',0)>0
        and any(s.get('calls',0)>0 and s.get('sends',{}).get('chunk',0)>0 for s in report['service_diagnostics']))
    report['native_diagnostics_complete']=bool(metrics.get('all',{}).get('frames',0)>0
                                              and metrics.get('all',{}).get('samples',0)>0)
    report['diagnostics_requirement_met']=(report['native_diagnostics_complete']
        and raw.get('enabled') is False and not stages_path.exists()
        if report.get('requested_tests',{}).get('diagnostics_mode')=='native-only'
        else report['diagnostics_complete'])
    report['functional_ok']=bool(report.get('child_returncode')==0 and not report.get('timeout')
        and not report.get('cancelled') and gui and not gui.get('errors') and gui.get('assertions')
        and all(value is True for value in gui['assertions'].values()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--hold',type=int,choices=(20,60,80,120),default=60)
    parser.add_argument('--radio-rate',type=int,choices=(40000,1860465,2000000),default=1860465)
    parser.add_argument('--radio-bits',type=int,choices=(8,10,12),default=8)
    parser.add_argument('--private-rate',type=int,help='Source-bound ADC10/12 candidates only')
    parser.add_argument('--scan',action='store_true');parser.add_argument('--us',action='store_true')
    parser.add_argument('--scan-during-a0',action='store_true');parser.add_argument('--restart-a0',action='store_true')
    parser.add_argument('--prime-real-time',action='store_true',help='Private ADC8/2M priming cadence experiment')
    parser.add_argument('--minimal-diagnostics',action='store_true',help='Native metrics and strict decoder; no detailed host stage timers')
    parser.add_argument('--stall-trace',action='store_true')
    parser.add_argument('--trace-numpy-any',action='store_true',help='Private main-thread native-crash callsite journal')
    parser.add_argument('--window-seconds',type=float,default=0)
    parser.add_argument('--detail-percent',type=int,choices=range(1,101))
    parser.add_argument('--wav',action='store_true');parser.add_argument('--fm',action='store_true')
    parser.add_argument('--voices',type=int,choices=range(1,21),default=1)
    parser.add_argument('--synth-hold',type=int,choices=(5,30,60),default=5)
    parser.add_argument('--synth-rate',type=int,choices=(20000,40000),default=20000)
    parser.add_argument('--synth-profile',choices=('panel','sustained-fm'),default='panel')
    parser.add_argument('--synth-early-play',action='store_true')
    args=parser.parse_args();output=args.output.resolve()
    if args.radio_bits!=8:
        from tools.private_rate_profiles_v20 import PRIVATE_PROFILES
        if not any(b==args.radio_bits and 160000000//ticks==args.private_rate for b,ticks,_ in PRIVATE_PROFILES):
            parser.error('Explicit source-bound --private-rate required for ADC10/12')
        args.radio_rate=args.private_rate
    elif args.private_rate is not None:parser.error('--private-rate requires ADC10/12')
    if args.scan and args.scan_during_a0:parser.error('Choose scan before or during A0')
    if args.us and not (args.scan or args.scan_during_a0):parser.error('--us requires a scan')
    if args.prime_real_time and (args.radio_bits,args.radio_rate)!=(8,2000000):parser.error('Priming experiment requires ADC8/2M')
    if args.window_seconds<0 or (args.detail_percent is not None and not args.window_seconds):parser.error('Detail requires a positive time window')
    if args.window_seconds and (args.wav or args.fm):parser.error('Long-window screen must be separate from audio-source transitions')
    if not args.fm and (args.voices!=1 or args.synth_hold!=5 or args.synth_rate!=20000 or args.synth_profile!='panel'):
        parser.error('Nondefault --voices/--synth-hold/--synth-rate require --fm')
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v20'):
        parser.error('New output under diagnosticos/resultados_v20 required')
    receipt=json.loads(RECEIPT.read_text());receipt_hash=digest(RECEIPT)
    before=identity(args.serial)
    if before!=receipt['identity']:raise RuntimeError('Working V20 identity changed before screen')
    activation=Path(receipt['activation_report']);activation_hash=digest(activation)
    output.mkdir(parents=True);binding=output/'report.json'
    report=dict(schema=1,version=20,private=True,promoted=False,private_firmware_activated=True,
        private_identity=before,source_report=receipt['source_report'],source_report_sha256=receipt['source_report_sha256'],
        working_receipt=dict(path=str(RECEIPT),sha256=receipt_hash),identity_before=before,
        requested_tests=dict(radio=True,wav=args.wav,fm=args.fm,synth_early_play=args.synth_early_play,voices=args.voices if args.fm else None,synth_profile=args.synth_profile if args.fm else None,
            hold_seconds=args.hold,diagnostics_mode='native-only' if args.minimal_diagnostics else 'detailed',priming_realtime=args.prime_real_time,scan=args.scan,us=args.us,scan_during_a0=args.scan_during_a0,restart_a0=args.restart_a0,stall_trace=args.stall_trace,trace_numpy_any=args.trace_numpy_any,window_seconds=args.window_seconds,detail_percent=args.detail_percent,analysis_mode='vt_radio' if args.window_seconds else 'fft_radio',radio_adc_bits=args.radio_bits,radio_adc_rate=args.radio_rate,radio_a0_rate=40000,
            wav_source='synthetic 500 Hz temporary WAV' if args.wav else None,
            synth_prepare_timeout=120 if args.fm else None,synth_confirmed_hold_seconds=args.synth_hold if args.fm else None,
            synth_dac_rate=args.synth_rate if args.fm else None),
        scope='Installed working V20 audio screen; private, no public/analog acceptance',ok=False)
    if args.radio_bits!=8:report['private_profile']=dict(bits=args.radio_bits,rate=args.radio_rate)
    if args.prime_real_time:report['private_priming_realtime']=True
    paths=(Path(__file__).resolve(),ROOT/'tools/gui_private_v20.py',ROOT/'tools/private_v20_pair.py',ROOT/'tools/private_rate_profiles_v20.py',
           ROOT/'tools/gui_live_smoke_v20.py',ROOT/'tools/synth_transition_scenario_v20.py',
           ROOT/'monitor/v20/receiver/unoq_config_receiver.py',ROOT/'monitor/v20/io/receiver_process.py',
           ROOT/'monitor/v20/fm_source.py',ROOT/'monitor/v20/fm_panel.py',ROOT/'monitor/v20/synth_process.py',
           ROOT/'monitor/v20/app.py',ROOT/'monitor/v20/radio_multiscan.py',ROOT/'monitor/v20/temporal_raster.py',ROOT/'monitor/v20/scope_cursors.py')
    if args.prime_real_time:paths=(*paths,ROOT/'tools/private_radio_priming_v20.py')
    if args.trace_numpy_any:paths=(*paths,ROOT/'tools/private_numpy_any_trace_v20.py')
    report['host_sources']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    save=lambda:atomic_report(binding,report);save()
    cmd=command(args.serial,binding,args.hold,wav=args.wav,fm=args.fm,voices=args.voices,
        synth_hold=args.synth_hold,synth_rate=args.synth_rate,synth_profile=args.synth_profile,radio_rate=args.radio_rate,radio_bits=args.radio_bits,scan=args.scan,us=args.us,scan_during_a0=args.scan_during_a0,restart_a0=args.restart_a0,stall_trace=args.stall_trace,trace_numpy_any=args.trace_numpy_any,window_seconds=args.window_seconds,detail_percent=args.detail_percent,synth_early_play=args.synth_early_play);report['gui_command']=cmd;save()
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    def cancelled(*_):raise KeyboardInterrupt('Working V20 screen cancelled')
    for sig in previous:signal.signal(sig,cancelled)
    finished=False
    try:
        finished=run_child(cmd,output,args.hold,report,save)
        if not finished:raise RuntimeError('GUI still restoring after graceful interrupt; no administrative takeover')
        if report.get('child_returncode')!=0:
            report['receiver_close_after_gui_error']=wait_for_receiver_close(output)
            save()
        collect(output,report,before)
    except BaseException as exc:report['error']=repr(exc)
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
        report['receipt_unchanged']=digest(RECEIPT)==receipt_hash
        report['activation_report_unchanged']=digest(activation)==activation_hash
        if finished:
            try:
                report['identity_after']=identity(args.serial)
                report['identity_unchanged']=report['identity_after']==before
            except BaseException as exc:report['identity_after_error']=repr(exc)
        report['ok']=bool(report.get('functional_ok') and report.get('diagnostics_requirement_met')
            and report.get('v20_snapshot_restore',{}).get('ok') and report.get('identity_unchanged')
            and report['receipt_unchanged'] and report['activation_report_unchanged'] and not report.get('error'))
        save()
    print(json.dumps(dict(ok=report['ok'],report=str(binding),exposure=report.get('exposure'),error=report.get('error'))))
    return 0 if report['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
