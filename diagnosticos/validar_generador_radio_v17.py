"""Actual RADIO DSP -> live A0 streaming/retuning/volume; no firmware changes."""
import sys,json,time,traceback,struct,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dataclasses import asdict
from collections import deque
from unittest.mock import patch
from monitor.v17.qt_environment import prepare_platform_plugins
prepare_platform_plugins()
from PyQt6 import QtCore,QtWidgets
from monitor.v17.board_owner import board_owner
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.app import SerialMonitorWindow,OutputWorker


def main(owner_context=None):
 duration=float(sys.argv[sys.argv.index('--seconds')+1]) if '--seconds' in sys.argv else 20
 audio_rate=int(sys.argv[sys.argv.index('--audio-rate')+1]) if '--audio-rate' in sys.argv else 40000
 report={'ok':False,'restored':False,'errors':[],'samples':0,'wav_states':[]};receivers=[]
 refill_ring=deque(maxlen=20000);deferred='--defer-diagnostics' in sys.argv
 trace_refill='--refill-ring' in sys.argv
 original_try_codes=None
 report['requested_audio_seconds']=duration
 report['source_hashes']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('monitor/v17/radio_output.py','monitor/v17/radio_output_panel.py','monitor/v17/receiver/unoq_config_receiver.py','monitor/v17/radio_loop_guard.py','monitor/v17/processing.py','monitor/v17/radio_am.py','monitor/v17/app.py')}
 from monitor.v17.radio_output import RadioDacSource
 if trace_refill:
  original_try_codes=RadioDacSource.try_codes
  def traced_codes(source,start,end,levels=None):
   began=time.monotonic();result=original_try_codes(source,start,end,levels)
   if result is None:
    reason='closed' if source.closed else 'error' if source.error else 'audio' if source._available<end-start else 'prebuffer'
    refill_ring.append(('codes_none',began,time.monotonic(),reason,start,end,source._available,source._position))
   return result
  RadioDacSource.try_codes=traced_codes
 probe=RadioDacSource(rate=audio_rate)
 report['audio_transport']={'rate':probe.rate,'poll_interval':probe.poll_interval,'credits':probe.credit_window,'chunk_interval':probe.chunk_interval,'chunk_burst':probe.chunk_burst,'prebuffer_samples':probe.prebuffer_samples}
 class MeasuredWorker(OutputWorker):
  def _feed_radio_output(self,batch):
   result=getattr(batch,'processing',None)
   with self._batch_lock:
    active=self.radio_output_source is not None;settings=self.processing_settings
   if active and result is not None and settings is not None and result['generation']!=settings.generation:
    from monitor.v17.processing import same_audio_continuity
    same_session=getattr(batch,'radio_output_session',None)==self._radio_output_session
    recovered=same_session and same_audio_continuity(result['settings'],settings)
    prefix='preserved_generation_audio' if recovered else 'old_generation_audio'
    report[prefix+'_batches']=report.get(prefix+'_batches',0)+1
    audio=result.get('audio')
    report[prefix+'_samples']=report.get(prefix+'_samples',0)+(len(audio) if audio is not None else 0)
   began=time.monotonic()
   outcome=super()._feed_radio_output(batch)
   if trace_refill and active:
    with self._batch_lock:source=self.radio_output_source
    if source is not None:
     audio=result.get('audio') if result is not None else None
     refill_ring.append(('feed',began,time.monotonic(),len(audio) if audio is not None else 0,source._available,source.played,source.accepted,source._position,self.pending_dsp))
   return outcome
 class MeasuredReceiver(OutputReceiver):
  def __init__(self,*args,**kwargs):
   super().__init__(*args,**kwargs)
   receivers.append(self)
   self.last_wav_seen=None;self.recent=deque(maxlen=256);self.trace=deque(maxlen=3000)
   self.last_pump=None;self.seen_produced=None
  def _trace_transport(self,stage,start,end,rid=None,cpu_seconds=None,process_cpu_seconds=None):
   self.trace.append((stage,start,end,rid))
   maxima=report.setdefault('transport_max_ms',{})
   maxima[stage]=max(maxima.get(stage,0),(end-start)*1000)
   if stage=='ack' and rid in self.wav_inflight:
    latency=(end-self.wav_inflight[rid][0])*1000
    maxima['ack_latency']=max(maxima.get('ack_latency',0),latency)
  def pump(self):
   now=time.monotonic()
   if self.last_pump is not None:report['pump_gap_max_ms']=max(report.get('pump_gap_max_ms',0),(now-self.last_pump)*1000)
   self.last_pump=now
   result=super().pump()
   status=self.wav_status
   if status is not None and status.request_id!=self.last_wav_seen:
    self.last_wav_seen=status.request_id
    self.recent.append((time.monotonic(),int(status.state),status.free_blocks,status.accepted,status.played))
   if self.decoder.status:
    status=self.decoder.status
    if status.get('queue_peak',0)>report.get('adc_queue_peak',0):
     report.setdefault('adc_peak_events',[]).append({'time':time.monotonic(),'peak':status['queue_peak'],'wav_played':getattr(self.wav_status,'played',None),'wav_state':int(self.wav_status.state) if self.wav_status else None})
    report['adc_queue_peak']=max(report.get('adc_queue_peak',0),status.get('queue_peak',0))
    report['adc_status']=status.copy()
    token=(status.get('epoch'),status.get('produced'))
    if self.config._native and 'send_ticks' in status and token!=self.seen_produced:
     self.seen_produced=token
     groups=['send_statistics']
     if self.wav_status is not None and int(self.wav_status.state)==2:groups.append('joint_send_statistics')
     for group in groups:
      stats=report.setdefault(group,{'sum_ticks':0,'observations':0,'minimum_slack_ticks':0xffffffff})
      stats['sum_ticks']+=status['send_ticks'];stats['observations']+=1
      stats['minimum_slack_ticks']=min(stats['minimum_slack_ticks'],status['slack_ticks'])
      stats['mean_margin']=1-stats['sum_ticks']/stats['observations']/(self.config.node_pairs*self.config.period)
   # Keep capture bookkeeping bounded; copying the 3000-entry trace for
   # every wire frame can itself delay the audio being measured.
   if not deferred and now-getattr(self,'last_trace_snapshot',0)>=1:
    self.last_trace_snapshot=now
    report['transport_recent']=list(self.trace);report['wav_recent']=list(self.recent)
   return result
  def service_wav(self):
   source=self.wav_codes
   before=getattr(self,'ring_sent',0)
   result=super().service_wav()
   now=time.monotonic()
   if trace_refill and source is not None and getattr(source,'radio_audio',False) and now-getattr(self,'ring_service_at',0)>=.005:
    self.ring_service_at=now;s=self.wav_status
    if s is not None:
     pending=self.wav_pending
     reason=('sent' if getattr(self,'ring_sent',0)!=before else
             'control_pending' if pending and any(v[1]!=13 for v in self.wav_inflight.values()) else
             'credits' if len(self.wav_inflight)>=getattr(source,'credit_window',30) or s.free_blocks<=len(self.wav_inflight) else
             'tokens' if getattr(self,'wav_chunk_tokens',0)<1 else 'target_or_audio')
     refill_ring.append(('service',now,reason,int(s.state),s.accepted,s.played,s.free_blocks,len(self.wav_inflight),getattr(self,'wav_chunk_tokens',None),source._available,self.wav_next_offset))
   return result
  def _wav_send(self,frame):
   kind=struct.unpack_from('<H',frame,6)[0]
   self.ring_sent=getattr(self,'ring_sent',0)+int(kind==13)
   if trace_refill and kind==13:refill_ring.append(('chunk',time.monotonic(),self.wav_next_offset,len(self.wav_inflight)))
   name='chunks' if kind==13 else f'op_{frame[20]}'
   counts=report.setdefault('wav_commands',{});counts[name]=counts.get(name,0)+1
   return super()._wav_send(frame)
 import monitor.v17.app as app_module
 app_module.OutputReceiver=MeasuredReceiver
 folder=ROOT/'diagnosticos/resultados_v17'/('generador_radio_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);report['qt_platform']=app.platformName()
 worker=thread=w=None;prior=None
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 def exception(kind,value,tb):
  detail=''.join(traceback.format_exception(kind,value,tb));report['errors'].append(detail);save();print(detail,flush=True)
 sys.excepthook=exception
 with (owner_context if owner_context is not None else board_owner('1060031107','validar Generador Radio')):
  require_exclusive_monitor()
  try:
   with Connection('1060031107') as c:
    r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);g=r.generator().active
    if g.enabled:raise RuntimeError('Generador ocupado')
    prior={'adc':asdict(r.config),'generator':asdict(g)};report['prior']=prior
    r.configure(Configuration(14,40000))
   report['identity_before']=instrument_identity('1060031107');save()
   with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
   w.generator_mode.setCurrentIndex(7)
   w.radio_output_rate.setCurrentIndex(w.radio_output_rate.findData(audio_rate))
   bandwidth=int(sys.argv[sys.argv.index('--bandwidth')+1]) if '--bandwidth' in sys.argv else 8000
   index=w.radio_bandwidth.findData(bandwidth)
   if index<0:raise ValueError('Ancho de banda RADIO no soportado')
   w.radio_bandwidth.setCurrentIndex(index);report['radio_bandwidth']=bandwidth
   if '--filter-input' in sys.argv:
    w.filter_source.setCurrentText('RADIO')
    w.filter_preset.setCurrentIndex(w.filter_preset.findData('reject_50'))
    w.radio_output_panel.input_source.setCurrentText('FILTER')
    report['output_input']='FILTER';report['filter_preset']='reject_50'
   else:report['output_input']='RADIO'
   # Fixed real RF input and existing ADC firmware. No synthetic replacement.
   bits=int(sys.argv[sys.argv.index('--bits')+1]) if '--bits' in sys.argv else 8 if '--fast' in sys.argv or '--rate' in sys.argv else 14
   rate=int(sys.argv[sys.argv.index('--rate')+1]) if '--rate' in sys.argv else {8:1600000,10:1167883,12:981595,14:599250,16:76226}[bits]
   config=Configuration(bits,rate)
   from monitor.v17.radio_am import radio_tuning_max
   tuned=min(550 if bits==8 else 20,radio_tuning_max(config.actual_rate)*.00065)
   retuned=min(tuned+5,radio_tuning_max(config.actual_rate)*.0009)
   w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(config.bits))
   if w.config_rate_combo.findData(config.rate)<0:
    w.config_rate_combo.addItem(f'{config.rate} Hz (diagnóstico)',config.rate)
   w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(config.rate))
   w.radio_enabled.setChecked(True)
   worker=MeasuredWorker('1060031107',Mode.SPI,config=config,processing_settings=w._processing_settings(),startup_gui_ack=True,processing_backend='process')
   # Warm the process while the Q remains at low load; exclude cold filesystem
   # and spawn stalls from the sustained qualification, but retain failures.
   worker._ensure_process().result(timeout=45)
   report['dsp_prewarmed']=True
   w.serial_worker=worker;w.is_running=True;w.show()
   def confirmed(bits,rate):w._acquisition_confirmed(bits,rate);worker.confirm_startup(bits,rate)
   worker.acquisition_confirmed.connect(confirmed)
   worker.generator_confirmed.connect(w._generator_confirmed)
   def wav(status):
    if not report['wav_states'] or report['wav_states'][-1]['state']!=int(status.state):
     report['wav_states'].append({'state':int(status.state),'reason':int(status.reason),'played':int(status.played),'accepted':int(status.accepted),'queue_slots':getattr(status,'queue_slots',16)})
    if int(status.state)==2:report['max_played']=max(report.get('max_played',0),int(status.played))
    if int(status.state) in (4,5) or status.reason:report['errors'].append(f'WAV {status.state}/{status.reason}')
    w._wav_confirmed(status)
   worker.wav_confirmed.connect(wav)
   def collect(batch):report['samples']+=len(batch);w._deliver_worker_batch(worker,batch)
   worker.batch_ready.connect(collect);worker.error_occurred.connect(report['errors'].append)
   thread=QtCore.QThread();worker.moveToThread(thread);thread.started.connect(worker.run);worker.finished.connect(thread.quit)
   thread.start();start=time.monotonic();wall_start=time.time();played_at=None;changed=set();source=None
   while time.monotonic()-start<duration+30 and thread.isRunning():
    app.processEvents();time.sleep(.001)
    if played_at is None and w._wav_capable and w.applied_configuration==config:
     w.radio_frequency.setValue(tuned);w.radio_output_panel.toggle()
     source=w.radio_output_panel.source
     if source is not None:
      played_at=time.monotonic();report['play_started_seconds']=played_at-start
      report['audio_source_type']=type(source).__name__
      report['audio_transport'].update(chunk_burst=source.chunk_burst,chunk_interval=source.chunk_interval)
    if played_at is not None:
     if report['errors'] or (source is not None and source.error):break
     elapsed=time.monotonic()-played_at
     if '--gui-stress' in sys.argv:
      epoch=int(elapsed//10)
      if epoch>0 and epoch!=report.get('gui_epoch',0):
       report['gui_epoch']=epoch;pause=(.05,.1,.25,.5)[(epoch-1)%4]
       before=source.played;time.sleep(pause)
       report.setdefault('gui_pauses',[]).append(dict(seconds=pause,played_before=before,played_after=source.played,pending=worker.pending_batches,dsp_pending=worker.pending_dsp,bytes=worker.delivery_budget.bytes))
     report['dsp_pending_peak']=worker.pending_dsp_peak
     report['retained_bytes_peak']=max(report.get('retained_bytes_peak',0),worker.delivery_budget.bytes)
     if elapsed-getattr(w,'_audit_saved',0)>15:
      w._audit_saved=elapsed;report['elapsed_audio_seconds']=elapsed
      if not deferred:save()
      print(f'LIVE audio={elapsed:.0f}s played={source.played} pendingGUI={worker.pending_batches} pendingDSP={worker.pending_dsp}',flush=True)
     if '--gain-stress' in sys.argv:
      step=int(elapsed//2)
      if step!=report.get('gain_step'):
       report['gain_step']=step;w.radio_gain.setValue(5 if step%2 else 2)
     if '--auto-gain' in sys.argv and 'auto_gain' not in changed:
      w.radio_auto_gain.setChecked(True);changed.add('auto_gain')
     if elapsed>8 and 'volume' not in changed:w.radio_output_panel.volume.setValue(50);changed.add('volume')
     if elapsed>12 and 'retune' not in changed:w.radio_frequency.setValue(retuned);changed.add('retune')
     if not deferred and elapsed>17 and 'snapshot' not in changed:
      w.grab().save(str(folder/'radio_mode.png'));changed.add('snapshot')
     if elapsed>duration and 'stop' not in changed:w.radio_output_panel.stop();changed.add('stop')
     if elapsed>duration+3 and not w._wav_active:break
   report['wall_monotonic_drift_seconds']=time.time()-wall_start-(time.monotonic()-start)
   if abs(report['wall_monotonic_drift_seconds'])>2:report['errors'].append('Discontinuidad del reloj del host')
   report.update(changed=sorted(changed),pending_peak=worker.pending_batches_peak,
     max_queue_delay_ms=w.batch_queue_delay_max_ms,radio_enabled_after_stop=w.radio_enabled.isChecked(),
     output_source_detached=w.radio_output_panel.source is None,adc=asdict(w.applied_configuration))
   if source is not None:report.update(retunes=source.retunes,source_error=source.error,clipped=source.clipped_samples,source_buffer_minimum=source.buffer_minimum)
   report['ok']=(not report['errors'] and report.get('max_played',0)>audio_rate*max(10,duration-4) and report.get('source_error') is None and report['output_source_detached'] and 'stop' in changed and report.get('retunes',0)>=1 and w.applied_configuration==config)
  except BaseException as exc:
   report['errors'].append(repr(exc));report['traceback']=traceback.format_exc();save();raise
  finally:
   if worker:worker.stop()
   if thread:
    deadline=time.monotonic()+15
    while thread.isRunning() and time.monotonic()<deadline:app.processEvents();time.sleep(.001)
    if thread.isRunning():raise RuntimeError('Worker did not exit; no competing connection opened')
   if receivers:
    report['transport_recent']=list(receivers[-1].trace);report['wav_recent']=list(receivers[-1].recent)
   if w:w.serial_worker=None;w.close()
   if prior is not None:
    with Connection('1060031107') as c:
     r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000))
    report['identity_after']=instrument_identity('1060031107');assert report['identity_after']==report['identity_before']
    with Connection('1060031107') as c:
     r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
     final={'adc':asdict(r.config),'generator':asdict(r.generator().active)};before=r.decoder.pairs;end=time.monotonic()+10
     while time.monotonic()<end:r.pump()
     report.update(restored=final==prior,recovery={'samples':r.decoder.pairs-before,'status':r.decoder.status})
   if original_try_codes is not None:RadioDacSource.try_codes=original_try_codes
   if trace_refill:report['refill_ring_schema']='feed: start,end,audio_len,host,played,accepted,rendered,dsp; codes_none: start,end,reason,offset,endoffset,host,rendered; service: time,reason,state,accepted,played,free,inflight,tokens,host,next; chunk: time,next,inflight';report['refill_ring']=list(refill_ring)
   report['diagnostics_deferred']=deferred
   save();print(json.dumps({k:v for k,v in report.items() if k not in ('transport_recent','wav_recent','refill_ring')},indent=2),flush=True)
 return report,folder
if __name__=='__main__':main()
