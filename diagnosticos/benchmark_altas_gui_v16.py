import sys,os,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['QT_QPA_PLATFORM']='offscreen'
import numpy as np
from unittest.mock import patch
from PyQt6 import QtWidgets
from monitor.v16.app import SerialMonitorWindow
from monitor.v16.receiver.unoq_native import PROFILES
from monitor.v16.numeric_batch import NumericBatch,SampleClock
app=QtWidgets.QApplication([]);results=[]
with patch('monitor.v16.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
w.render_timer.stop()
for p in PROFILES:
 rate=160000000//p['ticks'];w._acquisition_confirmed(p['bits'],rate);config=w.applied_configuration
 for window in (4096,100000):
  w.clear_data();w.h_scale=window;clock=SampleClock(config.timestamp_hz);ingest=[];render=[];count=max(512,round(rate*.02))
  for block in range(25):
   indices=np.arange(block*count,(block+1)*count);phase=indices*(2*np.pi*5000/rate);maximum=config.maximum
   raw=np.column_stack(((indices*config.period)%2**32,maximum*(.5+.25*np.sin(phase)),maximum*(.5+.2*np.sin(phase-.2)),indices))
   began=time.perf_counter();batch=NumericBatch(raw,maximum,clock,config.channels);w.handle_batch(batch);ingest.append((time.perf_counter()-began)*1000)
   began=time.perf_counter();w.render_frame();render.append((time.perf_counter()-began)*1000)
  results.append(dict(bits=config.bits,rate=rate,channels=config.channels,window=window,ingest_ms_per_20ms=float(np.median(ingest[5:])),render_ms=float(np.median(render[5:]))))
w.close();report={'scope':'Synthetic host ingestion and temporal render preparation; excludes USB decoding, Qt queued deliveries and screen painting. Not measured physical FPS.','cases':results}
Path('diagnosticos/resultados_v16/highrate_host_20261012.json').write_text(json.dumps(report,indent=2))
for r in sorted(results,key=lambda x:x['render_ms']+x['ingest_ms_per_20ms'],reverse=True)[:8]:print(r)
