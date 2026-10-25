"""Measure live Qt acquisition transitions; no firmware, restart or DAC playback.

Run explicitly, e.g. QT_QPA_PLATFORM=cocoa python diagnosticos/medir_arranque_v17.py.
Connection uses the already running stack. A dead stream is reported, never restarted.
"""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from monitor.v17.qt_environment import prepare_platform_plugins
prepare_platform_plugins()
from PyQt6 import QtCore, QtWidgets
from monitor.v17.app import OutputWorker, SerialMonitorWindow
from monitor.v17.board_owner import board_owner
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_wav import State
from monitor.v17.startup_trace import StartupTrace
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor

BASE=Configuration(14,40000)
STAGES=[('connect_live_base',BASE),('control_1403508',Configuration(8,1403508)),
        ('base_after_control',BASE),('target_1600000',Configuration(8,1600000)),
        ('base_after_target',BASE)]

def candidate_configure(seconds):
    """The qualified live wait is integrated; stale campaign overrides must stop."""
    raise ValueError('Private preparation override disabled: production now uses 0.5s live / 2s initial; omit --candidate-settle')


@contextmanager
def live_only_scope(serial, progress=lambda text:None, running=lambda:True):
    """Outer campaign owns Q; never call ensure_scope or retry a dead stack."""
    if not running():raise InterruptedError('Connection cancelled')
    progress('Conectando stack activo, sin reinicio…')
    with Connection(serial) as connection:
        connection.scope_restarted=False
        connection.wav_firmware=True
        yield connection


def receiver_for(connection):
    receiver=OutputReceiver(connection,lambda rows:None)
    receiver.decoder.numeric=True
    receiver.select(Mode.SPI)
    return receiver


def snapshot_idle_and_lower(serial, report):
    with Connection(serial) as connection:
        receiver=receiver_for(connection)
        receiver.wav_request()
        deadline=time.monotonic()+3
        while receiver.wav_pending and time.monotonic()<deadline:receiver.pump()
        if receiver.wav_pending or receiver.wav_status is None or receiver.wav_status.state!=State.IDLE:
            raise RuntimeError('WAV ocupado o sin confirmación IDLE; ensayo cancelado')
        generator=receiver.generator().active
        if generator.enabled:raise RuntimeError('Generador ocupado; ensayo cancelado')
        report['prior']={'adc':asdict(receiver.config),'generator':asdict(generator)}
        receiver.configure(BASE)
    # Administrative identity reads only after lowering ADC and closing the reader.
    report['identity_before']=instrument_identity(serial)
    if report['identity_before'] is None:raise RuntimeError('Identidad V17 desconocida')


def restore(serial, report):
    prior=report['prior']
    with Connection(serial) as connection:
        receiver=receiver_for(connection)
        receiver.configure(BASE)
    report['identity_after']=instrument_identity(serial)
    with Connection(serial) as connection:
        receiver=receiver_for(connection)
        receiver.configure(Configuration(**prior['adc']))
        receiver.generator(GeneratorConfig(**prior['generator']))
        final={'adc':asdict(receiver.config),'generator':asdict(receiver.generator().active)}
        before=receiver.decoder.pairs;began=time.monotonic()
        while time.monotonic()-began<10:receiver.pump()
        status=dict(receiver.decoder.status or {})
        recovery={'seconds':time.monotonic()-began,'samples':receiver.decoder.pairs-before,'status':status}
        recovery['ok']=recovery['samples']>0 and not status.get('dropped',0) and not status.get('fatal',0)
        report.update(final_settings=final,recovery=recovery)
    report['restored']=(final==prior and recovery['ok'] and
        report['identity_after']==report.get('identity_before') and report['identity_after'] is not None)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',default='1060031107')
    parser.add_argument('--candidate-settle',type=float,choices=(.5,),help='Private preparation duration; no production edit')
    parser.add_argument('--target-seconds',type=int,choices=(10,60,120),default=10)
    parser.add_argument('--radio',action='store_true',help='Real RADIO DSP active, A0 remains off')
    args=parser.parse_args(argv)
    folder=ROOT/'diagnosticos/resultados_v17'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/('arranque_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
    report={'ok':False,'restored':False,'serial':args.serial,'errors':[],'stages':[],
        'autoload_hook':'live_only','scope_restarted':False,'cold_not_measured':True,
        'measurement':'GUI batch delivery; no paint or visible FPS claim',
        'stage_seconds_after_first_delivery':10,'stage_timeout_seconds':45,
        'filter':'OFF','radio_enabled':args.radio}
    report.update(candidate_settle_seconds=args.candidate_settle,target_seconds=args.target_seconds)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    report['qt_platform']=app.platformName()
    window=worker=thread=None;receivers=[];active=[None]
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    def error(text):report['errors'].append(str(text))
    def gui_exception(kind,value,tb):
        error(''.join(traceback.format_exception(kind,value,tb)))
    class MeasuredReceiver(OutputReceiver):
        def __init__(self,*a,**kw):super().__init__(*a,**kw);receivers.append(self)
    if args.candidate_settle is not None:
        MeasuredReceiver.configure,report['original_configure_sha256']=candidate_configure(args.candidate_settle)
        report['trace_note']='settle_2s event names identify the existing phase; candidate duration is recorded separately'
    old_hook=sys.excepthook
    try:
        with board_owner(args.serial,'medir arranque V17 sin reinicio'):
            require_exclusive_monitor()
            try:
                snapshot_idle_and_lower(args.serial,report)
                with patch('monitor.v17.app.usb_devices',return_value=[]):window=SerialMonitorWindow()
                window.filter_source.setCurrentText('OFF')
                window.radio_enabled.setChecked(args.radio)
                if args.radio:
                    window.radio_frequency.setValue(20)
                window._auto_apply_timer.stop()
                window._auto_apply_timer.timeout.disconnect()
                worker=OutputWorker(args.serial,Mode.SPI,config=BASE,autoload=True,
                    processing_settings=window._processing_settings(),startup_gui_ack=True,
                    processing_backend='process')
                worker.trace=StartupTrace(enabled=True)
                window.serial_worker=worker;window.is_running=True
                window.show()
                worker.acquisition_confirmed.connect(window._acquisition_confirmed)
                worker.trace_configuration_ready.connect(lambda event:window._trace_configuration_installed(worker,event))
                worker.status_changed.connect(window._set_connection_status)
                worker.error_occurred.connect(error)
                worker.shutdown_confirmed.connect(lambda ok,text:report.update(shutdown={'ok':ok,'message':text}))
                def collect(batch):
                    window._deliver_worker_batch(worker,batch)
                    row=active[0]
                    if (row is not None and getattr(batch,'startup_trace_generation',None)==row['generation']
                            and asdict(batch.acquisition)==row['adc']):
                        now=time.monotonic()
                        if row['first_delivery_monotonic'] is None:row['first_delivery_monotonic']=now
                        row['last_delivery_monotonic']=now
                        row['samples']+=len(batch);row['batches']+=1
                worker.batch_ready.connect(collect)
                thread=QtCore.QThread();worker.moveToThread(thread)
                thread.started.connect(worker.run);worker.finished.connect(thread.quit)
                sys.excepthook=gui_exception
                # Keep the real worker/receiver paths; replace only automatic recovery.
                with patch('monitor.v17.app.connect_scope',live_only_scope),patch('monitor.v17.app.OutputReceiver',MeasuredReceiver):
                    for generation,(name,config) in enumerate(STAGES,1):
                        began=time.monotonic()
                        row={'name':name,'generation':generation,'adc':asdict(config),
                            'requested_monotonic':began,'first_delivery_monotonic':None,
                            'samples':0,'batches':0,'ok':False}
                        report['stages'].append(row);active[0]=row
                        if generation==1:thread.start()
                        else:worker.request_output(Mode.SPI,None,config)
                        duration=args.target_seconds if name=='target_1600000' else 10
                        row['requested_seconds_after_delivery']=duration
                        while time.monotonic()-began<duration+45:
                            app.processEvents()
                            if report['errors']:raise RuntimeError('Worker/GUI reported an error')
                            if not thread.isRunning():raise RuntimeError('Worker ended before stage completion')
                            first=row['first_delivery_monotonic']
                            if first is not None and time.monotonic()-first>=duration:
                                row['ok']=True;break
                            time.sleep(.001)
                        row['finished_monotonic']=time.monotonic()
                        if row['first_delivery_monotonic'] is not None:
                            row['requested_to_first_delivery_seconds']=row['first_delivery_monotonic']-began
                        row['trace']=[r for r in worker.trace.snapshot() if r['generation']==generation]
                        if receivers:row['status']=dict(receivers[-1].decoder.status or {})
                        if not row['ok']:raise TimeoutError('Stage timeout: '+name)
                        print(name,'OK',row['samples'],'samples',flush=True)
                    report['ok']=True
            except BaseException as exc:
                error(repr(exc));report['traceback']=traceback.format_exc()
            finally:
                if worker is not None:worker.stop()
                if thread is not None:
                    deadline=time.monotonic()+15
                    while thread.isRunning() and time.monotonic()<deadline:
                        app.processEvents();time.sleep(.001)
                    report['worker_exited']=not thread.isRunning()
                if worker is not None:
                    report.update(trace_final=worker.trace.snapshot(),pending_batches_peak=worker.pending_batches_peak,
                        pending_dsp_peak=worker.pending_dsp_peak,delivery_failure=getattr(worker,'delivery_failure_snapshot',None))
                    if active[0] is not None and 'trace' not in active[0]:
                        active[0]['trace']=[r for r in worker.trace.snapshot() if r['generation']==active[0]['generation']]
                if thread is not None and thread.isRunning():
                    error('Worker did not exit; no competing reader or recovery opened')
                    # Preserve the live QThread reference until process exit, never terminate it.
                    globals()['_unfinished_worker']=(thread,worker,window)
                else:
                    if window is not None:window.serial_worker=None;window.close()
                    if 'prior' in report:
                        try:restore(args.serial,report)
                        except BaseException as exc:error('Restoration: '+repr(exc));report['restore_traceback']=traceback.format_exc()
                report['ok']=report['ok'] and report['restored'] and not report['errors']
                save()
    except BaseException as exc:
        error(repr(exc));report['ok']=False;save()
    finally:
        sys.excepthook=old_hook
    print(path,flush=True)
    return report,path


if __name__=='__main__':
    result,_=main()
    raise SystemExit(0 if result['ok'] else 1)
