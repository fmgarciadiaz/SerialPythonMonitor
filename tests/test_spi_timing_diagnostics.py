import struct,zlib,unittest,subprocess,tempfile
from pathlib import Path
from experimentos.timing_spi.receiver.unoq_config_decoder import ConfigurationDecoder
from experimentos.timing_spi.receiver.unoq_usb import ProtocolError
ROOT=Path(__file__).resolve().parents[1]
def packet():
 p=bytearray(512);struct.pack_into('<4sHHII',p,0,b'SCP1',2,3,0,492)
 struct.pack_into('<I',p,32,512)
 struct.pack_into('<IIIIHBBIII',p,48,100000,2014,0,0,34,14,2,10,0,0)
 for i in range(34):struct.pack_into('<IHH',p,80+8*i,1000+10*i,42,43)
 p[352:356]=b'TDG1';struct.pack_into('<IIII',p,488,2,3,0,0)
 struct.pack_into('<I',p,508,zlib.crc32(p[:508]));return p
class TimingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  source=Path(cls.tmp.name)/'relay.c';cls.exe=Path(cls.tmp.name)/'relay'
  source.write_text('#define main verifier_main\n#include "diagnosticos/verificar_spi.c"\n#undef main\n#include "experimentos/timing_spi/relay/config_relay_protocol.h"\nint main(int argc,char **argv){(void)argv;init_crc();DualChecker d={.period=10,.bits=14};uint8_t p[512];if(fread(p,1,512,stdin)!=512)return 2;return (argc>1?dual_command(p):dual_feed(&d,p))?0:2;}')
  subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT),str(source),'-lm','-o',str(cls.exe)],check=True)
 def test_snapshot_preserves_every_sample_and_is_cross_validated(self):
  p=packet();d=ConfigurationDecoder();samples=d.feed(p)
  self.assertEqual(len(samples),34);self.assertEqual(samples[-1],(1330,42,43,2047))
  self.assertEqual(d.telemetry[0]['queue_peak'],3);self.assertEqual(len(d.telemetry[0]['metrics']),11)
  self.assertEqual(subprocess.run([str(self.exe)],input=p).returncode,0)
 def test_crc_queue_and_padding_corruption_rejected(self):
  for offset,value,reseal in ((81,9,False),(488,5,True),(504,1,True),(352,0,True)):
   p=packet();p[offset]=value
   if reseal:struct.pack_into('<I',p,508,zlib.crc32(p[:508]))
   with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(p)
   self.assertNotEqual(subprocess.run([str(self.exe)],input=p).returncode,0)
