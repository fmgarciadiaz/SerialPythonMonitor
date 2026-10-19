"""Promote qualified ADC14/N5952 MCU, relay and host; full rollback on failure."""
import argparse,hashlib,json,sys,time,traceback,subprocess,os
from pathlib import Path
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.radio14_nodes_v17.run import EXP,RelayCampaign,Board,config_path,board_owner,instrument_identity,audio_trial,usb_stream,FILES,PROFILE
from monitor.relay_identity import relay_digest

def evidence(path):
 r=json.loads(path.read_text())
 if not(r.get('ok') and r.get('restored') and r.get('recovery',{}).get('ok') and r.get('prior_identity')==r.get('final_identity')):raise ValueError('Campaign incomplete or unrestored')
 for stage,seconds in [('screen60',60)]+[('acceptance'+str(i),120) for i in (1,2,3)]:
  rows=[v for v in r['cases'] if v['stage']==stage]
  if len(rows)!=1 or not rows[0]['ok'] or not rows[0].get('headroom_ok') or rows[0]['rate']!=851063 or rows[0]['seconds']!=seconds:raise ValueError('Missing physical integrity/headroom acceptance')
  audio=json.loads(Path(rows[0]['report']).read_text())
  if not(audio['ok'] and audio['restored'] and not audio['errors'] and audio['identity_before']==r['candidate_identity']):raise ValueError('Invalid audio evidence')
  status=audio.get('adc_status',{})
  if status.get('node_pairs')!=5952 or status.get('dropped',1) or status.get('fatal',1) or audio.get('requested_audio_seconds')!=seconds:raise ValueError('Wrong geometry or integrity evidence')
  stats=audio.get('joint_send_statistics',{})
  if stats.get('mean_margin',0)<.1 or audio.get('adc_queue_peak',99)>=4 or stats.get('minimum_slack_ticks',0)<=0:raise ValueError('Joint headroom evidence failed')
 for name,digest in r['source_hashes'].items():
  if hashlib.sha256((EXP/'relay'/name).read_bytes()).hexdigest()!=digest:raise ValueError('Candidate changed')
  if name not in ('cpu_profile.h','native_profiles.h','high_rate_profile.h') and hashlib.sha256((ROOT/'arduino/v17/relay'/name).read_bytes()).hexdigest()!=digest:raise ValueError('Unrelated production change')
 for name,digest in r['host_hashes'].items():
  if hashlib.sha256((EXP/name).read_bytes()).hexdigest()!=digest:raise ValueError('Host candidate changed')
 for name,digest in r['mcu_hashes'].items():
  if hashlib.sha256((EXP/'oscilloscope/sketch'/name).read_bytes()).hexdigest()!=digest:raise ValueError('MCU candidate changed')
 return r

def main():
 parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);a=parser.parse_args();accepted=evidence(a.report)
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None
 x.folder=EXP/('installation_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
 x.report=dict(ok=False,installed=False,restored=False,cases=[],acceptance=str(a.report));x.save();changed=False;local_changed=False
 registry_path=ROOT/'monitor/v17/receiver/native_profiles.json'
 production=ROOT/'arduino/v17/relay/cpu_profile.h'
 targets=[production,ROOT/'monitor/v17/radio_output.py',ROOT/'monitor/v17/radio_loop_guard.py',ROOT/'monitor/v17/radio_output_panel.py',ROOT/'tests/v17/test_radio_credit_recovery.py',ROOT/'tests/v17/test_radio_combined_limit.py']
 targets += [registry_path]+[ROOT/'arduino/v17/oscilloscope/sketch'/n for n in FILES]+[ROOT/'arduino/v17/relay'/n for n in FILES]
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
   prior_headers=x.folder/'prior_headers';prior_headers.mkdir()
   for name in FILES:x.board.run('pull',x.board.remote+'/sketch/'+name,str(prior_headers/name))
   local_changed=True
   production.write_bytes((EXP/'relay/cpu_profile.h').read_bytes())
   for name in FILES:
    (ROOT/'arduino/v17/relay'/name).write_bytes((EXP/'relay'/name).read_bytes())
    (ROOT/'arduino/v17/oscilloscope/sketch'/name).write_bytes((EXP/'oscilloscope/sketch'/name).read_bytes())
   registry=json.loads(registry_path.read_text())
   profile=next(v for v in registry if v['bits']==14 and v['channels']==1 and v['ticks']==188)
   joint_headroom=all(v.get('headroom_ok') for v in accepted['cases'])
   profile.update(node_pairs=5952,optimized_transport=True,headroom=joint_headroom,isolated_headroom=False,radio_a0_headroom=joint_headroom,validation='RADIO_A0_60s_3x120s',radio_a0_evidence=str(a.report),evidence=str(a.report),integrated_evidence=str(x.folder/'report.json'),headroom_scope='joint RADIO+A0 at40k; isolated ADC not separately qualified',firmware_sha256=accepted['candidate_identity']['firmware_sha256'])
   registry_path.write_text(json.dumps(registry,indent=2)+'\n')
   (ROOT/'monitor/v17/radio_output.py').write_bytes((EXP/'promoted_source.py').read_bytes())
   panel=ROOT/'monitor/v17/radio_output_panel.py'
   text=panel.read_text().replace('import RadioDacSource,acquisition_error','import RadioDacSource,HighRateRadioDacSource,acquisition_error')
   text=text.replace('        source=RadioDacSource(self.volume.value()/100,input_source=self.input_source.currentText(),rate=rate)',"        source_type=HighRateRadioDacSource if owner.applied_configuration.bits==14 and owner.applied_configuration.rate==851063 else RadioDacSource\n        source=source_type(self.volume.value()/100,input_source=self.input_source.currentText(),rate=rate)")
   panel.write_text(text)
   (ROOT/'monitor/v17/radio_loop_guard.py').write_bytes((EXP/'radio_guard.py').read_bytes())
   (ROOT/'tests/v17/test_radio_combined_limit.py').write_bytes((EXP/'test_combined_limit_promoted.py').read_bytes())
   checks=['tests.v17.test_native_profiles','tests.v17.test_optimized_profiles','tests.v17.test_radio_combined_limit','tests.v17.test_radio_output' ,'tests.v17.test_radio_output_rates','tests.v17.test_radio_filter_output','tests.v17.test_radio_loop_guard','tests.v17.test_radio_credit_recovery','tests.v17.test_radio_autogain']
   with (x.folder/'local_tests.log').open('w') as log:
    subprocess.run([sys.executable,'-m','unittest',*checks],cwd=ROOT,env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},stdout=log,stderr=subprocess.STDOUT,check=True)
   # This installer imported the GUI before promotion. Refresh its module
   # globals so physical tests exercise the new registry and host source.
   import importlib
   from monitor.v17.receiver import unoq_native
   from monitor.v17.receiver.unoq_config_decoder import _wire_configuration
   from monitor.v17 import radio_loop_guard,radio_output,radio_output_panel
   importlib.reload(unoq_native);importlib.reload(radio_loop_guard);importlib.reload(radio_output)
   _wire_configuration.cache_clear()
   radio_output_panel.RadioDacSource=radio_output.RadioDacSource
   radio_output_panel.HighRateRadioDacSource=radio_output.HighRateRadioDacSource
   radio_output_panel.acquisition_error=radio_output.acquisition_error
   importlib.reload(radio_output_panel)
   import monitor.v17.app as gui
   gui.RadioOutputPanel=radio_output_panel.RadioOutputPanel
   target='/home/arduino/.cache/serialmonitor/usb-stream-'+relay_digest(ROOT/'arduino/v17/relay')+'/unoq_stream'
   x.board.shell('mkdir','-p',target.rsplit('/',1)[0]);x.board.shell('cp',candidate_binary,target)
   if x.board.shell('sha256sum',target,capture=True).stdout.split()[0]!=digest:raise ValueError('Binary copy mismatch')
   usb_stream.stop(x.board);x.board.stop();changed=True
   for name in FILES:x.board.run('push',str(EXP/'oscilloscope/sketch'/name),x.board.remote+'/sketch/'+name)
   x.board.start();x.start_relay(target)
   if instrument_identity(x.board.serial)!=accepted['candidate_identity']:raise ValueError('Installed MCU differs from qualified identity')
   x.report.update(installed_relay=target,relay_sha256=digest);x.save()
   for bits,rate,audio_rate in ((14,833333,40000),(14,851063,40000),(8,1600000,40000),(10,1250000,40000),(12,1066666,40000),(14,851063,20000)):
    sys.argv=['radio14_install','--bits',str(bits),'--rate',str(rate),'--seconds','60','--audio-rate',str(audio_rate)]
    if audio_rate==20000:sys.argv.append('--filter-input')
    report,folder=audio_trial(owner_context=nullcontext());x.report['cases'].append(dict(bits=bits,rate=rate,audio_rate=audio_rate,ok=report['ok'],audio_report=str(folder/'report.json')));x.save()
    if not report['ok']:raise ValueError('Final RADIO14 failed: '+str(rate))
   prior_identity=x.report['prior_identity'];x.report['prior_identity']=accepted['candidate_identity']
   try:x.restore_settings()
   finally:x.report['prior_identity']=prior_identity
   if not x.report['recovery']['ok']:raise ValueError('Recovery failed')
   x.report.update(ok=True,installed=True)
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());x.save();raise
  finally:
   try:
    if not x.report['ok']:
     if local_changed:
      for name,data in prior_local.items():(ROOT/name).write_bytes(data)
      import importlib
      from monitor.v17.receiver import unoq_native
      from monitor.v17.receiver.unoq_config_decoder import _wire_configuration
      importlib.reload(unoq_native);_wire_configuration.cache_clear()
     if changed:
      usb_stream.stop(x.board);x.board.stop()
      for name in FILES:x.board.run('push',str(prior_headers/name),x.board.remote+'/sketch/'+name)
      x.board.start();x.start_relay(x.report['old_relay'],prior=True)
     if x.report.get('prior'):x.restore_settings()
   except BaseException as exc:
    x.report.update(restored=False,restoration_error=repr(exc));raise
   finally:
    x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
