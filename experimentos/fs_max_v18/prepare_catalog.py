"""Combine the private audio anchors and CH1 bridges for integration tests."""
import json,shutil
from pathlib import Path
from experimentos.fs_max_v18.probe_journal import source_manifest
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent;OUT=EXP/'catalog'
def prepare():
 baseline=source_manifest(ROOT/'arduino/v18')
 for name in ('audio_catalog','catalog_bridges'):
  if json.loads((EXP/name/'source_manifest.json').read_text())!=baseline:raise ValueError('Private source baseline mismatch')
 profiles=[]
 for name in ('audio_catalog','catalog_bridges'):profiles+=json.loads((EXP/name/'candidate_profiles.json').read_text())
 for name in ('oscilloscope','relay'):
  shutil.copytree(EXP/'catalog_bridges'/name,OUT/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.cache','__pycache__','.DS_Store'))
  p=OUT/name/('sketch/native_profiles.h' if name=='oscilloscope' else 'native_profiles.h');s=p.read_text();pos=s.index('\n};',s.index('scope_native_profiles[]'))
  rows=''.join(f'    {{{v["bits"]}, {v["channels"]}, {v["ticks"]}, {v["node_pairs"]}}},\n' for v in profiles if v.get('nominal_rate'))
  p.write_text(s[:pos]+'\n// Private audio anchors integrated with CH1 bridges.\n'+rows+s[pos:])
 (OUT/'candidate_profiles.json').write_text(json.dumps(profiles,indent=2)+'\n');(OUT/'source_manifest.json').write_text(json.dumps(baseline,indent=2)+'\n');print(OUT,len(profiles))
if __name__=='__main__':prepare()
