"""Offline host-stage timing, not transport/analog/FPS acceptance."""
import sys,json,time,pickle
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.v17.processing import BatchProcessor,ProcessingSettings
from monitor.v17.digital_filter import FilterConfig
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.radio_output import RadioDacSource,HighRateRadioDacSource
from monitor.v17.numeric_batch import NumericBatch,SampleClock

def main():
 report=dict(scope=__doc__,cases=[])
 for bits,rate in ((8,1600000),(10,1250000),(12,1066666),(14,851063),(16,76226)):
  config=Configuration(bits,rate)
  for filtered in (False,True):
   settings=ProcessingSettings(acquisition=config,radio_enabled=True,radio_frequency=min(550000,config.actual_rate*.25),radio_bandwidth=8000,filter=FilterConfig(source='RADIO' if filtered else 'OFF'))
   processor=BatchProcessor();clock=SampleClock(config.timestamp_hz)
   source=(HighRateRadioDacSource if bits==14 else RadioDacSource)(buffer_seconds=0,input_source='FILTER' if filtered else 'RADIO')
   stages={};position=0;audios=0
   def record(name,start):stages.setdefault(name,[]).append((time.perf_counter()-start)*1000)
   count=config.node_pairs
   for i in range(120):
    indices=np.arange(i*count,(i+1)*count,dtype=np.uint64)
    t=indices/config.actual_rate
    rf=1.65+.5*(1+.3*np.cos(2*np.pi*1000*t))*np.cos(2*np.pi*settings.radio_frequency*t)
    codes=np.rint(rf*((1<<bits)-1)/3.3).astype(np.uint32)
    rows=np.column_stack(((indices*config.period)&0xffffffff,codes,codes,indices&0xffffffff)).astype(np.uint32)
    start=time.perf_counter();batch=NumericBatch(rows,(1<<bits)-1,clock,config.channels);batch.acquisition=config;record('numeric_batch_ms',start)
    payload=SimpleNamespace(columns={k:v for k,v in batch.columns.items() if k in ('Muestra','Tiempo (us)','CH1')},acquisition=config)
    start=time.perf_counter();pickle.loads(pickle.dumps((payload,settings),protocol=5));record('ipc_pickle_roundtrip_ms',start)
    start=time.perf_counter();processor.process(batch,settings);record('batch_processor_ms',start)
    for name,value in batch.processing['timings'].items():stages.setdefault(name,[]).append(value)
    start=time.perf_counter();source.observe_input(batch.columns['CH1'],config.actual_rate);record('loop_observe_ms',start)
    start=time.perf_counter();source.feed_result(batch.processing);record('audio_feed_ms',start)
    start=time.perf_counter()
    while True:
     rendered=source.try_codes(position,position+480)
     if rendered is None:break
     position+=480
    record('dac_render_ms',start)
    if source.error:raise RuntimeError(source.error)
   stages={name:dict(mean_ms=float(np.mean(values[10:])),p95_ms=float(np.percentile(values[10:],95)),max_ms=float(max(values[10:]))) for name,values in stages.items()}
   report['cases'].append(dict(bits=bits,rate=config.actual_rate,node_pairs=count,node_ms=count/config.actual_rate*1000,filter=filtered,rendered=position,stages=stages))
 path=ROOT/'diagnosticos/resultados_v17/radio_chain_audit'/('offline_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
 path.write_text(json.dumps(report,indent=2)+'\n')
 print(path)
 for c in report['cases']:
  print(c['bits'],c['filter'], 'node_ms',round(c['node_ms'],2),{k:round(c['stages'][k]['mean_ms'],3) for k in ('batch_processor_ms','radio_demod_ms','radio_resample_ms','ipc_pickle_roundtrip_ms','loop_observe_ms','dac_render_ms')})
if __name__=='__main__':main()
