"""Reversible ADC14 RADIO+A0 CPU/send policy experiment; MCU unchanged."""
import hashlib,json,os,subprocess,sys,time,traceback,zipfile
from pathlib import Path
from contextlib import nullcontext,ExitStack
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.radio14_nodes_v17 import radio_source as candidate
from tools.unoq import Board,config_path
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from monitor.v17.board_owner import board_owner
from monitor.v17.bode_calibration import instrument_identity
from diagnosticos.validar_generador_radio_v17 import main as audio_trial
from monitor.v17.receiver import unoq_native
import usb_stream
FILES=("native_profiles.h","high_rate_profile.h")
PROFILE=dict(bits=14,channels=1,ticks=188,node_pairs=5952,optimized_transport=True,internal_only=True,headroom=False)

def main():
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None
 x.folder=EXP/('probe_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
 x.sources=sorted(p for p in (EXP/'relay').iterdir() if p.is_file())
 x.report=dict(ok=False,restored=False,cases=[],scope='ADC14 CH1 RADIO+A0; CPU/send + burst16 + loop correlation outside audio lock',host_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (EXP/'radio_source.py',EXP/'radio_guard.py')},mcu_hashes={n:hashlib.sha256((EXP/'oscilloscope/sketch'/n).read_bytes()).hexdigest() for n in FILES},profile=PROFILE,source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in x.sources})
 (x.folder/'runner.py').write_bytes(Path(__file__).read_bytes())
 with zipfile.ZipFile(x.folder/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in x.sources:z.write(p,p.name)
  for name in ('radio_source.py','radio_guard.py'):z.write(EXP/name,'host/'+name)
  for name in FILES:z.write(EXP/'oscilloscope/sketch'/name,'sketch/'+name)
 subprocess.Popen(['/usr/bin/caffeinate','-dimsu','-w',str(os.getpid())])
 x.save();changed=False
 from PyQt6 import QtWidgets
 app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def trial(stage,rate,seconds):
  print('BEGIN',stage,rate,seconds,flush=True)
  sys.argv=['radio14_trial','--bits','14','--rate',str(rate),'--seconds',str(seconds),'--audio-rate','40000']
  with ExitStack() as stack:
   if stage!='baseline599':
    stack.enter_context(patch.object(unoq_native,'PROFILES',tuple(p for p in unoq_native.PROFILES if not(p['bits']==14 and p['channels']==1 and p['ticks']==188))+(PROFILE,)))
    stack.enter_context(patch('monitor.v17.radio_output.RadioDacSource',candidate.RadioDacSource))
    stack.enter_context(patch('monitor.v17.radio_output_panel.RadioDacSource',candidate.RadioDacSource))
    stack.enter_context(patch('monitor.v17.radio_output_panel.acquisition_error',candidate.acquisition_error))
   report,folder=audio_trial(owner_context=nullcontext())
  stats=report.get('joint_send_statistics') or {}
  row=dict(stage=stage,rate=rate,seconds=seconds,ok=report['ok'],report=str(folder/'report.json'),queue_peak=report.get('adc_queue_peak'),statistics=stats)
  row['headroom_ok']=row['ok'] and stats.get('mean_margin',0)>=.1 and row['queue_peak']<4 and stats.get('minimum_slack_ticks',0)>0
  x.report['cases'].append(row);x.save()
  print('END',stage,'ok',row['ok'],'headroom',row['headroom_ok'],flush=True)
  if not row['ok']:raise RuntimeError('Audio integrity failed: '+stage)
 with board_owner(x.board.serial,'ADC14 RADIO+A0 política CPU/envío'):
  try:
   x.snapshot()
   info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus'])
   x.normal=x.policy();x.report['normal_policy']=x.normal;x.save()
   prior=x.folder/'prior_headers';prior.mkdir();presence={};x.report['prior_header_presence']=presence
   for name in FILES:
    x.board.run('pull',x.board.remote+'/sketch/'+name,str(prior/name));presence[name]=True
   x.save();usb_stream.stop(x.board);x.board.stop();changed=True;x.build()
   for name in FILES:x.board.run('push',str(EXP/'oscilloscope/sketch'/name),x.board.remote+'/sketch/'+name)
   x.report['candidate_relay_sha256']=x.board.shell('sha256sum',x.relay,capture=True).stdout.split()[0];x.save()
   usb_stream.stop(x.board);changed=True;x.board.start();x.start_relay(x.relay)
   identity=instrument_identity(x.board.serial)
   if identity is None or identity==x.report['prior_identity']:raise ValueError('Candidate MCU identity not distinct')
   x.report['candidate_identity']=identity;x.save()
   trial('screen60',851063,60)
   for i in (1,2,3):trial('acceptance'+str(i),851063,120)
   x.report['ok']=True
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());x.save()
   try:x.logs('failure_relay.log')
   except Exception:pass
   raise
  finally:
   if changed:
    usb_stream.stop(x.board);x.board.stop()
    for name in FILES:x.board.run('push',str(prior/name),x.board.remote+'/sketch/'+name)
    x.board.start();x.start_relay(x.report['old_relay'],prior=True)
   if x.report.get('prior'):x.restore_settings()
   x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
