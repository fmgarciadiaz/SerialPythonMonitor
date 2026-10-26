import time,json
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets
from monitor.v18.app import SerialMonitorWindow
from monitor.v18.receiver.unoq_acquisition import Configuration
app=QtWidgets.QApplication([])
with patch('monitor.v18.app.usb_devices',return_value=[]),patch('monitor.v18.app.list_ports.comports',return_value=[]):w=SerialMonitorWindow()
w.applied_configuration=Configuration(8,1860465);d=w.spectral;d.set_mode(1);d.fft_mode.setCurrentText('Radio');d.channels[1].setCurrentText('Ninguno')
fs=w.applied_configuration.actual_rate;length=262144;t=np.arange(length)/fs
owner=SimpleNamespace(sample_numbers=np.arange(length),sample_counter=length,series={'Tiempo (us)':t*1e6,'CH1':np.cos(2*np.pi*550000*t)},channel_colors=w.channel_colors,_reduce_trace_for_display=w._reduce_trace_for_display)
rows=[]
for n in (16384,32768,65536):
 for crop in (False,True):
  d.size.setCurrentText(str(n));w.radio_candidates=[{'frequency':x} for x in (350000,550000,710000)];d.refresh_radio_overlay();d.radio_crop.setChecked(crop)
  costs=[]
  for i in range(16):
   owner.sample_counter+=1;start=time.perf_counter();d._render_fft_analysis(owner,fs,n);app.processEvents();costs.append((time.perf_counter()-start)*1000)
  rows.append(dict(n=n,crop=crop,median_ms=float(np.median(costs[3:])),p95_ms=float(np.percentile(costs[3:],95))))
w.close();print(json.dumps(rows,indent=2))
