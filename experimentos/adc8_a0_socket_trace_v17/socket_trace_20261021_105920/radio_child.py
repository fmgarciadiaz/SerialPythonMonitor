"""Owned RADIO/FFT/A0 qualification child; exact helper evidence survives errors."""
import argparse
from contextlib import nullcontext, ExitStack
import json
import os
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]


def trial_arguments(seconds):
    if seconds not in (60,120):raise ValueError('Qualification duration must be 60 or 120 seconds')
    return ['adc8_accept_radio','--bits','8','--rate','1632653','--seconds',str(seconds),
        '--audio-rate','40000','--bandwidth','8000','--analysis-audit','--keep-visible','--refill-ring','--defer-diagnostics','--host-cpu-trace']


def outcome(report):
    paint=report.get('paint_audit',{})
    transport=report.get('audio_transport',{})
    ordinary=report.get('audio_source_type')=='RadioDacSource' and transport.get('chunk_burst')==8
    audio=bool(report.get('ok') and report.get('restored') and ordinary and not report.get('errors'))
    visual=paint.get('exposed_fraction',0)>=.9 and paint.get('fft_fps',0)>=5
    stats=report.get('joint_send_statistics',{})
    headroom=audio and stats.get('mean_margin',0)>=.1 and report.get('adc_queue_peak',99)<4 and stats.get('minimum_slack_ticks',0)>0
    return dict(ok=audio and visual,audio_integrity_ok=audio,visual_ok=visual,headroom_ok=headroom,
        restored=bool(report.get('restored')),ordinary_source_policy_ok=ordinary)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=int,choices=(60,120),required=True)
    parser.add_argument('--result',type=Path,required=True)
    parser.add_argument('--switch-interval-ms',type=float,choices=(1.,5.))
    parser.add_argument('--fast-read',action='store_true')
    args=parser.parse_args(argv)
    if int(os.environ.get('SPM_ADC8_ACCEPT_OWNER_PID','0'))!=os.getppid():
        raise RuntimeError('Child requires its live board owner parent')
    from monitor.v17.receiver import unoq_native
    from experimentos.fs_max_all_bits_v17.adc8_ab import private_profiles,EXP
    profiles=private_profiles(unoq_native.PROFILES,json.loads((EXP/'candidate_profiles.json').read_text()))
    remaining=tuple(p for p in unoq_native.PROFILES if not(p['bits']==8 and p['channels']==1 and p['ticks'] in (98,100)))
    from monitor.v17.receiver.unoq_usb import Connection
    from experimentos.adc8_a0_socket_trace_v17.socket_trace import SocketTrace
    socket_trace=SocketTrace()
    original_read=Connection.read
    original_close=Connection.close
    from experimentos.adc8_a0_socket_trace_v17.ready_read import ReadyRead
    ready_read=ReadyRead()
    from experimentos.adc8_a0_socket_trace_v17.gui_trace import GuiTrace
    gui_trace=GuiTrace()
    import gc
    from experimentos.adc8_a0_socket_trace_v17.gc_trace import GcTrace
    gc_trace=GcTrace(lambda:bool(getattr(gui_trace.window,'_wav_active',False)))
    selected_read=(lambda connection:ready_read.read(connection,original_read)) if args.fast_read else original_read
    prior_switch=sys.getswitchinterval()
    result=dict(ok=False,audio_integrity_ok=False,visual_ok=False,headroom_ok=False,restored=False,
        original_switch_interval_seconds=prior_switch,requested_switch_interval_ms=args.switch_interval_ms)
    reports=ROOT/'diagnosticos/resultados_v17'
    before=set(reports.glob('generador_radio_*/report.json'))
    try:
        if args.switch_interval_ms is not None:sys.setswitchinterval(args.switch_interval_ms/1000)
        result['effective_switch_interval_seconds']=sys.getswitchinterval()
        with patch.object(unoq_native,'PROFILES',profiles+remaining):
            from experimentos.fs_max_all_bits_v17.joint import private_profile_access
            from diagnosticos.validar_generador_radio_v17 import main as audio_trial
            sys.argv=trial_arguments(args.seconds)
            from monitor.v17.app import SerialMonitorWindow
            original_render=SerialMonitorWindow._render_with_diagnostics
            original_batch=SerialMonitorWindow._deliver_worker_batch
            from monitor.v17.spectrum import SpectralDisplay
            gc.callbacks.append(gc_trace.callback)
            with private_profile_access(8,1632653), ExitStack() as stack:
                stack.enter_context(patch.object(Connection,'read',lambda connection:socket_trace.read(connection,selected_read)))
                stack.enter_context(patch.object(Connection,'close',lambda connection:ready_read.close_connection(connection,original_close)))
                stack.enter_context(patch.object(SerialMonitorWindow,'_render_with_diagnostics',lambda window:gui_trace.call('render',original_render,window)))
                stack.enter_context(patch.object(SerialMonitorWindow,'_deliver_worker_batch',lambda window,*a,**kw:gui_trace.call('batch',original_batch,window,*a,**kw)))
                for method in ('_render_fft_analysis','_draw_fft_arrays','_draw_spectral_annotations','refresh_measurement_panel'):
                    original=getattr(SpectralDisplay,method)
                    def traced(display,*a,_name=method,_function=original,**kw):
                        return gui_trace.call(_name,_function,display,*a,**kw)
                    stack.enter_context(patch.object(SpectralDisplay,method,traced))
                original_measurements=SerialMonitorWindow._update_live_measurements
                stack.enter_context(patch.object(SerialMonitorWindow,'_update_live_measurements',lambda window,*a,**kw:gui_trace.call('measurements',original_measurements,window,*a,**kw)))
                report,folder=audio_trial(owner_context=nullcontext())
            result.update(outcome(report),report=str(folder/'report.json'),host_profiles=list(profiles))
    except BaseException as exc:
        new=list(set(reports.glob('generador_radio_*/report.json'))-before)
        path=max(new,key=lambda p:p.stat().st_mtime) if new else None
        if path is not None:
            report=json.loads(path.read_text());result.update(outcome(report),report=str(path))
        result.update(ok=False,audio_integrity_ok=False,error=repr(exc),traceback=traceback.format_exc())
    finally:
        result['socket_trace']=socket_trace.snapshot()
        result['gui_trace']=gui_trace.snapshot()
        if gc_trace.callback in gc.callbacks:gc.callbacks.remove(gc_trace.callback)
        result['gc_trace']=gc_trace.snapshot()
        result['ready_read']=dict(enabled=args.fast_read,immediate=ready_read.immediate,fallback=ready_read.fallback)
        ready_read.close()
        sys.setswitchinterval(prior_switch)
        result['switch_interval_restored']=sys.getswitchinterval()==prior_switch
        args.result.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    report=main()
    raise SystemExit(0 if report['audio_integrity_ok'] and report['restored'] else 1)
