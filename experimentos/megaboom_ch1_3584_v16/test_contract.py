import unittest,struct,zlib,tempfile,subprocess
from pathlib import Path
from experimentos.megaboom_ch1_3584_v16.support import load
from monitor.v16.receiver.unoq_usb import ProtocolError
from tests.v16.test_ch1_fast import extract
EXP=Path(__file__).resolve().parent
contract,Decoder=load()
def packet(values,index=0,seq=0,t0=0):
 p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,18 if contract.CHANNELS==2 else 19,seq,972)
 struct.pack_into('<i',p,32,992)
 struct.pack_into('<IIIIHBBIII',p,48,1203007,index,0,0,len(values),8,contract.CHANNELS,133,index//3584,0)
 struct.pack_into('<I',p,80,t0)
 for i,(a,b) in enumerate(values):
  p[84+i*contract.CHANNELS]=a
  if contract.CHANNELS==2:p[85+i*contract.CHANNELS]=b
 struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return bytes(p)
class MegaboomTests(unittest.TestCase):
 def test_full_node_wrap_crc_and_native_relay(self):
  values=[(i%256,(255-i)%256) for i in range(3584)]
  count=904//contract.CHANNELS
  frames=[packet(values[i:i+count],i,n,(0xfffffff0+i*133)&0xffffffff) for n,i in enumerate(range(0,3584,count))]
  rows=Decoder().feed(b''.join(frames));self.assertEqual([r[1:3] for r in rows],[(a,b if contract.CHANNELS==2 else 0) for a,b in values])
  self.assertEqual(rows[-1][0],(0xfffffff0+3583*133)&0xffffffff)
  bad=bytearray(frames[0]);bad[84]^=1
  with self.assertRaises(ProtocolError):Decoder().feed(bad)
  base=EXP/'arduino/v16/relay/base_verifier.c';header=base.with_name('config_relay_protocol.h')
  source=f'#define main baseline_main\n#include "{base}"\n#undef main\n#include "{header}"\nint main(void){{uint8_t p[BLOCK];init_crc();DualChecker d={{.period=133,.bits=8}};while(fread(p,1,BLOCK,stdin)==BLOCK)printf("%d\\n",dual_feed(&d,p));}}'
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'check.c';src.write_text(source);exe=src.with_suffix('')
   subprocess.run(['cc','-O2','-std=c11',str(src),'-lm','-o',str(exe)],check=True,capture_output=True)
   result=subprocess.run([str(exe)],input=b''.join(frames),capture_output=True,check=True).stdout
   self.assertEqual(result,b'1\n'*len(frames))
 def test_actual_mcu_packer(self):
  body=extract(EXP/'arduino/v16/oscilloscope/sketch/sketch.ino','build_samples');header=EXP/'arduino/v16/oscilloscope/sketch/benchmark_protocol.h'
  source=f'''#include "{header}"
#include <algorithm>
#include <cstring>
#include <cstdio>
using namespace scope_bench;
constexpr unsigned DMA_NODE_PAIRS=3584;struct Pair{{uint16_t ch1,ch2;}};using ChannelPair=Pair;
namespace acquisition{{constexpr unsigned MEGABOOM_CHANNELS={contract.CHANNELS};struct Node{{uint32_t index,timestamp;Pair samples[3584];}};uint32_t period=133,bits=8,epoch=0,dropped_nodes=0,fatal_errors=0;}}
{body}
int main(){{acquisition::Node node{{0,100,{{}}}};for(unsigned i=0;i<3584;++i)node.samples[i]={{uint16_t(i%256),uint16_t((255-i)%256)}};
uint32_t seq=0;for(unsigned offset=0;offset<3584;offset+=904/{contract.CHANNELS}){{uint8_t p[992];build_samples(p,&node,offset,std::min(904U/{contract.CHANNELS},3584-offset));data_frame(p,seq++,0,0,0,0,992);put16(p+6,{18 if contract.CHANNELS==2 else 19});seal(p);fwrite(p,1,992,stdout);}}}}'''
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'packer.cpp';src.write_text(source);exe=src.with_suffix('')
   subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],check=True,capture_output=True)
   rows=Decoder().feed(subprocess.run([str(exe)],check=True,capture_output=True).stdout)
   self.assertEqual(len(rows),3584);self.assertEqual(rows[-1][1],255)
 def test_actual_adc8_validator_rejects_range_and_timestamp_errors(self):
  header=EXP/'arduino/v16/oscilloscope/sketch/node_validation.h'
  source=f'''#include "{header}"
struct Pair{{uint16_t ch1,ch2;}};
int main(){{uint16_t adc[7168];uint32_t t[3584];Pair out[3584];
for(unsigned i=0;i<3584;++i){{adc[2*i]=i%256;adc[2*i+1]=(255-i)%256;t[i]=0xfffffff0U+i*133U;}}
if(!scope_validation::validate_node<true>(adc,t,3584,8,133,false,0,out))return 1;
for(unsigned i=0;i<3584;++i)if(out[i].ch1!=adc[2*i]||out[i].ch2!=adc[2*i+1])return 2;
t[1024]++;if(scope_validation::validate_node<false>(adc,t,3584,8,133,false,0,out))return 3;
t[1024]--;adc[2049]=256;if(scope_validation::validate_node<true>(adc,t,3584,8,133,false,0,out))return 4;
}}'''
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'validator.cpp';src.write_text(source);exe=src.with_suffix('')
   subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],check=True,capture_output=True)
   subprocess.run([str(exe)],check=True,capture_output=True)
