"""Physical DAC memory ownership transitions at an established low ADC rate."""
import time
from dataclasses import asdict,replace
import numpy as np
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_wav import State
def run(serial):
 with Connection(serial) as connection:
  r=OutputReceiver(connection,lambda _:None);r.decoder.numeric=True;r.select(Mode.SPI)
  prior=r.config;generator=r.generator().active
  if generator.enabled:raise RuntimeError('Generator busy before storage smoke test')
  r.configure(Configuration(14,40000))
  tone=GeneratorConfig(wave=1,enabled=1,mode=3,frequency=20000000,final_frequency=40000000,duration=1000,low=800,high=3300)
  applied=r.generator(tone)
  if not applied.running:raise RuntimeError('Radio Test failed after PCM output')
  before=r.decoder.pairs;end=time.monotonic()+2
  while time.monotonic()<end:r.pump()
  samples=r.decoder.pairs-before;r.generator(replace(tone,enabled=0))
  codes=np.rint(2048+200*np.sin(np.arange(3840)*2*np.pi*1000/40000)).astype('<u2')
  r.reset_wav_output();r.wav_request(1,codes,40000);end=time.monotonic()+5
  while time.monotonic()<end:
   r.pump()
   if r.wav_status and r.wav_status.state in (State.DONE,State.UNDERRUN,State.FAULT):break
  status=r.wav_status
  if status is None or status.state!=State.DONE or status.played!=len(codes):
   raise RuntimeError('PCM failed after Radio Test: '+str(status))
  r.wav_request(3);end=time.monotonic()+3
  while r.wav_pending and time.monotonic()<end:r.pump()
  if r.wav_pending:raise RuntimeError('Storage test Stop unconfirmed')
  r.generator(generator);r.configure(prior)
  return {'ok':True,'radio_test_adc_samples':samples,'pcm_played':status.played,'queue_slots':status.queue_slots,'generator_restored':asdict(r.generator().active)==asdict(generator)}
