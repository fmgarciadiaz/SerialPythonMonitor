"""Validate the unchanged integrated profile and preserve a fresh Q snapshot."""
import sys,time,json
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_generator import GeneratorConfig
from monitor.v16.receiver.unoq_switch import Mode
from monitor.v16.receiver.unoq_wav import State
EXP=Path(__file__).resolve().parent
require_exclusive_monitor()
report={'ok':False,'restored':False,'cases':[]}
with Connection('1060031107') as c:
 r=OutputReceiver(c,lambda b:None,print);r.select(Mode.SPI)
 g=r.generator();r.wav_request();end=time.monotonic()+5
 while r.wav_pending and time.monotonic()<end:r.pump()
 if r.wav_status.state not in (State.IDLE,State.DONE):raise RuntimeError('WAV ocupado')
 # Session snapshot was recovered before resetting the previously failed relay.
 assert (EXP/'prior.json').is_file()
 snapshot=json.loads((EXP/'prior.json').read_text())
 prior={'adc':snapshot['adc'],'generator':snapshot['generator']}
 r.generator(GeneratorConfig(enabled=0))
 try:
  r.configure(Configuration(8,1203007));start=time.monotonic();before=r.decoder.pairs;next_log=start+10
  while time.monotonic()-start<120:
   r.pump()
   if time.monotonic()>=next_log:
    print(f'Baseline {time.monotonic()-start:.0f}s {r.decoder.pairs-before}',flush=True);next_log+=10
  elapsed=time.monotonic()-start;count=r.decoder.pairs-before
  report['cases'].append({'seconds':elapsed,'samples':count,'status':r.decoder.status})
  assert abs(count/elapsed/r.config.actual_rate-1)<.02
  report['ok']=True
 except Exception as exc:
  report['error']=str(exc);report['status']=r.decoder.status
 finally:
  try:
   r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
   report['final_adc']=asdict(r.config);report['final_generator']=asdict(r.generator().active)
   report['restored']=report['final_adc']==prior['adc'] and report['final_generator']==prior['generator']
  except Exception as exc:report['restore_error']=str(exc)
  (EXP/'baseline.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
