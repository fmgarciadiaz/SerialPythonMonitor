"""Build a reviewable local ADC16 proposal; never edits production or contacts Q."""
import hashlib,json,shutil,time
from pathlib import Path
from experimentos.fs_max_v18.probe_journal import source_manifest
ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stage():
 qualification=EXP/'resultados/20261025_015536/report.json'
 gui=ROOT/'diagnosticos/resultados_v18/gui_private_20261025_020837/report.json'
 measured=json.loads(qualification.read_text());combined=json.loads(gui.read_text())
 cases=measured['cases']
 if not (measured.get('ok') and measured.get('restoration',{}).get('hardware_restored')
         and [row['seconds'] for row in cases]==[60,120,120,120]
         and all(row['ok'] and row['headroom_ok'] and (row['bits'],row['channels'],row['ticks'],row['node_pairs'])==(16,1,1060,3488) for row in cases)):
  raise ValueError('Incomplete ADC16 isolated qualification')
 evidence=json.loads((gui.parent/'gui.json').read_text())
 if not (combined.get('ok') and combined.get('hardware_restored') and evidence['radio_hold_seconds']>=120
         and not evidence['errors'] and all(evidence['assertions'].values())):
  raise ValueError('Incomplete ADC16 combined qualification')
 expected=measured['candidate_identity_expected']
 if any(combined['candidate_identity'][key]!=expected[key] for key in ('firmware_sha256','relay_sha256')):
  raise ValueError('Isolated and combined binaries differ')
 folder=EXP/('release_adc16_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 for name in ('oscilloscope','relay'):
  shutil.copytree(ROOT/'arduino/v18'/name,folder/name,ignore=shutil.ignore_patterns('.cache','__pycache__','.DS_Store'))
 for name in ('oscilloscope/sketch/native_profiles.h','relay/native_profiles.h'):
  shutil.copyfile(EXP/'adc16'/name,folder/name)
 sources={'app':source_manifest(folder/'oscilloscope'),'relay':source_manifest(folder/'relay')}
 for name,subpath in (('app','oscilloscope'),('relay','relay')):
  original=source_manifest(ROOT/'arduino/v18'/subpath)
  changed={key for key in sources[name] if sources[name][key]!=original.get(key)}
  if changed!=({'sketch/native_profiles.h'} if name=='app' else {'native_profiles.h'}):
   raise ValueError('Unexpected proposal source change')
 profiles=json.loads((ROOT/'monitor/v18/receiver/native_profiles.json').read_text())
 profiles.append(dict(bits=16,channels=1,ticks=1060,node_pairs=3488,queue_slots=4,
   headroom=True,isolated_headroom=True,combined_qualified=True,validation='physical_60s_3x120s_and_gui120',
   acceptance_seconds=[60,120,120,120],evidence=str(qualification.relative_to(ROOT)),
   gui_evidence=str(gui.relative_to(ROOT)),analog_enob_qualified=False))
 (folder/'native_profiles.proposed.json').write_text(json.dumps(profiles,indent=2)+'\n')
 bundle=dict(accepted=False,production_changed=False,stage_only=True,sources=sources,
   candidate_identity=expected,qualification=dict(path=str(qualification.relative_to(ROOT)),sha256=digest(qualification)),
   combined=dict(path=str(gui.relative_to(ROOT)),sha256=digest(gui)),
   pending=['private same-app rollback rehearsal for exact binary pair','production-source prebuild proof','paired backup','transactional Scope V18 update','installed GUI verification','public host profile promotion'])
 (folder/'proposal.json').write_text(json.dumps(bundle,indent=2)+'\n')
 print(folder)
 return folder
if __name__=='__main__':stage()
