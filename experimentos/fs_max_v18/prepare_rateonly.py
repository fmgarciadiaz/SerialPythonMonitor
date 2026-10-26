"""Private rate-only staircase; preserve production processing and transport."""
import json,shutil
from pathlib import Path
from experimentos.fs_max_v18.probe_journal import source_manifest
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'rateonly'
PROFILES=[dict(bits=b,channels=1,ticks=t,node_pairs=n,queue_slots=8 if b==8 else 4,
 headroom=False,internal_only=True,validation='unmeasured')
 for b,n,ts in ((8,3488,(87,86,84)),(10,5568,(120,118,116)),
                (12,7488,(144,142,140)),(14,5952,(174,172,170))) for t in ts]
for p in PROFILES:
 if p['bits']==8:p['compact_adc8_ipc']=True
def prepare():
 for src,name in ((ROOT/'arduino/v18/oscilloscope','oscilloscope'),(ROOT/'arduino/v18/relay','relay')):
  shutil.copytree(src,OUT/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.cache','__pycache__','.DS_Store'))
 for folder in (OUT/'oscilloscope/sketch',OUT/'relay'):
  p=folder/'native_profiles.h';s=p.read_text();pos=s.index('\n};',s.index('scope_native_profiles[]'))
  rows=''.join(f'    {{{v["bits"]}, 1, {v["ticks"]}, {v["node_pairs"]}}},\n' for v in PROFILES)
  p.write_text(s[:pos]+'\n// Private rate-only staircase.\n'+rows+s[pos:])
  p=folder/'high_rate_profile.h';s=p.read_text()
  guard=' || '.join(f'(bits=={v["bits"]} && ticks=={v["ticks"]} && pairs=={v["node_pairs"]})' for v in PROFILES)
  s=s.replace('return channels==1 && (','return channels==1 && ('+guard+' || ',1)
  guard8=' || '.join(f'ticks=={v["ticks"]}' for v in PROFILES if v['bits']==8)
  s=s.replace('    return (bits==8 && channels==1',f'    return (bits==8 && channels==1 && pairs==3488 && ({guard8})) || (bits==8 && channels==1',1)
  p.write_text(s)
 # Same CPU policy as the corresponding accepted high-rate profiles.
 p=OUT/'relay/cpu_profile.h';s=p.read_text()
 guard=' || '.join(f'(bits=={v["bits"]} && channels==1 && ticks=={v["ticks"]} && pairs=={v["node_pairs"]})' for v in PROFILES if v['bits']!=8)
 s=s.replace('    return ', '    return '+guard+' || ',1);p.write_text(s)
 (OUT/'candidate_profiles.json').write_text(json.dumps(PROFILES,indent=2)+'\n')
 (OUT/'source_manifest.json').write_text(json.dumps(source_manifest(ROOT/'arduino/v18'),indent=2)+'\n')
if __name__=='__main__':prepare()
