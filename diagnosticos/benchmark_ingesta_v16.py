"""Synthetic host comparison at 200 kpair/s; no hardware/FPS acceptance claim."""
from pathlib import Path
import sys,os,time,json
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6 import QtWidgets
from monitor.historico.v16.app import SerialMonitorWindow,MAX_BUFFER_SAMPLES
from monitor.historico.v16.history import SampleHistory
from monitor.historico.v16.numeric_batch import NumericBatch
from monitor.historico.v16.receiver.unoq_acquisition import Configuration

def legacy(w,batch):
 rate=w.applied_configuration.rate
 source=np.fromiter((s[w.filter_config.source] for s in batch),dtype=float,count=len(batch))
 indices=[s['Muestra'] for s in batch] if all('Muestra' in s for s in batch) else None
 timestamps=[s['Tiempo (us)'] for s in batch] if all('Tiempo (us)' in s for s in batch) else None
 filtered=w.digital_filter.process(source,rate,w.filter_config,indices,timestamps)
 batch=[dict(s,FILTER=float(value)) for s,value in zip(batch,filtered)]
 size=len(batch);w.sample_numbers.extend(range(w.sample_counter+1,w.sample_counter+size+1));w.sample_counter+=size
 columns=set().union(*(s.keys() for s in batch))
 for col in columns:
  if col not in w.series:w.series[col]=SampleHistory(MAX_BUFFER_SAMPLES)
 for col,history in w.series.items():history.extend(np.fromiter((s.get(col,0.) for s in batch),dtype=float,count=size))

app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
results={}
for mode in ('legacy','numeric'):
 with patch('monitor.historico.v16.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
 w.applied_configuration=Configuration(14,200000)
 elapsed=[];renders=[]
 for block in range(100):
  indices=np.arange(block*4096,(block+1)*4096)
  raw=np.column_stack((indices*5,8192+4000*np.sin(indices*.0314),8192+2000*np.sin(indices*.0314-.2),indices))
  start=time.perf_counter()
  if mode=='legacy':
   batch=[{'Tiempo (us)':float(t),'CH1':a*3.3/16383,'CH2':b*3.3/16383,'Muestra':float(i)} for t,a,b,i in raw]
   legacy(w,batch)
  else:w.handle_batch(NumericBatch(raw,16383))
  elapsed.append(time.perf_counter()-start)
  start=time.perf_counter();w.render_frame();renders.append(time.perf_counter()-start)
 results[mode]={'samples':w.sample_counter,'ingest_ms_per_4096':float(np.median(elapsed[10:])*1000),'render_call_ms':float(np.median(renders[10:])*1000)}
 assert w.sample_counter==409600
 w.close()
results['speedup']=results['legacy']['ingest_ms_per_4096']/results['numeric']['ingest_ms_per_4096']
results['scope']='Synthetic batch construction + GUI ingestion; no painting, USB or physical FPS proof'
folder=ROOT/'diagnosticos/resultados_v16';folder.mkdir(exist_ok=True)
(folder/'benchmark_ingesta.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
