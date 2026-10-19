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
 if '--pcm-window2' in sys.argv or '--pcm-buffer30' in sys.argv:
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
 if '--pcm-frame-service' in sys.argv:
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
    self.wav_trace.append(('send',time.monotonic(),struct.unpack_from('<H',frame,6)[0],status.accepted if status else None,status.played if status else None,len(self.wav_inflight)))
    return super()._wav_send(frame)
   def _process_decoder_events(self):
    before=self.wav_status
    outcome=super()._process_decoder_events()
    if self.wav_status is not before and self.wav_status is not None:
     s=self.wav_status;self.wav_trace.append(('ack',time.monotonic(),int(s.state),s.accepted,s.played,s.free_blocks))
    return outcome
  import monitor.v17.app as app_module
  app_module.OutputReceiver=TraceReceiver
 app=QtWidgets.QApplication([])
 folder=ROOT/'diagnosticos/resultados_v17'/('wav_playback_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 report={'cases':[],'errors':[],'restored':False,'platform':app.platformName(),'experimental_pcm_frame_service':'--pcm-frame-service' in sys.argv,'experimental_pcm_buffer30':'--pcm-buffer30' in sys.argv,'experimental_pcm_window2':'--pcm-window2' in sys.argv,'trace_cpu_clock':'process_time fallback; use wall timestamps for causal analysis'};prior=None
 config=None;duration=float(sys.argv[sys.argv.index('--seconds')+1]) if '--seconds' in sys.argv else 120 if '--long' in sys.argv else 18
 matrix=((16,76226,50000),(16,76226,40000),(16,76226,20000)) if '--adc16' in sys.argv else ((14,100000,50000),) if '--long' in sys.argv else ((8,40000,20000),(8,40000,40000),(8,40000,50000),(14,100000,20000),(14,100000,40000),(14,100000,50000))
 if '--case16' in sys.argv:matrix=((16,76226,50000),)
 if '--critical-pair' in sys.argv:matrix=((16,76226,50000),(14,100000,50000))
 if '--qualify16' in sys.argv:matrix=((16,76226,50000),)*3;duration=120
 if '--controls' in sys.argv:matrix=((16,76226,50000),);duration=35
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 sys.excepthook=lambda kind,value,tb:report['errors'].append(''.join(traceback.format_exception(kind,value,tb)))
 with board_owner('1060031107','Diagnosticar cortes WAV hacia A0'):
  require_exclusive_monitor()
  try:
   with Connection('1060031107') as c:
    r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);g=r.generator().active
    if g.enabled:raise RuntimeError('Generator occupied')
    prior={'adc':asdict(r.config),'generator':asdict(g)};report['prior']=prior;r.configure(Configuration(14,40000))
   report['identity_before']=instrument_identity('1060031107');save()
   for bits,adc_rate,audio_rate in matrix:
    config=Configuration(bits,adc_rate);radio=False
    w=worker=thread=None
    row={'bits':bits,'adc_rate':adc_rate,'audio_rate':audio_rate,'radio':radio,'samples':0,'errors':[],'states':[]};report['cases'].append(row)
    try:
     with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
     w.generator_mode.setCurrentIndex(4)
     w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(bits));w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(adc_rate))
     w.radio_enabled.setChecked(radio)
     worker=OutputWorker('1060031107',Mode.SPI,config=config,processing_settings=w._processing_settings(),startup_gui_ack=True,processing_backend='process')
     worker._ensure_process().result(timeout=45)
     w.serial_worker=worker;w.is_running=True;w.show()
     def confirmed(bits,rate):w._acquisition_confirmed(bits,rate);worker.confirm_startup(bits,rate)
     worker.acquisition_confirmed.connect(confirmed)
     def collect(batch):row['samples']+=len(batch);w._deliver_worker_batch(worker,batch)
     def wav_status(status):
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
      if not selected and time.monotonic()-start>6 and w.applied_configuration==config:
       selected=True
       w._wav_file_selected(str(ROOT/'audios/imperial.wav'))
       w.wav_rate.setCurrentIndex(w.wav_rate.findData(audio_rate))
       w._play_wav();row['play_requested']=True
      if '--controls' in sys.argv and selected:
       actions=row.setdefault('actions',[]);age=time.monotonic()-start
       if age>8 and 'forward' not in actions and w._wav_active:w._seek_wav(10);actions.append('forward')
       if age>10 and 'backward' not in actions and w._wav_active:w._seek_wav(-5);actions.append('backward')
       if age>12 and 'stop' not in actions and w._wav_active:w._stop_wav();actions.append('stop')
       if age>14 and 'stop' in actions and 'replay' not in actions and not w._wav_active and not w._wav_preparing:w._play_wav();actions.append('replay')
       if age>17 and 'replay' in actions and 'near_eof' not in actions and w._wav_active:w._seek_wav(175);actions.append('near_eof')
       if any(state['state']==3 for state in row['states']) and 'eof' not in actions:actions.append('eof')
       if 'eof' in actions and 'restart_after_eof' not in actions and not w._wav_active and not w._wav_preparing:w._play_wav();actions.append('restart_after_eof');row['restart_at']=time.monotonic()
       if 'restart_after_eof' in actions and time.monotonic()-row['restart_at']>2 and w._wav_active and 'final_stop' not in actions:w._stop_wav();actions.append('final_stop')
       if 'final_stop' in actions and not w._wav_active:break
      elif row.get('max_played',0)>=audio_rate*duration:break
      if row['errors']:break
     row['generator_status']=w.generator_status.text()
     row.update(metadata=w._wav_metadata,selected=selected and w._wav_metadata is not None,pending_peak=worker.pending_batches_peak,dsp_peak=worker.pending_dsp_peak,gui_delay_max_ms=w.batch_queue_delay_max_ms,ok=selected and not row['errors'] and row.get('max_played',0)>=audio_rate*duration)
    finally:
     if '--controls' in sys.argv:row['ok']=not row['errors'] and set(row.get('actions',[]))=={'forward','backward','stop','replay','near_eof','eof','restart_after_eof','final_stop'}
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
    if '--qualify16' in sys.argv and not row['ok']:break
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
