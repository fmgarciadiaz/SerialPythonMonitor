"""Promote the exact restored 60+3x120 RADIO14 experiment; no MCU edits."""
import argparse,hashlib,json,sys,time,traceback,subprocess,os
from pathlib import Path
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.radio14_refill_v17.run import EXP,RelayCampaign,Board,config_path,board_owner,instrument_identity,audio_trial,usb_stream
from monitor.relay_identity import relay_digest

def evidence(path):
 r=json.loads(path.read_text())
 if not(r.get('ok') and r.get('restored') and r.get('recovery',{}).get('ok') and r.get('prior_identity')==r.get('final_identity')):raise ValueError('Campaign incomplete or unrestored')
 for stage,seconds in [('screen60',60)]+[('acceptance'+str(i),120) for i in (1,2,3)]:
  rows=[v for v in r['cases'] if v['stage']==stage]
  if len(rows)!=1 or not rows[0]['ok'] or rows[0]['rate']!=851063 or rows[0]['seconds']!=seconds:raise ValueError('Missing physical acceptance')
  audio=json.loads(Path(rows[0]['report']).read_text())
  if not(audio['ok'] and audio['restored'] and not audio['errors'] and audio['identity_before']==r['prior_identity']):raise ValueError('Invalid audio evidence')
 for name,digest in r['source_hashes'].items():
  if hashlib.sha256((EXP/'relay'/name).read_bytes()).hexdigest()!=digest:raise ValueError('Candidate changed')
  if name!='cpu_profile.h' and hashlib.sha256((ROOT/'arduino/v17/relay'/name).read_bytes()).hexdigest()!=digest:raise ValueError('Unrelated production change')
 for name,digest in r['host_hashes'].items():
  if hashlib.sha256((EXP/name).read_bytes()).hexdigest()!=digest:raise ValueError('Host candidate changed')
 return r

def main():
 parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);a=parser.parse_args();accepted=evidence(a.report)
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None
 x.folder=EXP/('installation_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
 x.report=dict(ok=False,installed=False,restored=False,cases=[],acceptance=str(a.report));x.save();changed=False;local_changed=False
 production=ROOT/'arduino/v17/relay/cpu_profile.h'
 targets=[production,ROOT/'monitor/v17/radio_output.py',ROOT/'monitor/v17/radio_loop_guard.py',ROOT/'tests/v17/test_radio_credit_recovery.py',ROOT/'tests/v17/test_radio_combined_limit.py']
 prior_local={str(p.relative_to(ROOT)):p.read_bytes() for p in targets}
 for name,data in prior_local.items():
  backup=x.folder/'prior_sources'/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(data)
 from PyQt6 import QtWidgets
 app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 with board_owner(x.board.serial,'Instalar política CPU/envío RADIO14 validada'):
  try:
   x.snapshot()
   if x.report['prior_identity']!=accepted['prior_identity']:raise ValueError('MCU identity drift')
   info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus']);x.normal=x.policy();x.report['normal_policy']=x.normal;x.save()
   candidate_binary=accepted['candidate_relay'];digest=accepted['candidate_relay_sha256']
   if x.board.shell('sha256sum',candidate_binary,capture=True).stdout.split()[0]!=digest:raise ValueError('Candidate binary changed')
   local_changed=True
   production.write_bytes((EXP/'relay/cpu_profile.h').read_bytes())
   source=(EXP/'radio_source.py').read_text().replace('from experimentos.radio14_refill_v17.radio_guard import RadioLoopGuard','from monitor.v17.radio_loop_guard import RadioLoopGuard')
   source=source.replace('usar adquisición de hasta 599,25 kHz','usar adquisición de hasta 851,063 kHz')
   (ROOT/'monitor/v17/radio_output.py').write_text(source)
   (ROOT/'monitor/v17/radio_loop_guard.py').write_bytes((EXP/'radio_guard.py').read_bytes())
   credit_test=ROOT/'tests/v17/test_radio_credit_recovery.py'
   text=credit_test.read_text().replace('((100.096,8),(100.192,16),(100.288,24),(100.384,30))','((100.096,16),(100.192,30),(100.288,30),(100.384,30))').replace('96 ms allows eight chunks each turn.','96 ms allows up to sixteen chunks each turn.')
   credit_test.write_text(text)
   (ROOT/'tests/v17/test_radio_combined_limit.py').write_bytes((EXP/'test_combined_limit_promoted.py').read_bytes())
   checks=['tests.v17.test_radio_combined_limit','tests.v17.test_radio_output' ,'tests.v17.test_radio_output_rates','tests.v17.test_radio_filter_output','tests.v17.test_radio_loop_guard','tests.v17.test_radio_credit_recovery','tests.v17.test_radio_autogain']
   with (x.folder/'local_tests.log').open('w') as log:
    subprocess.run([sys.executable,'-m','unittest',*checks],cwd=ROOT,env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},stdout=log,stderr=subprocess.STDOUT,check=True)
   target='/home/arduino/.cache/serialmonitor/usb-stream-'+relay_digest(ROOT/'arduino/v17/relay')+'/unoq_stream'
   x.board.shell('mkdir','-p',target.rsplit('/',1)[0]);x.board.shell('cp',candidate_binary,target)
   if x.board.shell('sha256sum',target,capture=True).stdout.split()[0]!=digest:raise ValueError('Binary copy mismatch')
   usb_stream.stop(x.board);changed=True;x.board.start();x.start_relay(target)
   x.report.update(installed_relay=target,relay_sha256=digest);x.save()
   for bits,rate,audio_rate in ((14,833333,40000),(14,851063,40000),(8,1600000,40000),(10,1250000,40000),(12,1066666,40000),(14,851063,20000)):
    sys.argv=['radio14_install','--bits',str(bits),'--rate',str(rate),'--seconds','60','--audio-rate',str(audio_rate)]
    report,folder=audio_trial(owner_context=nullcontext());x.report['cases'].append(dict(bits=bits,rate=rate,audio_rate=audio_rate,ok=report['ok'],audio_report=str(folder/'report.json')));x.save()
    if not report['ok']:raise ValueError('Final RADIO14 failed: '+str(rate))
   x.restore_settings()
   if not x.report['recovery']['ok']:raise ValueError('Recovery failed')
   x.report.update(ok=True,installed=True)
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());x.save();raise
  finally:
   if not x.report['ok']:
    if local_changed:
     for name,data in prior_local.items():(ROOT/name).write_bytes(data)
    if changed:
     usb_stream.stop(x.board);x.board.start();x.start_relay(x.report['old_relay'],prior=True)
    if x.report.get('prior'):x.restore_settings()
   x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
