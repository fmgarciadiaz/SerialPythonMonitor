"""Physical V16 integrity check; preserves ADC settings and leaves A0 disabled."""
from pathlib import Path
import sys,json,time,argparse
from dataclasses import asdict,replace
from datetime import datetime
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig
from monitor.historico.v16.receiver.unoq_wav import State

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=120);parser.add_argument('--serial',default='1060031107');args=parser.parse_args()
 folder=ROOT/'diagnosticos/resultados_v16';folder.mkdir(exist_ok=True)
 path=folder/(datetime.now().strftime('%Y%m%d_%H%M%S')+'_integridad.json')
 report=dict(serial=args.serial,protocol=4,firmware='v16',cases=[],ok=False,uart='No probado: requiere R4 disponible',analog='No certifica precisión analógica',timing='DMA original sigue validando timestamps por muestra')
 pairs=0
 def collect(batch):
  nonlocal pairs
  pairs+=len(batch)
 def save():path.write_text(json.dumps(report,indent=2)+'\n')
 with Connection(args.serial) as c:
  r=OutputReceiver(c,collect,lambda msg:print(msg,flush=True));r.select(Mode.SPI);prior=r.config;gen=r.generator().active
  report['prior_adc']=asdict(prior);report['prior_generator']=asdict(gen);save()
  try:
   for bits,rate in ((14,40000),(14,125000),(16,62500)):
    r.configure(Configuration(bits,rate));r.generator(replace(gen,enabled=0))
    before=pairs;start=time.monotonic();next_log=start+20;case=dict(kind='adc',bits=bits,rate=rate);report['cases'].append(case)
    while time.monotonic()-start<args.seconds:
     r.pump()
     if time.monotonic()>next_log:
      print(f'ADC{bits}/{rate}: {time.monotonic()-start:.0f}s, {pairs-before} pares',flush=True);next_log+=20
    elapsed=time.monotonic()-start
    case.update(pairs=pairs-before,seconds=elapsed,observed_rate=(pairs-before)/elapsed,status=r.decoder.status,ok=True);save();print(case,flush=True)
   r.configure(Configuration(14,100000))
   wave=GeneratorConfig(wave=1,enabled=1,frequency=1000000,low=806,high=3290)
   r.generator(wave);start=time.monotonic();before=pairs
   while time.monotonic()-start<10:r.pump()
   report['cases'].append(dict(kind='generator',pairs=pairs-before,reply=asdict(r.generator()),ok=True));r.generator(replace(wave,enabled=0));save()
   for rate in (20000,40000):
    count=rate*5;codes=np.rint((1.65+np.sin(2*np.pi*997*np.arange(count)/rate))*(4095/3.3)).astype('<u2')
    r.wav_request();end=time.monotonic()+5
    while r.wav_pending and time.monotonic()<end:r.pump()
    r.wav_request(1,codes,rate);start=time.monotonic();before=pairs
    while time.monotonic()-start<15:
     r.pump();s=r.wav_status
     if s and s.state in (State.DONE,State.UNDERRUN,State.FAULT):break
    s=r.wav_status
    case=dict(kind='wav',rate=rate,state=s.state.name,played=s.played,total=count,adc_pairs=pairs-before,ok=s.state==State.DONE and s.played==count)
    report['cases'].append(case);save();print(case,flush=True)
    if not case['ok']:raise RuntimeError('WAV incompleto')
   report['ok']=True
  except Exception as exc:report['error']=str(exc);raise
  finally:
   try:
    if r.wav_codes is not None:r.wav_request(3)
    r.generator(replace(gen,enabled=0));r.configure(prior)
    report['final_adc']=asdict(r.config);report['final_generator']=asdict(r.generator().active)
   except Exception as exc:report['restore_error']=str(exc);report['ok']=False
   save();print(path,flush=True)
if __name__=='__main__':main()
