"""Negotiated DAC capacity; old 16-block firmware remains compatible."""
import struct,unittest,zlib,subprocess,tempfile
from pathlib import Path
from monitor.v17.receiver import unoq_wav as wav
from monitor.v17.receiver.unoq_usb import ProtocolError
class WavSlotsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  folder=Path(cls.tmp.name);src=folder/'check.c';cls.checker=folder/'check'
  src.write_text('#define main base_main\n#include "base_verifier.c"\n#undef main\n#include "config_relay_protocol.h"\nint main(){init_crc();DualChecker d={0};uint8_t p[992];return fread(p,1,992,stdin)==992 && dual_feed(&d,p)?0:1;}\n')
  relay=Path(__file__).resolve().parents[2]/'experimentos/radio_dac_headroom_v17/relay'
  subprocess.run(['cc','-O2','-std=c11','-I',str(relay),str(src),'-lm','-o',str(cls.checker)],check=True)
 def frame(self,slots,free):
  p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,12,0,972)
  struct.pack_into('<IIBBHIIIIII',p,16,0x80000001,1,1,0,free,0,0,48000,40000,7,slots)
  struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return bytes(p)
 def test_legacy_and_extended_statuses(self):
  for field,expected in ((0,16),(16,16),(30,30)):
   frame=self.frame(field,expected)
   subprocess.run([str(self.checker)],input=frame,check=True)
   result=wav.status(frame);self.assertEqual(result.queue_slots,expected)
   self.assertEqual(result.free_blocks,expected)
 def test_unknown_capacity_and_impossible_free_count_are_rejected(self):
  for field,free in ((31,31),(30,31),(0,17)):
   frame=self.frame(field,free)
   self.assertNotEqual(subprocess.run([str(self.checker)],input=frame).returncode,0)
   with self.assertRaises(ProtocolError):wav.status(frame)
