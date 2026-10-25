"""Owned child: real RADIO + FFT for one ADC8 target; A0 stays off."""
import argparse
from collections import deque
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


class UniqueNodeStatistics:
    """Unique observed (epoch, produced) statuses; not a census of every node."""
    def __init__(self,rate):
        self.rate=rate;self.seen=set();self.count=0;self.sum_ticks=0
        self.send_max=0;self.queue_peak=0;self.copy_max=0;self.slack_min=None

    def observe(self,status):
        if status.get('rate')!=self.rate or status.get('bits',8)!=8 or 'send_ticks' not in status:return
        self.send_max=max(self.send_max,status['send_ticks'])
        self.queue_peak=max(self.queue_peak,status['queue_peak'])
        self.copy_max=max(self.copy_max,status['copy_ticks'])
        self.slack_min=status['slack_ticks'] if self.slack_min is None else min(self.slack_min,status['slack_ticks'])
        token=(status['epoch'],status['produced'])
        if token in self.seen:return
        if len(self.seen)>=65536:raise RuntimeError('Unique status diagnostic bound exceeded')
        self.seen.add(token);self.count+=1;self.sum_ticks+=status['send_ticks']

    def snapshot(self,period,node_pairs):
        return dict(unique_observations=self.count,sum_send_ticks=self.sum_ticks,
            mean_send_margin=1-self.sum_ticks/self.count/(period*node_pairs) if self.count else None,
            maximum_send_ticks=self.send_max,queue_peak=self.queue_peak,maximum_copy_ticks=self.copy_max,
            minimum_slack_ticks=self.slack_min,
            sampling='Deduplicated observed (epoch, produced); unobserved nodes are not reconstructed')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rate',type=int,required=True,choices=(1600000,1632653))
    parser.add_argument('--result',type=Path,required=True)
    parser.add_argument('--serial',default='1060031107')
    args=parser.parse_args(argv)
    if int(os.environ.get('SPM_ADC8_AB_OWNER_PID','0'))!=os.getppid():
        raise RuntimeError('Child requires its live campaign owner parent')
    from contextlib import ExitStack
    from monitor.v17.receiver import unoq_native
    from experimentos.fs_max_all_bits_v17.adc8_ab import EXP,private_profiles
    profiles=private_profiles(unoq_native.PROFILES,json.loads((EXP/'candidate_profiles.json').read_text()))
    remaining=tuple(p for p in unoq_native.PROFILES if not(p['bits']==8 and p['channels']==1 and p['ticks'] in (98,100)))
    with patch.object(unoq_native,'PROFILES',profiles+remaining):
        from monitor.v17.qt_environment import prepare_platform_plugins
        prepare_platform_plugins()
        from PyQt6 import QtCore,QtWidgets
        from monitor.v17.app import SerialMonitorWindow,OutputWorker
        from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
        from monitor.v17.receiver.unoq_acquisition import Configuration
        from monitor.v17.receiver.unoq_switch import Mode
        from monitor.v17.startup_trace import StartupTrace
        from diagnosticos.medir_arranque_v17 import live_only_scope,snapshot_idle_and_lower,restore,BASE
        from experimentos.fs_max_all_bits_v17.joint import private_profile_access
        target=Configuration(8,args.rate)
        report=dict(ok=False,restored=False,errors=[],rate=args.rate,adc=asdict(target),
            host_profiles=list(profiles),a0_enabled=False,radio_frequency_hz=20000,radio_bandwidth_hz=8000,
            requested_seconds=60,first_gui_delivery=None,samples=0,batches=0,audio_samples=0,
            scope='RADIO + FFT65536 CH1/RADIO; first GUI delivery is not a paint claim',
            paint_note='FFT paint events and exposure do not count distinct newly acquired frames')
        stats=UniqueNodeStatistics(args.rate);receivers=[];transport=deque(maxlen=3000);maxima={}
        class MeasuredReceiver(OutputReceiver):
            def __init__(self,*a,**kw):super().__init__(*a,**kw);receivers.append(self)
            def pump(self):
                result=super().pump()
                for status in self.decoder.statuses:stats.observe(status)
                return result
            def _trace_transport(self,stage,start,end,rid=None,cpu_seconds=None,process_cpu_seconds=None):
                if self.config.rate==args.rate and stage in ('read','decode'):
                    maxima[stage]=max(maxima.get(stage,0.),end-start)
                    transport.append((stage,start,end))
                return super()._trace_transport(stage,start,end,rid,cpu_seconds,process_cpu_seconds)
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        report['qt_platform']=app.platformName()
        worker=thread=window=None;old_hook=sys.excepthook
        paint={'fft_paints':0,'exposure_checks':0,'exposed_checks':0};painting=[False]
        def error(text):report['errors'].append(str(text))
        def exception(kind,value,tb):error(''.join(traceback.format_exception(kind,value,tb)))
        def pump_gui():
            app.processEvents()
            if report['errors']:raise RuntimeError('Worker/GUI error')
            if thread is not None and not thread.isRunning():raise RuntimeError('Worker ended early')
            time.sleep(.001)
        try:
            snapshot_idle_and_lower(args.serial,report)
            with ExitStack() as stack:
                stack.enter_context(private_profile_access(8,args.rate))
                stack.enter_context(patch('monitor.v17.app.connect_scope',live_only_scope))
                stack.enter_context(patch('monitor.v17.app.OutputReceiver',MeasuredReceiver))
                with patch('monitor.v17.app.usb_devices',return_value=[]):window=SerialMonitorWindow()
                window._auto_apply_timer.stop();window._auto_apply_timer.timeout.disconnect()
                window.filter_source.setCurrentText('OFF');window.radio_enabled.setChecked(True)
                window.radio_frequency.setValue(20)
                window.radio_bandwidth.setCurrentIndex(window.radio_bandwidth.findData(8000))
                window.spectral.set_mode(1);window.spectral.size.setCurrentText('65536')
                window.spectral.channels[0].setCurrentText('CH1');window.spectral.channels[1].setCurrentText('RADIO')
                class PaintObserver(QtCore.QObject):
                    def eventFilter(self,obj,event):
                        if painting[0] and event.type()==QtCore.QEvent.Type.Paint:paint['fft_paints']+=1
                        return False
                observer=PaintObserver(window)
                window.spectral.widget.viewport().installEventFilter(observer)
                worker=OutputWorker(args.serial,Mode.SPI,config=BASE,autoload=True,
                    processing_settings=window._processing_settings(),startup_gui_ack=True,processing_backend='process')
                worker.trace=StartupTrace(enabled=True)
                worker._ensure_process().result(timeout=45)
                report['dsp_prewarmed_at_base']=True
                window.serial_worker=worker;window.is_running=True
                window.show();window.raise_();window.activateWindow()
                worker.acquisition_confirmed.connect(window._acquisition_confirmed)
                worker.trace_configuration_ready.connect(lambda event:window._trace_configuration_installed(worker,event))
                worker.status_changed.connect(window._set_connection_status)
                worker.error_occurred.connect(error)
                base_delivery=[False]
                def collect(batch):
                    window._deliver_worker_batch(worker,batch)
                    if batch.acquisition==BASE:base_delivery[0]=True
                    if batch.acquisition!=target:return
                    now=time.monotonic()
                    if report['first_gui_delivery'] is None:report['first_gui_delivery']=now;painting[0]=True
                    report['samples']+=len(batch);report['batches']+=1
                    audio=(getattr(batch,'processing',None) or {}).get('audio')
                    if audio is not None:report['audio_samples']+=len(audio)
                worker.batch_ready.connect(collect)
                thread=QtCore.QThread();worker.moveToThread(thread)
                thread.started.connect(worker.run);worker.finished.connect(thread.quit)
                sys.excepthook=exception
                thread.start();deadline=time.monotonic()+45
                while not base_delivery[0] and time.monotonic()<deadline:pump_gui()
                if not base_delivery[0]:raise TimeoutError('No base GUI delivery')
                report['target_requested_monotonic']=time.monotonic()
                worker.request_output(Mode.SPI,None,target)
                deadline=time.monotonic()+105;last_exposure=0.
                while time.monotonic()<deadline:
                    pump_gui();now=time.monotonic();first=report['first_gui_delivery']
                    if first is None:continue
                    if now-last_exposure>=.1:
                        paint['exposure_checks']+=1;paint['exposed_checks']+=int(window.windowHandle().isExposed());last_exposure=now
                    if now-first>=60:break
                else:raise TimeoutError('Target did not complete 60 seconds')
                painting[0]=False;report['seconds']=time.monotonic()-report['first_gui_delivery']
                report['requested_to_first_gui_seconds']=report['first_gui_delivery']-report['target_requested_monotonic']
                paint['fft_fps']=paint['fft_paints']/report['seconds']
                paint['exposed_fraction']=paint['exposed_checks']/max(1,paint['exposure_checks'])
                report['ok']=report['audio_samples']>0 and paint['fft_fps']>=5 and paint['exposed_fraction']>=.9
        except BaseException as exc:
            error(repr(exc));report['traceback']=traceback.format_exc()
        finally:
            painting[0]=False
            if worker is not None:worker.stop()
            if thread is not None:
                deadline=time.monotonic()+15
                while thread.isRunning() and time.monotonic()<deadline:app.processEvents();time.sleep(.001)
            exited=thread is None or not thread.isRunning();report['worker_exited']=exited
            if worker is not None:
                report.update(startup_trace=worker.trace.snapshot(),pending_gui_peak=worker.pending_batches_peak,
                    pending_dsp_peak=worker.pending_dsp_peak,delivery_failure=getattr(worker,'delivery_failure_snapshot',None))
            report.update(metrics=stats.snapshot(target.period,target.node_pairs),transport_recent=list(transport),
                transport_max_seconds=maxima,paint=paint)
            if exited:
                if window is not None:window.serial_worker=None;window.close()
                if 'prior' in report:
                    try:restore(args.serial,report)
                    except BaseException as exc:error('Return to base failed: '+repr(exc));report['restore_traceback']=traceback.format_exc()
            else:
                error('Worker did not exit; no competing reader opened')
                globals()['_unfinished_worker']=(thread,worker,window)
            sys.excepthook=old_hook
            report['ok']=report['ok'] and report['restored'] and not report['errors']
            args.result.write_text(json.dumps(report,indent=2)+'\n')
        return report


if __name__=='__main__':
    report=main()
    raise SystemExit(0 if report['ok'] else 1)
