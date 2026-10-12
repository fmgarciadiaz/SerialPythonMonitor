"""Verify integrated packed/legacy ADC codecs on Q, preserving the active profile."""
from pathlib import Path
import sys, time, json
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_switch import Mode

def main():
 require_exclusive_monitor()
 report={'cases':[],'analog':'No evaluado','ok':False}
 path=ROOT/'diagnosticos/resultados_v16/integracion_adc_codecs.json'
 with Connection('1060031107') as c:
  r=OutputReceiver(c,lambda batch:None,print);r.select(Mode.SPI);prior=r.config
  try:
   for bits,rate in ((8,62500),(10,62500),(12,62500),(16,62500),(14,31250),(14,250000)):
    r.configure(Configuration(bits,rate));start=time.monotonic();before=r.decoder.pairs
    while time.monotonic()-start<5:r.pump()
    elapsed=time.monotonic()-start;count=r.decoder.pairs-before
    assert abs(count/elapsed/rate-1)<.03
    report['cases'].append({'bits':bits,'rate':rate,'pairs':count,'seconds':elapsed,'status':r.decoder.status})
   report['ok']=True
  finally:
   r.configure(prior);report['final_adc']=asdict(r.config)
   path.write_text(json.dumps(report,indent=2)+'\n')
 print(path)
if __name__=='__main__':main()
