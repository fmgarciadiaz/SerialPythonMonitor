"""Paced real-frame decoder -> numeric -> DSP worker -> GUI/FFT benchmark.

No board access. Offscreen paint counts do not establish visible FPS.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import argparse
import importlib.util
import hashlib
import json
import struct
import sys
import threading
import time
import zlib
from pathlib import Path
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PyQt6 import QtCore,QtWidgets
from monitor.v17.app import SerialMonitorWindow,OutputWorker
from monitor.v17.numeric_batch import NumericBatch,SampleClock
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.native_unpack import unpack_native


def summary(values):
    values=np.asarray(values,dtype=float)
    return dict(count=len(values),mean_ms=float(values.mean()),
        p50_p95_p99_max_ms=np.percentile(values,[50,95,99,100]).tolist()) if len(values) else {'count':0}


def memory_comparison():
    path=ROOT/'diagnosticos/referencias/v17_processing_before/native_unpack.py'
    spec=importlib.util.spec_from_file_location('baseline_unpack',path)
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    payload=np.arange(864,dtype=np.uint8).tobytes()
    results={}
    for label,fn in [('before',baseline.unpack_native),('after',unpack_native)]:
        times=[]
        for _ in range(1000):
            start=time.perf_counter();rows=fn(payload,8,1,864,0xfffffff0,114,0xfffffff0,True)
            times.append((time.perf_counter()-start)*1000)
        results[label]=dict(**summary(times),bytes_per_sample=rows.array.nbytes/len(rows))
    assert list(baseline.unpack_native(payload,8,1,864,0xfffffff0,114,0xfffffff0,True)) == list(
        unpack_native(payload,8,1,864,0xfffffff0,114,0xfffffff0,True))
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=15)
    parser.add_argument('--backend',choices=['thread','process'],default='thread')
    parser.add_argument('--mixed-view',action='store_true')
    parser.add_argument('--radio-frequency',type=float)
    parser.add_argument('--fft-size',type=int,default=65536)
    parser.add_argument('--filter',choices=['OFF','RADIO'],default='RADIO')
    parser.add_argument('--output',default='diagnosticos/resultados_v17/processing_gui_offline.json')
    args=parser.parse_args()
    app=QtWidgets.QApplication([])
    with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
    config=Configuration(8,1403508)
    w._acquisition_confirmed(config.bits,config.rate)
    w.filter_source.setCurrentText(args.filter);w.radio_enabled.setChecked(True)
    w.graph_channel_actions['CH1'].setChecked(args.mixed_view);w.graph_channel_actions['CH2'].setChecked(False)
    w.graph_channel_actions['RADIO'].setChecked(True)
    w.trigger_source_combo.setCurrentText('RADIO');w.trigger_checkbox.setChecked(True)
    w.spectral.mode=1;w.spectral.channels[0].setCurrentText('RADIO')
    w.spectral.channels[1].setCurrentText('Ninguno');w.spectral.size.setCurrentText(str(args.fft_size))
    w.radio_frequency.setValue(args.radio_frequency if args.radio_frequency is not None else 20.525 if args.mixed_view else 550)
    if args.mixed_view:
        w.spectral.set_mode(0)
        w.on_h_scale_changed(round(config.actual_rate*.01))
        w.dial_trigger_level.setValue(165)
    w.show()
    worker=OutputWorker('offline',Mode.SPI,config=config,processing_settings=w._processing_settings(),processing_backend=args.backend)
    w.serial_worker=worker
    report=dict(scope='Offline actual native frames at ADC8 CH1 1.4035MHz, RADIO40, trigger, FFT; no physical transport or visible FPS acceptance',
        seconds=args.seconds,backend=args.backend,mixed_view=args.mixed_view,radio_frequency_hz=w.radio_frequency.value()*1000,fft_size=args.fft_size,filter=args.filter,errors=[],stages={},native_width=memory_comparison())
    if args.mixed_view:report['scope']='Offline native ADC8 CH1 1.4035MHz + RADIO40 on common temporal view, 10ms window; no physical transport or visible FPS acceptance'
    timings={};done=threading.Event()
    def record(name,value):timings.setdefault(name,[]).append(value)
    def consume(batch):
        try:
            start=time.perf_counter();w._deliver_worker_batch(worker,batch)
            record('gui_delivery_ms',(time.perf_counter()-start)*1000)
            for name,value in batch.processing['timings'].items():record(name,value)
            record('publish_to_consume_ms',(time.monotonic()-batch.published_at)*1000)
        except Exception as exc:
            report['errors'].append(str(exc));worker.running=False
    worker.batch_ready.connect(consume,QtCore.Qt.ConnectionType.QueuedConnection)
    worker.error_occurred.connect(lambda text:report['errors'].append(text))
    original_render=w.render_frame
    def render():
        start=time.perf_counter();original_render();record('render_frame_ms',(time.perf_counter()-start)*1000)
    original_spectral=w.spectral.render
    def spectral_render():
        start=time.perf_counter();previous=w.spectral.last_fast_render
        original_spectral()
        if w.spectral.last_fast_render!=previous:
            record('fft_render_ms',(time.perf_counter()-start)*1000)
    # Replace the timer connection, preserving the production render cadence.
    w.render_timer.timeout.disconnect(w.render_frame);w.render_timer.timeout.connect(render)
    w.render_timer.timeout.disconnect(w.spectral.render);w.render_timer.timeout.connect(spectral_render)
    decoder=ConfigurationDecoder();decoder.numeric=True
    def produce():
        started=time.monotonic();batches=0;clock=SampleClock(160000000)
        node=seq=0;count=config.node_pairs*8;period=count/config.actual_rate
        try:
            while time.monotonic()-started<args.seconds and worker.running:
                frames=[]
                for _ in range(8):
                    indices=np.arange(node*config.node_pairs,(node+1)*config.node_pairs,dtype=np.uint64)
                    t=indices/config.actual_rate
                    values=np.rint((1.65+.3*(1+.5*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*20525*t))*255/3.3).astype(np.uint8)
                    for offset in range(0,config.node_pairs,864):
                        sample=values[offset:offset+864];index=node*config.node_pairs+offset
                        p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,20,seq,972)
                        struct.pack_into('<i',p,32,992)
                        struct.pack_into('<IIIIHBBIII',p,48,config.rate,index&0xffffffff,0,0,len(sample),8,1,114,node,0)
                        struct.pack_into('<I8I',p,80,(index*114)&0xffffffff,config.node_pairs,1,2,100,100,100,100,1)
                        p[116:116+len(sample)]=sample.tobytes();struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
                        frames.append(p);seq+=1
                    node+=1
                start=time.perf_counter();rows=decoder.feed(b''.join(frames));record('decoder_ms',(time.perf_counter()-start)*1000)
                start=time.perf_counter();batch=NumericBatch(rows.array,255,clock,1);batch.acquisition=config
                record('numeric_conversion_ms',(time.perf_counter()-start)*1000)
                worker.publish_batch(batch);batches+=1
                delay=started+batches*period-time.monotonic()
                if delay>0:time.sleep(delay)
        except Exception as exc:report['errors'].append(str(exc))
        report.update(produced_batches=batches,decoded_samples=decoder.pairs)
        done.set()
    thread=threading.Thread(target=produce);thread.start()
    timer=QtCore.QTimer();timer.setInterval(50)
    def finish():
        if done.is_set() and worker.pending_batches==0:app.quit()
    timer.timeout.connect(finish);timer.start();app.exec();thread.join();timer.stop()
    if worker._processing_executor is not None:worker._processing_executor.shutdown(wait=True)
    if worker._processing_process is not None:worker._processing_process.shutdown(wait=True)
    report.update(stages={name:summary(values) for name,values in timings.items()},
        pending_peak=worker.pending_batches_peak,processed_batches=w.batch_processing_count,
        gui_samples=w.sample_counter,audio_samples=w.radio_stream.counter if w.radio_stream else 0)
    report['delivery_ok']=not report['errors'] and report['produced_batches']==report['processed_batches'] and report['decoded_samples']==report['gui_samples']
    report['nominal_rate_fraction']=report['decoded_samples']/(args.seconds*config.actual_rate)
    report['full_rate_ok']=report['nominal_rate_fraction']>=.98
    report['ok']=report['delivery_ok'] and report['full_rate_ok']
    w.serial_worker=None;w.close()
    report['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('monitor/v17/app.py','monitor/v17/history.py','monitor/v17/spectrum.py','monitor/v17/receiver/unoq_config_decoder.py','monitor/v17/processing.py','monitor/v17/radio_stream.py')}
    (ROOT/args.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
