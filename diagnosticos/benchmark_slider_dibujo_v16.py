"""Host-only point-count and drawing comparison of the existing detail slider."""
import sys,os,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
from unittest.mock import patch
from PyQt6 import QtWidgets
from monitor.v16.app import SerialMonitorWindow
from monitor.v16.numeric_batch import NumericBatch,SampleClock
app=QtWidgets.QApplication([])
with patch('monitor.v16.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
w.render_timer.stop();w._acquisition_confirmed(8,1221374);w.resize(1320,860);w.show();app.processEvents();c=w.applied_configuration
n=40000;i=np.arange(n);raw=np.column_stack((i*c.period,127.5+100*np.sin(2*np.pi*5000*i/c.actual_rate),np.zeros(n),i))
w.handle_batch(NumericBatch(raw,c.maximum,SampleClock(c.timestamp_hz),1));app.processEvents();results=[]
for duration_ms in (1,10):
 for detail in (0,50,100):
  w.h_scale=round(c.actual_rate*duration_ms/1000);w.detail_slider.setValue(detail);prep=[];paint=[]
  for _ in range(15):
   w.h_scale=round(c.actual_rate*duration_ms/1000)
   began=time.perf_counter();w.render_frame();prep.append((time.perf_counter()-began)*1000)
   began=time.perf_counter();w.plot_widget.grab();paint.append((time.perf_counter()-began)*1000)
  points=sum(len(line.xData) for line in w.line_items.values() if line.isVisible() and line.xData is not None)
  results.append(dict(duration_ms=duration_ms,slider=detail,samples_visible=w.h_scale,vertices_sent=points,plot_width=float(w.plot_widget.getViewBox().width()),prepare_ms=float(np.median(prep[3:])),raster_ms=float(np.median(paint[3:]))))
w.close();report={'scope':'Host-only fixed 5 kHz sine, ADC8 CH1/1221374, existing slider. Raster includes QWidget grab overhead, no live Q or physical FPS claim. Acquisition samples untouched.','cases':results}
p=ROOT/'diagnosticos/resultados_v16/slider_dibujo_20261012.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
