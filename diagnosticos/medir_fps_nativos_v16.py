"""Live Qt painting and acquisition timing; one Q reader, restores prior state."""
import sys,time,json,os,hashlib
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PyQt6 import QtCore,QtWidgets
from monitor.v16.app import SerialMonitorWindow
from monitor.v16.receiver.unoq_autoload import connect_scope
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v16.receiver.unoq_switch import Mode
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_native import PROFILES
SERIAL='1060031107';OUT=ROOT/'diagnosticos/resultados_v16'/('fps_nativos_live_remaining_20261012.json' if os.environ.get('V16_FPS_REMAINING')=='1' else 'fps_nativos_live_5khz_20261012.json')
if os.environ.get('V16_FPS_QUICK')=='1':OUT=ROOT/'diagnosticos/resultados_v16/fps_numeric_20261012.json'
if os.environ.get('V16_FPS_SLIDER')=='1':OUT=ROOT/'diagnosticos/resultados_v16/slider_live_20261012.json'
SUSTAINED=os.environ.get('V16_FPS_SUSTAINED')=='1'
if SUSTAINED:OUT=ROOT/'diagnosticos/resultados_v16'/datetime.now().strftime('fps_numeric_visible_%Y%m%d_%H%M%S.json')
SMOKE=os.environ.get('V16_FPS_SMOKE')=='1'
if SMOKE:OUT=ROOT/'diagnosticos/resultados_v16'/datetime.now().strftime('fps_paint_smoke_%Y%m%d_%H%M%S.json')
MEASURE_MS=120000 if SUSTAINED else 5000
report={'scope':'Live Q + Qt native temporal painting; 5 kHz normal generator verified in millihertz, 1 ms window, 2 s warmup + 5 s screening. No periodic raster captures during measurement.','cases':[],'errors':[]}
if SUSTAINED:
 report['scope']='Live visible Qt painting with production numeric receiver; 120 s per CH1 profile, 2 s warmup, one Q reader; prior generator state preserved.'
 report['source_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT/'monitor/v16/app.py',ROOT/'monitor/v16/receiver/unoq_config_decoder.py',ROOT/'monitor/v16/receiver/native_unpack.py')}
if SMOKE:report['scope']='5 s Qt paint instrumentation smoke on ADC8 CH1; generator preserved.'
def save():OUT.write_text(json.dumps(report,indent=2)+'\n')
with connect_scope(SERIAL) as c:
 r=OutputReceiver(c,lambda rows:None);r.select(Mode.SPI);prior=r.config;gen=r.generator().active
report['prior']={'bits':prior.bits,'rate':prior.rate,'generator':str(gen)};save()
active={'decode':[],'started':None,'case':None,'stopping':False}
import pyqtgraph as pg
original_plot=pg.PlotWidget
class PaintPlot(original_plot):
 def paintEvent(self,event):
  began=time.perf_counter()
  super().paintEvent(event)
  if active['started'] is not None:
   active['paint_times'].append((time.perf_counter()-began)*1000)
   w.paint_count+=1
pg.PlotWidget=PaintPlot
original_feed=ConfigurationDecoder.feed
def feed(self,data):
 began=time.perf_counter()
 try:return original_feed(self,data)
 finally:
  if active['started'] is not None:active['decode'].append((time.perf_counter()-began)*1000)
ConfigurationDecoder.feed=feed
class Window(SerialMonitorWindow):
 def __init__(self):
  self.paint_count=0;self.render_times=[];self.ingest_times=[];self.delays=[]
  super().__init__();self.paint_viewport=self.plot_widget.viewport()
 def render_frame(self):
  began=time.perf_counter()
  super().render_frame()
  if active['started'] is not None:self.render_times.append((time.perf_counter()-began)*1000)
 def handle_batch(self,batch):
  began=time.perf_counter();super().handle_batch(batch)
  if active['started'] is not None:
   self.ingest_times.append((time.perf_counter()-began)*1000);self.delays.append(self.batch_queue_delay_ms)
 def _on_worker_error(self,message):
  report['errors'].append(message);print('ERROR',message,flush=True);save();finish()
app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);w=Window();w.show()
class PaintFilter(QtCore.QObject):
 def eventFilter(self,obj,event):
  if event.type()==QtCore.QEvent.Type.Paint and active['started'] is not None:active['viewport_paints']+=1
  return False
paint_filter=PaintFilter();w.plot_widget.viewport().installEventFilter(paint_filter)
screened=[Configuration(14,40000),Configuration(10,909090),Configuration(8,1221374),Configuration(12,437158),Configuration(14,747663)]
profiles=[Configuration(14,40000)]+[Configuration(p['bits'],160000000//p['ticks']) for p in PROFILES]
if os.environ.get('V16_FPS_REMAINING')=='1':
 measured={(c.bits,c.rate) for c in screened}
 profiles=[Configuration(p['bits'],160000000//p['ticks']) for p in PROFILES if (p['bits'],160000000//p['ticks']) not in measured]
if os.environ.get('V16_FPS_SLIDER')=='1':profiles=[Configuration(8,1221374)]*3
if os.environ.get('V16_FPS_QUICK')=='1':profiles=[Configuration(14,40000),Configuration(8,1221374),Configuration(10,909090)]
if SUSTAINED:profiles=[Configuration(8,1221374),Configuration(10,909090)]
if SMOKE:profiles=[Configuration(8,1221374)]
position=[-1];watchdog=QtCore.QTimer();watchdog.setSingleShot(True)
def stop_done():
 if w.stop_input() is False:QtCore.QTimer.singleShot(100,stop_done)
 else:w.close();app.quit()
def finish():
 if active['stopping']:return
 active['stopping']=True;active['started']=None;watchdog.stop();stop_done()
def percentile(values,q):
 if not values:return None
 values=sorted(values);return round(values[min(len(values)-1,int((len(values)-1)*q))],3)
def complete():
 if active['stopping']:return
 elapsed=time.perf_counter()-active['started'];c=active['case']
 result={'bits':c.bits,'rate':c.rate,'channels':c.channels,'detail_slider':w.detail_slider.value(),'vertices_sent':sum(len(line.xData) for line in w.line_items.values() if line.isVisible() and line.xData is not None),'seconds':round(elapsed,3),'paint_fps':round(w.paint_count/elapsed,2),'viewport_paint_fps':round(active['viewport_paints']/elapsed,2),'plot_is_instrumented':isinstance(w.plot_widget,PaintPlot),'window_exposed':w.windowHandle().isExposed(),'window_active':w.isActiveWindow(),'render_ms_p50':percentile(w.render_times,.5),'ingest_ms_p50':percentile(w.ingest_times,.5),'decode_ms_p50':percentile(active['decode'],.5),'batch_delay_ms_p95':percentile(w.delays,.95),'batch_delay_ms_max':max(w.delays,default=0),'samples':w.sample_counter-active['samples'],'viewport_visible':w.paint_viewport.isVisible(),'window_visible':w.isVisible(),'timer_fps':round(len(w.render_times)/elapsed,2),'generator':str(w._generator_active),'paint_ms_p50':percentile(active.get('paint_times',[]),.5),'generator_frequency_hz':w._generator_active.frequency/1000,'painting_valid':w.paint_count>0 and active['viewport_paints']>0}
 report['cases'].append(result);save();print(json.dumps(result),flush=True);active['started']=None;next_case()
def measure():
 if active['stopping']:return
 if not (SUSTAINED or SMOKE) and (w._generator_active.frequency!=5000000 or not w._generator_active.enabled):
  w._on_worker_error('Generador 5 kHz no confirmado: '+str(w._generator_active));return
 if os.environ.get('V16_FPS_SLIDER')=='1':w.detail_slider.setValue((0,50,100)[position[0]])
 print('MEASURE',active['case'],flush=True)
 w.plot_widget.grab()  # Warm the native backing store before counters start.
 w.h_scale=max(8,round(active['case'].actual_rate*.001));w.paint_count=0;w.render_times=[];w.ingest_times=[];w.delays=[];active['decode']=[];active['paint_times']=[];active['viewport_paints']=0;active['samples']=w.sample_counter;active['started']=time.perf_counter();QtCore.QTimer.singleShot(MEASURE_MS,complete)
def confirmed(bits,rate):
 if active['stopping'] or active['case'] is None:return
 if (bits,rate)==(active['case'].bits,active['case'].rate):watchdog.stop();QtCore.QTimer.singleShot(2000,measure)
def next_case():
 position[0]+=1
 if position[0]>=len(profiles):finish();return
 active['case']=profiles[position[0]];print('PROFILE',active['case'],flush=True);watchdog.start(15000)
 if w.applied_configuration==active['case']:
  watchdog.stop();QtCore.QTimer.singleShot(2000,measure);return
 w.serial_worker.request_output(Mode.SPI,None,active['case'])
watchdog.timeout.connect(lambda:w._on_worker_error('Timeout esperando confirmación del perfil'))
try:
 idx=w.port_combo.findData(SERIAL)
 if idx<0:raise RuntimeError('Q no disponible en selector')
 w.port_combo.setCurrentIndex(idx)
 if not (SUSTAINED or SMOKE):w.generator_frequency.setValue(5000);w.generator_enabled.setChecked(True)
 w.raise_();w.activateWindow()
 w.connect_serial();w.serial_worker.acquisition_confirmed.connect(confirmed)
 QtCore.QTimer.singleShot(3000,next_case);QtCore.QTimer.singleShot(300000 if SUSTAINED else 150000,finish)
 print('LOOP START',flush=True);app.exec();print('LOOP END',flush=True)
finally:
 ConfigurationDecoder.feed=original_feed;pg.PlotWidget=original_plot
 if w.serial_thread is not None and w.serial_thread.isRunning():raise RuntimeError('Worker sigue activo: no iniciar segundo lector')
 try:
  with connect_scope(SERIAL) as c:
   r=OutputReceiver(c,lambda rows:None);r.select(Mode.SPI);r.configure(prior);r.generator(gen)
   report['restored']=r.config==prior and r.generator().active==gen
 except Exception as exc:report['restored']=False;report['restore_error']=str(exc)
 report['acquisition_observed']=len(report['cases'])==len(profiles) and all(case['samples']>0 for case in report['cases']) and not report['errors']
 report['painting_complete']=len(report['cases'])==len(profiles) and all(case['painting_valid'] for case in report['cases'])
 report['outcome']='acquisition_and_painting' if report['acquisition_observed'] and report['painting_complete'] and report['restored'] else 'acquisition_with_partial_painting' if report['acquisition_observed'] and report['restored'] else 'incomplete'
 save();print('RESTORED',report.get('restored'),flush=True)
