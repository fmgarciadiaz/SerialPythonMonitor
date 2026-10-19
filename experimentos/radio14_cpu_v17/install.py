"""Promote the exact restored 60+3x120 RADIO14 experiment; no MCU edits."""
import argparse,hashlib,json,sys,time,traceback
from pathlib import Path
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.radio14_cpu_v17.run import EXP,RelayCampaign,Board,config_path,board_owner,instrument_identity,audio_trial,usb_stream
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
 return r

def main():
 parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);a=parser.parse_args();accepted=evidence(a.report)
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None
 x.folder=EXP/('installation_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
 x.report=dict(ok=False,installed=False,restored=False,cases=[],acceptance=str(a.report));x.save();changed=False;local_changed=False
 production=ROOT/'arduino/v17/relay/cpu_profile.h';prior_local=production.read_bytes();(x.folder/'prior_cpu_profile.h').write_bytes(prior_local)
 from PyQt6 import QtWidgets
 app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 with board_owner(x.board.serial,'Instalar política CPU/envío RADIO14 validada'):
  try:
   x.snapshot()
   if x.report['prior_identity']!=accepted['prior_identity']:raise ValueError('MCU identity drift')
   info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus']);x.normal=x.policy();x.report['normal_policy']=x.normal;x.save()
   source=accepted['candidate_relay'];digest=accepted['candidate_relay_sha256']
   if x.board.shell('sha256sum',source,capture=True).stdout.split()[0]!=digest:raise ValueError('Candidate binary changed')
   production.write_bytes((EXP/'relay/cpu_profile.h').read_bytes());local_changed=True
   target='/home/arduino/.cache/serialmonitor/usb-stream-'+relay_digest(ROOT/'arduino/v17/relay')+'/unoq_stream'
   x.board.shell('mkdir','-p',target.rsplit('/',1)[0]);x.board.shell('cp',source,target)
   if x.board.shell('sha256sum',target,capture=True).stdout.split()[0]!=digest:raise ValueError('Binary copy mismatch')
   usb_stream.stop(x.board);changed=True;x.board.start();x.start_relay(target)
   x.report.update(installed_relay=target,relay_sha256=digest);x.save()
   for rate in (833333,851063):
    sys.argv=['radio14_install','--bits','14','--rate',str(rate),'--seconds','60']
    report,folder=audio_trial(owner_context=nullcontext());x.report['cases'].append(dict(rate=rate,ok=report['ok'],audio_report=str(folder/'report.json')));x.save()
    if not report['ok']:raise ValueError('Final RADIO14 failed: '+str(rate))
   x.restore_settings()
   if not x.report['recovery']['ok']:raise ValueError('Recovery failed')
   x.report.update(ok=True,installed=True)
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());x.save();raise
  finally:
   if not x.report['ok']:
    if local_changed:production.write_bytes(prior_local)
    if changed:
     usb_stream.stop(x.board);x.board.start();x.start_relay(x.report['old_relay'],prior=True)
    if x.report.get('prior'):x.restore_settings()
   x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
