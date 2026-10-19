"""Publish only the scoped ADC8/CH1 1.4035 MHz profile from complete V16 evidence."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STAGES=('finalist','acceptance_1','acceptance_2','acceptance_3','endurance')
def sync(path):
 report=json.loads(path.read_text())
 if not (report.get('ok') and report.get('restored') and report.get('recovery',{}).get('ok')):
  raise ValueError('Integration report is incomplete or unrestored')
 rows=[r for r in report['cases'] if r['adc']=={'bits':8,'rate':1403508}]
 if [r['stage'] for r in rows]!=list(STAGES):raise ValueError('Missing independent acceptance stages')
 for r,seconds in zip(rows,(60,120,120,120,600)):
  if not r['ok'] or r['seconds']<seconds or r['status']['dropped'] or r['status']['fatal']:
   raise ValueError('Invalid physical acceptance')
 headroom=all(r.get('headroom_ok',False) for r in rows)
 target=ROOT/'monitor/v16/receiver/native_profiles.json';profiles=json.loads(target.read_text())
 profile={'bits':8,'ticks':114,'node_pairs':3456,'channels':1,'headroom':headroom,
          'isolated_headroom':True,'historical_queue_peak':4,
          'evidence':str(path.relative_to(ROOT))}
 position=next((i for i,p in enumerate(profiles) if (p['bits'],p['ticks'],p['node_pairs'],p['channels'])==(8,114,3456,1)),len(profiles))
 if position==len(profiles):profiles.append(profile)
 else:profiles[position]=profile
 target.write_text(json.dumps(profiles,indent=2)+'\n')
 for folder in ('arduino/v16/oscilloscope/sketch','arduino/v16/relay'):
  header=ROOT/folder/'native_profiles.h';text=header.read_text()
  if not re.search(r'\{\s*8\s*,\s*1\s*,\s*114\s*,\s*3456\s*\}',text):
   text=text.replace('static const ScopeNativeProfile scope_native_profiles[] = {','static const ScopeNativeProfile scope_native_profiles[] = {\n    {8, 1, 114, 3456},')
   header.write_text(text)
 print('Scoped ADC8/CH1 profile synchronized; production headroom=',headroom)
 return profile
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);args=parser.parse_args();sync(args.report.resolve())
