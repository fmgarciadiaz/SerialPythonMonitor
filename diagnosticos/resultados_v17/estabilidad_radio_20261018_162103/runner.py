"""One-owner RADIO+A0 stability matrix on installed firmware, exact recovery."""
import hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.unoq import Board,config_path
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from monitor.v17.board_owner import board_owner
from monitor.v17.bode_calibration import instrument_identity
from diagnosticos.validar_generador_radio_v17 import main as audio_trial
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_switch import Mode
import usb_stream

RATES={8:(100000,1403508,1600000),10:(100000,909090,1250000),12:(100000,930232,1066666),16:(40000,50000,76226)}

def main():
 selected=int(sys.argv[sys.argv.index('--bits')+1]) if '--bits' in sys.argv else None
 gain_only='--gain-only' in sys.argv
 rates_matrix={bits:rates for bits,rates in RATES.items() if selected is None or bits==selected}
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None
 x.folder=ROOT/'diagnosticos/resultados_v17'/('estabilidad_radio_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
 names=('monitor/v17/app.py','monitor/v17/processing.py','monitor/v17/radio_output.py','monitor/v17/radio_output_panel.py','monitor/v17/radio_loop_guard.py','monitor/v17/receiver/unoq_config_receiver.py')
 hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
 x.report=dict(ok=False,restored=False,cases=[],host_hashes=hashes,scope='Installed firmware; RADIO+A0, low/mid/max, gain stress, FILTER20k, max120s')
 (x.folder/'runner.py').write_bytes(Path(__file__).read_bytes());x.save()
 subprocess.Popen(['/usr/bin/caffeinate','-dimsu','-w',str(os.getpid())])
 from PyQt6 import QtWidgets
 app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def recover():
  # A failed relay cannot attach to an advanced acquisition epoch.
  usb_stream.stop(x.board);x.board.start();x.start_relay(x.report['old_relay'],prior=True)
  x.restore_settings()
 def trial(bits,rate,phase,seconds=60,audio_rate=40000,filtered=False,gain=False):
  row=dict(bits=bits,rate=rate,phase=phase,seconds=seconds,audio_rate=audio_rate,input='FILTER' if filtered else 'RADIO',gain_stress=gain,ok=False)
  print('BEGIN',row,flush=True)
  try:
   for name,digest in hashes.items():
    if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Host changed during measurement: '+name)
   sys.argv=['validar_generador_radio_v17','--bits',str(bits),'--rate',str(rate),'--seconds',str(seconds),'--audio-rate',str(audio_rate)]
   if filtered:sys.argv.append('--filter-input')
   if gain:sys.argv.append('--gain-stress')
   report,folder=audio_trial(owner_context=nullcontext())
   stats=report.get('joint_send_statistics') or {}
   row.update(ok=report['ok'],report=str(folder/'report.json'),errors=report['errors'],source_error=report.get('source_error'),queue_peak=report.get('adc_queue_peak'),statistics=stats,old_generation_audio_samples=report.get('old_generation_audio_samples',0),buffer_minimum=report.get('source_buffer_minimum'))
   row['headroom_ok']=(stats['mean_margin']>=.1 and row['queue_peak']<4 and stats['minimum_slack_ticks']>0) if stats else None
   if report.get('identity_after')!=x.report['prior_identity']:raise RuntimeError('Firmware identity drift')
   if not report.get('restored'):raise RuntimeError('Individual trial not restored')
  except BaseException as exc:
   row.update(error=repr(exc),traceback=traceback.format_exc());x.report['cases'].append(row);x.save()
   try:x.logs('failure_'+str(bits)+'_'+phase+'.log')
   except Exception:pass
   recover()
   print('END failed/recovered',bits,rate,phase,flush=True)
   return
  x.report['cases'].append(row);x.save()
  print('END',bits,rate,phase,'ok',row['ok'],'headroom',row.get('headroom_ok'),flush=True)
 with board_owner(x.board.serial,'Estabilidad RADIO+A0 otros bits/tasas'):
  try:
   x.snapshot()
   info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus']);x.normal=x.policy();x.report['normal_policy']=x.normal;x.save()
   if gain_only:
    for bits,rates in rates_matrix.items():trial(bits,rates[0],'low_gain40',gain=True)
   else:
    for bits,rates in rates_matrix.items():trial(bits,rates[-1],'max40')
    for bits,rates in rates_matrix.items():
     trial(bits,rates[1],'mid40')
     trial(bits,rates[0],'low_gain40',gain=True)
     trial(bits,rates[-1],'filter20',audio_rate=20000,filtered=True)
    for bits,rates in rates_matrix.items():
     if any(v['bits']==bits and v['phase']=='max40' and v['ok'] for v in x.report['cases']):trial(bits,rates[-1],'max120',seconds=120)
   x.report['ok']=all(v['ok'] for v in x.report['cases'])
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());raise
  finally:
   try:
    if x.report.get('prior'):
     try:x.restore_settings()
     except Exception:recover()
   except BaseException as exc:
    x.report.update(restored=False,restoration_error=repr(exc));raise
   finally:
    x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
