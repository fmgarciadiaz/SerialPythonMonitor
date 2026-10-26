"""Reviewable default catalogue using accepted rates plus private audio anchors."""
import json
from pathlib import Path
from monitor.v18.receiver.unoq_acquisition import Configuration,RATES
from experimentos.fs_max_v18.run_probe import private_profiles
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent/'audio_catalog'
def plan():
 result=dict(audio_nominals=[44100,48000,96000,192000],common_low=[1000,5000,10000,20000,31250,40000],bits={})
 # Audio has priority. Above the largest available audio rate, use existing
 # accepted dual profiles; CH1 extends only above the maximum dual rate.
 with private_profiles(OUT):
  audio=json.loads((OUT/'candidate_profiles.json').read_text())
  for bits in (8,10,12,14,16):
   configs=[]
   for rate in RATES:
    try:configs.append(Configuration(bits,rate))
    except ValueError:pass
   for p in audio:
    if p['bits']==bits:configs.append(Configuration.from_wire(bits,(p['node_pairs']<<16)|p['ticks']|(0x80000000 if p['channels']==2 else 0)))
   unique={(c.channels,c.period,c.node_pairs):c for c in configs};configs=list(unique.values())
   selected=[c for c in configs if c.rate in result['common_low']]
   selected += [c for c in configs if c._native and c._native.get('nominal_rate') in result['audio_nominals']]
   dualmax=max(c.actual_rate for c in configs if c.channels==2)
   last_audio=max((c.actual_rate for c in selected if c.channels==2),default=40000)
   for channels,low,high,steps in ((2,last_audio,dualmax,3),(1,dualmax,max(c.actual_rate for c in configs if c.channels==1),4)):
    available=[c for c in configs if c.channels==channels and c.actual_rate>low]
    for index in range(1,steps+1):
     if available:
      target=low+(high-low)*index/steps
      selected.append(min(available,key=lambda c:abs(c.actual_rate-target)))
   selected=sorted({c.request_period:c for c in selected}.values(),key=lambda c:c.actual_rate)
   result['bits'][str(bits)]=[dict(rate=c.rate,actual_rate=c.actual_rate,channels=c.channels,ticks=c.period if c._native else None,node_pairs=c.node_pairs,nominal_rate=(c._native or {}).get('nominal_rate'),private_audio=(c._native or {}).get('internal_only',False)) for c in selected]
 return result
if __name__=='__main__':
 result=plan();(OUT/'catalog.proposed.json').write_text(json.dumps(result,indent=2)+'\n')
 for bits,rows in result['bits'].items():print(bits,[(round(c['actual_rate']/1000,3),c['channels']) for c in rows])
