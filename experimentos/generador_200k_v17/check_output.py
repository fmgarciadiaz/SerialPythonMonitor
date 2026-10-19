"""Final-output check for an already installed candidate; does not deploy firmware."""
import time,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig

def run(serial):
 blocks=[]
 def collect(b):
  if sum(map(len,blocks))<32768:blocks.append(np.asarray(b.array if hasattr(b,'array') else b,dtype=float))
 result=[]
 with Connection(serial) as c:
  r=OutputReceiver(c,collect);r.decoder.numeric=True;r.select(0)
  prior=r.config;gen=r.generator().active
  try:
   r.configure(Configuration(8,632411))
   for wave,freq in ((1,150000),(0,200000)):
    cfg=GeneratorConfig(wave=wave,frequency=freq*1000,final_frequency=freq*1000,low=1427,high=2668)
    r.generator(cfg);end=time.monotonic()+60
    while time.monotonic()<end:r.pump()
    final=r.generator();blocks.clear();end=time.monotonic()+.2
    while time.monotonic()<end:r.pump()
    a=np.concatenate(blocks);y=a[:,2]*3.3/255;n=len(y)
    spectrum=abs(np.fft.rfft((y-y.mean())*np.hanning(n)));frequency=np.argmax(spectrum[1:])+1;measured=frequency*r.config.actual_rate/n
    row={'wave':wave,'requested_hz':freq,'end_running':bool(final.running),'measured_end_hz':measured,'end_vpp':float(np.ptp(y)),'adc_status':r.decoder.status}
    row['ok']=row['end_running'] and final.active==cfg and abs(measured/freq-1)<.01 and row['end_vpp']>.5
    result.append(row);print('END_CHECK',row,flush=True)
    if not row['ok']:raise RuntimeError('Final signal check failed')
   for mode in (1,2):
    for start,finish in ((62500,150000),(150000,62500)):
     cfg=GeneratorConfig(wave=1,mode=mode,frequency=start*1000,final_frequency=finish*1000,low=1427,high=2668,duration=500)
     begin=r.generator(cfg);end=time.monotonic()+.7
     while time.monotonic()<end:r.pump()
     final=r.generator();row={'mode':mode,'start':start,'finish':finish,'ok':begin.active==cfg and not final.running and final.reason==0};result.append(row)
     if not row['ok']:raise RuntimeError('Sweep/chirp check failed')
  finally:
   r.generator(GeneratorConfig(enabled=0));r.configure(prior);r.generator(gen)
 return result
if __name__=='__main__':
 result=run('1060031107')
 if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
