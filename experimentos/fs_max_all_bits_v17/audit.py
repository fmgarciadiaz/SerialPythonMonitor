"""Audit the complete restored continuation chain; never accesses the Q."""
import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from experimentos.fs_max_all_bits_v17.run import continuation_reports,EXP
STAGES=('screen60','acceptance_1','acceptance_2','acceptance_3')
def audit(path):
 latest=json.loads(Path(path).read_text())
 reports=continuation_reports(path,latest['source_hashes'],hashlib.sha256((EXP/'candidate_profiles.json').read_bytes()).hexdigest())
 for report in reports:
  if report.get('prior_identity')!=report.get('final_identity'):raise ValueError('Production firmware not restored')
 chain_paths=[str(path)]+[report['continuation_of'] for report in reports[:-1]]
 result={'scope':'ADC transport qualification only; no GUI/RADIO/A0/analog acceptance','reports':chain_paths,'candidate_identity':latest['candidate_identity'],'all_restored':True,'bits':{}}
 for bits in (8,10,12,14,16):
  rows={};controls={};baseline=[]
  for report in reports:
   for row in report['cases']:
    for stage in STAGES:
     name=f'adc{bits}_{stage}'
     if row['stage']==name:
      if stage in rows:raise ValueError('Repeated candidate stage; do not select successful repeats')
      rows[stage]=row
     if row['stage']==name+'_normal':controls[stage]=row
    if row['stage']==f'adc{bits}_baseline':baseline.append(row)
  integrity=(set(rows)==set(STAGES) and all(r.get('ok') for r in rows.values()) and
      set(controls)==set(STAGES) and all(r.get('ok') for r in controls.values()) and
      len(baseline)==1 and baseline[0].get('ok'))
  if bits==16:
   format_controls=[r for p in reports for r in p['cases'] if r['stage']=='adc16_ch1_format']
   integrity=integrity and len(format_controls)==1 and format_controls[0].get('ok')
  for name,row in rows.items():
   if row.get('ok'):
    expected=60 if name=='screen60' else 120
    if row['requested_seconds']!=expected or row['seconds']<expected:raise ValueError('Wrong duration')
    if row['adc']['bits']!=bits:raise ValueError('Wrong bits')
    if row['status'].get('dropped') or row['status'].get('fatal'):raise ValueError('Incorrect success with ADC error')
  margins=[r['metrics']['mean_send_headroom'] for r in rows.values() if r.get('metrics')]
  queues=[r['metrics']['maxima']['queue_peak'] for r in rows.values() if r.get('metrics')]
  result['bits'][str(bits)]={'integrity_ok':bool(integrity),'headroom_ok':bool(integrity and all(r.get('headroom_ok') for r in rows.values())),
      'stages':{name:{k:r.get(k) for k in ('ok','headroom_ok','requested_seconds','seconds','samples','error')} for name,r in rows.items()},
      'mean_send_headroom_range':([min(margins),max(margins)] if margins else None),'queue_peaks':queues,
      'completed_window_samples':sum(r.get('samples',0) or 0 for r in rows.values())}
 return result
if __name__=='__main__':
 path=Path(sys.argv[1]);result=audit(path)
 target=EXP/'qualification_summary.json';target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
