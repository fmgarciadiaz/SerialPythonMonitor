#!/usr/bin/env python3
"""Private O2 GUI/RADIO screen with an exact selected relay and paired rollback."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.private_firmware_v19 import checked_pair
from tools.probe_prepare_firmware_v19 import activate
from tools.probe_relay_gui_v19 import execute_gui
from tools.summarize_spi_costs_v19 import summarize
from monitor.v19.q_support.backend import ProductionBackend
from monitor.v19.q_support.prepare import load_acceptance,atomic_report
from monitor.v19.q_support.service import RECEIPT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--build-report',required=True,type=Path)
    parser.add_argument('--relay-report',type=Path,help='Exact verified private relay, accepted relay otherwise')
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--hold',type=float,default=60)
    parser.add_argument('--bits',type=int,choices=(8,10),default=8)
    parser.add_argument('--rate',type=int,default=1860465)
    parser.add_argument('--view',choices=('fft','vt'),default='fft')
    parser.add_argument('--scan',action='store_true');parser.add_argument('--us',action='store_true')
    parser.add_argument('--no-retune',action='store_true')
    parser.add_argument('--window-seconds',type=float,default=0)
    parser.add_argument('--detail-percent',type=int,default=50,choices=range(1,101))
    parser.add_argument('--inline-burst',type=int,choices=(1,4,8),default=None,
                        help='Private descriptor burst with current inline ACK; legacy replay otherwise')
    parser.add_argument('--inline-interval-ms',type=int,choices=(6,8,10))
    parser.add_argument('--startup-only',action='store_true')
    parser.add_argument('--query-interval-ms',type=int,choices=(12,24,30,40))
    parser.add_argument('--ipc-empty-backoff-us',type=int,choices=(0,500),default=0)
    parser.add_argument('--play-burst',type=int,choices=(1,2))
    args=parser.parse_args()
    if args.play_burst is not None and (not args.startup_only or args.inline_burst is None):
        parser.error('Private PLAY arm requires explicit prefill/startup selection')
    if (args.inline_interval_ms is not None or args.startup_only or args.query_interval_ms is not None) and args.inline_burst is None:
        parser.error('Explicit inline-burst required for cadence/startup arms')
    if args.ipc_empty_backoff_us and args.inline_burst is None:
        parser.error('IPC combination requires explicit production inline ACK arm')
    if args.inline_burst==1 and not args.startup_only:
        parser.error('Burst1 is prefill-only; explicit startup-only required')
    if (args.bits,args.rate) not in ((8,1860465),(10,1355932)):
        parser.error('Private GUI supports only the two reviewed target profiles')
    output=args.output.resolve()
    if not 0<args.hold<=120:parser.error('hold must be in (0,120]')
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('New private diagnostic output required')
    candidate=checked_pair(args.build_report,args.relay_report);acceptance=load_acceptance(RECEIPT)
    output.mkdir(parents=True);binding=output/'report.json'
    report=dict(private=True,promoted=False,source_build_report=candidate['build_report'],
                host_candidate='ACK-refresh fixed; chunk_burst=8',firmware_candidate=candidate)
    if candidate.get('diagnostic_schema'):
        report.update(diagnostic_schema=candidate['diagnostic_schema'],performance_acceptance_eligible=False,
                      relay_prepare_check_aggregates_valid=False,
                      scope='WAV critical-section profiling; instrumented timing, not performance acceptance')
    from tools.ipc_empty_backoff_v19 import ENV as IPC_ENV
    os.environ.pop(IPC_ENV,None)
    if args.ipc_empty_backoff_us:
        os.environ[IPC_ENV]=str(args.ipc_empty_backoff_us)
        report['private_ipc_empty_backoff_us']=args.ipc_empty_backoff_us
    if args.relay_report is not None:report['private_relay_build_report']=candidate['relay_build_report']
    from tools.radio_burst_inline_v19 import ENV as BURST_ENV, INTERVAL_ENV, STARTUP_ENV,POLL_ENV,PLAY_ENV
    os.environ.pop(PLAY_ENV,None)
    if args.play_burst is not None:
        os.environ[PLAY_ENV]=str(args.play_burst)
        report['private_play_burst']=args.play_burst
    os.environ.pop(INTERVAL_ENV,None)
    os.environ.pop(STARTUP_ENV,None)
    os.environ.pop(POLL_ENV,None)
    # Select explicitly; never inherit an accidental arm from another campaign.
    if args.inline_burst is None:
        os.environ.pop(BURST_ENV,None)
    else:
        os.environ[BURST_ENV]=str(args.inline_burst)
        report['host_candidate']=f'production inline ACK; descriptor chunk_burst={args.inline_burst}'
        if args.inline_interval_ms is not None:
            os.environ[INTERVAL_ENV]=str(args.inline_interval_ms)
            report['host_candidate']+=f'; interval={args.inline_interval_ms}ms'
        if args.startup_only:
            os.environ[STARTUP_ENV]='1'
            report['host_candidate']+=('; startup only, PLAY restores burst8/6ms' if args.play_burst is None
                                       else '; startup cadence with explicit private PLAY override')
        if args.query_interval_ms is not None:
            os.environ[POLL_ENV]=str(args.query_interval_ms)
            report['host_candidate']+=f'; query={args.query_interval_ms}ms'
    if args.ipc_empty_backoff_us:
        report['host_candidate']+=f'; empty IPC backoff={args.ipc_empty_backoff_us}us'
    if args.play_burst is not None:report['host_candidate']+=f'; private PLAY burst={args.play_burst}/6ms'
    save=lambda:atomic_report(binding,report);save()
    backend=ProductionBackend(acceptance);backend._board().serial=args.serial
    def gui():
        command=[sys.executable,str(ROOT/'tools/gui_firmware_candidate_v19.py'),'--firmware-binding',str(binding),
            '--serial',args.serial,'--output',str(output/'gui.json'),'--bits',str(args.bits),'--rate',str(args.rate),
            '--duration',str(args.hold+5),'--hold-radio-seconds',str(args.hold),
            '--frequency-khz','710']
        if args.view=='fft':command+=['--fft-size','16384']
        if args.scan:command+=['--scan']
        if args.us:command+=['--us']
        if args.no_retune:command+=['--no-retune']
        if args.window_seconds:command+=['--window-seconds',str(args.window_seconds)]
        if args.detail_percent!=50:command+=['--detail-percent',str(args.detail_percent)]
        report['gui_command']=command;save();child=guard=None
        try:
            if sys.platform=='darwin':
                guard=subprocess.Popen(['/usr/bin/caffeinate','-du','-t',str(int(args.hold+180))])
            with (output/'gui.log').open('w') as log:
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
                report['gui_pid']=child.pid;save()
                child.wait(timeout=args.hold+150)
        finally:
            if child is not None and child.poll() is None:
                report['cancelling']=True;child.send_signal(signal.SIGINT)
                try:child.wait(timeout=90)
                except subprocess.TimeoutExpired:report['gui_owner_still_active']=True
                report['cancelling']=False;save()
            if guard is not None:guard.terminate();guard.wait(timeout=5)
        evidence=json.loads((output/'gui.json').read_text())
        rows=[s for s in evidence['stages'] if s['stage']=='periodic']
        radio=[s for s in rows if s.get('radio_playing_seconds') is not None]
        exposed=sum(bool(s.get('exposed')) for s in rows)/max(1,len(rows))
        visible=evidence.get('display',{}).get('platform')=='cocoa' and exposed>=.9 and evidence['paint_events']>=(args.hold*8 if args.view=='fft' else 1)
        profile=bool(radio) and all(s.get('applied_configuration')==dict(bits=args.bits,rate=args.rate,channels=1) for s in radio)
        fft=bool(radio) and any(radio[-1].get('fft_finite_points',())) and any(
            a.get('spectral_last_end') is not None and a.get('spectral_last_end')!=b.get('spectral_last_end') for a,b in zip(radio,radio[1:]))
        if args.view=='vt':
            fft=bool(radio) and any(b.get('raster_published',0)>a.get('raster_published',0)
                                   for a,b in zip(radio,radio[1:]))
        metrics=json.loads((output/'wire_metrics.json').read_text())
        if not metrics['radio_playing']['send_nodes']:raise RuntimeError('No RADIO native send metrics')
        costs=(dict(valid=False,reason='Private WAV cycle schema replaces prepare/check; relay timing aggregates invalid')
               if candidate.get('diagnostic_schema') else summarize(metrics))
        atomic_report(output/'cost_summary.json',costs)
        report['wire_metrics']=metrics;save()
        return dict(ok=child.returncode==0 and not evidence['errors'] and all(evidence['assertions'].values())
                        and visible and profile and fft,
            errors=evidence['errors'],assertions=evidence['assertions'],visible_gui_ok=visible,
            profile_ok=profile,fft_ok=bool(fft),exposed_fraction=exposed,paint_events=evidence['paint_events'],
            radio_hold_seconds=evidence['radio_hold_seconds'],radio_played_samples=evidence['radio_played_samples'],
            headroom_pass=metrics['radio_playing']['headroom_pass'] and not candidate.get('diagnostic_schema'),
            performance_acceptance_eligible=not bool(candidate.get('diagnostic_schema')))
    previous={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def interrupted(*_):
        if report.get('restoring') or report.get('cancelling'):return
        raise KeyboardInterrupt('Private GUI cancelled; restoring accepted pair')
    for sig in previous:signal.signal(sig,interrupted)
    try:ok=execute_gui(backend,acceptance,candidate,report,save,gui,activate_pair=activate)
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
    report['candidate_active_at_end']=not report.get('restoration',{}).get('ok',False);save()
    print(json.dumps(dict(ok=ok,error=report.get('error'),restored=report.get('restoration',{}).get('ok'))))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
