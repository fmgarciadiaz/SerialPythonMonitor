import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path.cwd();folder=root/'diagnosticos/resultados_v18'/time.strftime('fft_final_physical_%Y%m%d_%H%M%S');folder.mkdir()
paths=['monitor/v18/spectrum.py','monitor/v18/fft_cadence.py','tools/gui_live_smoke_v18.py','tools/probe_radio_rate_v18.py']
def hashes():return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
report=dict(ok=False,complete=False,cases=[],source_hashes=hashes(),hardware_changed=False)
def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
save();print(folder,flush=True)
for variant,extra in [('fixed10',['--fft-fixed-10']),('adaptive',[]),('adaptive_crop',['--crop-radios'])]:
 assert hashes()==report['source_hashes'],'Source drift during comparison'
 before=set((root/'diagnosticos/resultados_v18').glob('radio_rate_check_*'))
 command=[sys.executable,'tools/probe_radio_rate_v18.py','--bits','8','--ticks','86','--hold','120','--frequency-khz','550','--keep-display-awake','--fft-size','65536',*extra]
 print('BEGIN',variant,flush=True)
 with (folder/(variant+'.log')).open('w') as log:
  result=subprocess.run(command,env=dict(os.environ,MONITOR_V18_CHILD_STAGE_TIMING='1'),stdout=log,stderr=subprocess.STDOUT)
 added=set((root/'diagnosticos/resultados_v18').glob('radio_rate_check_*'))-before
 if len(added)!=1:raise RuntimeError('Missing unique case evidence')
 path=added.pop();g=json.loads((path/'report.json').read_text());e=json.loads((path/'gui.json').read_text())
 stages=[s for s in e['stages'] if s['stage']=='periodic' and s.get('radio_playing_seconds') is not None and s['radio_playing_seconds']>=10]
 intervals=[(b['fft_metrics']['completed']-a['fft_metrics']['completed'],b['elapsed']-a['elapsed']) for a,b in zip(stages,stages[1:]) if a['exposed'] and b['exposed']]
 total=sum(dt for _,dt in intervals)
 functional=not e['errors'] and all(e['assertions'].values()) and e['radio_hold_seconds']>=120
 restored=g.get('restoration',{}).get('hardware_restored') and g.get('identity_unchanged')
 row=dict(variant=variant,functional_ok=bool(functional),restored=bool(restored),visible_gui_ok=g.get('visible_gui_ok',False),exposed_fraction=g.get('exposed_fraction'),
  visible_analysis_hz=sum(n for n,_ in intervals)/total if total else None,visible_measurement_seconds=total,
  crop_active=any(s.get('fft_crop_active') for s in stages),evidence=str((path/'report.json').relative_to(root)),errors=e['errors'],identity=g.get('identity'))
 report['cases'].append(row);save();print('END',json.dumps(row),flush=True)
 if not functional or not restored:break
report['complete']=len(report['cases'])==3
report['functional_ok']=report['complete'] and all(c['functional_ok'] and c['restored'] for c in report['cases'])
report['ok']=report['functional_ok'] and all(c['visible_gui_ok'] for c in report['cases'])
assert hashes()==report['source_hashes']
save();print('FINAL',report['ok'],folder,flush=True)
