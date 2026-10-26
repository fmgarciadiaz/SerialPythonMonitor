"""Stage a catalogue proposal only after physical integration and GUI evidence."""
import argparse,hashlib,json,shutil,time
from pathlib import Path
from experimentos.fs_max_v18.probe_journal import source_manifest
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent

def stage(gui_report):
 audio_path=EXP/'resultados/20261025_194759/report.json';bridge_path=EXP/'resultados/20261025_201421/report.json';integration_path=EXP/'resultados/20261025_203801/report.json'
 audio=json.loads(audio_path.read_text());bridges=json.loads(bridge_path.read_text());integration=json.loads(integration_path.read_text());gui=json.loads(Path(gui_report).read_text())
 for report,count in ((audio,17),(bridges,15),(integration,17)):
  if not(report['ok'] and report['restoration']['hardware_restored'] and len(report['cases'])==count and all(c['ok'] and c['headroom_ok'] for c in report['cases'])):raise ValueError('Incomplete physical evidence')
 if not(gui['ok'] and len(gui['cases'])==10 and all(c['hardware_restored'] and c['visible_gui_ok'] for c in gui['cases'])):raise ValueError('Incomplete GUI evidence')
 identity={key:bridges['cases'][0]['candidate_identity'][key] for key in ('firmware_sha256','relay_sha256')}
 for c in integration['cases']:
  if any(c['candidate_identity'][key]!=identity[key] for key in identity):raise ValueError('Integration identity mismatch')
 for row in gui['cases']:
  g=json.loads((ROOT/row['evidence']).read_text())
  if any(g['candidate_identity'][key]!=identity[key] for key in identity):raise ValueError('GUI identity mismatch')
 if source_manifest(ROOT/'arduino/v18')!=json.loads((EXP/'catalog/source_manifest.json').read_text()):raise ValueError('Production source drift')
 folder=EXP/('release_catalog_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 for name in ('oscilloscope','relay'):shutil.copytree(EXP/'catalog'/name,folder/name,ignore=shutil.ignore_patterns('.cache','__pycache__','.DS_Store'))
 profiles=json.loads((ROOT/'monitor/v18/receiver/native_profiles.json').read_text());additions=json.loads((EXP/'catalog/candidate_profiles.json').read_text())
 for p in additions:
  audio_profile=bool(p.get('nominal_rate'));physical=audio if audio_profile else bridges;source=audio_path if audio_profile else bridge_path
  rows=[c for c in physical['cases'] if (c['bits'],c['channels'],c['ticks'],c['node_pairs'])==(p['bits'],p['channels'],p['ticks'],p['node_pairs'])]
  if len(rows)!=1 or rows[0]['seconds']!=60:raise ValueError('Missing exact 60-second case')
  entry=dict(p);entry.pop('internal_only');entry.update(headroom=True,isolated_headroom=True,validation='60s',purpose='audio' if audio_profile else 'intermediate',evidence=str(source.relative_to(ROOT)),catalog_profile=True,analog_enob_qualified=False,headroom_scope='ADC only; representative GUI/audio tested separately',catalog_gui_evidence=str(Path(gui_report).relative_to(ROOT)))
  if audio_profile:entry['integration_evidence']=str(integration_path.relative_to(ROOT))
  profiles.append(entry)
 (folder/'native_profiles.proposed.json').write_text(json.dumps(profiles,indent=2)+'\n')
 shutil.copyfile(EXP/'audio_catalog/catalog.proposed.json',folder/'rate_catalog.proposed.json')
 from monitor.v18.receiver.unoq_acquisition import Configuration,RATES
 from monitor.v18.radio_multiscan import scan_profiles
 before=[]
 for bits in (8,10,12,14,16):
  for rate in RATES:
   try:config=Configuration(bits,rate)
   except ValueError:continue
   before.append(dict(bits=bits,rate=rate,profiles=[(c.bits,c.period,c.node_pairs) for c in scan_profiles(config)]))
 (folder/'scan_profiles.before.json').write_text(json.dumps(before,indent=2)+'\n')
 proposal=dict(stage_only=True,accepted=False,candidate_identity=identity,sources={'app':source_manifest(folder/'oscilloscope'),'relay':source_manifest(folder/'relay')},physical_audio=str(audio_path.relative_to(ROOT)),physical_bridges=str(bridge_path.relative_to(ROOT)),integrated_audio=str(integration_path.relative_to(ROOT)),gui_report=str(Path(gui_report).relative_to(ROOT)),public_profile_count_added=len(additions),pending=['rollback exact binary pair','prebuild','paired backup','transactional deployment','installed catalogue matrix'])
 (folder/'proposal.json').write_text(json.dumps(proposal,indent=2)+'\n');print(folder);return folder
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--gui-report',type=Path,required=True);args=parser.parse_args();stage(args.gui_report.resolve())
