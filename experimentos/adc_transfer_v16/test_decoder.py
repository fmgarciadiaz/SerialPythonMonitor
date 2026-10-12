import unittest,struct
from tests.v16.test_compact_protocol import packet,seal
from experimentos.adc_transfer_v16.decoder import TransferDecoder
from monitor.v16.receiver.unoq_usb import ProtocolError
class TransferDecoderTests(unittest.TestCase):
 def diagnostic(self):
  p=bytearray(packet(index=1806,count=0,t0=100));struct.pack_into('<H',p,6,15);struct.pack_into('<H',p,64,242)
  group=(123|(456<<14)|(123<<28)|(456<<42)).to_bytes(7,'little');p[84:931]=group*121
  struct.pack_into('<13I',p,931,0x32474454,10,7000,8000,70000,100,9900,5000,40000,9900,3,3,1)
  return seal(p)
 def test_telemetry_and_fragmented_input(self):
  d=TransferDecoder();p=self.diagnostic();self.assertEqual(d.feed(p[:20]),[]);rows=d.feed(p[20:])
  self.assertEqual(len(rows),242);self.assertEqual(rows[-1][3],2047)
  self.assertEqual(d.telemetry[-1]['queued'],3)
 def test_raw_crc_is_validated(self):
  p=bytearray(self.diagnostic());p[935]^=1
  with self.assertRaisesRegex(ProtocolError,'CRC'):TransferDecoder().feed(p)
 def test_reserved_padding_stays_strict(self):
  p=bytearray(self.diagnostic());p[985]=1
  with self.assertRaisesRegex(ProtocolError,'Padding'):TransferDecoder().feed(seal(p))
 def test_queue_range(self):
  p=bytearray(self.diagnostic());struct.pack_into('<I',p,971,5)
  with self.assertRaisesRegex(ProtocolError,'Telemetría'):TransferDecoder().feed(seal(p))
