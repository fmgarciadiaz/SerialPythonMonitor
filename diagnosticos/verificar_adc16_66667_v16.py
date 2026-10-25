"""Exercise ADC16/66.67 kHz and mode switching with real timestamps; restore prior profile."""
from pathlib import Path
import sys,json,time
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.numeric_batch import SampleClock,NumericBatch
import numpy as np

def main():
 require_exclusive_monitor();prior=json.loads((ROOT/'diagnosticos/resultados_v16/integracion_adc_prior.json').read_text())
 report={'cases':[],'ok':False,'restored':False,'analog':'No evaluado'}
 path=ROOT/'diagnosticos/resultados_v16/adc16_66667_integrado.json'
 def save():path.write_text(json.dumps(report,indent=2)+'\n')
 clock=SampleClock();last_time=None
 def configured(config):
  nonlocal clock,last_time
  clock=SampleClock(config.timestamp_hz);last_time=None
 def collect(rows):
  nonlocal last_time
  batch=NumericBatch(rows,r.config.maximum,clock,r.config.channels)
  if r.config.channels==1:
   times=batch.columns['Tiempo (us)'];delta=np.diff(times)
   assert np.all(np.abs(delta-r.config.dt_us)<1e-6)
   if last_time is not None:assert abs(times[0]-last_time-r.config.dt_us)<1e-6
   assert np.isnan(batch.columns['CH2']).all()
   last_time=float(times[-1])
 with Connection('1060031107') as c:
  r=OutputReceiver(c,collect,print);r.on_configuration=configured;r.select(Mode.SPI)
  try:
   for bits,rate,seconds in ((16,62500,10),(16,66666,120),(14,661157,10),(16,66666,10),(14,333333,10)):
    r.configure(Configuration(bits,rate));configured(r.config)
    before=r.decoder.pairs;start=time.monotonic();next_log=start+10
    while time.monotonic()-start<seconds:
     r.pump()
     if time.monotonic()>=next_log:
      print(f'ADC{bits}/{rate}: {time.monotonic()-start:.0f}s {r.decoder.pairs-before} muestras',flush=True);next_log+=10
    elapsed=time.monotonic()-start;count=r.decoder.pairs-before
    case={'bits':bits,'rate':rate,'channels':r.config.channels,'seconds':elapsed,'samples':count,'observed_rate':count/elapsed,'status':r.decoder.status}
    report['cases'].append(case);save()
    assert abs(count/elapsed/r.config.actual_rate-1)<.02
   report['ok']=True
  finally:
   r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
   report['final_adc']=asdict(r.config);report['final_generator']=asdict(r.generator().active)
   report['restored']=report['final_adc']==prior['adc'] and report['final_generator']==prior['generator']
   save()
 print(path)
if __name__=='__main__':main()
