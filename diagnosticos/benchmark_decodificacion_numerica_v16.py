import sys,time,struct,zlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from monitor.v16.receiver.unoq_native import PROFILES
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_config_decoder import ConfigurationDecoder
path=Path('diagnosticos/resultados_v16/decoder_numeric_20261012.json');report={'scope':'Same-process comparison of native decoding to Python rows versus numeric blocks; all samples retained.'};results=[]
for profile in PROFILES:
 c=Configuration(profile['bits'],160000000//profile['ticks']);frames=[];offset=0;seq=0;capacity=(872*8//(c.bits*c.channels))&~3
 while offset<c.node_pairs:
  count=min(capacity,c.node_pairs-offset);p=bytearray(992)
  struct.pack_into('<4sHHII',p,0,b'SCP1',4,20,seq,972);struct.pack_into('<i',p,32,992)
  struct.pack_into('<IIIIHBBIII',p,48,c.rate,offset,0,0,count,c.bits,c.channels,c.period,0,0)
  struct.pack_into('<I',p,80,offset*c.period);struct.pack_into('<8I',p,84,c.node_pairs,1,2,100,100,100,100,1)
  struct.pack_into('<I',p,988,zlib.crc32(p[:988]));frames.append(bytes(p));offset+=count;seq+=1
 data=b''.join(frames);modes={}
 for numeric in (False,True):
  timings=[]
  for _ in range(40):
   d=ConfigurationDecoder();d.numeric=numeric;start=time.perf_counter();rows=d.feed(data);timings.append(time.perf_counter()-start)
   assert len(rows)==c.node_pairs
  modes['numeric_ms' if numeric else 'rows_ms']=float(np.median(timings)*1000)
 results.append(dict(bits=c.bits,rate=c.rate,channels=c.channels,**modes,speedup=modes['rows_ms']/modes['numeric_ms']))
report['decoder_cases']=results;path.write_text(json.dumps(report,indent=2))
for r in results:print(r)
