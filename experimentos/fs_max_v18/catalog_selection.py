"""Pure proposal builder: compact visible rates without deleting old profiles."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent

def build():
 from monitor.v18.receiver.unoq_acquisition import Configuration,RATES
 from experimentos.fs_max_v18.run_probe import private_profiles
 from contextlib import ExitStack
 with ExitStack() as stack:
  for name in ('audio_catalog','catalog_bridges'):stack.enter_context(private_profiles(BASE/name))
  candidates=[]
  for name in ('audio_catalog','catalog_bridges'):candidates+=json.loads((BASE/name/'candidate_profiles.json').read_text())
  result=dict(schema=1,bits={})
  dual_ticks={8:(480,389,253),10:(640,466,308),12:(558,480,366),14:(640,480,440),16:(2560,2099)}
  for bits in (8,10,12,14,16):
   rows=[]
   def add(config,kind):
    if any(row['rate']==config.rate for row in rows):return
    rows.append(dict(rate=config.rate,channels=config.channels,ticks=config.period,node_pairs=config.node_pairs,actual_rate=config.actual_rate,nominal_rate=(config._native or {}).get('nominal_rate'),kind=kind))
   for rate in (1000,5000,10000,20000,31250,40000):add(Configuration(bits,rate),'low')
   from monitor.v18.receiver import unoq_native
   for profile in unoq_native.PROFILES:
    if profile['bits']==bits and profile.get('nominal_rate') in (44100,48000,96000,192000):add(Configuration.from_wire(bits,unoq_native.code(profile)),'audio')
   available=[]
   for rate in RATES:
    try:available.append(Configuration(bits,rate))
    except ValueError:pass
   for target in dual_ticks[bits]:
    match=[c for c in available if c.channels==2 and abs(c.actual_rate-160000000/target)<1]
    if not match:raise ValueError((bits,target))
    add(match[0],'dual_intermediate')
   for profile in candidates:
    if profile['bits']==bits and not profile.get('nominal_rate'):add(Configuration.from_wire(bits,unoq_native.code(profile)),'single_intermediate')
   maximum=max((c for c in available if c.channels==1),key=lambda c:c.actual_rate);add(maximum,'single_maximum')
   result['bits'][str(bits)]=sorted(rows,key=lambda row:row['actual_rate'])
  return result
if __name__=='__main__':
 result=build();(BASE/'audio_catalog/catalog.proposed.json').write_text(json.dumps(result,indent=2)+'\n')
 for bits,rows in result['bits'].items():print(bits,[(round(row['actual_rate']/1000,3),row['channels']) for row in rows])
