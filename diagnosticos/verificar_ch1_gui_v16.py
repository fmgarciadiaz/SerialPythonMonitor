"""Headless Qt integration check with the real Q worker; requires output off."""
import os,sys,time,json
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from unittest.mock import patch
from PyQt6 import QtWidgets,QtCore
from monitor.historico.v16.app import SerialMonitorWindow,OutputWorker
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_switch import Mode
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
rate=1203007 if "--megaboom" in sys.argv else 71428 if '--71428' in sys.argv else 66666 if '--16' in sys.argv else 661157 if '--661' in sys.argv else 599250
config=Configuration(8 if "--megaboom" in sys.argv else 16 if '--16' in sys.argv or '--71428' in sys.argv else 14,rate)
require_exclusive_monitor()
with Connection('1060031107') as c:
 r=OutputReceiver(c,lambda b:None,print);r.select(Mode.SPI);prior=r.config
 if r.generator().active.enabled:raise RuntimeError('Salida ocupada')
app=QtWidgets.QApplication([])
with patch('monitor.historico.v16.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
worker=OutputWorker('1060031107',Mode.SPI,config=config)
report={'rate':rate,'samples':0,'batches':0,'errors':[]};last=None
worker.acquisition_confirmed.connect(w._acquisition_confirmed)
def collect(batch):
 global last
 report['samples']+=len(batch);report['batches']+=1
 times=batch.columns['Tiempo (us)']
 if last is not None and abs(times[0]-last-config.dt_us)>1e-6:report['errors'].append('Tiempo discontinuo')
 last=times[-1];w.handle_batch(batch)
class Sink(QtCore.QObject):
 @QtCore.pyqtSlot(object)
 def accept(self,batch):collect(batch)
sink=Sink();worker.batch_ready.connect(sink.accept)
thread=QtCore.QThread();worker.moveToThread(thread);thread.started.connect(worker.run);worker.finished.connect(thread.quit)
w.is_running=True
if "--fft" in sys.argv:
 w.spectral.size.setCurrentText("1024");w.spectral.set_mode(1)
worker.error_occurred.connect(lambda text:report['errors'].append(text))
try:
 if '--already-fast' in sys.argv:
  with Connection('1060031107') as c:
   r=OutputReceiver(c,lambda b:None,print);r.select(Mode.SPI);r.configure(config)
 thread.start();start=time.monotonic()
 while time.monotonic()-start<10:app.processEvents();time.sleep(.001)
finally:
 worker.stop();end=time.monotonic()+10
 while thread.isRunning() and time.monotonic()<end:app.processEvents();time.sleep(.001)
 assert not thread.isRunning()
 app.processEvents()
 if "--fft" in sys.argv:
  report["fft_ok"]="CH1" in w.spectral.statistics_by_channel and w.spectral.curves[0].xData is not None and len(w.spectral.curves[0].xData)>0
  if not report["fft_ok"]:report["errors"].append("FFT sin resultado CH1")
 w.close()
 with Connection('1060031107') as c:
  r=OutputReceiver(c,lambda b:None,print);r.select(Mode.SPI);r.configure(prior)
 report['ok']=not report['errors'] and report['samples']>rate*8
 open(ROOT/('diagnosticos/resultados_v16/megaboom_gui_fft.json' if '--megaboom' in sys.argv else 'diagnosticos/resultados_v16/adc16_71428_gui_fft.json' if '--71428' in sys.argv else 'diagnosticos/resultados_v16/adc16_66667_gui_fft.json' if '--16' in sys.argv else 'diagnosticos/resultados_v16/ch1_661_gui_fft.json' if '--661' in sys.argv else 'diagnosticos/resultados_v16/ch1_gui_fft.json' if '--fft' in sys.argv else 'diagnosticos/resultados_v16/ch1_gui_reconnect.json' if '--already-fast' in sys.argv else 'diagnosticos/resultados_v16/ch1_gui.json'),'w').write(json.dumps(report,indent=2)+'\n')
 print(report)
assert report['ok']
