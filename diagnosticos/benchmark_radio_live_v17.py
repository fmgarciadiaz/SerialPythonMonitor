"""Live Q RADIO40/FILTER/FFT timing and actual visible paint events; restore Q."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PyQt6 import QtCore, QtWidgets
from PyQt6 import sip
import pyqtgraph as pg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17 import app as gui
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_wav import State


def summary(values):
    a = np.asarray(values, dtype=float)
    return dict(count=len(a), mean_ms=float(a.mean()),
        p50_p95_p99_max_ms=np.percentile(a,[50,95,99,100]).tolist()) if len(a) else dict(count=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default='1060031107')
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--view',choices=('fft','scope'),default='fft')
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120:
        raise ValueError('Maximum authorized measurement is 120 s')
    require_exclusive_monitor()
    report = dict(ok=False,restored=False,errors=[],seconds=args.seconds,
        scope=f'Live ADC8/CH1 1.4035MHz RADIO40 FILTER RADIO {args.view}. Generator off; no known AM/analog acceptance.',
        identity=instrument_identity(args.serial))
    path = ROOT/'diagnosticos/resultados_v17'/('radio_live_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
    sources = ('app.py','processing.py','radio_stream.py','radio_am.py','spectral_analysis.py','spectrum.py','numeric_batch.py',
        'receiver/unoq_config_receiver.py','receiver/unoq_config_decoder.py')
    if report['identity'] is None:
        raise RuntimeError('Unknown installed V17 firmware identity')
    report['source_sha256'] = {name:hashlib.sha256((ROOT/'monitor/v17'/name).read_bytes()).hexdigest() for name in sources}
    with Connection(args.serial) as connection:
        receiver = OutputReceiver(connection, lambda rows: None)
        receiver.decoder.numeric=True
        receiver.select(Mode.SPI); receiver.wav_request()
        deadline = time.monotonic()+3
        while receiver.wav_pending and time.monotonic()<deadline:receiver.pump()
        if receiver.wav_pending or receiver.wav_status.state != State.IDLE:
            raise RuntimeError('WAV not idle')
        prior_config, prior_generator = receiver.config, receiver.generator().active
    report['prior'] = dict(adc=asdict(prior_config),generator=asdict(prior_generator))
    path.write_text(json.dumps(report,indent=2)+'\n')
    application = QtWidgets.QApplication([])
    active = dict(start=None,stopping=False,paints=0,fft_paints=0,viewport_paints=0,fft_viewport_paints=0,exposed=0,polls=0)
    timings, statuses = {}, []
    def record(name, value):timings.setdefault(name,[]).append(value)
    class PaintPlot(pg.PlotWidget):
        def paintEvent(self,event):
            began = time.perf_counter()
            super().paintEvent(event)
            if active['start'] is not None and not active['stopping']:
                active['paints'] += 1
                record('paint_ms',(time.perf_counter()-began)*1000)
    class PaintGraphics(pg.GraphicsLayoutWidget):
        def paintEvent(self,event):
            began=time.perf_counter()
            super().paintEvent(event)
            if active['start'] is not None and not active['stopping']:
                active['fft_paints']+=1
                record('fft_paint_ms',(time.perf_counter()-began)*1000)
    class PaintObserver(QtCore.QObject):
        def eventFilter(self,obj,event):
            if event.type()==QtCore.QEvent.Type.Paint and active['start'] is not None and not active['stopping']:
                active['fft_viewport_paints' if obj.property('diagnostic_fft') else 'viewport_paints'] += 1
            return False
    with patch.object(gui,'usb_devices',return_value=[]), patch.object(pg,'PlotWidget',PaintPlot), patch.object(pg,'GraphicsLayoutWidget',PaintGraphics):
        window = gui.SerialMonitorWindow()
    observer = PaintObserver(window)
    window.plot_widget.viewport().installEventFilter(observer)
    window.spectral.widget.viewport().setProperty('diagnostic_fft',True)
    window.spectral.widget.viewport().installEventFilter(observer)
    config = Configuration(8,1403508)
    window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(config.bits))
    window.config_rate_combo.setCurrentIndex(window.config_rate_combo.findData(config.rate))
    window._acquisition_confirmed(config.bits,config.rate)
    window.filter_source.setCurrentText('RADIO')
    window.radio_frequency.setValue(20.525)
    window.radio_enabled.setChecked(True)
    for name in ('CH1','CH2'):window.graph_channel_actions[name].setChecked(False)
    window.graph_channel_actions['RADIO'].setChecked(True)
    window.trigger_source_combo.setCurrentText('RADIO');window.trigger_checkbox.setChecked(True)
    window.spectral.set_mode(1);window.spectral.channels[0].setCurrentText('RADIO')
    window.spectral.channels[1].setCurrentText('Ninguno');window.spectral.size.setCurrentText('65536')
    if args.view=='scope':window.spectral.set_mode(0)
    window.h_scale=400
    worker = gui.OutputWorker(args.serial,Mode.SPI,config=config,autoload=False,
        initial_generator=GeneratorConfig(enabled=0),processing_settings=window._processing_settings(),startup_gui_ack=True,processing_backend='process')
    thread = QtCore.QThread()
    window.serial_worker,window.serial_thread=worker,thread
    worker.moveToThread(thread);thread.started.connect(worker.run)
    worker.finished.connect(thread.quit,QtCore.Qt.ConnectionType.DirectConnection)
    worker.acquisition_confirmed.connect(window._acquisition_confirmed)
    worker.output_confirmed.connect(window._output_confirmed)
    worker.switching.connect(window._set_output_pending)
    worker.generator_confirmed.connect(window._generator_confirmed)
    worker.finished.connect(application.quit)
    def consume(batch):
        try:
            began=time.perf_counter()
            window._deliver_worker_batch(worker,batch)
            if active['start'] is not None and not active['stopping']:
                record('gui_delivery_ms',(time.perf_counter()-began)*1000)
            if active['start'] is None:
                active['start']=time.monotonic()
                print('RADIO LIVE first batch',flush=True)
                active['sample_start']=window.sample_counter
                active['batch_start']=window.batch_processing_count
            if not active['stopping']:
                for name,value in batch.processing['timings'].items():record(name,value)
                record('publish_to_consume_ms',(time.monotonic()-batch.published_at)*1000)
        except Exception as exc:
            error(str(exc))
    worker.batch_ready.connect(consume,QtCore.Qt.ConnectionType.QueuedConnection)
    def error(message):
        report['errors'].append(message)
        if active['start'] is not None:
            active['elapsed']=time.monotonic()-active['start']
        active['stopping']=True
        worker.stop()
    worker.error_occurred.connect(error)
    original_pump = OutputReceiver.pump
    def pump(receiver):
        if receiver.transport_trace is None:receiver.transport_trace=[]
        original_pump(receiver)
        if receiver.config==config and active['start'] is not None and not active['stopping']:
            for entry in receiver.transport_trace:
                stage,began,end=entry[:3]
                record('transport_'+stage+'_ms',(end-began)*1000)
            for status in receiver.decoder.statuses:
                if 'send_ticks' in status:
                    statuses.append((status['send_ticks'],status['queue_peak'],status['slack_ticks'],status['dropped'],status['fatal']))
        receiver.transport_trace.clear()
    original_render=window.spectral.render
    def render():
        began=time.perf_counter();previous=window.spectral.last_fast_render
        original_render()
        if active['start'] is not None and not active['stopping'] and previous!=window.spectral.last_fast_render:
            record('fft_render_ms',(time.perf_counter()-began)*1000)
    window.render_timer.timeout.disconnect(window.spectral.render)
    window.render_timer.timeout.connect(render)
    timer=QtCore.QTimer();timer.setInterval(100)
    began=time.monotonic()
    def tick():
        if active['stopping']:return
        if active['start'] is None:
            if time.monotonic()-began>30:error('No live batches within 30 s')
            return
        active['polls']+=1
        active['exposed']+=int(window.isVisible() and window.windowHandle().isExposed())
        progress=int((time.monotonic()-active['start'])//30)
        if progress>active.get('progress',0):
            active['progress']=progress
            print('RADIO LIVE',progress*30,'s',flush=True)
        if time.monotonic()-active['start']>=args.seconds:
            active['elapsed']=time.monotonic()-active['start']
            active['stopping']=True;worker.stop()
    timer.timeout.connect(tick)
    window.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint,True)
    window.show();window.raise_();window.activateWindow()
    window._auto_apply_timer.stop()
    window._set_output_pending(True)
    try:
        with patch.object(OutputReceiver,'pump',pump):
            # Match normal use: the window finishes its first layout/paint
            # before the user connects. Avoid injecting GUI startup work into
            # the sustained acquisition measurement.
            QtCore.QTimer.singleShot(1500,thread.start)
            timer.start();application.exec()
        timer.stop()
        if not sip.isdeleted(thread) and not thread.wait(10000):raise RuntimeError('Reader did not stop; cannot take Q for restoration')
        drain_deadline=time.monotonic()+2
        while worker.pending_batches and time.monotonic()<drain_deadline:
            application.processEvents()
        if worker.pending_batches:report['errors'].append('Pending GUI deliveries did not drain')
        elapsed=active.get('elapsed',0)
        report.update(elapsed_seconds=elapsed,rf_samples=window.sample_counter-active.get('sample_start',0),
            audio_samples=window.radio_stream.counter if window.radio_stream else 0,
            batches=window.batch_processing_count-active.get('batch_start',0),pending_peak=worker.pending_batches_peak,
            stages={name:summary(values) for name,values in timings.items()},paints=active['paints'],
            fft_paints=active['fft_paints'],fft_viewport_paints=active['fft_viewport_paints'],
            fft_paint_fps=active['fft_paints']/elapsed if elapsed else 0,
            viewport_paints=active['viewport_paints'],paint_fps=active['paints']/elapsed if elapsed else 0,
            viewport_paint_fps=active['viewport_paints']/elapsed if elapsed else 0,
            exposed_fraction=active['exposed']/active['polls'] if active['polls'] else 0)
        report['deferred_spectral_timer_calls']=window.spectral.deferred_live_timer_calls
        report['processing_backend']=worker.processing_backend
        report['coalesced_rf_peak']=worker.coalesced_rf_peak
        report['coalesced_flush_calls']=worker.coalesced_flush_calls
        if statuses:
            a=np.asarray(statuses,dtype=np.float64)
            report['transport']=dict(mean_send_headroom=1-float(a[:,0].mean())/(config.period*config.node_pairs),
                queue_peak=int(a[:,1].max()),slack_min_us=float(a[:,2].min())/160,
                dropped=int(a[:,3].max()),fatal=int(a[:,4].max()))
        report['ok']=not report['errors'] and elapsed>=args.seconds and report['rf_samples']>0 and report['audio_samples']>0
        report['visible_painting_valid']=(report['fft_paints']>0 and report['fft_viewport_paints']>0 if args.view=='fft'
            else report['paints']>0 and report['viewport_paints']>0) and report['exposed_fraction']>.99
        report['ok']=report['ok'] and report['visible_painting_valid']
    except Exception as exc:
        report['errors'].append(repr(exc))
    finally:
        if not sip.isdeleted(thread) and thread.isRunning():
            worker.stop()
            if not thread.wait(10000):raise RuntimeError('Reader still owns Q')
        window.serial_worker=None;window.serial_thread=None;window.close()
        def restore():
            with Connection(args.serial) as connection:
                receiver=OutputReceiver(connection,lambda rows:None);receiver.decoder.numeric=True
                receiver.select(Mode.SPI);receiver.generator(GeneratorConfig(enabled=0))
                receiver.configure(prior_config);receiver.generator(prior_generator)
                report['restored']=receiver.config==prior_config and receiver.generator().active==prior_generator
                before=receiver.decoder.pairs;start=time.monotonic()
                while time.monotonic()-start<10:receiver.pump()
                report['recovery']=dict(samples=receiver.decoder.pairs-before,status=receiver.decoder.status)
            report['final_identity']=instrument_identity(args.serial)
            report['restored']=report['restored'] and report['final_identity']==report['identity']
        try:
            restore()
        except Exception as exc:
            report['first_restore_error']=repr(exc)
            try:
                # A transport/DMA fault requires a fresh acquisition epoch
                # before commands can be validated. Restart the installed
                # stack, then restore the exact original ADC/generator.
                subprocess.run([sys.executable,str(ROOT/'tools/usb_stream.py'),'start','--firmware','v17'],
                    check=True,timeout=600)
                report['recovery_restart']=True
                restore()
            except Exception as failure:
                report['restore_error']=repr(failure)
        path.write_text(json.dumps(report,indent=2)+'\n')
        print('REPORT',path,'OK',report['ok'],'RESTORED',report['restored'],flush=True)
    return 0 if report['ok'] and report['restored'] else 1


if __name__=='__main__':raise SystemExit(main())
