"""V16 40/50 kHz command/integrity validation; records raw ADC and restores saved state."""
from pathlib import Path
import sys,json,time,argparse
from dataclasses import asdict
from datetime import datetime
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig

def main():
 p=argparse.ArgumentParser();p.add_argument('--snapshot',action='store_true');p.add_argument('--seconds',type=float,default=10);a=p.parse_args()
 folder=ROOT/'diagnosticos/resultados_v16';folder.mkdir(exist_ok=True)
 saved=folder/'estado_previo_generador_50khz.json'
 blocks=[];pairs=0
 def collect(batch):
  nonlocal pairs
  pairs+=len(batch)
  if sum(len(b) for b in blocks)<65536:blocks.append(np.asarray(batch,dtype=np.float64))
 with Connection('1060031107') as c:
  r=OutputReceiver(c,collect,lambda m:print(m,flush=True));r.select(Mode.SPI)
  if a.snapshot:
   state={'adc':asdict(r.config),'generator':asdict(r.generator().active),'transport':'SPI'}
   saved.write_text(json.dumps(state,indent=2)+'\n');print(state);return
  prior=json.loads(saved.read_text());report={'prior':prior,'cases':[],'ok':False,'scope':'Command acceptance and strict ADC integrity; raw channels depend on existing wiring, no absolute analog calibration'}
  path=folder/(datetime.now().strftime('%Y%m%d_%H%M%S')+'_generador_50khz.json')
  def save():path.write_text(json.dumps(report,indent=2)+'\n')
  try:
   r.configure(Configuration(14,250000))
   for wave in (0,1,2,3):
    for hz in (40000,50000):
     cfg=GeneratorConfig(wave=wave,frequency=hz*1000,final_frequency=hz*1000,low=1427,high=2668)
     reply=r.generator(cfg);blocks.clear();before=pairs;start=time.monotonic()
     while time.monotonic()-start<a.seconds:r.pump()
     raw=np.concatenate(blocks) if blocks else np.empty((0,4))
     name=path.stem+f'_wave{wave}_{hz}.npy';np.save(folder/name,raw)
     case={'wave':wave,'hz':hz,'reply':asdict(reply),'seconds':time.monotonic()-start,'pairs':pairs-before,'status':r.decoder.status,'raw':name,'channel_min_max_codes':[[float(raw[:,i].min()),float(raw[:,i].max())] for i in (1,2)] if len(raw) else [],'ok':reply.active==cfg and reply.running and pairs-before>0}
     report['cases'].append(case);save();print(case,flush=True)
     case['observed_rate']=(pairs-before)/case['seconds']
     case['ok']=case['ok'] and abs(case['observed_rate']/250000-1)<.02
     save()
     if not case['ok']:raise RuntimeError('Generator case failed')
   for mode in (1,2):
    for initial,final in ((40000,50000),(50000,40000)):
     cfg=GeneratorConfig(wave=1,mode=mode,frequency=initial*1000,final_frequency=final*1000,low=1427,high=2668,duration=2000)
     reply=r.generator(cfg);before=pairs;start=time.monotonic()
     while time.monotonic()-start<2.5:r.pump()
     end=r.generator();case={'mode':mode,'initial':initial,'final':final,'reply':asdict(reply),'end':asdict(end),'pairs':pairs-before,'ok':reply.active==cfg and not end.running and pairs-before>0};report['cases'].append(case);save();print(case,flush=True)
     if not case['ok']:raise RuntimeError('Sweep/chirp case failed')
   report['ok']=True
  except Exception as exc:report['error']=str(exc);raise
  finally:
   try:
    r.generator(GeneratorConfig(**dict(prior['generator'],enabled=0)))
    r.configure(Configuration(**prior['adc']))
    r.generator(GeneratorConfig(**prior['generator']))
    report['final']={'adc':asdict(r.config),'generator':asdict(r.generator().active),'transport':'SPI'}
    report['restored']=report['final']==prior
    report['ok']=report['ok'] and report['restored']
   except Exception as exc:report['restore_error']=str(exc);report['ok']=False
   save();print(path,flush=True)
if __name__=='__main__':main()
