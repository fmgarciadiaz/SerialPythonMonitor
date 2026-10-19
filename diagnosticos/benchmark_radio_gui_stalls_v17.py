"""Isolated real OutputWorker DSP/Qt delivery with simulated ADC and GUI stalls.
No Q/DAC hardware, no transport/headroom acceptance. Admission mirrors run.flush.
"""
import sys,time,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PyQt6 import QtCore,QtWidgets
from monitor.v17.app import OutputWorker
from monitor.v17.processing import ProcessingSettings
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_switch import Mode

class Sink(QtCore.QObject):
    def __init__(self,worker):super().__init__();self.worker=worker;self.samples=0
    @QtCore.pyqtSlot(object)
    def consume(self,batch):self.samples+=len(batch.columns['CH1']);self.worker.batch_consumed()

def main():
 app=QtWidgets.QApplication([]);report=dict(scope=__doc__,cases=[])
 config=Configuration(10,1250000);settings=ProcessingSettings(acquisition=config,radio_enabled=True,radio_frequency=300000)
 for variant,pause_ms in ((v,p) for v in ('legacy_gui_pressure','integrated_dsp_pressure') for p in (0,50,100,250,500)):
  worker=OutputWorker('offline',Mode.SPI,config=config,processing_settings=settings)
  feeds=[]
  source=SimpleNamespace(observe_input=lambda *args:None,feed_result=lambda result:feeds.append(time.monotonic()))
  worker.set_radio_output_source(source)
  sink=Sink(worker);worker.batch_ready.connect(sink.consume,QtCore.Qt.ConnectionType.QueuedConnection)
  size=25000;counter=0;pending=[];coalesced=0;maxrf=0
  start=time.monotonic();deadline=start
  while time.monotonic()-start<1.4:
   now=time.monotonic()
   if now>=deadline:
    numbers=np.arange(counter,counter+size);counter+=size
    t=numbers/config.actual_rate
    pending.append(dict(CH1=np.cos(2*np.pi*300000*t)*(1+.2*np.sin(2*np.pi*1000*t)),**{'Muestra':numbers,'Tiempo (us)':t*1e6}))
    maxrf=max(maxrf,sum(len(x['CH1']) for x in pending))
    pressure=worker.pending_batches if variant=='legacy_gui_pressure' else worker.delivery_pressure()
    if pressure<4:
     columns={name:np.concatenate([p[name] for p in pending]) for name in pending[0]}
     worker.publish_batch(SimpleNamespace(columns=columns,acquisition=config));pending=[]
    else:coalesced+=1
    deadline+=.02
   elapsed=now-start
   if not (.25<=elapsed<.25+pause_ms/1000):app.processEvents()
   time.sleep(.001)
  if worker._processing_executor:worker._processing_executor.shutdown(wait=True)
  app.processEvents()
  gaps=np.diff(feeds)*1000
  report['cases'].append(dict(variant=variant,pause_ms=pause_ms,max_audio_feed_gap_ms=float(max(gaps)) if len(gaps) else None,pending_peak=worker.pending_batches_peak,pending_dsp_peak=getattr(worker,'pending_dsp_peak',None),coalesced=coalesced,max_rf_age_ms=maxrf/config.actual_rate*1000,audio_batches=len(feeds),generated_rf_samples=counter,gui_rf_samples=sink.samples,rf_continuity=sink.samples==counter and not pending))
 path=ROOT/'diagnosticos/resultados_v17/radio_chain_audit'/('gui_stalls_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
 path.write_text(json.dumps(report,indent=2)+'\n');print(path);print(json.dumps(report['cases'],indent=2))
if __name__=='__main__':main()
