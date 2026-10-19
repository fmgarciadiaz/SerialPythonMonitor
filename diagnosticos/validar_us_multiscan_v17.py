"""Live GUI multirate scan against CH1 antenna, with exact final restoration."""
import os,sys,time,json
from collections import deque
from pathlib import Path
from dataclasses import asdict
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PyQt6 import QtWidgets,QtCore
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.app import SerialMonitorWindow,OutputWorker
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.bode_calibration import instrument_identity

def main():
 require_exclusive_monitor();app=QtWidgets.QApplication([])
 callbacks=deque(maxlen=512)
 if '--scan-play' in sys.argv:
  for method_name in ('render_frame','_draw_display_frame','_deliver_worker_batch','_radio_changed'):
   original=getattr(SerialMonitorWindow,method_name)
   def timed(self,*args,_original=original,_name=method_name,**kwargs):
    began=time.monotonic()
    try:return _original(self,*args,**kwargs)
    finally:
     elapsed=time.monotonic()-began
     if elapsed>.01:callbacks.append((_name,began,elapsed))
   setattr(SerialMonitorWindow,method_name,timed)

 folder=ROOT/'diagnosticos/resultados_v17'/('us_multiscan_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 report=dict(errors=[],restored=False,ok=False);w=None;worker=None;thread=None;prior=None;gen=None
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 try:
  report['identity']=instrument_identity('1060031107')
  with Connection('1060031107') as c:
   r=OutputReceiver(c,lambda _:None);r.select(Mode.SPI);gen=r.generator().active;prior=r.config
   if gen.enabled:raise RuntimeError('Generador ocupado')
   r.wav_request();end=time.monotonic()+3
   while r.wav_pending and time.monotonic()<end:r.pump()
   if r.wav_status is None or r.wav_status.state.value not in (0,3):raise RuntimeError('WAV ocupado')
  report['prior']=dict(adc=asdict(prior),generator=asdict(gen));save()
  with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  target=Configuration(16,76226) if "--adc16" in sys.argv else Configuration(14,851063) if '--adc14' in sys.argv else Configuration(10,1250000) if '--adc10' in sys.argv else Configuration(8,1600000);w.radio_us.setChecked('--direct' not in sys.argv);w.radio_scan_threshold.setCurrentIndex(w.radio_scan_threshold.findData(10))
  w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(target.bits))
  w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(target.rate))
  worker=OutputWorker('1060031107',Mode.SPI,config=target,processing_settings=w._processing_settings(),startup_gui_ack=True,processing_backend='process');w.serial_worker=worker;w.is_running=True
  def confirmed(bits,rate):w._acquisition_confirmed(bits,rate);worker.confirm_startup(bits,rate)
  worker.acquisition_confirmed.connect(confirmed)
  worker.switching.connect(w._set_output_pending)
  worker.generator_confirmed.connect(w._generator_confirmed)
  worker.wav_confirmed.connect(w._wav_confirmed)
  worker.batch_ready.connect(lambda batch:w._deliver_worker_batch(worker,batch))
  worker.error_occurred.connect(report['errors'].append)
  if '--fft65536' in sys.argv:w.spectral.set_mode(4);w.spectral.size.setCurrentText('65536')
  if '--wide-temporal' in sys.argv:
   w.spectral.set_mode(0);w.h_scale=281250 if target.bits==10 else 360000
   w._h_time_ms=w.h_scale/target.actual_rate*1000
   w.graph_channel_actions['CH1'].setChecked(True);w.graph_channel_actions['RADIO'].setChecked(True)
  w.show()
  thread=QtCore.QThread();worker.moveToThread(thread);thread.started.connect(worker.run);worker.finished.connect(thread.quit);thread.start()
  start=time.monotonic();started=False;a0_started=False;not_before=0;pressure=deque(maxlen=2000);last_pressure=0
  repeat=5 if '--repeat-direct' in sys.argv else 1;report['scans']=[]
  if '--a0' in sys.argv:w.generator_mode.setCurrentIndex(7)
  while time.monotonic()-start<90 and thread.isRunning():
   app.processEvents();time.sleep(.002)
   now=time.monotonic()
   if now-last_pressure>.05:
    pressure.append((now,worker.pending_batches,worker.pending_dsp,worker.delivery_budget.seconds,worker.delivery_budget.bytes,now-last_pressure if last_pressure else 0));last_pressure=now
   if report['errors']:break
   if report.get('radio_play_started') and now-report['radio_play_started']>=60:break
   if time.monotonic()-start>20 and not started and not report['scans']:
    raise RuntimeError(f'Scan no inició: ADC{w.applied_configuration.bits}/{w.applied_configuration.rate}, WAVcap={w._wav_capable}, A0={w.radio_output_panel.state.text()}')
   if not started and time.monotonic()>=not_before and w.applied_configuration==target and w.sample_counter>250000 and not w.output_pending:
    w.radio_frequency.setValue(20 if '--adc16' in sys.argv else (300 if '--adc14' in sys.argv else 500) if '--direct' in sys.argv else 700 if '--adc14' in sys.argv else 1000)
    if '--radio-on' in sys.argv:
     w.radio_enabled.setChecked(True)
     if '--wide-temporal' in sys.argv and getattr(w.radio_stream,'counter',0)<80000:continue
    if '--a0' in sys.argv:
     if not a0_started:
      if not w._wav_capable:continue
      w.radio_output_panel.toggle();a0_started=True
      if w.radio_output_panel.source is None:raise RuntimeError(w.radio_output_panel.state.text())
     if w.radio_output_panel.source is None:raise RuntimeError(w.radio_output_panel.state.text())
     if not w.radio_output_panel.source.played:continue
     if '--gui-stall' in sys.argv:
      before=w.radio_output_panel.source.played
      time.sleep(.5)
      report['gui_pause_ms']=500
      report['a0_played_across_gui_pause']=[before,w.radio_output_panel.source.played]
      report['gui_pending_peak']=worker.pending_batches_peak
      report['dsp_pending_peak']=worker.pending_dsp_peak
      report['retained_payload_bytes']=worker.delivery_budget.bytes
      if w.radio_output_panel.source.error:raise RuntimeError(w.radio_output_panel.source.error)
     report['a0_played_before_scan']=w.radio_output_panel.source.played
    report['scan_frequency_before']=w.radio_frequency.value()
    w._radio_scan();started=w._radio_scan_future is not None if '--direct' in sys.argv else hasattr(w,'_radio_multiscan') and w._radio_multiscan.active
    started=started or getattr(w,'_radio_scan_a0',None) is not None
    if not started:raise RuntimeError(w.radio_status.text())
   if started and getattr(w,'_radio_scan_a0',None) is not None:continue
   if started and '--a0' in sys.argv:
    if w.radio_output_panel.source is None:raise RuntimeError('A0 no reanudó: '+w.radio_output_panel.state.text())
    if not w.radio_output_panel.source.played:continue
    report['a0_played_after_scan']=w.radio_output_panel.source.played
   if started and '--direct' in sys.argv and w._radio_scan_future is None and not report.get('radio_play_started'):
    report['scans'].append(dict(seconds=time.monotonic()-start,status=w.radio_status.text(),candidates=len(w.radio_candidates),pending_gui=worker.pending_batches,pending_dsp=worker.pending_dsp,gui_delay_max_ms=w.batch_queue_delay_max_ms))
    print('SCAN',len(report['scans']),report['scans'][-1],flush=True)
    if len(report['scans'])<repeat:
     started=False;not_before=time.monotonic()+2;continue
    report.update(scan_error=None,status=w.radio_status.text(),candidates=w.radio_candidates,scan_restored=w.applied_configuration==target,frequency_restored=w.radio_frequency.value()==report['scan_frequency_before'],radio_resumed=w.radio_enabled.isChecked(),dial_markers=len(w.radio_frequency_dial.peak_frequencies))
    if '--scan-play' in sys.argv:
     report['radio_play_started']=time.monotonic();w.radio_enabled.setChecked(True);continue
    break
   if started and hasattr(w,'_radio_multiscan') and not w._radio_multiscan.active:
    scan=w._radio_multiscan
    report.update(scan_error=scan.error,status=w.radio_status.text(),candidates=w.radio_candidates,profiles=[dict(rate=fs,count=len(peaks)) for fs,peaks in scan.scans],scan_restored=w.applied_configuration==target,frequency_restored=w.radio_frequency.value()==report['scan_frequency_before'],radio_resumed=w.radio_enabled.isChecked(),dial_markers=len(w.radio_frequency_dial.peak_frequencies))
    break
  else:raise RuntimeError('Scan no terminó')
  if '--a0' in sys.argv:w.radio_output_panel.stop(reason='Fin diagnóstico Scan A0')
  w.spectral.set_mode(4);w.resize(1400,900);w.show();app.processEvents();w.grab().save(str(folder/'us_scan.png'))
 except Exception as exc:report['error']=str(exc)
 finally:
  if worker:
   report['slow_callbacks']=list(callbacks)
   report['radio_play_counter']=getattr(w.radio_stream,'counter',0)
   report['worker_failure_snapshot']=getattr(worker,'delivery_failure_snapshot',None)
   report['pressure_trace']=list(pressure) if 'pressure' in locals() else []
   report['pending_gui_peak']=worker.pending_batches_peak;report['pending_dsp_peak']=worker.pending_dsp_peak
   report['gui_delay_max_ms']=w.batch_queue_delay_max_ms
   worker.stop()
  if thread:
   end=time.monotonic()+15
   while thread.isRunning() and time.monotonic()<end:app.processEvents();time.sleep(.002)
   if thread.isRunning():raise RuntimeError('Worker no terminó; no abrir conexión competidora')
  if w:
   if hasattr(w,'_radio_multiscan'):w._radio_multiscan.active=False;w._radio_multiscan.timer.stop()
   w.serial_worker=None;w.close()
  if prior is not None:
   with Connection('1060031107') as c:
    r=OutputReceiver(c,lambda _:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(prior);reply=r.generator(gen);before=r.decoder.pairs;end=time.monotonic()+10
    while time.monotonic()<end:r.pump()
    report['restored']=r.config==prior and reply.active==gen;report['recovery']=dict(samples=r.decoder.pairs-before,status=dict(r.decoder.status))
   report['final_identity']=instrument_identity('1060031107')
  report['ok']=report['restored'] and report.get('scan_restored',False) and report.get('frequency_restored',False) and not report.get('scan_error') and not report.get('error') and not report['errors'] and report.get('identity')==report.get('final_identity')
  save();print(json.dumps({k:v for k,v in report.items() if k not in ('candidates','pressure_trace','slow_callbacks')},indent=2),flush=True);print(folder,flush=True)
if __name__=='__main__':main()
