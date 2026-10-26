"""Local Qt paint/analysis comparison with synthetic RF; no hardware connection."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PyQt6 import QtCore,QtWidgets
from monitor.v18.app import SerialMonitorWindow
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18 import spectrum

app=QtWidgets.QApplication([])
with patch('monitor.v18.app.usb_devices',return_value=[]),patch('monitor.v18.app.list_ports.comports',return_value=[]):w=SerialMonitorWindow()
w.render_timer.stop();w.resize(1400,900)
w.applied_configuration=Configuration(8,1860465);fs=w.applied_configuration.actual_rate;w.current_fs_hz=fs
n=262144;t=np.arange(n)/fs
w.sample_numbers=np.arange(n);w.series={'Tiempo (us)':t*1e6,'CH1':np.cos(2*np.pi*550000*t)+.2*np.cos(2*np.pi*552000*t)}
w.sample_counter=n;w.serial_worker=SimpleNamespace(pending_batches=0)
d=w.spectral;d.set_mode(1);d.fft_mode.setCurrentText('Radio');d.size.setCurrentText('65536');d.channels[1].setCurrentText('Ninguno')
w.radio_candidates=[{'frequency':f} for f in (350000,550000,710000)];d.refresh_radio_overlay()
class Paints(QtCore.QObject):
 count=0
 def eventFilter(self,obj,event):
  if event.type()==QtCore.QEvent.Type.Paint:self.count+=1
  return False
paints=Paints();d.widget.viewport().installEventFilter(paints);w.show();app.processEvents()
original=spectrum.live_interval;rows=[];timer=QtCore.QTimer();timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer);timer.setInterval(16)
state={}
def tick():
 now=time.monotonic();w.sample_counter+=int(fs*.016)
 before=d.last_end;start=time.perf_counter();d.render();cost=time.perf_counter()-start
 if d.last_end!=before and now-state['start']>=1.5:state['updates'].append(cost)
 if not state.get('measuring') and now-state['start']>=1.5:
  state['measuring']=True;state['measure_start']=now;state['paint_start']=paints.count
 if now-state['start']>=5:
  timer.stop();duration=now-state['measure_start'];costs=state['updates']
  rows.append(dict(variant=state['variant'],crop=state['crop'],duration_s=duration,
   analysis_hz=len(costs)/duration,paint_hz=(paints.count-state['paint_start'])/duration,
   median_callback_ms=float(np.median(costs)*1000) if costs else None,
   p95_callback_ms=float(np.percentile(costs,95)*1000) if costs else None))
  loop.quit()
timer.timeout.connect(tick)
try:
 for crop in (False,True):
  for variant in ('fixed_10','adaptive'):
   d.radio_crop.setChecked(crop);d.reset();d.last_fast_render=0
   spectrum.live_interval=(lambda *args,**kwargs:.1) if variant=='fixed_10' else original
   state.clear();state.update(start=time.monotonic(),variant=variant,crop=crop,updates=[])
   loop=QtCore.QEventLoop();timer.start();loop.exec()
finally:
 spectrum.live_interval=original;w.serial_worker=None;w.close();app.processEvents()
output=Path(__file__).with_name('cadence_simulation.json');output.write_text(json.dumps(dict(hardware=False,offscreen=True,fft_size=65536,averages=4,results=rows),indent=2)+'\n');print(output)
