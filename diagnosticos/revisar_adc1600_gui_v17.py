"""Reproduce real V17 worker/GUI delivery without replacing firmware."""
import sys,time,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from unittest.mock import patch
from monitor.v17.qt_environment import prepare_platform_plugins
prepare_platform_plugins()
from PyQt6 import QtWidgets,QtCore
import pyqtgraph as pg
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_acquisition import Configuration
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor

def main():
 require_exclusive_monitor()
 report={'errors':[],'statuses':[],'paints':0,'batches':0,'samples':0,'restored':False}
 path=ROOT/('diagnosticos/resultados_v17/adc1600_startup_baseline.json' if '--baseline-settle' in sys.argv else 'diagnosticos/resultados_v17/adc1600_startup_optimized.json' if '--startup-benchmark' in sys.argv else 'diagnosticos/resultados_v17/adc1600_gui_generator_preserved.json' if '--preserve-generator' in sys.argv else 'diagnosticos/resultados_v17/adc1600_gui_review_visible.json' if '--visible' in sys.argv else 'diagnosticos/resultados_v17/adc1600_gui_review.json')
 prior=generator=None;worker=thread=w=None
 app=QtWidgets.QApplication([])
 report['qt_platform']=app.platformName()
 oldpaint=pg.PlotWidget.paintEvent
 def paint(widget,event):
  oldpaint(widget,event);report['paints']+=1
  if report['samples'] and 'first_data_paint_seconds' not in report:report['first_data_paint_seconds']=time.monotonic()-report['started_at']
 pg.PlotWidget.paintEvent=paint
 def exception(kind,value,tb):
  report['errors'].append(''.join(traceback.format_exception(kind,value,tb)));print(report['errors'][-1],flush=True)
 sys.excepthook=exception
 try:
  with Connection('1060031107') as c:
   r=OutputReceiver(c,lambda b:None);r.select(Mode.SPI);prior=r.config;generator=r.generator().active
   if generator.enabled:raise RuntimeError('Generador ocupado; no se inicia ensayo')
   if '--preserve-generator' in sys.argv:
    from monitor.v17.receiver.unoq_generator import GeneratorConfig
    desired_generator=GeneratorConfig(wave=1,enabled=0,frequency=1234000,final_frequency=2345000,low=0,high=1024,duration=2345)
    r.generator(desired_generator)
   r.configure(Configuration(8,1403508))
   until=time.monotonic()+2
   while time.monotonic()<until:r.pump()
   report['entry_rate']=1403508
  from monitor.v17.app import SerialMonitorWindow,OutputWorker
  if '--baseline-settle' in sys.argv:
   from contextlib import contextmanager
   from monitor.v17.receiver.unoq_autoload import connect_scope as original_connect
   @contextmanager
   def baseline_connect(*args,**kwargs):
    with original_connect(*args,**kwargs) as connection:
     connection.scope_restarted=True
     yield connection
   from monitor.v17 import app as module
   module.connect_scope=baseline_connect
  with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  config=Configuration(8,1600000)
  worker=OutputWorker('1060031107',Mode.SPI,config=config,autoload='--startup-benchmark' in sys.argv,processing_settings=w._processing_settings(),startup_gui_ack=True,processing_backend='process')
  w.serial_worker=worker;w.is_running=True;w.show()
  def confirmed(bits,rate):
   w._acquisition_confirmed(bits,rate);worker.confirm_startup(bits,rate)
  worker.acquisition_confirmed.connect(confirmed)
  def generator_confirmed(reply):
   w._generator_confirmed(reply)
   if '--preserve-generator' in sys.argv and report.get('monitoring_generator',False) and reply.active!=desired_generator:
    report['errors'].append('Configuración del generador alterada: '+repr(reply.active))
  worker.generator_confirmed.connect(generator_confirmed)
  def collect(batch):
   if 'first_samples_seconds' not in report:report['first_samples_seconds']=time.monotonic()-report['started_at']
   report['samples']+=len(batch);report['batches']+=1;w._deliver_worker_batch(worker,batch)
  worker.batch_ready.connect(collect)
  worker.status_changed.connect(lambda s:report['statuses'].append(s))
  worker.error_occurred.connect(lambda s:report['errors'].append(s))
  thread=QtCore.QThread();worker.moveToThread(thread);thread.started.connect(worker.run);worker.finished.connect(thread.quit)
  report['monitoring_generator']=True
  report['started_at']=time.monotonic()
  thread.start();start=time.monotonic();last=0;requested=set()
  while time.monotonic()-start<(20 if '--startup-benchmark' in sys.argv else 40) and thread.isRunning():
   app.processEvents();time.sleep(.001)
   for second,rate in (() if '--startup-benchmark' in sys.argv else ((12,1403508),(16,1600000),(27,1403508),(31,1600000))):
    if time.monotonic()-start>=second and second not in requested:
     worker.request_output(Mode.SPI,None,Configuration(8,rate));requested.add(second)
   if time.monotonic()-start>last+10:
    last=time.monotonic()-start;print('GUI',round(last),report['samples'],report['paints'],report['errors'],flush=True)
  if '--preserve-generator' in sys.argv:
   report['generator_controls_preserved']=(w._generator_active==desired_generator and abs(w.generator_amplitude.value()-1024*3.3/4095)<.01 and abs(w.generator_frequency.value()-1234)<.01)
   if not report['generator_controls_preserved']:report['errors'].append('Controles del generador alterados')
  report.update(seconds=time.monotonic()-start,pending_peak=worker.pending_batches_peak,queue_delay_max_ms=w.batch_queue_delay_max_ms,exposed=w.windowHandle().isExposed())
 finally:
  report['monitoring_generator']=False
  if worker:worker.stop()
  if thread:
   deadline=time.monotonic()+15
   while thread.isRunning() and time.monotonic()<deadline:app.processEvents();time.sleep(.001)
   if thread.isRunning():raise RuntimeError('Worker no terminó; no se abre segunda conexión')
  if w:w.serial_worker=None;w.close()
  if prior is not None:
   with Connection('1060031107') as c:
    r=OutputReceiver(c,lambda b:None);r.select(Mode.SPI);r.configure(prior);r.generator(generator)
    end=time.monotonic()+3
    while time.monotonic()<end:r.pump()
    report['restored']=True
  report['ok']=not report['errors'] and report['samples']>1600000*(10 if '--startup-benchmark' in sys.argv else 30) and report['paints']>0
  path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
