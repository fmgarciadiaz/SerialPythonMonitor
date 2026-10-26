"""ADC16 rate staircase, unchanged 14-bit ADC x16 oversampling and 54 MHz clock."""
import json,shutil
from pathlib import Path
from experimentos.fs_max_v18.probe_journal import source_manifest
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'adc16'
PROFILES=[dict(bits=16,channels=ch,ticks=t,node_pairs=3488 if ch==1 else 3456,
              queue_slots=4,headroom=False,internal_only=True,validation='unmeasured')
          for ch,ticks in ((1,(1080,1060,1048)),(2,(2090,2088,2086))) for t in ticks]
def prepare():
 for src,name in ((ROOT/'arduino/v18/oscilloscope','oscilloscope'),(ROOT/'arduino/v18/relay','relay')):
  shutil.copytree(src,OUT/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.cache','__pycache__','.DS_Store'))
 for folder in (OUT/'oscilloscope/sketch',OUT/'relay'):
  p=folder/'native_profiles.h';s=p.read_text();pos=s.index('\n};',s.index('scope_native_profiles[]'))
  rows=[f'    {{16, {v["channels"]}, {v["ticks"]}, {v["node_pairs"]}}},\n' for v in PROFILES]
  missing=[row for row in rows if row.strip() not in s]
  if missing:s=s[:pos]+'\n// ADC16 private staircase: same oversampling and clock.\n'+''.join(missing)+s[pos:]
  p.write_text(s)
 (OUT/'candidate_profiles.json').write_text(json.dumps(PROFILES,indent=2)+'\n')
 (OUT/'source_manifest.json').write_text(json.dumps(source_manifest(ROOT/'arduino/v18'),indent=2)+'\n')
if __name__=='__main__':prepare()
