"""Measure A0->CH2 start/end steps of sine Sweep/Chirp; never installs firmware."""
import sys,json,time,argparse
from pathlib import Path
from dataclasses import asdict
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.unoq import Board,config_path
from monitor.v17.board_owner import board_owner
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_acquisition import Configuration
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--repeat',type=int,default=1)
 parser.add_argument('--duration-ms',type=int,default=2000)
 parser.add_argument('--start-hz',type=float,default=100)
 parser.add_argument('--end-hz',type=float,default=2000)
 args=parser.parse_args()
 if not (1<=args.repeat<=100 and 200<=args.duration_ms<=120000 and
         0<args.start_hz<=150000 and 0<args.end_hz<=150000):
  parser.error('Repeticiones 1–100, duración 200–120000 ms y frecuencias positivas hasta 150 kHz.')
 folder=ROOT/'diagnosticos/resultados_v17'/('sweep_transitions_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 report={'cases':[],'restored':False,'firmware_changed':False};prior=None
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 b=Board(json.loads(config_path('v17').read_text()))
 with board_owner(b.serial,'Medir transitorios Sweep/Chirp A0 CH2'):
  require_exclusive_monitor()
  try:
   report['identity_before']=instrument_identity(b.serial)
   with Connection(b.serial) as c:
    blocks=[]
    def collect(samples):blocks.append(np.asarray(samples.array if hasattr(samples,'array') else samples).copy())
    r=OutputReceiver(c,collect);r.decoder.numeric=True;r.select(0)
    g=r.generator().active
    if g.enabled:raise RuntimeError('Generador ocupado')
    prior={'adc':asdict(r.config),'generator':asdict(g)};report['prior']=prior;save()
    cfg=Configuration(8,632411);r.configure(cfg)
    for iteration,mode in ((i,m) for i in range(args.repeat) for m in (1,2)):
     r.generator(GeneratorConfig(enabled=0));end=time.monotonic()+.3
     while time.monotonic()<end:r.pump()
     blocks.clear();end=time.monotonic()+.25
     while time.monotonic()<end:r.pump()
     stimulus=GeneratorConfig(wave=1,mode=mode,frequency=round(args.start_hz*1000),final_frequency=round(args.end_hz*1000),low=1427,high=2668,duration=args.duration_ms)
     r.generator(stimulus);end=time.monotonic()+args.duration_ms/1000+.35
     while time.monotonic()<end:r.pump()
     status=r.generator();a=np.concatenate(blocks);codes=a[:,2].astype(np.uint8);y=codes.astype(float)*3.3/255
     capture=f'mode{mode}.npz' if args.repeat==1 else f'repeat{iteration+1}_mode{mode}.npz'
     np.savez_compressed(folder/capture,ch2=codes,rate=cfg.actual_rate)
     dy=np.abs(np.diff(y));rises=np.flatnonzero((y[:-1]<.3)&(y[1:]>.5))
     row={'mode':mode,'iteration':iteration+1,'capture':capture,'stimulus':asdict(stimulus),'running_after':bool(status.running),'adc_status':r.decoder.status,'sample_rate':cfg.actual_rate}
     if len(rises):
      onset=int(rises[0]);stop=onset+round(args.duration_ms/1000*cfg.actual_rate)
      lo=max(onset+1,stop-round(.03*cfg.actual_rate));hi=min(len(dy),stop+round(.03*cfg.actual_rate))
      row.update(onset=onset,start_step_v=float(dy[onset]),end_step_v=float(dy[lo:hi].max()),
          interior_step_max_v=float(dy[onset+round(.05*cfg.actual_rate):stop-round(.05*cfg.actual_rate)].max()),
          start_level_v=float(y[onset+1]),settled_end_v=float(np.median(y[-round(.05*cfg.actual_rate):])))
     else:row['error']='No se observó transición A0; confirmar cable A0→CH2/A3 y masa común.'
     report['cases'].append(row);save();print(json.dumps(row),flush=True)
  finally:
   if prior:
    with Connection(b.serial) as c:
     r=OutputReceiver(c,lambda _:None);r.decoder.numeric=True;r.select(0);r.generator(GeneratorConfig(enabled=0));r.configure(Configuration(14,40000));r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
     report['restored']=asdict(r.config)==prior['adc'] and asdict(r.generator().active)==prior['generator'];end=time.monotonic()+5
     while time.monotonic()<end:r.pump()
     report['recovery']=r.decoder.status
    report['identity_after']=instrument_identity(b.serial)
   save();print(folder/'report.json',flush=True)
if __name__=='__main__':main()
