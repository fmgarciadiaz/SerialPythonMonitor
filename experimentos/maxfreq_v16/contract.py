"""Isolated kind-20 compact CH1 contract. Stable V16 imports are untouched."""
import struct,zlib,time,secrets
from collections import Counter
from dataclasses import dataclass
from monitor.v16.receiver.unoq_generator import generator_request,generator_reply
MASK=0xffffffff
CAPACITY={8:864,10:696,14:496}
def valid(bits,ticks,n):
 return bits in CAPACITY and 78<=ticks<=640 and 1024<=n<=8192 and n%16==0
def frame(kind,rid):
 p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,kind,rid,972);return p
def seal(p):
 struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return bytes(p)
def request(rid,bits,ticks,n):
 if not valid(bits,ticks,n):raise ValueError('Perfil experimental inválido')
 p=frame(6,rid);p[16]=bits;struct.pack_into('<I',p,20,(n<<16)|ticks);return seal(p)
class Decoder:
 def __init__(self):
  self.buffer=bytearray();self.seq=None;self.profile=None;self.epoch=0;self.last=None
  self.pairs=0;self.nodes=0;self.status=None;self.applied={};self.generators={}
  self.queue_hist=Counter();self.send_ticks=[];self.maxima=Counter();self.node_first=None
 def reset_metrics(self):
  self.queue_hist.clear();self.send_ticks.clear();self.maxima.clear()
 def feed(self,data):
  self.buffer.extend(data)
  while len(self.buffer)>=992:
   p=bytes(self.buffer[:992]);del self.buffer[:992]
   magic,version,kind,seq,length=struct.unpack_from('<4sHHII',p)
   if (magic,version,length)!=(b'SCP1',4,972) or zlib.crc32(p[:988])!=struct.unpack_from('<I',p,988)[0]:raise ValueError('CRC/cabecera')
   if self.seq is not None and (seq-self.seq)&MASK!=1:raise ValueError('Secuencia')
   self.seq=seq
   if kind==9:
    reply=generator_reply(p);self.generators[reply.request_id]=reply;continue
   if kind==7:
    rid,bits,active,phase,reason,wanted,encoded,epoch=struct.unpack_from('<IBBBBIII',p,16)
    ticks,n=encoded&65535,encoded>>16
    if not valid(active,ticks,n) or any(p[36:988]):raise ValueError('APPLIED inválido')
    if phase==3:raise ValueError(f'Configuración rechazada: {reason}')
    if phase==2:
     if bits!=active or wanted!=encoded:raise ValueError('APPLIED contradictorio')
     if epoch!=self.epoch:self.last=None;self.node_first=None
     self.profile=(active,ticks,n);self.epoch=epoch;self.applied[rid]=self.profile
    continue
   if kind!=20:raise ValueError(f'Tipo desconocido {kind}')
   ack,spi,bad,short,result,error=struct.unpack_from('<IIIIii',p,16)
   rate,index,dropped,fatal,count,bits,channels,ticks,node,flags=struct.unpack_from('<IIIIHBBIII',p,48)
   n,q,peak,copy,poll,detect,send,produced=struct.unpack_from('<8I',p,84)
   self.status=dict(bits=bits,ticks=ticks,node_pairs=n,rate=rate,dropped=dropped,fatal=fatal,queue=q,queue_peak=peak,copy_ticks=copy,poll_ticks=poll,slack_ticks=detect,send_ticks=send,produced=produced,epoch=flags>>1)
   if spi or bad or short or error or result not in (0,992) or dropped or fatal or flags&1:raise ValueError(f'Adquisición interrumpida: {self.status}')
   if not valid(bits,ticks,n) or channels!=1 or rate!=160000000//ticks or q>4 or peak>4:raise ValueError('Metadatos')
   if self.profile is None:self.profile=(bits,ticks,n);self.epoch=flags>>1
   if self.profile!=(bits,ticks,n) or self.epoch!=flags>>1:raise ValueError('Cambio sin APPLIED')
   used=(count*bits+7)//8;offset=(index-node*n)&MASK
   if any(p[116+used:988]) or count>CAPACITY[bits] or count%4:raise ValueError('Padding/cantidad')
   timestamp=struct.unpack_from('<I',p,80)[0]
   if not count:
    if index or node or timestamp:raise ValueError('Estado vacío')
    continue
   if offset>=n or count>n-offset:raise ValueError('Fuera de nodo')
   if self.last is not None and (((index-self.last[0])&MASK)!=1 or ((timestamp-self.last[1])&MASK)!=ticks):raise ValueError('Continuidad índice/timestamp')
   self.last=((index+count-1)&MASK,(timestamp+(count-1)*ticks)&MASK)
   self.queue_hist[q]+=1
   self.maxima['slack_min_ticks']=min(self.maxima.get('slack_min_ticks',0xffffffff),detect)
   for key,value in (('copy_ticks',copy),('poll_ticks',poll),('queue_peak',peak)):
    self.maxima[key]=max(self.maxima[key],value)
   if offset==0 and send:self.send_ticks.append(send)
   if offset+count==n:self.nodes+=1
   self.pairs+=count

class Session:
 def __init__(self,connection):self.connection=connection;self.decoder=Decoder()
 def pump(self):self.decoder.feed(self.connection.read())
 def configure(self,bits,ticks,n):
  rid=secrets.randbelow(0x7ffffffe)+0x80000000
  self.connection.socket.sendall(request(rid,bits,ticks,n));end=time.monotonic()+5
  while time.monotonic()<end:
   self.pump()
   if rid in self.decoder.applied:return
  raise TimeoutError('Sin APPLIED')
 def generator(self,config=None):
  rid=secrets.randbelow(0x7ffffffe)+0x80000000
  self.connection.socket.sendall(generator_request(rid,config));end=time.monotonic()+5
  while time.monotonic()<end:
   self.pump()
   if rid in self.decoder.generators:
    reply=self.decoder.generators[rid]
    if int(reply.phase)==2:return reply
    if int(reply.phase)==3:raise ValueError('Generador rechazado')
  raise TimeoutError('Sin generador APPLIED')
