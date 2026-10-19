"""Locate RADIO TEST startup failures while preserving phase-level evidence."""
import argparse,json,sys,time
from pathlib import Path
from dataclasses import asdict,replace
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--rate',type=int,default=1142857);p.add_argument('--cycles',type=int,default=5);args=p.parse_args()
require_exclusive_monitor();report={'cases':[],'ok':False,'restored':False};args.output.parent.mkdir(parents=True,exist_ok=True)
def save():args.output.write_text(json.dumps(report,indent=2)+'\n')
def hold(r,seconds):
 start=time.monotonic();before=r.decoder.pairs;peak=0
 while time.monotonic()-start<seconds:
  r.pump();peak=max(peak,r.decoder.status.get('queue_peak',0))
 return {'seconds':time.monotonic()-start,'samples':r.decoder.pairs-before,'queue_peak':peak,'status':r.decoder.status}
try:
 with Connection('1060031107') as c:
  r=OutputReceiver(c,lambda _:None);r.decoder.numeric=True;r.select(Mode.SPI);g=r.generator()
  prior={'adc':asdict(r.config),'generator':asdict(g.active),'identity':instrument_identity('1060031107')};report['prior']=prior;save()
  r.generator(replace(g.active,enabled=0));r.configure(Configuration(10,args.rate));report['phase']='steady_generator_off';save();report['steady_off']=hold(r,5);save()
  for i in range(args.cycles):
   case={'cycle':i,'before':r.decoder.status};report['cases'].append(case);report['phase']='start_command';save()
   wanted=GeneratorConfig(wave=1,enabled=1,mode=3,frequency=(20000+i*25)*1000,final_frequency=40000000,duration=1000,low=807,high=3288)
   start=time.monotonic();reply=r.generator(wanted);case['command_ms']=(time.monotonic()-start)*1000;case['running']=reply.running;report['phase']='after_start';save()
   case['on']=hold(r,3);report['phase']='stop_command';save();r.generator(replace(wanted,enabled=0));case['off']=hold(r,1);save()
  r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']));report['recovery']=hold(r,10);report['final_identity']=instrument_identity('1060031107');report['restored']=asdict(r.config)==prior['adc'] and asdict(r.generator().active)==prior['generator'];report['ok']=report['restored'] and report['final_identity']==prior['identity'];report['phase']='complete'
except Exception as exc:report['error']=str(exc)
save();print(json.dumps(report,indent=2));sys.exit(0 if report['ok'] else 1)
