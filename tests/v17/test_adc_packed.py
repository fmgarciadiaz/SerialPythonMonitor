import unittest,struct,tempfile,subprocess,random
from pathlib import Path
from tests.v16.test_compact_protocol import packet,seal
from monitor.v17.receiver.unoq_config_decoder import ConfigurationDecoder as PackedDecoder
from monitor.v17.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v17.receiver.unoq_usb import ProtocolError
EXP=Path(__file__).resolve().parents[2] / 'arduino/v17'

def extract(path,name):
 s=path.read_text();start=s.index('static void '+name+'(');begin=s.index('{',start);end=begin+1;depth=1
 while depth:
  if s[end]=='{':depth+=1
  elif s[end]=='}':depth-=1
  end+=1
 return s[start:end]

def packed_packet(pairs,index=0,t0=100,seq=0):
 p=bytearray(packet(index=index,count=0,t0=t0,seq=seq));struct.pack_into('<H',p,6,15);struct.pack_into('<H',p,64,len(pairs))
 for i in range(0,len(pairs),2):
  a,b=pairs[i],pairs[i+1];bits=a[0]|(a[1]<<14)|(b[0]<<28)|(b[1]<<42);p[84+i//2*7:91+i//2*7]=bits.to_bytes(7,'little')
 return seal(p)
class PackedTests(unittest.TestCase):
 def test_fixed_profile_compatibility_decoder_accepts_packed(self):
  from monitor.v17.receiver.unoq_usb import Decoder
  p=bytearray(packed_packet([(0,16383)]*258))
  struct.pack_into('<I',p,48,31250);struct.pack_into('<I',p,68,32)
  self.assertEqual(len(Decoder(check_ack_sequence=False).frame(seal(p))),258)

 def test_complete_node_exact_values(self):
  rng=random.Random(14);pairs=[(rng.randrange(16384),rng.randrange(16384)) for _ in range(2048)]
  pairs[:4]=[(0,0),(16383,16383),(0,16383),(16383,0)]
  d=PackedDecoder();rows=[]
  for seq,offset in enumerate(range(0,2048,258)):
   p=packed_packet(pairs[offset:offset+258],offset,100+offset*8,seq);rows.extend(d.feed(p))
  self.assertEqual([(a,b) for _,a,b,_ in rows],pairs)
  self.assertEqual(rows[-1][0],100+2047*8);self.assertEqual(rows[-1][3],2047)
 def test_reject_bad_counts_range_padding_and_legacy_pairing(self):
  p=packed_packet([(0,16383)]*258)
  self.assertEqual(len(ConfigurationDecoder().feed(p)),258)
  for offset,value,fmt in ((64,257,'<H'),(66,12,'<B'),(52,1,'<I'),(987,1,'<B')):
   q=bytearray(p);struct.pack_into(fmt,q,offset,value)
   with self.assertRaises(ProtocolError):PackedDecoder().feed(seal(q))
 def test_crc_clock_and_index_discontinuity(self):
  p=packed_packet([(1,2)]*258);q=bytearray(p);q[150]^=1
  with self.assertRaisesRegex(ProtocolError,'CRC'):PackedDecoder().feed(q)
  for index,t0 in ((260,100+258*8),(258,101+258*8)):
   d=PackedDecoder();d.feed(p)
   with self.assertRaises(ProtocolError):d.feed(packed_packet([(3,4)]*258,index,t0,1))
 def test_native_relay_matches_python(self):
  base=EXP/'relay/base_verifier.c';header=base.with_name('config_relay_protocol.h')
  src=f'''#define main baseline_main\n#include "{base}"\n#undef main\n#include "{header}"\nint main(void){{uint8_t p[BLOCK];init_crc();DualChecker d={{.period=8,.bits=14}};while(fread(p,1,BLOCK,stdin)==BLOCK){{printf("%d\\n",dual_feed(&d,p));}}}}'''
  rng=random.Random(258);pairs=[(rng.randrange(16384),rng.randrange(16384)) for _ in range(2048)]
  frames=[packed_packet(pairs[o:o+258],o,100+o*8,n) for n,o in enumerate(range(0,2048,258))]
  bad=bytearray(frames[-1]);struct.pack_into('<I',bad,8,8);bad[987]=1
  with tempfile.TemporaryDirectory() as folder:
   source=Path(folder)/'checker.c';source.write_text(src);exe=source.with_suffix('')
   built=subprocess.run(['cc','-std=c11','-O2',str(source),'-lm','-o',str(exe)],capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr)
   out=subprocess.run([str(exe)],input=b''.join(frames)+seal(bad),capture_output=True,check=True).stdout
   self.assertEqual(out,b'1\n'*8+b'0\n')
 def test_actual_mcu_packer_matches_original_adc_values(self):
  from monitor.v17.receiver.unoq_config_decoder import ConfigurationDecoder as TransferDecoder
  body=extract(EXP/'oscilloscope/sketch/sketch.ino','build_samples')
  header=EXP/'oscilloscope/sketch/benchmark_protocol.h'
  source=f'''#include "{header}"\n#include <algorithm>\n#include <cstring>\n#include <cstdlib>\n#include <cstdio>\nusing namespace scope_bench;using std::max;
[[maybe_unused]] constexpr unsigned DMA_NODE_PAIRS=2048;struct ChannelPair{{uint16_t ch1,ch2;}};
namespace acquisition {{struct Node{{uint32_t index,timestamp;ChannelPair samples[2048];}};
uint32_t period=8,bits=14,epoch=0,dropped_nodes=0,fatal_errors=0;unsigned node_pairs(){{return 2048;}}bool single(){{return false;}}bool native(){{return false;}}int full_slots=2,empty_slots=1;}}
void build_native_samples(uint8_t*,acquisition::Node*,unsigned,unsigned){{std::abort();}}
uint32_t k_sem_count_get(const int*p){{return *p;}}
struct TransferMetrics {{uint32_t nodes,node_last,node_max,node_sum,frames,prep_sum,setup_sum,wait_sum,check_sum,queued_max,idle_frames;}};

{body}
int main(){{acquisition::Node node{{0,100,{{}}}};if(fread(node.samples,4,2048,stdin)!=2048)return 2;
uint32_t seq=0;for(unsigned offset=0;offset<2048;offset+=258){{unsigned count=std::min(258U,2048-offset);uint8_t p[992];
build_samples(p,&node,offset,count);data_frame(p,seq++,0,0,0,0,992);put16(p+6,15);seal(p);fwrite(p,1,992,stdout);
}}return 0;}}'''
  rng=random.Random(1024);pairs=[(rng.randrange(16384),rng.randrange(16384)) for _ in range(2048)]
  pairs[:4]=[(0,0),(16383,16383),(0,16383),(16383,0)]
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'packer.cpp';src.write_text(source);exe=src.with_suffix('')
   built=subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr)
   data=subprocess.run([str(exe)],input=b''.join(struct.pack('<HH',*p) for p in pairs),capture_output=True,check=True).stdout
   self.assertEqual(len(data),8*992)
   rows=TransferDecoder().feed(data)
   self.assertEqual([(a,b) for _,a,b,_ in rows],pairs)
   self.assertEqual(rows[-1][3],2047)

class RateContractTests(unittest.TestCase):
 def test_three_microsecond_configuration_reply(self):
  from monitor.v17.receiver.unoq_acquisition import acquisition_reply,Configuration
  p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,7,0,972)
  struct.pack_into('<I4BIII',p,16,0x80000001,14,14,2,0,3,3,1)
  self.assertEqual(acquisition_reply(seal(p)).active,Configuration(14,333333))
  self.assertEqual(Configuration(14,333333).period,3)
  for period in (0,7,9):
   q=bytearray(p);struct.pack_into('<I',q,28,period)
   with self.assertRaises(ProtocolError):acquisition_reply(seal(q))
  with self.assertRaises(ValueError):Configuration(16,333333)
