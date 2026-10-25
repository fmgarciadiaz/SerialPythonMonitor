import unittest,struct,zlib,subprocess,tempfile,shutil
from pathlib import Path
from monitor.historico.v16.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.historico.v16.receiver.unoq_usb import ProtocolError
from monitor.historico.v16.receiver.unoq_generator import generator_request,GeneratorConfig
from monitor.historico.v16.receiver.unoq_acquisition import acquisition_request,Configuration
from monitor.historico.v16.receiver.unoq_control import status_request
ROOT=Path(__file__).resolve().parents[3]
MASK=0xffffffff
def packet(index=0,count=226,t0=0,seq=0,version=4,epoch=0):
 p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',version,3,seq,972)
 struct.pack_into('<i',p,32,992)
 struct.pack_into('<IIIIHBBIII',p,48,125000,index,0,0,count,14,2,8,index//2048,epoch<<1)
 struct.pack_into('<I',p,80,t0)
 for i in range(count):struct.pack_into('<HH',p,84+4*i,123,456)
 return seal(p)
def seal(p):struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return bytes(p)
class CompactProtocolTests(unittest.TestCase):
 def test_node_fragments_and_fragmented_tcp(self):
  decoder=ConfigurationDecoder();result=[]
  for seq,offset in enumerate(range(0,2048,226)):
   p=packet(offset,min(226,2048-offset),100+offset*8,seq)
   result.extend(decoder.feed(p[:17]));result.extend(decoder.feed(p[17:]))
  self.assertEqual(len(result),2048);self.assertEqual(result[-1],(100+2047*8,123,456,2047))
 def test_clock_wrap(self):
  d=ConfigurationDecoder();a=d.feed(packet(t0=MASK-15,count=2));b=d.feed(packet(index=2,count=1,t0=0,seq=1))
  self.assertEqual(a[0][0],MASK-15);self.assertEqual(b[0][0],0)
 def test_index_sequence_and_clock_wrap_across_packet_boundary(self):
  d=ConfigurationDecoder()
  a=d.feed(packet(index=MASK-1,count=2,t0=MASK-15,seq=MASK))
  b=d.feed(packet(index=0,count=2,t0=0,seq=0))
  self.assertEqual([row[3] for row in a+b],[MASK-1,MASK,0,1])
  self.assertEqual([row[0] for row in a+b],[MASK-15,MASK-7,0,8])
 def test_range_check_covers_each_channel_and_entire_packet(self):
  for sample in (0,113,225):
   for channel in (0,1):
    with self.subTest(sample=sample,channel=channel):
     p=bytearray(packet());struct.pack_into('<H',p,84+sample*4+channel*2,16384)
     with self.assertRaisesRegex(ProtocolError,'ADC fuera de rango'):ConfigurationDecoder().feed(seal(p))
 def test_reject_previous_protocol(self):
  with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(packet(version=3))
 def test_invalid_crc_range_padding_boundary(self):
  for offset,value in [(84,65535),(64,227),(72,1)]:
   p=bytearray(packet(count=1));struct.pack_into('<H' if offset!=72 else '<I',p,offset,value)
   with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(seal(p))
  p=bytearray(packet(count=1));p[90]=1
  with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(seal(p))
  p=bytearray(packet());p[100]^=1
  with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(p)
 def test_discontinuity(self):
  for index,t0,seq in [(3,16,1),(2,17,1),(2,16,2)]:
   d=ConfigurationDecoder();d.feed(packet(count=2))
   with self.assertRaises(ProtocolError):d.feed(packet(index=index,count=1,t0=t0,seq=seq))
 def test_empty_status(self):
  self.assertEqual(ConfigurationDecoder().feed(packet(count=0)),[])
  with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(packet(count=0,t0=1))
 def test_control_versions(self):
  from monitor.historico.v16.receiver.unoq_wav import command,chunk
  frames=[status_request(0x80000001),generator_request(0x80000001),acquisition_request(0x80000001,Configuration(14,125000)),command(0x80000001),chunk(0x80000001,1,0,[0,4095])]
  for p in frames:
   self.assertEqual(struct.unpack_from('<H',p,4)[0],4)
   self.assertEqual(zlib.crc32(p[:988]),struct.unpack_from('<I',p,988)[0])
 def test_c_python_vectors(self):
  if not shutil.which('cc'):self.skipTest('C compiler missing')
  with tempfile.TemporaryDirectory() as folder:
   exe=Path(folder)/'check';subprocess.run(['cc','-std=c11','-O2',str(ROOT/'arduino/historico/v16/tests/checker.c'),'-lm','-o',str(exe)],check=True,capture_output=True)
   reply=bytearray(992);struct.pack_into('<4sHHII',reply,0,b'SCP1',4,9,0,972)
   struct.pack_into('<I',reply,16,0x80000001);reply[20]=2
   config=GeneratorConfig(wave=1,enabled=0,frequency=50000000,final_frequency=40000000)
   reply[24:44]=config.pack();reply[44:64]=config.pack()
   cases=[packet(),packet(count=14),packet(count=0),packet(version=3),seal(reply)]
   output=subprocess.run([str(exe)],input=b''.join(cases),capture_output=True,check=True).stdout
   self.assertEqual(output,b'1\n1\n1\n0\n1\n')

 def test_native_full_timestamp_validation(self):
  if not shutil.which('c++'):self.skipTest('C++ compiler missing')
  with tempfile.TemporaryDirectory() as folder:
   exe=Path(folder)/'node-validation'
   subprocess.run(['c++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(ROOT/'arduino/historico/v16/tests/node_validation.cpp'),'-o',str(exe)],check=True,capture_output=True)
   subprocess.run([str(exe)],check=True,capture_output=True)

 def test_generator_50khz_contract_and_timing(self):
  config=GeneratorConfig(wave=1,frequency=50000000,final_frequency=50000000)
  self.assertEqual(struct.unpack_from('<I',config.pack(),4)[0],50000000)
  with self.assertRaises(ValueError):GeneratorConfig(frequency=50000001)
  if not shutil.which('c++'):self.skipTest('C++ compiler missing')
  with tempfile.TemporaryDirectory() as folder:
   exe=Path(folder)/'timing'
   subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',str(ROOT/'arduino/historico/v16/tests/generator_timing.cpp'),'-o',str(exe)],check=True,capture_output=True)
   subprocess.run([str(exe)],check=True,capture_output=True)
