import unittest,struct,zlib,random,tempfile,subprocess
from pathlib import Path
from experimentos.ch1_660_v16.support import load
from monitor.historico.v16.receiver.unoq_usb import ProtocolError
EXP=Path(__file__).resolve().parent
contract,SingleDecoder=load()
def seal(p):struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return bytes(p)
def packet(samples,index=0,t0=0,seq=0):
 p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,16,seq,972)
 struct.pack_into('<i',p,32,992)
 struct.pack_into('<IIIIHBBIII',p,48,661157,index,0,0,len(samples),14,1,242,index//2048,0)
 struct.pack_into('<I',p,80,t0)
 for i in range(0,len(samples),4):
  word=sum(samples[i+j]<<(14*j) for j in range(4));p[84+i//4*7:91+i//4*7]=word.to_bytes(7,'little')
 return seal(p)
def extract(path,name):
 s=path.read_text();start=s.index('static void '+name+'(');begin=s.index('{',start);end=begin+1;depth=1
 while depth:
  if s[end]=='{':depth+=1
  elif s[end]=='}':depth-=1
  end+=1
 return s[start:end]
class ContractTests(unittest.TestCase):
 def test_full_node_exact_values_timestamp_wrap(self):
  rng=random.Random(600);values=[rng.randrange(16384) for _ in range(2048)];values[:4]=[0,16383,1,16382]
  d=SingleDecoder();rows=[]
  for seq,i in enumerate(range(0,2048,516)):rows+=d.feed(packet(values[i:i+516],i,(0xfffffff0+i*242)&0xffffffff,seq))
  self.assertEqual([r[1] for r in rows],values)
  self.assertEqual(rows[-1][0],(0xfffffff0+2047*242)&0xffffffff)
 def test_reject_count_channels_padding_clock_crc(self):
  p=packet([0,16383]*258)
  for offset,value,fmt in ((64,515,'<H'),(67,2,'<B'),(68,268,'<I'),(987,1,'<B')):
   q=bytearray(p);struct.pack_into(fmt,q,offset,value)
   with self.assertRaises(ProtocolError):SingleDecoder().feed(seal(q))
  q=bytearray(p);q[84]^=1
  with self.assertRaises(ProtocolError):SingleDecoder().feed(q)
  d=SingleDecoder();d.feed(p)
  with self.assertRaises(ProtocolError):d.feed(packet([1]*516,516,516*242+1,1))
 def test_native_relay_matches_decoder(self):
  base=EXP/'arduino/historico/v16/relay/base_verifier.c';header=base.with_name('config_relay_protocol.h')
  source=f'''#define main baseline_main\n#include "{base}"\n#undef main\n#include "{header}"\nint main(void){{uint8_t p[BLOCK];init_crc();DualChecker d={{.period=242,.bits=14}};while(fread(p,1,BLOCK,stdin)==BLOCK)printf("%d\\n",dual_feed(&d,p));}}'''
  values=[i%16384 for i in range(2048)];frames=[packet(values[i:i+516],i,i*242,n) for n,i in enumerate(range(0,2048,516))]
  bad=bytearray(packet([1]*516,2048,2048*242,4));bad[987]=1
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'check.c';src.write_text(source);exe=src.with_suffix('')
   subprocess.run(['cc','-O2','-std=c11',str(src),'-lm','-o',str(exe)],check=True,capture_output=True)
   out=subprocess.run([str(exe)],input=b''.join(frames)+seal(bad),check=True,capture_output=True).stdout
   self.assertEqual(out,b'1\n'*4+b'0\n')
 def test_actual_mcu_packer(self):
  body=extract(EXP/'arduino/historico/v16/oscilloscope/sketch/sketch.ino','build_samples');header=EXP/'arduino/historico/v16/oscilloscope/sketch/benchmark_protocol.h'
  source=f'''#include "{header}"\n#include <algorithm>\n#include <cstring>\n#include <cstdio>\nusing namespace scope_bench;
constexpr unsigned DMA_NODE_PAIRS=2048;struct Pair{{uint16_t ch1,ch2;}};
namespace acquisition{{struct Node{{uint32_t index,timestamp;Pair samples[2048];}};uint32_t period=242,bits=14,epoch=0,dropped_nodes=0,fatal_errors=0;}}
{body}
int main(){{acquisition::Node node{{0,100,{{}}}};for(unsigned i=0;i<2048;++i)node.samples[i]={{uint16_t(i*13%16384),0}};
uint32_t seq=0;for(unsigned offset=0;offset<2048;offset+=516){{uint8_t p[992];build_samples(p,&node,offset,std::min(516U,2048-offset));data_frame(p,seq++,0,0,0,0,992);put16(p+6,16);seal(p);fwrite(p,1,992,stdout);}}}}'''
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'packer.cpp';src.write_text(source);exe=src.with_suffix('')
   subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],check=True,capture_output=True)
   out=subprocess.run([str(exe)],check=True,capture_output=True).stdout
   self.assertEqual(len(out),4*992);rows=SingleDecoder().feed(out)
   self.assertEqual([r[1] for r in rows],[i*13%16384 for i in range(2048)])
 def test_tick_contract_does_not_replace_stable(self):
  from monitor.historico.v16.receiver.unoq_acquisition import Configuration
  self.assertEqual(Configuration(14,250000).period,4)
  self.assertEqual(contract.Configuration().period,242)
 def test_actual_single_channel_node_validator(self):
  header=EXP/'arduino/historico/v16/oscilloscope/sketch/node_validation.h'
  source=f'''#include "{header}"\nstruct Pair{{uint16_t ch1,ch2;}};
int main(){{uint16_t adc[2048];uint32_t t[2048];Pair out[2048];
for(unsigned i=0;i<2048;++i){{adc[i]=i;t[i]=0xfffffff0U+i*242U;}}
if(!scope_validation::validate_node<true>(adc,t,2048,14,242,false,0,out))return 1;
for(unsigned i=0;i<2048;++i)if(out[i].ch1!=adc[i]||out[i].ch2)return 2;
t[1024]++;if(scope_validation::validate_node<false>(adc,t,2048,14,242,false,0,out))return 3;
t[1024]--;adc[1024]=16384;if(scope_validation::validate_node<true>(adc,t,2048,14,242,false,0,out))return 4;
}}'''
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'validator.cpp';src.write_text(source);exe=src.with_suffix('')
   subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],check=True,capture_output=True)
   subprocess.run([str(exe)],check=True,capture_output=True)
