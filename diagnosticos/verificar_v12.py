"""Coordinator-only GUI smoke with real Q acquisition, trigger, SINGLE and CSV."""
import argparse,csv,json,sys,time
from dataclasses import asdict
import numpy as np
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
HERE=ROOT/'capturas/validacion_v12';HERE.mkdir(parents=True,exist_ok=True)
from PyQt5 import QtWidgets,QtTest
from monitor.historico.v12.app import SerialMonitorWindow
from monitor.historico.v12.receiver.unoq_usb import Connection
from monitor.historico.v12.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v12.receiver.unoq_generator import GeneratorConfig
folder=HERE/datetime.now().strftime('%Y%m%d_%H%M%S_%f');folder.mkdir()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fft-size',type=int,choices=(256,512,1024,2048,4096,8192),default=2048)
args=parser.parse_args()
app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
report={'kind':'monitor_v12_real','passed':False,'errors':[]}
w=None;saved_generator=None
try:
 with Connection('1060031107') as connection:
  receiver=OutputReceiver(connection,lambda samples:None)
  try:
   saved_generator=receiver.generator().active
   stimulus=GeneratorConfig(1,1,0,2000000,2000000,500,3500,1000)
   receiver.generator(stimulus)
   report['stimulus']=asdict(stimulus)
  finally:receiver.close()
 QtWidgets.QMessageBox.critical=lambda parent,title,text:report['errors'].append(title+': '+text)
 QtWidgets.QMessageBox.warning=lambda parent,title,text:report['errors'].append(title+': '+text)
 w=SerialMonitorWindow();w.resize(1500,900);w.show()
 w.spectral.size.setCurrentText(str(args.fft_size))
 report['fft_size']=args.fft_size
 queue_delays={0:[],1:[],2:[]};render_times={1:[],2:[]};mode_clock=[None,time.monotonic()]
 original_render=w.spectral.render
 def measured_render():
  mode=w.spectral.mode;started=time.perf_counter();original_render()
  elapsed=(time.perf_counter()-started)*1000
  if mode in render_times and elapsed>.1 and time.monotonic()-mode_clock[1]>=1:
   render_times[mode].append(elapsed)
 w.render_timer.timeout.disconnect(w.spectral.render)
 w.render_timer.timeout.connect(measured_render)
 original_handle=w.handle_batch
 def measured_handle(batch):
  mode=w.spectral.mode;now=time.monotonic()
  if mode!=mode_clock[0]:mode_clock[:]=[mode,now]
  published_at=getattr(batch,'published_at',None)
  if published_at is not None and now-mode_clock[1]>=1 and mode in queue_delays:
   queue_delays[mode].append(max(0.,(now-published_at)*1000))
  original_handle(batch)
 w.handle_batch=measured_handle
 w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(125000))
 index=w.port_combo.findData('1060031107')
 if index<0:raise RuntimeError('Q no encontrado')
 w.port_combo.setCurrentIndex(index);w.connect_serial()
 def wait(seconds):
  until=time.monotonic()+seconds
  while time.monotonic()<until:
   QtTest.QTest.qWait(20)
   if report['errors']:raise RuntimeError(report['errors'][-1])
 wait(5)
 if w.applied_configuration.rate!=125000:raise RuntimeError('Perfil no aplicado')
 w.trigger_checkbox.setChecked(False);w.render_frame()
 x,y=w.line_items['V_IN'].getData()
 if x is None or len(x)<50:raise RuntimeError('Grafico sin datos')
 report.update(configuration={'rate':w.applied_configuration.rate,'bits':w.applied_configuration.bits},graph_points=len(x),samples=w.sample_counter)
 if not w.grab().save(str(folder/'grafico.png')):raise RuntimeError('No se pudo guardar grafico.png')
 w._create_log_filename=lambda:folder/'captura.csv';w.start_recording();wait(4);w.stop_recording()
 for mode,name in ((1,'fft'),(2,'heatmap')):
  w.spectral.set_mode(mode);wait(1)
  first=w.spectral.last_end;sample_start=w.sample_counter
  wait(3)
  last=w.spectral.last_end
  if first is None or last is None or last<=first or w.sample_counter<=sample_start:raise RuntimeError(name+' no avanza con muestras reales')
  if mode==1:
   frequencies,amplitudes=w.spectral.curves[0].getData()
   if frequencies is None or amplitudes is None or len(frequencies)<2 or not np.isfinite(amplitudes).all():raise RuntimeError('FFT sin datos finitos')
   details={'bins':len(frequencies)}
  else:
   raster=w.spectral.images[0].image
   if raster is None or np.count_nonzero(np.any(np.isfinite(raster),axis=0))<2:raise RuntimeError('Heatmap sin columnas de datos')
   details={'finite_columns':int(np.count_nonzero(np.any(np.isfinite(raster),axis=0))),'frames':len(w.spectral.frames)}
  report[name]=dict(details,validated=True,first_end=int(first),last_end=int(last),new_samples=w.sample_counter-sample_start)
  if not w.grab().save(str(folder/(name+'.png'))):raise RuntimeError('No se pudo guardar '+name+'.png')
 w.spectral.set_mode(0);w.render_frame()
 recent=list(w.series['V_IN'])[-1500:]
 if not recent:raise RuntimeError('Sin datos V_IN para SINGLE')
 report['v_in_range']={'min':float(min(recent)),'max':float(max(recent)),'vpp':float(max(recent)-min(recent)),'samples':len(recent)}
 if report['v_in_range']['vpp']<1:raise RuntimeError('Estimulo insuficiente para SINGLE físico')
 w.trigger_source_combo.setCurrentText('V_IN');w.auto_center_trigger_level();w.on_trigger_mode_changed('Normal');w.arm_single_shot()
 report['trigger_level']=w.trigger_level
 wait(3)
 if w.is_running or w.single_shot_armed or w.frozen_frame is None:raise RuntimeError('SINGLE no capturo; comprobar estimulo V_IN (rango informado)')
 report.update(single_captured=True,queue_delay_ms=w.batch_queue_delay_ms,queue_delay_max_ms=w.batch_queue_delay_max_ms,timed_batches=w.timed_batch_count)
 if not w.grab().save(str(folder/'single.png')):raise RuntimeError('No se pudo guardar single.png')
 w.stop_input()
except Exception as exc:report['errors'].append(str(exc))
finally:
 if w is not None:w.stop_input();w.close()
 # Analyze the closed CSV after disconnecting, even if a display/SINGLE check failed.
 if (folder/'captura.csv').exists():
  try:
   count=0;prev=None
   with (folder/'captura.csv').open() as stream:
    for row in csv.DictReader(stream):
     current=(int(float(row['Muestra'])),int(float(row['Tiempo_us'])))
     if prev and ((current[0]-prev[0])&0xffffffff,(current[1]-prev[1])&0xffffffff)!=(1,8):raise RuntimeError('CSV discontinuo')
     prev=current;count+=1
   report['csv_rows']=count
   if count<350000:raise RuntimeError('CSV insuficiente')
   report['csv_validated']=True
  except Exception as exc:report['errors'].append(str(exc));report['csv_validated']=False
 if saved_generator is not None:
  try:
   with Connection('1060031107') as connection:
    receiver=OutputReceiver(connection,lambda samples:None)
    try:
     receiver.generator(saved_generator)
     report['generator_after']=asdict(receiver.generator().active)
     report['generator_restored']=report['generator_after']==asdict(saved_generator)
     if not report['generator_restored']:raise RuntimeError('Generador no restaurado')
    finally:receiver.close()
  except Exception as exc:report['errors'].append('Restauracion: '+str(exc))
 if w is not None:
  report['render_by_mode']={('vt','fft','heatmap')[mode]:{'updates':len(values),'median_ms':float(np.median(values)),'p95_ms':float(np.percentile(values,95)),'max_ms':float(max(values))} for mode,values in render_times.items() if values}
  report['queue_by_mode']={('vt','fft','heatmap')[mode]:{
   'batches':len(values),'median_ms':float(np.median(values)),
   'p95_ms':float(np.percentile(values,95)),'max_ms':float(max(values))}
   for mode,values in queue_delays.items() if values}
 report['passed']=not report['errors'] and report.get('csv_validated',False) and report.get('single_captured',False) and all(report.get(name,{}).get('validated',False) for name in ('fft','heatmap'))
 (folder/'informe.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));print(folder)
raise SystemExit(0 if report['passed'] else 1)
