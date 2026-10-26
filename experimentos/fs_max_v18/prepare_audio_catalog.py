"""Isolated native-clock audio anchors; current public profiles stay intact."""
import json,shutil
from pathlib import Path
from experimentos.fs_max_v18.probe_journal import source_manifest
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent/'audio_catalog'
def profiles():
 from monitor.v18.receiver.unoq_acquisition import Configuration,RATES
 result=[]
 for bits in (8,10,12,14,16):
  existing=[]
  for rate in RATES:
   try:existing.append(Configuration(bits,rate))
   except ValueError:pass
  for nominal in (44100,48000,96000,192000):
   ticks=round(160000000/nominal);actual=160000000/ticks
   dual=max(c.actual_rate for c in existing if c.channels==2)
   single=max(c.actual_rate for c in existing if c.channels==1)
   channels=2 if actual<=dual else 1 if actual<=single else None
   if channels is None:continue
   if any(c._native and c.period==ticks for c in existing):continue
   geometry=max((c for c in existing if c.channels==channels and c._native),key=lambda c:c.actual_rate)
   result.append(dict(bits=bits,channels=channels,ticks=ticks,node_pairs=geometry.node_pairs,
    queue_slots=geometry._native.get('queue_slots',4),nominal_rate=nominal,
    catalog_profile=True,internal_only=True,headroom=False,validation='unmeasured'))
 return result

def prepare():
 baseline=source_manifest(ROOT/'arduino/v18')
 if (OUT/'source_manifest.json').exists() and json.loads((OUT/'source_manifest.json').read_text())!=baseline:raise ValueError('Frozen baseline changed')
 candidates=profiles()
 for name in ('oscilloscope','relay'):
  shutil.copytree(ROOT/'arduino/v18'/name,OUT/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.cache','__pycache__','.DS_Store'))
  folder=OUT/name/('sketch' if name=='oscilloscope' else '')
  p=folder/'native_profiles.h';s=p.read_text();pos=s.index('\n};',s.index('scope_native_profiles[]'))
  rows=''.join(f'    {{{p["bits"]}, {p["channels"]}, {p["ticks"]}, {p["node_pairs"]}}},\n' for p in candidates)
  p.write_text(s[:pos]+'\n// Private audio anchors; existing policies unchanged.\n'+rows+s[pos:])
 (OUT/'candidate_profiles.json').write_text(json.dumps(candidates,indent=2)+'\n')
 (OUT/'source_manifest.json').write_text(json.dumps(baseline,indent=2)+'\n')
 print(OUT,len(candidates))
if __name__=='__main__':prepare()
