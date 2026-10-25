"""Review restored joint reports, preserving blocked attempts and genuine failures."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
FIRST=EXP/'joint_20261020_094007/report.json';SECOND=EXP/'joint_20261020_094801/report.json'
MANUAL={'adc10_filter':ROOT/'diagnosticos/resultados_v17/generador_radio_20261020_094338/report.json'}
def audit():
 adc=json.loads((EXP/'qualification_summary.json').read_text())
 reference=json.loads((ROOT/adc['reports'][0]).read_text())
 review={'scope':'Joint screening: FFT60s per input and temporal FILTER30s; not prolonged combined or analog acceptance','restored':True,'reports':[str(FIRST.relative_to(ROOT)),str(SECOND.relative_to(ROOT))],'cases':[],'bits':{}}
 for path in (FIRST,SECOND):
  parent=json.loads(path.read_text())
  assert parent['restored'] and parent['recovery']['ok'] and parent['prior_identity']==parent['final_identity']
  assert parent['candidate_identity']==adc['candidate_identity']
  assert parent['source_hashes']==reference['source_hashes']
  assert parent['candidate_relay']==reference['candidate_relay']
  for row in parent['cases']:
   if 'child' not in row:continue
   child=row['child'];report_path=Path(child['report']) if child.get('report') else MANUAL.get(row['stage'])
   if report_path is None:raise ValueError('Missing child evidence: '+row['stage'])
   report=json.loads(report_path.read_text());bits=row['bits'];view=row.get('view','fft')
   assert report['adc']['bits']==bits and report['output_input']==row['input']
   assert report['identity_before']==adc['candidate_identity']
   blocked=bool(report.get('source_error') and report['source_error'].startswith('Radio A0: adquisición máxima') and not report.get('max_played'))
   paints=report.get('paint_audit',{});fps=paints.get('scope_fps' if view=='scope' else 'fft_fps',0)
   visible=paints.get('exposed_fraction',0)>=.9 and fps>=5
   passed=bool(report['ok'] and report['restored'] and row['child_exit']==0 and visible)
   stats=report.get('joint_send_statistics',{});queue=report.get('adc_queue_peak',99)
   headroom=passed and stats.get('mean_margin',0)>=.1 and queue<4 and stats.get('minimum_slack_ticks',0)>0
   review['cases'].append(dict(stage=row['stage'],bits=bits,input=row['input'],view=view,report=str(report_path.relative_to(ROOT)),blocked_before_play=blocked,
    passed=passed,headroom=headroom,errors=report['errors'],source_error=report.get('source_error'),seconds=report.get('paint_audit',{}).get('seconds'),
    max_played_samples=report.get('max_played',0),source_buffer_minimum=report.get('source_buffer_minimum'),mean_send_margin=stats.get('mean_margin'),queue_peak=queue,
    exposed_fraction=paints.get('exposed_fraction'),active_paints_per_second=fps,child_restored=report['restored']))
 for bits in (8,10,14,16):
  cases=[r for r in review['cases'] if r['bits']==bits and not r['blocked_before_play']]
  keys=[(r['input'],r['view']) for r in cases]
  if len(set(keys))!=len(keys):raise ValueError('Repeated actual trial; do not select successful repeats')
  complete=set(keys)=={('RADIO','fft'),('FILTER','fft'),('FILTER','scope')}
  review['bits'][str(bits)]={'complete_screen':complete,'joint_pass':complete and all(r['passed'] for r in cases),'joint_headroom':complete and all(r['headroom'] for r in cases),'actual_cases':len(cases),'has_actual_failure':any(not r['passed'] for r in cases)}
 review['notes']=['The first visual gate wrongly required the hidden temporal viewport to paint during FFT. Review uses the active view and preserves original reports.','Both private acquisition guards are extended only for exact qualified candidates; production guards were not edited.','ADC8 dropped1 with correct CRC and queue_peak8; see adc8_failure_frame_summary.json. ADC10 FILTER stream closed; no specific lower-level cause asserted.','ADC12 is excluded because it failed isolated qualification.']
 return review
if __name__=='__main__':
 report=audit();path=EXP/'joint_summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['bits'],indent=2))
