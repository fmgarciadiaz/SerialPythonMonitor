"""Validate ADC8 CH1 high rate and transitions; restore the saved user profile."""
from pathlib import Path
import sys,json,time
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_generator import GeneratorConfig
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_switch import Mode
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
PATH=ROOT/'diagnosticos/resultados_v16/megaboom_integrado.json'
PRIOR=ROOT/'diagnosticos/resultados_v16/megaboom_prior.json'
def main():
 require_exclusive_monitor()
 with Connection('1060031107') as c:
  r=OutputReceiver(c,lambda b:None,print);r.select(Mode.SPI)
  if r.generator().active.enabled:raise RuntimeError('Salida ocupada')
  if '--snapshot' in sys.argv:
   PRIOR.write_text(json.dumps({'adc':asdict(r.config),'generator':asdict(r.generator().active)},indent=2)+'\n');return
  prior=json.loads(PRIOR.read_text());report={'cases':[],'ok':False,'restored':False}
  try:
   for bits,rate,seconds in ((14,333333,10),(8,1203007,120),(14,661157,10),(8,1203007,10),(16,71428,10),(14,250000,10)):
    r.configure(Configuration(bits,rate));start=time.monotonic();before=r.decoder.pairs;next_log=start+10
    while time.monotonic()-start<seconds:
     r.pump()
     if time.monotonic()>=next_log:print(f'ADC{bits}/{rate}: {time.monotonic()-start:.0f}s {r.decoder.pairs-before}',flush=True);next_log+=10
    elapsed=time.monotonic()-start;count=r.decoder.pairs-before
    report['cases'].append({'bits':bits,'rate':rate,'samples':count,'seconds':elapsed,'status':r.decoder.status})
    assert abs(count/elapsed/r.config.actual_rate-1)<.02
   report['ok']=True
  finally:
   r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
   report['final_adc']=asdict(r.config);report['restored']=report['final_adc']==prior['adc']
   PATH.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
