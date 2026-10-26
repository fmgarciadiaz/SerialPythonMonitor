import os,json,subprocess,sys,time
from pathlib import Path
root=Path.cwd();folder=root/'diagnosticos/resultados_v18'/time.strftime('fft_no_a0_%Y%m%d_%H%M%S');folder.mkdir()
report=dict(ok=False,scope='Raw RF only; no RADIO playback or A0; short FPS comparison',cases=[])
def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
save();print(folder,flush=True)
for name,extra in [('fixed10',['--fft-fixed-10']),('adaptive',[])]:
 before=set((root/'diagnosticos/resultados_v18').glob('radio_rate_check_*'))
 command=[sys.executable,'tools/probe_radio_rate_v18.py','--bits','8','--ticks','86','--hold','60','--frequency-khz','550','--keep-display-awake','--fft-size','65536','--fft-only','--crop-radios',*extra]
 with (folder/(name+'.log')).open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,MONITOR_V18_CHILD_STAGE_TIMING='1'))
 added=set((root/'diagnosticos/resultados_v18').glob('radio_rate_check_*'))-before;assert len(added)==1
 p=added.pop();g=json.loads((p/'report.json').read_text());e=json.loads((p/'gui.json').read_text())
 rows=[s for s in e['stages'] if s['stage']=='periodic' and (s.get('fft_live_seconds') or 0)>=10]
 intervals=[(b['fft_metrics']['completed']-a['fft_metrics']['completed'],b['elapsed']-a['elapsed']) for a,b in zip(rows,rows[1:]) if a['exposed'] and b['exposed']]
 seconds=sum(dt for _,dt in intervals)
 functional=not e['errors'] and all(e['assertions'].values()) and g.get('restoration',{}).get('hardware_restored') and g.get('identity_unchanged')
 row=dict(variant=name,functional_ok=bool(functional),visible_gui_ok=g.get('visible_gui_ok'),analysis_hz=sum(n for n,_ in intervals)/seconds if seconds else None,measurement_s=seconds,evidence=str((p/'report.json').relative_to(root)),errors=e['errors'])
 report['cases'].append(row);save();print('END',json.dumps(row),flush=True)
 if not functional:break
report['ok']=len(report['cases'])==2 and all(r['functional_ok'] and r['visible_gui_ok'] for r in report['cases']);save();print('FINAL',report['ok'],folder,flush=True)
