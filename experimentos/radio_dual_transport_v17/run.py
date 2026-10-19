"""Physical CH1 -> dual RADIO TEST transition; one Q owner, persistent evidence."""
import argparse,json,sys,time,hashlib
from dataclasses import asdict,replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
def capture(receiver,seconds):
 start=time.monotonic();before=receiver.decoder.pairs;maxima={};minimum_margin=1.;margin_sum=0.;margin_count=0;last_metric=None
 while time.monotonic()-start<seconds:
  receiver.pump()
  for status in receiver.decoder.statuses:
   for key in ('queue','queue_peak','copy_ticks','poll_ticks','send_ticks'):
    maxima[key]=max(maxima.get(key,0),status.get(key,0))
   config=receiver.config
   if status.get('send_ticks'):
    margin=1-status['send_ticks']/(config.period*config.node_pairs)
    minimum_margin=min(minimum_margin,margin)
    metric=(status.get('produced'),status['send_ticks'])
    if metric!=last_metric:
     margin_sum+=margin;margin_count+=1;last_metric=metric
 status=dict(receiver.decoder.status)
 return dict(seconds=time.monotonic()-start,samples=receiver.decoder.pairs-before,status=status,maxima=maxima,minimum_send_margin=minimum_margin,mean_observed_send_margin=margin_sum/margin_count if margin_count else None,send_margin_observations=margin_count,integrity_ok=receiver.decoder.pairs>before and not status.get('dropped',0) and not status.get('fatal',0))

p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--seconds',type=float,default=15);p.add_argument('--restore',action='store_true');p.add_argument('--prior',required=True,type=Path);p.add_argument('--cycles',type=int,default=1);p.add_argument('--levels',action='store_true');args=p.parse_args()
require_exclusive_monitor();report={'scope':'Physical ADC10 CH1 to dual with RADIO TEST; transport integrity only, no analog acceptance or GUI FPS','cases':[],'ok':False,'restored':False,'relay_sources_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'arduino/v17/relay').glob('*') if p.is_file()}};args.output.parent.mkdir(parents=True,exist_ok=True)
def save():args.output.write_text(json.dumps(report,indent=2)+'\n')
try:
 with Connection('1060031107') as c:
  r=OutputReceiver(c,lambda _:None);r.decoder.numeric=True;r.select(Mode.SPI);g=r.generator()
  if not args.prior.exists():args.prior.write_text(json.dumps({'adc':asdict(r.config),'generator':asdict(g.active),'identity':instrument_identity('1060031107')},indent=2)+'\n')
  prior=json.loads(args.prior.read_text());report['identity']=instrument_identity('1060031107');save()
  if not args.restore:
   r.generator(replace(g.active,enabled=0))
   r.configure(Configuration(14,40000))
   wanted=GeneratorConfig(wave=1,enabled=1,mode=3,frequency=20000000,final_frequency=40000000,duration=1000,low=807 if args.levels else 0,high=3288 if args.levels else 0)
   r.generator(wanted)
   for cycle in range(args.cycles):
    r.configure(Configuration(10,1142857))
    case={'cycle':cycle,'ch1':capture(r,2),'generator':asdict(wanted)};report['cases'].append(case);save()
    r.configure(Configuration(10,519480));case['dual']=capture(r,args.seconds);save();print('cycle',cycle,case['dual'],flush=True)
    if not case['dual']['integrity_ok']:raise RuntimeError('Dual integrity failed')
  r.generator(replace(r.generator().active,enabled=0));r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
  report['recovery']=capture(r,10);report['final_adc']=asdict(r.config);report['final_generator']=asdict(r.generator().active);report['final_identity']=instrument_identity('1060031107');report['restored']=report['final_adc']==prior['adc'] and report['final_generator']==prior['generator'];report['ok']=report['restored'] and report['identity']==report['final_identity'] and report['recovery']['integrity_ok'] and all(x['dual']['integrity_ok'] for x in report['cases'])
except Exception as exc:report['error']=str(exc)
save();print(json.dumps(report,indent=2),flush=True);sys.exit(0 if report['ok'] else 1)
