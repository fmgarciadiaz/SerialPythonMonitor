"""Physical GUI Bode self-pair CH2/CH2: isolates drawing from CH1 wiring."""
import sys,time,json,traceback
from pathlib import Path
from dataclasses import asdict
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.v17.app import SerialMonitorWindow,OutputWorker,QtWidgets,QtCore
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.board_owner import board_owner
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.bode_calibration import instrument_identity

def main():
 app=QtWidgets.QApplication([]);folder=ROOT/'diagnosticos/resultados_bode'/('gui_v17_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir(parents=True)
 report={'cases':[],'errors':[],'restored':False};prior=None;worker=thread=w=None
 import monitor.v17.bode as bode_module
 original_transfer=bode_module.tone_transfer
 def traced_transfer(t,x,y,frequency):
  np.save(folder/f'tone_{frequency}_capture.npy',np.column_stack((t,x,y)))
  return original_transfer(t,x,y,frequency)
 bode_module.tone_transfer=traced_transfer
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 sys.excepthook=lambda kind,value,tb:report['errors'].append(''.join(traceback.format_exception(kind,value,tb)))
 with board_owner('1060031107','Bode GUI CH2/CH2 diagnóstico'):
  require_exclusive_monitor()
  try:
   with Connection('1060031107') as c:
    r=OutputReceiver(c,lambda _:None);r.decoder.numeric=True;r.select(0);g=r.generator().active
    if g.enabled:raise RuntimeError('Generator occupied')
    prior={'adc':asdict(r.config),'generator':asdict(g)};r.configure(Configuration(14,40000))
   report['identity_before']=instrument_identity('1060031107');save()
   with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
   w.generator_amplitude.setValue(1);w.generator_offset.setValue(1.65);w._generator_timer.stop()
   cfg=Configuration(14,40000)
   w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(14));w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(40000));w._auto_apply_timer.stop()
   worker=OutputWorker('1060031107',0,config=cfg,processing_settings=w._processing_settings(),startup_gui_ack=True,processing_backend='process');w.serial_worker=worker;w.is_running=True;w.spectral.set_mode(3);w.show()
   def confirm(bits,rate):w._acquisition_confirmed(bits,rate);worker.confirm_startup(bits,rate)
   worker.acquisition_confirmed.connect(confirm);worker.generator_confirmed.connect(w._generator_confirmed);worker.wav_confirmed.connect(w._wav_confirmed);worker.error_occurred.connect(report['errors'].append);worker.batch_ready.connect(lambda b:w._deliver_worker_batch(worker,b))
   thread=QtCore.QThread();worker.moveToThread(thread);thread.started.connect(worker.run);worker.finished.connect(thread.quit);thread.start()
   end=time.monotonic()+15
   while time.monotonic()<end and not (w._generator_state_known and w.applied_configuration==cfg):app.processEvents();time.sleep(.002)
   for index in (0,1,2):
    w.spectral.bode.tabs.setCurrentIndex(index);p=w.spectral.bode.panels[index]
    p.reference_channel.setCurrentText('CH2');p.response_channel.setCurrentText('CH2');p.start.setValue(20);p.end.setValue(1000)
    if index==0:
     p.points.setValue(2);p.settle.setValue(int(sys.argv[sys.argv.index('--settle-ms')+1]) if '--settle-ms' in sys.argv else 200);p.cycles.setValue(4)
    else:p.capture.setValue(.5);p.averages.setValue(1);p.width.setValue(int(sys.argv[sys.argv.index('--pulse-us')+1]) if '--pulse-us' in sys.argv else 1000)
    end=time.monotonic()+2
    while time.monotonic()<end:app.processEvents();time.sleep(.002)
    w._auto_apply_timer.stop();w._generator_timer.stop();p.begin();start=time.monotonic()
    while p.active and time.monotonic()-start<35 and not report['errors']:app.processEvents();time.sleep(.002)
    data=np.asarray(p.result);curves=[]
    for curve in p.curve_sets[0]:
     x,y=curve.getData();curves.append({'visible':curve.isVisible(),'points':len(x) if x is not None else 0,'finite':int(np.isfinite(y).sum()) if y is not None else 0})
    row={'method':index,'status':p.status.text(),'active':p.active,'result_points':len(data),'valid_gain':int(np.isfinite(data[:,1]).sum()) if len(data) else 0,'curves':curves,'invalid_points':getattr(p,'invalid_points',None)}
    row['pair']=p.pair()
    row['settle_ms']=p.settle.value()
    if index!=0:row['pulse_width_us']=p.width.value()
    row['generator']=asdict(p.config)
    if p.buffer:
     captured=np.asarray(p.buffer);np.save(folder/f'method{index}_capture.npy',captured)
     row['reference_vpp']=float(np.ptp(captured[:,1]))
     row['reference_mean']=float(np.mean(captured[:,1]))
    report['cases'].append(row);print('CASE',json.dumps(row),flush=True);w.grab().save(str(folder/f'method{index}.png'));save()
    if p.active:p.cancel('Timeout diagnóstico')
   report['ok']=not report['errors'] and all(c['valid_gain']>0 and all(x['visible'] and x['finite']>0 for x in c['curves']) for c in report['cases'])
  finally:
   bode_module.tone_transfer=original_transfer
   if w:w.spectral.bode.cancel('Fin diagnóstico')
   if worker:worker.stop()
   if thread:
    end=time.monotonic()+15
    while thread.isRunning() and time.monotonic()<end:app.processEvents();time.sleep(.002)
    if thread.isRunning():raise RuntimeError('Worker not stopped')
   if w:w.serial_worker=None;w.close()
   if prior:
    with Connection('1060031107') as c:
     r=OutputReceiver(c,lambda _:None);r.decoder.numeric=True;r.select(0);r.configure(Configuration(14,40000));r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']));report['restored']=asdict(r.config)==prior['adc'] and asdict(r.generator().active)==prior['generator'];end=time.monotonic()+5
     while time.monotonic()<end:r.pump()
     report['recovery']=r.decoder.status
    report['identity_after']=instrument_identity('1060031107')
   save();print('REPORT',folder/'report.json',flush=True)
if __name__=='__main__':main()
