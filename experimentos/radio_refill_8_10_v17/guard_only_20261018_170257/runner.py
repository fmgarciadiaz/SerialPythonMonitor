"""Installed-host baseline and isolated per-source A0 refill qualification."""
import hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
from contextlib import nullcontext
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.unoq import Board,config_path
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from monitor.v17.board_owner import board_owner
from experimentos.radio_refill_8_10_v17.guard_only import GuardOnlySource as HighRateRadioDacSource
from diagnosticos.validar_generador_radio_v17 import main as audio_trial
import usb_stream

def main():
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None
 x.folder=Path(__file__).resolve().parent/('guard_only_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
 names=('monitor/v17/app.py','monitor/v17/processing.py','monitor/v17/radio_output.py','monitor/v17/radio_output_panel.py','monitor/v17/radio_loop_guard.py','monitor/v17/receiver/unoq_config_receiver.py','diagnosticos/validar_generador_radio_v17.py')
 hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
 x.report=dict(ok=False,restored=False,cases=[],source_hashes=hashes,scope='ADC10/1250000 and ADC8/1600000; baseline120 + candidate60/3x120, firmware unchanged')
 (x.folder/'runner.py').write_bytes(Path(__file__).read_bytes());x.save()
 subprocess.Popen(['/usr/bin/caffeinate','-dimsu','-w',str(os.getpid())])
 from PyQt6 import QtWidgets
 app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def recover():
  usb_stream.stop(x.board);x.board.start();x.start_relay(x.report['old_relay'],prior=True);x.restore_settings()
 def trial(bits,rate,stage,seconds,candidate):
  for name,digest in hashes.items():
   if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed source: '+name)
  print('BEGIN',bits,rate,stage,seconds,flush=True)
  row=dict(bits=bits,rate=rate,stage=stage,seconds=seconds,candidate=candidate,ok=False)
  try:
   sys.argv=['radio_refill','--bits',str(bits),'--rate',str(rate),'--seconds',str(seconds)]
   context=patch('monitor.v17.radio_output_panel.RadioDacSource',HighRateRadioDacSource) if candidate else nullcontext()
   with context:report,folder=audio_trial(owner_context=nullcontext())
   row.update(ok=report['ok'],report=str(folder/'report.json'),errors=report['errors'],queue_peak=report.get('adc_queue_peak'),statistics=report.get('joint_send_statistics'),transport_max_ms=report.get('transport_max_ms'),pump_gap_max_ms=report.get('pump_gap_max_ms'))
   if not report.get('restored'):raise RuntimeError('Individual recovery failed')
  except Exception as exc:
   row.update(error=repr(exc));x.report['cases'].append(row);x.save()
   try:x.logs('failure_'+str(bits)+'_'+stage+'.log')
   except Exception:pass
   recover();return False
  x.report['cases'].append(row);x.save();print('END',bits,stage,row['ok'],flush=True);return row['ok']
 with board_owner(x.board.serial,'Estabilidad A0 máximos8/10'):
  try:
   x.snapshot()
   info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus']);x.normal=x.policy();x.report['normal_policy']=x.normal;x.save()
   for bits,rate in ((10,1250000),):
    for stage,seconds in [('screen60',60)]+[('acceptance'+str(i),120) for i in (1,2,3)]:
     if not trial(bits,rate,stage,seconds,True):break
   x.report['ok']=all(len([v for v in x.report['cases'] if v['bits']==bits and v['candidate'] and v['ok']])==4 for bits in (10,))
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());raise
  finally:
   try:
    if x.report.get('prior'):
     try:x.restore_settings()
     except Exception:recover()
   except BaseException as exc:x.report.update(restored=False,restoration_error=repr(exc));raise
   finally:x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
