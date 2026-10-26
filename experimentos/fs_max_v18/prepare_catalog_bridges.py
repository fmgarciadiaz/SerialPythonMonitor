"""Private evenly spaced CH1 bridges; inherit accepted per-format transport."""
import json,shutil
from pathlib import Path
from experimentos.fs_max_v18.probe_journal import source_manifest
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent/'catalog_bridges'
# Periods chosen near quartiles of the extension above each dual maximum.
PROFILES=[dict(bits=b,channels=1,ticks=t,node_pairs=n,queue_slots=8 if b==8 else 4,catalog_profile=True,internal_only=True,headroom=False,validation='unmeasured',**({'compact_adc8_ipc':True} if b==8 else {})) for b,n,periods in ((8,3488,(170,128,104)),(10,5568,(220,171,141)),(12,7488,(265,208,171)),(14,5952,(306,235,190)),(16,3488,(1458,1296,1166))) for t in periods]
def prepare():
 before=source_manifest(ROOT/'arduino/v18')
 if (OUT/'source_manifest.json').exists() and json.loads((OUT/'source_manifest.json').read_text())!=before:raise ValueError('Frozen baseline drift')
 for name in ('oscilloscope','relay'):
  shutil.copytree(ROOT/'arduino/v18'/name,OUT/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.cache','__pycache__','.DS_Store'))
  folder=OUT/name/('sketch' if name=='oscilloscope' else '')
  p=folder/'native_profiles.h';s=p.read_text();pos=s.index('\n};',s.index('scope_native_profiles[]'))
  rows=''.join(f'    {{{v["bits"]}, 1, {v["ticks"]}, {v["node_pairs"]}}},\n' for v in PROFILES)
  p.write_text(s[:pos]+'\n// Private CH1 catalogue bridges.\n'+rows+s[pos:])
  p=folder/'high_rate_profile.h';s=p.read_text();guard=' || '.join(f'(bits=={v["bits"]} && ticks=={v["ticks"]} && pairs=={v["node_pairs"]})' for v in PROFILES if v['bits']!=16)
  s=s.replace('return channels==1 && (','return channels==1 && ('+guard+' || ',1)
  guard8=' || '.join(f'ticks=={v["ticks"]}' for v in PROFILES if v['bits']==8)
  s=s.replace('    return (bits==8 && channels==1',f'    return (bits==8 && channels==1 && pairs==3488 && ({guard8})) || (bits==8 && channels==1',1);p.write_text(s)
 p=OUT/'relay/cpu_profile.h';s=p.read_text();guard=' || '.join(f'(bits=={v["bits"]} && channels==1 && ticks=={v["ticks"]} && pairs=={v["node_pairs"]})' for v in PROFILES if v['bits'] not in (8,16))
 p.write_text(s.replace('    return ','    return '+guard+' || ',1))
 (OUT/'candidate_profiles.json').write_text(json.dumps(PROFILES,indent=2)+'\n');(OUT/'source_manifest.json').write_text(json.dumps(before,indent=2)+'\n');print(OUT)
if __name__=='__main__':prepare()
