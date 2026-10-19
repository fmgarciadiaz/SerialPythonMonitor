import sys,time,json,traceback
from pathlib import Path
from dataclasses import asdict
from unittest.mock import patch
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from monitor.v17.app import SerialMonitorWindow,OutputWorker,QtWidgets,QtCore
from monitor.v17.board_owner import board_owner
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.bode_calibration import instrument_identity
def main():
 app=QtWidgets.QApplication([])
 folder=ROOT/'diagnosticos/resultados_v17'/('wav_selection_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 report={'cases':[],'errors':[],'restored':False,'platform':app.platformName()};prior=None
 config=Configuration(8,1600000)
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 sys.excepthook=lambda kind,value,tb:report['errors'].append(''.join(traceback.format_exception(kind,value,tb)))
 with board_owner('1060031107','Diagnosticar selección WAV ADC8/1.6M'):
  require_exclusive_monitor()
  try:
   with Connection('1060031107') as c:
    r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);g=r.generator().active
    if g.enabled:raise RuntimeError('Generator occupied')
    prior={'adc':asdict(r.config),'generator':asdict(g)};report['prior']=prior;r.configure(Configuration(14,40000))
   report['identity_before']=instrument_identity('1060031107');save()
   for radio in (False,True):
    w=worker=thread=None
    row={'radio':radio,'samples':0,'errors':[]};report['cases'].append(row)
    try:
     with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
     w.generator_mode.setCurrentIndex(4)
     w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(8));w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(1600000))
     w.radio_enabled.setChecked(radio)
     worker=OutputWorker('1060031107',Mode.SPI,config=config,processing_settings=w._processing_settings(),startup_gui_ack=True,processing_backend='process')
     worker._ensure_process().result(timeout=45)
     w.serial_worker=worker;w.is_running=True;w.show()
     def confirmed(bits,rate):w._acquisition_confirmed(bits,rate);worker.confirm_startup(bits,rate)
     worker.acquisition_confirmed.connect(confirmed)
     def collect(batch):row['samples']+=len(batch);w._deliver_worker_batch(worker,batch)
     worker.batch_ready.connect(collect);worker.error_occurred.connect(row['errors'].append)
     thread=QtCore.QThread();worker.moveToThread(thread);thread.started.connect(worker.run);worker.finished.connect(thread.quit);thread.start()
     start=time.monotonic();selected=False
     while thread.isRunning() and time.monotonic()-start<22:
      app.processEvents();time.sleep(.001)
      if not selected and time.monotonic()-start>6 and w.applied_configuration==config:
       selected=True
       # First isolate the full post-selection path, excluding the native panel.
       before=row['samples'];began=time.monotonic()
       if '--native' in sys.argv:
        def accept_file():
         dialogs=[d for d in app.topLevelWidgets() if isinstance(d,QtWidgets.QFileDialog)]
         for d in dialogs:
          d.selectFile(str(ROOT/'audios/imperial.wav'))
          QtCore.QMetaObject.invokeMethod(d,'accept',QtCore.Qt.ConnectionType.QueuedConnection)
        QtCore.QTimer.singleShot(2000,accept_file)
        QtCore.QTimer.singleShot(6000,lambda:[d.reject() for d in app.topLevelWidgets() if isinstance(d,QtWidgets.QFileDialog)])
        w._choose_wav()
       else:
        with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(ROOT/'audios/imperial.wav'),'')):w._choose_wav()
       row['post_selection_ms']=(time.monotonic()-began)*1000
       row['metadata']=w._wav_metadata
       print('SELECTED',radio,row['post_selection_ms'],flush=True)
      if row['errors']:break
     row.update(selected=selected and w._wav_metadata is not None,pending_peak=worker.pending_batches_peak,dsp_peak=worker.pending_dsp_peak,gui_delay_max_ms=w.batch_queue_delay_max_ms,ok=selected and w._wav_metadata is not None and not row['errors'] and row['samples']>1000000)
    finally:
     if worker:worker.stop()
     if thread:
      deadline=time.monotonic()+15
      while thread.isRunning() and time.monotonic()<deadline:app.processEvents();time.sleep(.001)
      if thread.isRunning():raise RuntimeError('Worker failed to stop')
     if w:w.serial_worker=None;w.close()
     save()
    print('CASE',json.dumps(row),flush=True)
    with Connection('1060031107') as c:
     r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000))
  except BaseException:
   report['errors'].append(traceback.format_exc());raise
  finally:
   if prior:
    with Connection('1060031107') as c:
     r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000));r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
     report['restored']=asdict(r.config)==prior['adc'] and asdict(r.generator().active)==prior['generator'];end=time.monotonic()+5;before=r.decoder.pairs
     while time.monotonic()<end:r.pump()
     report['recovery']={'samples':r.decoder.pairs-before,'status':r.decoder.status}
    report['identity_after']=instrument_identity('1060031107')
   save();print('REPORT',folder/'report.json',flush=True)
if __name__=='__main__':main()
