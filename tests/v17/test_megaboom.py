import struct,subprocess,tempfile,unittest,zlib
from pathlib import Path
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_config_decoder import ConfigurationDecoder
from experimentos.megaboom_ch1_3584_v16.test_contract import packet
ROOT=Path(__file__).resolve().parents[2]
class IntegratedMegaboomTests(unittest.TestCase):
 def test_configuration_and_full_node_with_native_validation(self):
  config=Configuration(8,1203007)
  self.assertEqual((config.period,config.channels,config.sampling_cycles),(133,1,5))
  for bits in (10,12,14,16):
   with self.assertRaises(ValueError): Configuration(bits,1203007)
  values=[(i%256,0) for i in range(3584)]
  frames=[packet(values[i:i+904],i,n,(0xfffffff0+i*133)&0xffffffff) for n,i in enumerate(range(0,3584,904))]
  rows=ConfigurationDecoder().feed(b''.join(frames))
  self.assertEqual(len(rows),3584);self.assertEqual([r[1] for r in rows],[i%256 for i in range(3584)])
  base=ROOT/'arduino/v17/relay/base_verifier.c';header=base.with_name('config_relay_protocol.h')
  source=f'#define main baseline_main\n#include "{base}"\n#undef main\n#include "{header}"\nint main(void){{uint8_t p[BLOCK];init_crc();DualChecker d={{.period=133,.bits=8}};while(fread(p,1,BLOCK,stdin)==BLOCK)printf("%d\\n",dual_feed(&d,p));}}'
  # The sample index wraps inside this non-power-of-two node.
  wrap_frames=[]
  node=(1<<32)//3584
  for seq,i in enumerate(range(0,3584,904)):
   frame=bytearray(packet(values[i:i+904],i,seq,(0xfffffff0+i*133)&0xffffffff))
   struct.pack_into('<I',frame,52,(node*3584+i)&0xffffffff)
   struct.pack_into('<I',frame,72,node)
   struct.pack_into('<I',frame,988,zlib.crc32(frame[:988]));wrap_frames.append(bytes(frame))
  self.assertEqual(len(ConfigurationDecoder().feed(b''.join(wrap_frames))),3584)
  frames=wrap_frames
  bad=bytearray(frames[-1]);bad[987]=1;struct.pack_into('<I',bad,988,zlib.crc32(bad[:988]))
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'check.c';src.write_text(source);exe=src.with_suffix('')
   subprocess.run(['cc','-O2','-std=c11',str(src),'-lm','-o',str(exe)],check=True,capture_output=True)
   out=subprocess.run([str(exe)],input=b''.join(frames)+bytes(bad),check=True,capture_output=True).stdout
   self.assertEqual(out,b'1\n'*4+b'0\n')
