"""Install exact accepted sources, validate RADIO8/10/12, roll back on failure."""
import argparse,hashlib,json,subprocess,sys,time,traceback
from pathlib import Path
from contextlib import nullcontext
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.otros_bits_crc_v17.incorporate import qualified_profiles
from experimentos.otros_bits_crc_v17.run import FILES,EXP
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from monitor.v17.board_owner import board_owner
from monitor.relay_identity import relay_digest
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from diagnosticos.validar_generador_radio_v17 import main as audio_trial
from tools.unoq import Board,config_path
import usb_stream,os

def main():
 p=argparse.ArgumentParser();p.add_argument('screen',type=Path);p.add_argument('acceptance',type=Path);a=p.parse_args()
 profiles,evidence=qualified_profiles(a.screen,a.acceptance)
 for key,digest in evidence['source_hashes'].items():
  local=ROOT/('arduino/v17/oscilloscope/'+key if key.startswith('sketch/') else 'arduino/v17/'+key)
  if hashlib.sha256(local.read_bytes()).hexdigest()!=digest:raise ValueError('Production source differs: '+key)
 registry=json.loads((ROOT/'monitor/v17/receiver/native_profiles.json').read_text())
 for profile in profiles:
  if not any(all(row.get(k)==profile[k] for k in ('bits','channels','ticks','node_pairs','firmware_sha256')) for row in registry):
   raise ValueError('Host registry does not contain the accepted profile')
 subprocess.Popen(['/usr/bin/caffeinate','-dimsu','-w',str(os.getpid())])
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None
 x.folder=EXP/('deployment_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
 x.report=dict(ok=False,installed=False,restored=False,cases=[],audio_cases=[],screening_evidence=str(a.screen),acceptance_evidence=str(a.acceptance),source_hashes=evidence['source_hashes'])
 (x.folder/'runner.py').write_bytes(Path(__file__).read_bytes());x.save();changed=False
 with board_owner(x.board.serial,'Incorporar RADIO y tasas ADC10/12'):
  try:
   x.snapshot()
   info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus']);x.normal=x.policy();x.report['normal_policy']=x.normal
   prior=x.folder/'prior_headers';prior.mkdir();presence={};x.report['prior_header_presence']=presence
   for name in FILES:
    try:x.board.shell('test','-f',x.board.remote+'/sketch/'+name)
    except subprocess.CalledProcessError:presence[name]=False
    else:presence[name]=True;x.board.run('pull',x.board.remote+'/sketch/'+name,str(prior/name))
   source=evidence['candidate_relay'];digest=evidence['candidate_relay_sha256']
   if x.board.shell('sha256sum',source,capture=True).stdout.split()[0]!=digest:raise ValueError('Accepted relay binary changed')
   target='/home/arduino/.cache/serialmonitor/usb-stream-'+relay_digest(ROOT/'arduino/v17/relay')+'/unoq_stream'
   x.board.shell('mkdir','-p',target.rsplit('/',1)[0]);x.board.shell('cp',source,target)
   if x.board.shell('sha256sum',target,capture=True).stdout.split()[0]!=digest:raise ValueError('Production relay copy mismatch')
   x.report.update(installed_relay=target,installed_relay_sha256=digest);x.save()
   usb_stream.stop(x.board);x.board.stop();changed=True
   for name in FILES:x.board.run('push',str(ROOT/'arduino/v17/oscilloscope/sketch'/name),x.board.remote+'/sketch/'+name)
   x.board.start();x.start_relay(target)
   identity=instrument_identity(x.board.serial);x.report['installed_identity']=identity;x.save()
   if identity!=evidence['candidate_identity']:raise ValueError('Installed MCU differs from qualified binary')
   # Real GUI/DSP/live audio, not a generated replacement for RF input.
   from PyQt6 import QtWidgets
   qt_app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
   cases=[(8,1600000,120,False),(8,1600000,60,True)]+[(v['bits'],160000000//v['ticks'],60,True) for v in profiles]
   for bits,rate,seconds,filtered in cases:
    sys.argv=['validar_generador_radio_v17.py','--bits',str(bits),'--rate',str(rate),'--seconds',str(seconds)]
    if filtered:sys.argv.append('--filter-input')
    report,folder=audio_trial(owner_context=nullcontext())
    x.report['audio_cases'].append(dict(bits=bits,rate=rate,seconds=seconds,input='FILTER' if filtered else 'RADIO',ok=report['ok'],report=str(folder/'report.json'),queue_peak=report.get('adc_queue_peak'),joint_send_statistics=report.get('joint_send_statistics')));x.save()
    if not report['ok']:raise RuntimeError('Production RADIO failed: ADC'+str(bits))
   from experimentos.radio_dac_headroom_v17.storage_smoke import run as smoke
   x.report['storage_smoke']=smoke(x.board.serial)
   # Restore the user's settings on the accepted firmware, then verify continuity.
   with Connection(x.board.serial) as connection:
    r=OutputReceiver(connection,lambda _:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000))
    actual=x.pumping(r,x.policy)
    if actual!=x.normal:raise ValueError('Normal CPU policy did not restore')
    prior_state=x.report['prior'];r.configure(Configuration(**prior_state['adc']));r.generator(GeneratorConfig(**prior_state['generator']))
    final=dict(adc=asdict(r.config),generator=asdict(r.generator().active));before=r.decoder.pairs;started=time.monotonic()
    while time.monotonic()-started<10:r.pump()
    status=r.decoder.status;samples=r.decoder.pairs-before
    continuity=not(status['dropped'] or status['fatal']) and abs(samples/(time.monotonic()-started)/r.config.actual_rate-1)<.02
    x.report.update(final_settings=final,settings_restored=final==prior_state,recovery=dict(ok=continuity,samples=samples,status=status),final_identity=identity)
    if not continuity or final!=prior_state:raise ValueError('Final settings or acquisition continuity failed')
   x.report.update(ok=True,installed=True)
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());x.save()
   try:x.logs('failure_relay.log')
   except Exception:pass
   raise
  finally:
   if changed and not x.report['ok']:
    usb_stream.stop(x.board);x.board.stop()
    for name in FILES:
     if presence[name]:x.board.run('push',str(prior/name),x.board.remote+'/sketch/'+name)
     else:x.board.shell('python3','-c','from pathlib import Path;import sys;Path(sys.argv[1]).unlink(missing_ok=True)',x.board.remote+'/sketch/'+name)
    x.board.start();x.start_relay(x.report['old_relay'],prior=True);x.restore_settings()
   elif not changed and x.report.get('prior'):x.restore_settings()
   x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
