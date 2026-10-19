"""Promote exact physically qualified ADC10/12 sources; never operates Q."""
import argparse,hashlib,json,shutil,time,zipfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from experimentos.otros_bits_crc_v17.run import FILES

def qualified_profiles(screen_path,acceptance_path):
 screen=json.loads(Path(screen_path).read_text());accepted=json.loads(Path(acceptance_path).read_text())
 for report in (screen,accepted):
  if report.get('target_bits')!=[10,12] or not(report.get('ok') and report.get('restored') and report.get('recovery',{}).get('ok')):
   raise ValueError('ADC10/12 campaign incomplete or unrestored')
  if any(report['recovery']['status'].get(key,1) for key in ('dropped','fatal')):raise ValueError('Recovery integrity failed')
  if report.get('prior_identity')!=report.get('final_identity') or not report.get('final_identity'):
   raise ValueError('Original firmware identity not restored')
 if screen['source_hashes']!=accepted['source_hashes'] or screen['candidate_identity']!=accepted['candidate_identity']:
  raise ValueError('Screen and acceptance source/binary identity differ')
 expected={'sketch/'+name for name in FILES}|{'relay/'+p.name for p in (EXP/'relay').iterdir() if p.is_file()}
 if set(accepted['source_hashes'])!=expected:raise ValueError('Candidate source inventory incomplete')
 for key,digest in accepted['source_hashes'].items():
  source=EXP/('oscilloscope/'+key if key.startswith('sketch/') else key)
  if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('Candidate changed: '+key)
 profiles=json.loads((EXP/'candidate_profiles.json').read_text());result=[]
 if sorted(p['bits'] for p in profiles)!=[10,12]:raise ValueError('Candidate resolutions differ from active scope')
 for profile in profiles:
  bits=profile['bits']
  if bits not in (10,12) or profile['channels']!=1:raise ValueError('Deferred resolution in candidate')
  stages=[(screen,'screen60',60)]+[(accepted,'acceptance_'+str(i),120) for i in (1,2,3)]
  for report,stage,seconds in stages:
   rows=[r for r in report['cases'] if r['stage']=='adc'+str(bits)+'_'+stage]
   if len(rows)!=1:raise ValueError('Missing or repeated acceptance stage')
   r=rows[0];m=r.get('metrics',{});maxima=m.get('maxima',{})
   if not(r.get('ok') and r.get('headroom_ok') and r.get('seconds',0)>=seconds and
          r.get('requested_seconds')==seconds and r.get('adc')=={'bits':bits,'rate':160000000//profile['ticks']} and
          r.get('node_pairs')==profile['node_pairs'] and r.get('period')==profile['ticks'] and
          r.get('scheduler')=={'policy':1,'priority':10} and
          abs(r.get('wall_monotonic_drift_seconds',99))<=2 and
          not any(r['status'].get(k,1) for k in ('dropped','fatal')) and
          m.get('mean_send_headroom',0)>=.1 and maxima.get('queue_peak',99)<4 and maxima.get('slack_ticks',0)>0):
    raise ValueError('Invalid integrity/headroom evidence: ADC'+str(bits)+' '+stage)
  p={k:v for k,v in profile.items() if k not in ('internal_only','validation','headroom')}
  p.update(headroom=True,isolated_headroom=True,optimized_transport=True,validation='physical_60s_3x120s',
           acceptance_seconds=[60,120,120,120],evidence=str(Path(acceptance_path).resolve().relative_to(ROOT)),
           screening_evidence=str(Path(screen_path).resolve().relative_to(ROOT)),
           firmware_sha256=accepted['candidate_identity']['firmware_sha256'],headroom_scope='ADC only; joint RADIO measured separately')
  result.append(p)
 return result,accepted

def main():
 p=argparse.ArgumentParser();p.add_argument('screen',type=Path);p.add_argument('acceptance',type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
 profiles,evidence=qualified_profiles(a.screen,a.acceptance)
 if a.apply:
  backup=EXP/('local_integration_'+time.strftime('%Y%m%d_%H%M%S'));backup.mkdir()
  targets=[ROOT/('arduino/v17/oscilloscope/'+key if key.startswith('sketch/') else 'arduino/v17/'+key) for key in evidence['source_hashes']]
  targets.append(ROOT/'monitor/v17/receiver/native_profiles.json')
  targets.append(ROOT/'arduino/v17/tests/radio_test_backend.h')
  (backup/'presence.json').write_text(json.dumps({str(v.relative_to(ROOT)):v.exists() for v in targets},indent=2)+'\n')
  with zipfile.ZipFile(backup/'prior_sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
   for target in targets:
    if target.exists():archive.write(target,target.relative_to(ROOT))
  for key in evidence['source_hashes']:
   source=EXP/('oscilloscope/'+key if key.startswith('sketch/') else key)
   target=ROOT/('arduino/v17/oscilloscope/'+key if key.startswith('sketch/') else 'arduino/v17/'+key)
   target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
  path=ROOT/'monitor/v17/receiver/native_profiles.json';current=json.loads(path.read_text())
  for profile in profiles:
   key=lambda v:(v['bits'],v['channels'],v['ticks'],v['node_pairs'])
   old=next((v for v in current if key(v)==key(profile)),None)
   if old is None:current.append(profile)
   else:old.update(profile)
  path.write_text(json.dumps(current,indent=2)+'\n')
  shutil.copyfile(ROOT/'experimentos/radio_dac_headroom_v17/tests/radio_test_backend.h',ROOT/'arduino/v17/tests/radio_test_backend.h')
 print(json.dumps(profiles,indent=2))
if __name__=='__main__':main()
