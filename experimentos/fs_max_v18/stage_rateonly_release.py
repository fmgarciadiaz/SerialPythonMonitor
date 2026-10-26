"""Stage only qualified rate additions, preserving every existing public profile."""
import hashlib,json,shutil,time
from pathlib import Path
from experimentos.fs_max_v18.probe_journal import source_manifest
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent

def stage():
 from monitor.v18.radio_multiscan import scan_profiles
 from monitor.v18.receiver.unoq_acquisition import Configuration,RATES
 accepted=json.loads((EXP/'rateonly/qualified_candidates.json').read_text())
 if not accepted['hardware_restored']:raise ValueError('Candidate restoration missing')
 candidates=accepted['qualified_private_candidates']
 if {(p['bits'],p['ticks']) for p in candidates}!={(8,86),(10,120),(14,170)}:raise ValueError('Unexpected candidates')
 identity=None
 for p in candidates:
  q=json.loads((ROOT/p['physical_evidence']).read_text());g=json.loads((ROOT/p['gui_evidence']).read_text())
  cases=[c for c in q['cases'] if (c['bits'],c['ticks'])==(p['bits'],p['ticks'])]
  if not(q['ok'] and q['restoration']['hardware_restored'] and [c['seconds'] for c in cases]==[60,120,120,120] and all(c['ok'] and c['headroom_ok'] for c in cases) and g['ok'] and g['hardware_restored'] and g['visible_gui_ok']):raise ValueError('Unqualified candidate')
  hashes={k:g['candidate_identity'][k] for k in ('firmware_sha256','relay_sha256')}
  if identity is not None and hashes!=identity:raise ValueError('Candidate binaries differ')
  identity=hashes
 if source_manifest(ROOT/'arduino/v18')!=json.loads((EXP/'rateonly/source_manifest.json').read_text()):raise ValueError('Production drift')
 folder=EXP/('release_rateonly_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 for name in ('oscilloscope','relay'):
  shutil.copytree(ROOT/'arduino/v18'/name,folder/name,ignore=shutil.ignore_patterns('.cache','__pycache__','.DS_Store'))
  headers=('native_profiles.h','high_rate_profile.h')+ (('cpu_profile.h',) if name=='relay' else ())
  for header in headers:
   relative=Path('sketch')/header if name=='oscilloscope' else Path(header)
   shutil.copyfile(EXP/'rateonly'/name/relative,folder/name/relative)
 profiles=json.loads((ROOT/'monitor/v18/receiver/native_profiles.json').read_text())
 for p in candidates:
  entry=dict(bits=p['bits'],channels=1,ticks=p['ticks'],node_pairs=p['node_pairs'],queue_slots=8 if p['bits']==8 else 4,headroom=True,isolated_headroom=True,combined_qualified=True,headroom_scope='ADC only; joint GUI/RADIO/A0 functionality tested separately',validation='physical_60s_3x120s_and_gui_us120',acceptance_seconds=[60,120,120,120],evidence=p['physical_evidence'],gui_evidence=p['gui_evidence'],analog_enob_qualified=False)
  if p['bits']==8:entry['compact_adc8_ipc']=True
  profiles.append(entry)
 (folder/'native_profiles.proposed.json').write_text(json.dumps(profiles,indent=2)+'\n')
 baseline=[]
 for bits in (8,10,12,14,16):
  for rate in RATES:
   try:c=Configuration(bits,rate)
   except ValueError:continue
   baseline.append(dict(bits=bits,rate=rate,profiles=[(x.bits,x.period,x.node_pairs) for x in scan_profiles(c)]))
 (folder/'scan_profiles.before.json').write_text(json.dumps(baseline,indent=2)+'\n')
 proposal=dict(stage_only=True,accepted=False,candidate_identity=identity,sources={'app':source_manifest(folder/'oscilloscope'),'relay':source_manifest(folder/'relay')},qualified_candidates=candidates,pending=['exact same-app rollback','prebuild','paired backup','transactional deployment','installed regression'])
 (folder/'proposal.json').write_text(json.dumps(proposal,indent=2)+'\n');print(folder);return folder
if __name__=='__main__':stage()
