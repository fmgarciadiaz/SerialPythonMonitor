"""Isolated ADC333 experiment. Always reload stable MCU/relay and prior profile."""
from pathlib import Path
import sys, json, time, importlib.util, argparse, subprocess
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2]; EXP=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
# Only this process uses the experimental period/rate contract.
name='monitor.v16.receiver.unoq_acquisition'
spec=importlib.util.spec_from_file_location(name,EXP/'acquisition.py')
module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
from monitor.v16.receiver.unoq_acquisition import Configuration
import monitor.v16.receiver.unoq_config_receiver as receiver_module
from decoder import TransferDecoder
receiver_module.ConfigurationDecoder=TransferDecoder
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_switch import Mode
from monitor.v16.receiver.unoq_generator import GeneratorConfig
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from unoq import Board,config_path
import usb_stream
from spi_benchmark import IMAGE

def start_relay(board,target):
 usb_stream.stop(board)
 board.shell('docker','run','-d','--name',usb_stream.CONTAINER,'--network','host','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','0:0','--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw','--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly','--entrypoint','/work/unoq_stream',IMAGE)
 end=time.monotonic()+15
 while time.monotonic()<end:
  logs=board.run('shell','docker logs '+usb_stream.CONTAINER+' 2>&1',capture=True).stdout
  if 'SPI ready: first verified frame' in logs:return
  time.sleep(.2)
 raise RuntimeError('Relay no confirmó trama SPI')

def collect_case(receiver,rate,seconds,report,save):
 receiver.configure(Configuration(14,rate))
 first=receiver.decoder.pairs;telemetry_start=len(receiver.decoder.telemetry);start=time.monotonic();next_log=start+10
 case={'rate':rate,'period_us':receiver.config.period,'requested_seconds':seconds,'ok':False};report['cases'].append(case);save()
 try:
  while time.monotonic()-start<seconds:
   receiver.pump()
   if time.monotonic()>=next_log:
    print(f'{rate}: {time.monotonic()-start:.1f}s {receiver.decoder.pairs-first} pares',flush=True);next_log+=10
  elapsed=time.monotonic()-start;count=receiver.decoder.pairs-first
  case.update(seconds=elapsed,pairs=count,observed_rate=count/elapsed,status=receiver.decoder.status)
  if abs(count/elapsed/(1000000/receiver.config.period)-1)>.02:raise RuntimeError('Tasa incorrecta')
  case['ok']=True
 except Exception as exc:
  case.update(error=str(exc),seconds=time.monotonic()-start,pairs=receiver.decoder.pairs-first,status=receiver.decoder.status)
  raise
 finally:
  entries=receiver.decoder.telemetry[telemetry_start:]
  case['telemetry']=entries
  if len(entries)>1:
   a,b=entries[0],entries[-1];nodes=b['nodes']-a['nodes'];frames=b['frames']-a['frames']
   if nodes:case['node_mean_us']=(b['node_sum_us']-a['node_sum_us'])/nodes
   if frames:case['frame_mean_us']={key:(b[key]-a[key])/frames for key in ('prep_sum_us','setup_sum_us','wait_sum_us','check_sum_us')}
   case['queued_max']=max(e['queued'] for e in entries)
  save()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--restore-only',action='store_true');parser.add_argument('--reuse',action='store_true');args=parser.parse_args()
 require_exclusive_monitor()
 stable=Board(json.loads(config_path('v16').read_text()));config=dict(stable.config)
 config.update(name='Scope V16 Transfer Experimental',remote_app='/home/arduino/ArduinoApps/scope-v16-transfer-experimental',local_app='experimentos/adc_transfer_v16/arduino/v16/oscilloscope')
 candidate=Board(config)
 report={'cases':[],'restored':False,'analog':'No evaluado','queue_margin':'TDG1: ocupación y tiempo de vaciado por nodo; sobrecosto de instrumentación presente','timestamp_validation':'DMA TIM5 y node_validation originales, sin cambios'}
 path=EXP/'results.json'
 def save():path.write_text(json.dumps(report,indent=2)+'\n')
 prior=json.loads((EXP/'prior_profile.json').read_text());report['prior']=prior
 stable_binary=usb_stream.binary(stable,p992=True,audio=True)
 switched=False
 try:
  if not args.restore_only:
   if not args.reuse:
    candidate.compile()
    report['backup']=str(stable.backup());save()
   apps=json.loads(candidate.cli('app','list','--format','json',capture=True).stdout).get('apps',[])
   if any(a.get('name')==config['name'] for a in apps):candidate.push_sources(candidate.check_sources(),candidate.remote)
   else:candidate.create()
   usb_stream.ROOT=EXP
   try:
    try:target=usb_stream.binary(candidate,p992=True,audio=True)
    except subprocess.CalledProcessError:target=usb_stream.binary(candidate,build=True,p992=True,audio=True)
   finally:usb_stream.ROOT=ROOT
   require_exclusive_monitor();switched=True
   usb_stream.stop(stable);stable.stop();candidate.start();start_relay(candidate,target)
   with Connection(stable.serial) as c:
    r=OutputReceiver(c,lambda batch:None,lambda msg:print(msg,flush=True));r.select(Mode.SPI)
    r.generator(GeneratorConfig(**prior['generator']))
    trials=((250000,10),(333333,10)) if args.reuse else ((250000,20),(333333,10),(333333,120),(250000,20))
    for rate,seconds in trials:
     collect_case(r,rate,seconds,report,save)
   report['ok']=True
 except Exception as exc:
  report['error']=str(exc);report['ok']=False;print('Ensayo:',exc,flush=True)
 finally:
  if switched or args.restore_only:
   if switched:
    try:
     relay_logs=stable.run('shell','docker logs '+usb_stream.CONTAINER+' 2>&1',capture=True).stdout
     (EXP/'relay_trial.log').write_text(relay_logs);report['relay_logs']='relay_trial.log'
    except Exception as exc:report['relay_log_error']=str(exc)
   try:
    usb_stream.stop(stable);candidate.stop();stable.start();start_relay(stable,stable_binary)
    with Connection(stable.serial) as c:
     r=OutputReceiver(c,lambda batch:None,lambda msg:print(msg,flush=True));r.select(Mode.SPI)
     r.generator(GeneratorConfig(**prior['generator']));r.configure(Configuration(**prior['adc']))
     r.reset_wav_output()
     collect_case(r,prior['adc']['rate'],10,report,save)
     report['final_adc']=asdict(r.config);report['final_generator']=asdict(r.generator().active)
     report['restored']=report['final_adc']==prior['adc'] and report['final_generator']==prior['generator']
   except Exception as exc:report['restore_error']=str(exc)
  save();print(json.dumps(report,indent=2),flush=True)
 return 0 if report.get('ok') and report['restored'] else 1
if __name__=='__main__':raise SystemExit(main())
