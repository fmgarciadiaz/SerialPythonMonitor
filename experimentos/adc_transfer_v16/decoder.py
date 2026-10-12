"""Validate diagnostic CRC before stripping reserved telemetry for the V16 decoder."""
import struct,zlib
try:
 from .packed_decoder import PackedDecoder as ConfigurationDecoder
except ImportError:
 from packed_decoder import PackedDecoder as ConfigurationDecoder
from monitor.v16.receiver.unoq_usb import ProtocolError
KEYS=('magic','nodes','node_last_us','node_max_us','node_sum_us','frames','prep_sum_us','setup_sum_us','wait_sum_us','check_sum_us','queued','queued_max','free')
class TransferDecoder(ConfigurationDecoder):
 def __init__(self):
  super().__init__();self.wire=bytearray();self.telemetry=[]
 def feed(self,data):
  self.wire.extend(data);clean=bytearray()
  while len(self.wire)>=992:
   p=bytearray(self.wire[:992]);del self.wire[:992]
   if struct.unpack_from('<HH',p,4)==(4,15) and struct.unpack_from('<H',p,64)[0]==242 and struct.unpack_from('<I',p,52)[0]%2048==1806 and p[931:935]==b'TDG2':
    if zlib.crc32(p[:988])!=struct.unpack_from('<I',p,988)[0]:raise ProtocolError('CRC diagnóstico inválido')
    values=dict(zip(KEYS,struct.unpack_from('<13I',p,931)))
    if values['queued']>4 or values['free']>4 :raise ProtocolError('Telemetría inválida')
    values['period_us']=struct.unpack_from('<I',p,68)[0];values['epoch']=struct.unpack_from('<I',p,76)[0]>>1
    self.telemetry.append(values);p[931:983]=bytes(52);struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
   clean.extend(p)
  return super().feed(clean)
