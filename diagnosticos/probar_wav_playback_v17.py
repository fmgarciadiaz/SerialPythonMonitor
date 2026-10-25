import sys,time,json,traceback,struct
from collections import deque
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
 receivers=[]
 import inspect
 native_pcm='pcm=isinstance(self.wav_codes,np.ndarray)' in inspect.getsource(OutputReceiver.service_wav)
 thread_clock_available=hasattr(time,'thread_time')
 if not native_pcm and ('--pcm-window2' in sys.argv or '--pcm-buffer30' in sys.argv):
  # Isolated experiments: confirmed PCM window and/or advertised queue capacity.
  import inspect,textwrap
  import monitor.v17.receiver.unoq_config_receiver as receiver_module
  code=textwrap.dedent(inspect.getsource(OutputReceiver.service_wav))
  if '--pcm-window2' in sys.argv:
   old="live=getattr(self.wav_codes,'live',False)";assert old in code
   code=code.replace(old,"live=getattr(self.wav_codes,'live',False) or isinstance(self.wav_codes, np.ndarray)",1)
  if '--pcm-buffer30' in sys.argv:
   old="capacity=min(slots,getattr(self.wav_codes,'maximum_blocks',16))";assert old in code
   code=code.replace(old,"capacity=min(slots,getattr(self.wav_codes,'maximum_blocks',30 if isinstance(self.wav_codes,np.ndarray) else 16))",1)
   old="target=max(2,min(capacity,getattr(self.wav_codes,'target_blocks',16)))";assert old in code
   code=code.replace(old,"target=max(2,min(capacity,getattr(self.wav_codes,'target_blocks',30 if isinstance(self.wav_codes,np.ndarray) else 16)))",1)
  namespace=dict(vars(receiver_module));exec(code,namespace)
  OutputReceiver.service_wav=namespace['service_wav']
 native_frames='or isinstance(self.wav_codes,np.ndarray)' in inspect.getsource(OutputReceiver.pump)
 if '--pcm-frame-service' in sys.argv and not native_frames:
  import inspect,textwrap
  import monitor.v17.receiver.unoq_config_receiver as receiver_module
  code=textwrap.dedent(inspect.getsource(OutputReceiver.pump))
  old="stride=992 if getattr(self.wav_codes,'live',False) else max(1,len(data))";assert old in code
  code=code.replace(old,"stride=992 if getattr(self.wav_codes,'live',False) or isinstance(self.wav_codes,np.ndarray) else max(1,len(data))",1)
  namespace=dict(vars(receiver_module));exec(code,namespace)
  OutputReceiver.pump=namespace['pump']
 if '--trace' in sys.argv:
  # This Python lacks thread_time on macOS; CPU fields use process time here.
  if not hasattr(time, 'thread_time'):time.thread_time=time.process_time
  class TraceReceiver(OutputReceiver):
   def __init__(self,*args,**kwargs):
    super().__init__(*args,**kwargs);self.transport_trace=deque(maxlen=12000);self.wav_trace=deque(maxlen=6000);receivers.append(self)
   def _wav_send(self,frame):
    status=self.wav_status
    self.wav_trace.append(('send',time.monotonic(),struct.unpack_from('<H',frame,6)[0],status.accepted if status else None,status.played if status else None,len(self.wav_inflight),struct.unpack_from('<I',frame,8)[0]))
    return super()._wav_send(frame)
   def _process_decoder_events(self):
    before=self.wav_status
    outcome=super()._process_decoder_events()
    if self.wav_status is not before and self.wav_status is not None:
     s=self.wav_status;self.wav_trace.append(('ack',time.monotonic(),int(s.state),s.accepted,s.played,s.free_blocks,s.request_id,int(s.reason)))
    return outcome
  import monitor.v17.app as app_module
  app_module.OutputReceiver=TraceReceiver
 app=QtWidgets.QApplication([])
 folder=ROOT/'diagnosticos/resultados_v17'/('wav_playback_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 report={'cases':[],'errors':[],'restored':False,'platform':app.platformName(),'experimental_pcm_frame_service':'--pcm-frame-service' in sys.argv,'experimental_pcm_buffer30':'--pcm-buffer30' in sys.argv,'experimental_pcm_window2':'--pcm-window2' in sys.argv,'trace_cpu_clock':'process_time fallback; use wall timestamps for causal analysis'};prior=None
 report.update(native_pcm_delivery=native_pcm,native_pcm_frame_service=native_frames,
     trace_cpu_clock='thread_time' if thread_clock_available else 'process_time fallback; use wall timestamps for causal analysis')
 from diagnosticos.wav_cases_v17 import select_cases,near_eof_delta,select_window_configuration
 matrix,duration=select_cases(sys.argv)
 # Validate every case before establishing board ownership or changing Q.
 for bits,adc_rate,audio_rate in matrix:Configuration(bits,adc_rate)
 config=None;thread=None;report['requested_cases']=list(matrix);report['requested_seconds']=duration
 source=Path(sys.argv[sys.argv.index('--source')+1]).resolve() if '--source' in sys.argv else ROOT/'audios/imperial.wav'
 from monitor.v17.wav_source import inspect_wav
 report['source']=str(source);report['source_metadata']=inspect_wav(source)
 if '--controls' not in sys.argv and '--select-only' not in sys.argv and duration>=report['source_metadata']['duration']:raise ValueError('El WAV debe durar más que el ensayo solicitado')
 report['selection_only']='--select-only' in sys.argv
 report['wav_trace_schema']=dict(send='stage,time,kind,accepted,played,inflight,RID',ack='stage,time,state,accepted,played,free,RID,reason')
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 def gui_exception(kind,value,tb):
  detail=''.join(traceback.format_exception(kind,value,tb))
  report['errors'].append(detail)
  if report['cases']:
   report['cases'][-1]['errors'].append('GUI: '+detail)
   report['cases'][-1]['ok']=False
 sys.excepthook=gui_exception
 with board_owner('1060031107','Diagnosticar cortes WAV hacia A0'):
  require_exclusive_monitor()
  try:
   with Connection('1060031107') as c:
    r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);g=r.generator().active
    if g.enabled:raise RuntimeError('Generator occupied')
    prior={'adc':asdict(r.config),'generator':asdict(g)};report['prior']=prior;r.configure(Configuration(14,40000))
   report['identity_before']=instrument_identity('1060031107');save()
   if report['identity_before'] is None:raise RuntimeError('Identidad de firmware desconocida')
   for bits,adc_rate,audio_rate in matrix:
    config=Configuration(bits,adc_rate);radio='--radio' in sys.argv
    w=worker=thread=audit=None
    row={'bits':bits,'adc_rate':adc_rate,'audio_rate':audio_rate,'radio':radio,'samples':0,'errors':[],'states':[]};report['cases'].append(row)
    try:
     with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
     original_selection=w._wav_file_selected
     def measured_selection(path,row=row,original=original_selection):
      began=time.monotonic()
      try:return original(path)
      finally:row['selection_callback_ms']=(time.monotonic()-began)*1000
     w._wav_file_selected=measured_selection
     w.generator_mode.setCurrentIndex(4)
     select_window_configuration(w,config)
     w.radio_enabled.setChecked(radio)
     w._auto_apply_timer.stop()
     worker=OutputWorker('1060031107',Mode.SPI,config=config,processing_settings=w._processing_settings(),startup_gui_ack=True,processing_backend='process')
     worker._ensure_process().result(timeout=45)
     if '--keep-visible' in sys.argv:w.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint,True)
     w.serial_worker=worker;w.is_running=True;w.show()
     if '--analysis-audit' in sys.argv and '--select-only' not in sys.argv:
      from diagnosticos.wav_visual_audit_v17 import WavVisualAudit
      audit=WavVisualAudit(w)
      w.raise_();w.activateWindow()
     def confirmed(bits,rate,w=w,worker=worker):w._acquisition_confirmed(bits,rate);worker.confirm_startup(bits,rate)
     worker.acquisition_confirmed.connect(confirmed)
     def collect(batch,row=row,w=w,worker=worker):row['samples']+=len(batch);w._deliver_worker_batch(worker,batch)
     def wav_status(status,row=row,w=w,audit=audit):
      if audit:audit.playing(int(status.state)==2)
      row['last_played']=status.played
      if not row['states'] or row['states'][-1]['state']!=int(status.state):row['states'].append({'state':int(status.state),'reason':status.reason,'played':status.played,'accepted':status.accepted})
      if int(status.state)==2:
       row['max_played']=max(row.get('max_played',0),status.played)
       reserve=(status.accepted-status.played)*1000/status.rate
       if '--controls' not in sys.argv:row['dac_reserve_min_ms']=min(row.get('dac_reserve_min_ms',float('inf')),reserve)
       second=status.played//status.rate
       if second//15>row.get('live_epoch',0):
        row['live_epoch']=second//15;print('LIVE',second,'reserve_ms',reserve if '--controls' not in sys.argv else 'not comparable after seek',flush=True)
      if int(status.state) in (4,5):row['errors'].append('WAV '+str(int(status.state))+'/'+str(status.reason))
      w._wav_confirmed(status)
     worker.wav_confirmed.connect(wav_status)
     worker.batch_ready.connect(collect);worker.error_occurred.connect(row['errors'].append)
     thread=QtCore.QThread();worker.moveToThread(thread);thread.started.connect(worker.run);worker.finished.connect(thread.quit);thread.start()
     start=time.monotonic();selected=False
     while thread.isRunning() and time.monotonic()-start<duration+15:
      app.processEvents();time.sleep(.001)
      if audit:audit.sample_exposure()
      if not selected and time.monotonic()-start>6 and w.applied_configuration==config:
       selected=True
       w.wav_rate.setCurrentIndex(w.wav_rate.findData(audio_rate))
       if '--select-only' in sys.argv:
        w._choose_wav();row['dialog_opened']=True
       else:
        w._wav_file_selected(str(source))
        w._play_wav();row['play_requested']=True
      if '--select-only' in sys.argv and selected:
       age=time.monotonic()-start
       if age>7 and not row.get('file_chosen'):
        w._wav_file_dialog.findChild(QtWidgets.QLineEdit,'fileNameEdit').setText(str(source));row['file_chosen']=True
       if age>8 and not row.get('dialog_accepted'):
        w._wav_file_dialog.accept();row['dialog_accepted']=True
       if age>16:break
      if '--controls' in sys.argv and selected:
       actions=row.setdefault('actions',[]);age=time.monotonic()-start
       if age>8 and 'forward' not in actions and w._wav_active:w._seek_wav(10);actions.append('forward')
       if age>10 and 'backward' not in actions and w._wav_active:w._seek_wav(-5);actions.append('backward')
       if age>12 and 'stop' not in actions and w._wav_active:w._stop_wav();actions.append('stop')
       if age>14 and 'stop' in actions and 'replay' not in actions and not w._wav_active and not w._wav_preparing:w._play_wav();actions.append('replay')
       if age>17 and 'replay' in actions and 'near_eof' not in actions and w._wav_active:w._seek_wav(near_eof_delta(report['source_metadata']['duration'],row.get('last_played',0),audio_rate));actions.append('near_eof')
       if any(state['state']==3 for state in row['states']) and 'eof' not in actions:actions.append('eof')
       if 'eof' in actions and 'restart_after_eof' not in actions and not w._wav_active and not w._wav_preparing:w._play_wav();actions.append('restart_after_eof');row['restart_at']=time.monotonic()
       if 'restart_after_eof' in actions and time.monotonic()-row['restart_at']>2 and w._wav_active and 'final_stop' not in actions:w._stop_wav();actions.append('final_stop')
       if 'final_stop' in actions and not w._wav_active:break
      elif row.get('max_played',0)>=audio_rate*duration:break
      if row['errors'] or report['errors']:break
     row['generator_status']=w.generator_status.text()
     row['slow_gui_callbacks']=list(getattr(w,'_gui_slow_callbacks',()))
     row['delivery_failure']=getattr(worker,'delivery_failure_snapshot',None)
     row.update(metadata=w._wav_metadata,selected=selected and w._wav_metadata is not None,pending_peak=worker.pending_batches_peak,dsp_peak=worker.pending_dsp_peak,gui_delay_max_ms=w.batch_queue_delay_max_ms,ok=selected and not row['errors'] and row.get('max_played',0)>=audio_rate*duration)
     if '--select-only' in sys.argv:
      row.update(dialog_closed=w._wav_file_dialog is None,delivery_failure=getattr(worker,'delivery_failure_snapshot',None))
      row['ok']=bool(row['selected'] and row['dialog_closed'] and not row['errors'] and not w._wav_preparing and not w._wav_active)
    finally:
     if '--controls' in sys.argv:row['ok']=not row['errors'] and set(row.get('actions',[]))=={'forward','backward','stop','replay','near_eof','eof','restart_after_eof','final_stop'}
     if audit:
      audit.playing(False);row['paint_audit']=audit.snapshot()
      row['audio_integrity_ok']=row.get('ok',False)
      row['ok']=row.get('ok',False) and row['paint_audit']['visual_ok']
     if worker:worker.stop()
     if thread:
      deadline=time.monotonic()+15
      while thread.isRunning() and time.monotonic()<deadline:app.processEvents();time.sleep(.001)
      if thread.isRunning():raise RuntimeError('Worker failed to stop')
     if w:w.serial_worker=None;w.close()
     if receivers:row['transport_trace']=list(receivers[-1].transport_trace);row['wav_trace']=list(receivers[-1].wav_trace);row['adc_status']=receivers[-1].decoder.status
    save()
    print('CASE',json.dumps({k:v for k,v in row.items() if not k.endswith('_trace')}),flush=True)
    with Connection('1060031107') as c:
     r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000))
    if not row['ok'] or report['errors']:break
  except BaseException:
   report['errors'].append(traceback.format_exc());raise
  finally:
   try:
    if prior:
     if thread is not None and thread.isRunning():
      report.update(restored=False,restore_error='Worker sigue activo; no abrir una conexión competidora')
      save()
      raise RuntimeError(report['restore_error'])
     with Connection('1060031107') as c:
      r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000))
     report['identity_after']=instrument_identity('1060031107')
     if report['identity_after']!=report['identity_before']:raise RuntimeError('Cambió la identidad del firmware')
     # No administrative Q calls after restoring a potentially high-rate prior.
     with Connection('1060031107') as c:
      r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000));r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
      report['restored']=asdict(r.config)==prior['adc'] and asdict(r.generator().active)==prior['generator'];end=time.monotonic()+10;before=r.decoder.pairs
      while time.monotonic()<end:r.pump()
      report['recovery']={'samples':r.decoder.pairs-before,'status':r.decoder.status}
   except BaseException as exc:
    report.update(restored=False,restore_error=repr(exc))
    report['errors'].append(traceback.format_exc())
    raise
   finally:
    report['ok']=bool(report['restored'] and not report['errors'] and len(report['cases'])==len(matrix) and all(row.get('ok',False) for row in report['cases']) and report.get('identity_before') is not None and report.get('identity_after')==report.get('identity_before'))
    save();print('REPORT',folder/'report.json',flush=True)
 return report
if __name__=='__main__':
 result=main()
 raise SystemExit(0 if result['ok'] else 1)
