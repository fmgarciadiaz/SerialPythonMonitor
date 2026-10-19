"""Install qualified per-wave generator and verify final analog output; rollback on failure."""
import sys,json,time,shutil,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.generador_200k_v17.integrate import apply
from experimentos.generador_200k_v17.check_output import run as check_output
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from tools.unoq import Board,config_path
from monitor.v17.board_owner import board_owner
from monitor.v17.bode_calibration import instrument_identity
import usb_stream
EXP=Path(__file__).resolve().parent
FILES=('arduino/v17/tests/generator_timing.cpp','monitor/v17/app.py','monitor/v17/receiver/unoq_generator.py','arduino/v17/relay/config_relay_protocol.h','arduino/v17/oscilloscope/sketch/generator_protocol.h','arduino/v17/oscilloscope/sketch/generator_timing.h')
def main():
 evidence=Path(sys.argv[1]);x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None
 x.folder=EXP/('deployment_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir();x.report={'ok':False,'installed':False,'restored':False,'evidence':str(evidence)};changed=False
 with board_owner(x.board.serial,'Instalar generador ampliado validado'):
  try:
   x.snapshot();info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0];x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus']);x.save()
   backup=x.folder/'prior_local';backup.mkdir()
   for name in FILES:
    dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
   prior=x.folder/'prior_headers';prior.mkdir()
   for name in ('generator_protocol.h','generator_timing.h'):x.board.run('pull',x.board.remote+'/sketch/'+name,str(prior/name))
   apply(evidence);x.report['local_sources_updated']=True;x.save()
   import subprocess,os
   result=subprocess.run([sys.executable,'-m','unittest','experimentos.generador_200k_v17.test_limits','tests.v17.test_radio_test_generator','tests.v17.test_radio_autogain','tests.v17.test_wav_receiver_contract'],env=dict(os.environ,QT_QPA_PLATFORM='minimal'),capture_output=True,text=True)
   (x.folder/'local_tests.log').write_text(result.stdout+result.stderr)
   if result.returncode:raise RuntimeError('Local integration tests failed')
   subprocess.run(['c++','-std=c++17',str(ROOT/'arduino/v17/tests/generator_timing.cpp'),'-o','/tmp/generator_extended_test'],check=True)
   subprocess.run(['/tmp/generator_extended_test'],check=True)
   usb_stream.stop(x.board);x.board.stop();changed=True
   x.sources=sorted(p for p in (ROOT/'arduino/v17/relay').iterdir() if p.is_file());x.build()
   for name in ('generator_protocol.h','generator_timing.h'):x.board.run('push',str(ROOT/'arduino/v17/oscilloscope/sketch'/name),x.board.remote+'/sketch/'+name)
   x.board.start();x.start_relay(x.relay)
   identity=instrument_identity(x.board.serial);expected=json.loads(evidence.read_text())['candidate_identity']
   if identity!=expected:raise RuntimeError('Candidate firmware identity changed')
   # Fresh interpreter reads the contract just published by apply().
   output_path=x.folder/'output_checks.json'
   subprocess.run([sys.executable,str(EXP/'check_output.py'),str(output_path)],check=True)
   x.report['output_checks']=json.loads(output_path.read_text());x.save()
   from monitor.relay_identity import relay_digest
   target='/home/arduino/.cache/serialmonitor/usb-stream-'+relay_digest(ROOT/'arduino/v17/relay')+'/unoq_stream'
   x.board.shell('mkdir','-p',target.rsplit('/',1)[0]);x.board.shell('cp',x.relay,target)
   usb_stream.stop(x.board);x.board.start();x.start_relay(target)
   x.report['original_identity']=x.report['prior_identity'];x.report['prior_identity']=identity
   x.restore_settings();x.report.update(installed=True,ok=True,installed_relay=target);x.save()
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());x.save();raise
  finally:
   if not x.report.get('installed'):
    if x.report.get('local_sources_updated'):
     for name in FILES:shutil.copy2(x.folder/'prior_local'/name,ROOT/name)
    if changed:
     usb_stream.stop(x.board);x.board.stop()
     for name in ('generator_protocol.h','generator_timing.h'):x.board.run('push',str(x.folder/'prior_headers'/name),x.board.remote+'/sketch/'+name)
     x.board.start();x.start_relay(x.report['old_relay'],prior=True)
    if x.report.get('prior'):x.restore_settings()
   x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
