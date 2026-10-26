import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path.cwd();folder=root/'diagnosticos/resultados_v18'/time.strftime('radio_rates_review_%Y%m%d_%H%M%S');folder.mkdir()
profiles=json.loads((root/'monitor/v18/receiver/native_profiles.json').read_text());new=[p for p in profiles if p.get('catalog_profile')];assert len(new)==32
# Distinguish the broad regression from sustained maximum-rate controls.
cases=[(p,30,'new') for p in new]
for bits in (8,10,12,14,16):
 p=max((p for p in profiles if p['bits']==bits and not p.get('internal_only') and not p.get('integration_pending')),key=lambda p:160000000/p['ticks'])
 cases.append((p,120,'previous_maximum'))
report=dict(ok=False,complete=False,firmware_changed=False,rate_methods_changed=False,cases=[],expected_cases=len(cases),scope='30s per new rate with RADIO/A0; 120s maximum controls; visible GUI evaluated separately')
def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
save();print(folder,flush=True)
control=root/'diagnosticos/resultados_v18/adc8_max_radio_20261026_130130'
while True:
 p=control/'report.json';c=json.loads(p.read_text())
 if 'identity_unchanged' in c or 'restore_error' in c:break
 time.sleep(3)
initial=json.loads((control/'gui.json').read_text());assert not initial['errors'] and all(initial['assertions'].values()) and c['restoration']['hardware_restored'] and c['identity_unchanged'],c
report['initial_control']=str((control/'report.json').relative_to(root));save()
for profile,hold,kind in cases:
 bits,ticks=profile['bits'],profile['ticks'];before=set((root/'diagnosticos/resultados_v18').glob('radio_rate_check_*'));print('BEGIN',bits,ticks,kind,flush=True)
 command=[sys.executable,'tools/probe_radio_rate_v18.py','--bits',str(bits),'--ticks',str(ticks),'--hold',str(hold),'--frequency-khz','10' if 160000000/ticks<200000 else '550','--keep-display-awake']
 with (folder/f'{bits}_{ticks}.log').open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 added=set((root/'diagnosticos/resultados_v18').glob('radio_rate_check_*'))-before
 if len(added)!=1:raise RuntimeError('Missing unique case evidence')
 casefolder=added.pop();g=json.loads((casefolder/'report.json').read_text());e=json.loads((casefolder/'gui.json').read_text()) if (casefolder/'gui.json').exists() else {}
 restored=g.get('restoration',{}).get('hardware_restored',False) and g.get('identity_unchanged',False)
 functional=bool(e.get('assertions')) and not e.get('errors') and all(e['assertions'].values()) and restored
 row=dict(bits=bits,ticks=ticks,channels=profile['channels'],hold=hold,kind=kind,functional_ok=functional,visible_gui_ok=g.get('visible_gui_ok',False),restored=restored,evidence=str((casefolder/'report.json').relative_to(root)),errors=e.get('errors',[]),outer_error=g.get('error'),returncode=result.returncode)
 report['cases'].append(row)
 # Capture only between GUI owners; never compete with the acquisition child.
 from monitor.v18.q_support.board import Board,CONFIG
 from monitor.v18.board_owner import board_owner
 import shlex
 b=Board(json.loads(CONFIG.read_text()))
 with board_owner(b.serial,'RADIO rate review logs after child release'):
  r=subprocess.run([b.adb,'-s',b.serial,'shell',shlex.join(['docker','logs','--timestamps','--tail','35','serialmonitor-usb-stream-v18'])],capture_output=True,text=True)
  (casefolder/'relay_after.log').write_text(r.stdout+r.stderr)
 save();print('END',row,flush=True)
 if not functional:print('STOP: functional failure; evidence retained',flush=True);break
report['complete']=len(report['cases'])==len(cases)
report['ok']=report['complete'] and all(c['functional_ok'] for c in report['cases'])
report['visible_gui_ok']=report['complete'] and all(c['visible_gui_ok'] for c in report['cases'])
save();print('FINAL',report['ok'],folder,flush=True)
