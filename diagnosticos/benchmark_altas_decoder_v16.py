import sys,time,struct,zlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from monitor.v16.receiver.unoq_native import PROFILES
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_config_decoder import ConfigurationDecoder
path=Path('diagnosticos/resultados_v16/highrate_host_20261012.json');report=json.loads(path.read_text());results=[]
for profile in PROFILES:
 c=Configuration(profile['bits'],160000000//profile['ticks']);frames=[];offset=0;seq=0;capacity=(872*8//(c.bits*c.channels))&~3
 while offset<c.node_pairs:
  count=min(capacity,c.node_pairs-offset);p=bytearray(992)
  struct.pack_into('<4sHHII',p,0,b'SCP1',4,20,seq,972);struct.pack_into('<i',p,32,992)
  struct.pack_into('<IIIIHBBIII',p,48,c.rate,offset,0,0,count,c.bits,c.channels,c.period,0,0)
  struct.pack_into('<I',p,80,offset*c.period);struct.pack_into('<8I',p,84,c.node_pairs,1,2,100,100,100,100,1)
  struct.pack_into('<I',p,988,zlib.crc32(p[:988]));frames.append(bytes(p));offset+=count;seq+=1
 data=b''.join(frames);timings=[]
 for _ in range(20):
  d=ConfigurationDecoder();start=time.perf_counter();rows=d.feed(data);timings.append(time.perf_counter()-start)
  assert len(rows)==c.node_pairs
 ms=float(np.median(timings)*1000);results.append(dict(bits=c.bits,rate=c.rate,channels=c.channels,decode_ms_node=ms,estimated_cpu_percent=ms/(c.node_pairs/c.rate*1000)*100))
report['decoder_cases']=results;path.write_text(json.dumps(report,indent=2))
for r in sorted(results,key=lambda x:x['estimated_cpu_percent'],reverse=True)[:6]:print(r)
