"""RF-only GUI check on installed V20; no deployment and no audio playback."""
import argparse,json,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.probe_working_v20_gui import identity,run_child,collect
from monitor.v20.q_support.prepare import atomic_report
from monitor.v20.q_support.working_pair import RECEIPT,digest


def command(serial,binding,seconds,legacy=False,channels='CH1'):
    # FFT-only suppresses the audio actions in the existing smoke harness;
    # analysis-mode vt selects the temporal plot and its own assertions.
    cmd=[sys.executable,str(ROOT/'tools/gui_private_v20.py'),
         '--firmware-binding',str(binding),'--serial',serial,
         '--output',str(binding.parent/'gui.json'),'--bits','14','--rate','40000',
         '--analysis-mode','vt','--fft-only','--fft-size','16384',
         '--time-channels',channels,'--window-seconds','.225','--detail-percent','50',
         '--duration',str(seconds+10),'--no-retune','--stall-trace']
    if legacy:cmd.append('--legacy-cadence')
    return cmd


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--hold',type=int,choices=(20,60),default=20)
    parser.add_argument('--legacy-cadence',action='store_true')
    parser.add_argument('--channels',choices=('CH1','CH1+CH2'),default='CH1')
    args=parser.parse_args();out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'diagnosticos/resultados_v20'):
        parser.error('New V20 diagnostic directory required')
    receipt=json.loads(RECEIPT.read_text());receipt_hash=digest(RECEIPT)
    before=identity(args.serial)
    if before!=receipt['identity']:raise RuntimeError('Installed working pair changed')
    activation=Path(receipt['activation_report']);activation_hash=digest(activation)
    out.mkdir(parents=True);binding=out/'report.json'
    report=dict(schema=1,version=20,private=True,promoted=False,ok=False,
        private_firmware_activated=True,private_identity=before,
        source_report=receipt['source_report'],source_report_sha256=receipt['source_report_sha256'],
        identity_before=before,scope='Installed V20 RF-only; no firmware/relay changes',
        requested_tests=dict(radio=False,fm=False,hold_seconds=args.hold,
            bits=14,rate=40000,window_samples=9000,detail=50,channels=args.channels,
            legacy_cadence=args.legacy_cadence))
    paths=[Path(__file__),ROOT/'tools/gui_private_v20.py',ROOT/'tools/gui_live_smoke_v20.py',
           ROOT/'monitor/v20/app.py',ROOT/'monitor/v20/temporal_paint.py']
    report['host_sources']={str(p.relative_to(ROOT)):digest(p) for p in paths}
    save=lambda:atomic_report(binding,report)
    cmd=command(args.serial,binding,args.hold,args.legacy_cadence,args.channels)
    report['gui_command']=cmd;save();finished=False
    try:
        finished=run_child(cmd,out,args.hold,report,save)
        if not finished:raise RuntimeError('GUI still restoring; do not take over Q')
        collect(out,report,before)
        report['traceback_in_log']='Traceback (most recent call last)' in (out/'gui.log').read_text()
        gui=json.loads((out/'gui.json').read_text())
        periodic=[s for s in gui.get('stages',[]) if s['stage']=='periodic' and s.get('samples',0)>0]
        rows=[]
        for a,b in zip(periodic,periodic[1:]):
            dt=b['elapsed']-a['elapsed']
            rows.append(dict(seconds=dt,elapsed=b['elapsed'],
                fresh_paints_per_second=(b['temporal_paints']['new_data']-a['temporal_paints']['new_data'])/dt,
                interval_ms=b.get('render_interval_ms'),pending_gui=b.get('pending_gui'),
                gui_delay_max_ms=b.get('gui_delay_max_ms'),
                cpu_seconds_per_second=(b['process_cpu_seconds']-a['process_cpu_seconds'])/dt))
        report['cadence_intervals']=rows
        report['observed_acquisition_seconds']=gui.get('analysis_effective_seconds',0)
        report['cadence_target_met']=bool(rows and statistics.median(
            row['fresh_paints_per_second'] for row in rows)>=25)
        report['diagnostics_complete']=bool(rows)
        report['rf_only_confirmed']=bool(periodic and all(s.get('radio_samples',0)==0
            and s.get('radio_a0') is False and not s.get('wav_active')
            and s.get('applied_configuration',{}).get('rate')==40000 for s in periodic))
    except BaseException as exc:
        report['error']=repr(exc)
    finally:
        report['receipt_unchanged']=digest(RECEIPT)==receipt_hash
        report['activation_report_unchanged']=digest(activation)==activation_hash
        report['sources_unchanged']=all(digest(p)==report['host_sources'][str(p.relative_to(ROOT))] for p in paths)
        if finished:
            report['identity_after']=identity(args.serial)
            report['identity_unchanged']=report['identity_after']==before
        report['ok']=bool(not report.get('error') and report.get('functional_ok')
            and not report.get('traceback_in_log',False)
            and report.get('rf_only_confirmed') and report.get('diagnostics_complete')
            and report.get('exposure',{}).get('exposure_sufficient')
            and report.get('observed_acquisition_seconds',0)>=args.hold
            and (args.legacy_cadence or report.get('cadence_target_met'))
            and report.get('v20_snapshot_restore',{}).get('ok') and report.get('identity_unchanged')
            and report['receipt_unchanged'] and report['activation_report_unchanged'] and report['sources_unchanged'])
        save()
    print(json.dumps(dict(ok=report['ok'],report=str(binding),error=report.get('error'))))
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
