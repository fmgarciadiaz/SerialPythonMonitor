"""CRC-checked control-only rescue: snapshot before reset; never accept ADC data."""
import sys,json,time,struct,zlib,subprocess
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from unoq import Board,config_path
import usb_stream
from experimentos.megaboom_ch1_3584_v16.run import start_relay
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_generator import generator_request,generator_reply
from monitor.historico.v16.receiver.unoq_wav import command as wav_command,status as wav_status
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
require_exclusive_monitor()
b=Board(json.loads(config_path('v16').read_text()))
usb_stream.ROOT=EXP/'recovery'
try:
 try:target=usb_stream.binary(b,p992=True,audio=True)
 except subprocess.CalledProcessError:target=usb_stream.binary(b,build=True,p992=True,audio=True)
finally:usb_stream.ROOT=ROOT
start_relay(b,target)
prior={};buffer=bytearray()
with Connection(b.serial) as c:
 c.socket.sendall(generator_request(0x80000001))
 end=time.monotonic()+8
 while time.monotonic()<end and 'generator' not in prior:
  buffer.extend(c.read())
  while len(buffer)>=992:
   p=bytes(buffer[:992]);del buffer[:992]
   assert p[:4]==b'SCP1' and zlib.crc32(p[:988])==struct.unpack_from('<I',p,988)[0]
   kind=struct.unpack_from('<H',p,6)[0]
   if kind in (3,15,16,19):
    rate,index,dropped,fatal,count,bits,channels,period,node,flags=struct.unpack_from('<IIIIHBBIII',p,48)
    prior.update(adc={'bits':bits,'rate':rate},mode='SPI',initial_fault={'dropped':dropped,'fatal':fatal,'epoch':flags>>1})
   if kind==9:prior['generator']=asdict(generator_reply(p).active)
 if 'adc' not in prior or 'generator' not in prior:raise RuntimeError('Snapshot incompleto; no reiniciar')
(EXP/'prior.json').write_text(json.dumps(prior,indent=2)+'\n')
print(prior,flush=True)
