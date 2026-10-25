"""Independent CH1 trial; restore the stable MCU/relay and exact prior profile."""
from pathlib import Path
import sys,json,time,subprocess
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.megaboom_ch1_v16.support import load
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
import monitor.historico.v16.receiver.unoq_config_receiver as receiver_module
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig
from monitor.historico.v16.receiver.unoq_wav import State
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from unoq import Board,config_path
import usb_stream
from spi_benchmark import IMAGE

def start_relay(board,target):
 usb_stream.stop(board)
 board.shell('docker','run','-d','--name',usb_stream.CONTAINER,'--network','host','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','0:0','--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw','--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly','--entrypoint','/work/unoq_stream',IMAGE)
 end=time.monotonic()+15
 while time.monotonic()<end:
  logs=board.run('shell','docker logs '+usb_stream.CONTAINER+' 2>&1',capture=True).stdout
  if 'SPI ready: first verified frame' in logs:return
  time.sleep(.2)
 raise RuntimeError('Relay no confirmó trama SPI')


def main():
 require_exclusive_monitor()
 stable=Board(json.loads(config_path('v16').read_text()));config=dict(stable.config)
 config.update(name='Scope V16 Megaboom CH1 Experimental',remote_app='/home/arduino/ArduinoApps/scope-v16-megaboom-ch1-experimental',local_app='experimentos/megaboom_ch1_v16/arduino/historico/v16/oscilloscope')
 candidate=Board(config);report={'cases':[],'restored':False,'ok':False,'analog':'No evaluado','channels':1,'timestamp_hz':160000000,'period_ticks':133,'actual_rate':160000000/133}
 path=EXP/'results.json'
 def save():path.write_text(json.dumps(report,indent=2)+'\n')
 with Connection(stable.serial) as c:
  r=OutputReceiver(c,lambda b:None,print);r.select(Mode.SPI);g=r.generator();r.wav_request();end=time.monotonic()+5
  while r.wav_pending and time.monotonic()<end:r.pump()
  if g.running or g.active.enabled or not (r.wav_status.state==State.IDLE or (r.wav_status.state==State.DONE and not r.wav_status.reason)):raise RuntimeError('Salida ocupada; no se cambia el firmware')
  prior={'adc':asdict(r.config),'generator':asdict(g.active)};report['prior']=prior;save()
 stable_decoder=receiver_module.ConfigurationDecoder;stable_config=receiver_module.Configuration
 binary=usb_stream.binary(stable,p992=True,audio=True);switched=False
 try:
  candidate.compile();report['backup']=str(stable.backup());save()
  apps=json.loads(candidate.cli('app','list','--format','json',capture=True).stdout).get('apps',[])
  if any(a.get('name')==config['name'] for a in apps):candidate.push_sources(candidate.check_sources(),candidate.remote)
  else:candidate.create()
  usb_stream.ROOT=EXP
  try:
   try:target=usb_stream.binary(candidate,p992=True,audio=True)
   except subprocess.CalledProcessError:target=usb_stream.binary(candidate,build=True,p992=True,audio=True)
  finally:usb_stream.ROOT=ROOT
  require_exclusive_monitor();switched=True
  usb_stream.stop(stable);stable.stop();candidate.start();start_relay(candidate,target)
  contract,decoder=load();receiver_module.Configuration=contract.Configuration;receiver_module.ConfigurationDecoder=decoder
  with Connection(stable.serial) as c:
   r=OutputReceiver(c,lambda b:None,print);r.select(Mode.SPI)
   for seconds in (10,120):
    start=time.monotonic();before=r.decoder.pairs;next_log=start+10
    while time.monotonic()-start<seconds:
     r.pump()
     if time.monotonic()>=next_log:
      print(f'Megaboom: {time.monotonic()-start:.1f}s {r.decoder.pairs-before} muestras',flush=True);next_log+=10
    elapsed=time.monotonic()-start;count=r.decoder.pairs-before
    case={'seconds':elapsed,'samples':count,'observed_rate':count/elapsed,'status':r.decoder.status}
    report['cases'].append(case);save()
    if abs(count/elapsed/report['actual_rate']-1)>.02:raise RuntimeError('Tasa incorrecta')
   report['ok']=True
 except Exception as exc:
  report['error']=str(exc);print('Ensayo:',exc,flush=True)
 finally:
  receiver_module.ConfigurationDecoder=stable_decoder;receiver_module.Configuration=stable_config
  if switched:
   try:
    (EXP/'relay_trial.log').write_text(stable.run('shell','docker logs '+usb_stream.CONTAINER+' 2>&1',capture=True).stdout)
    usb_stream.stop(stable);candidate.stop();stable.start();start_relay(stable,binary)
    with Connection(stable.serial) as c:
     r=OutputReceiver(c,lambda b:None,print);r.select(Mode.SPI)
     r.generator(GeneratorConfig(**prior['generator']));r.configure(stable_config(**prior['adc']))
     start=time.monotonic();before=r.decoder.pairs
     while time.monotonic()-start<10:r.pump()
     report['final_adc']=asdict(r.config);report['final_generator']=asdict(r.generator().active)
     report['restore_samples']=r.decoder.pairs-before
     report['restored']=report['final_adc']==prior['adc'] and report['final_generator']==prior['generator']
   except Exception as exc:report['restore_error']=str(exc)
  else:report['restored']=True
  save();print(json.dumps(report,indent=2),flush=True)
 return 0 if report['ok'] and report['restored'] else 1
if __name__=='__main__':raise SystemExit(main())
