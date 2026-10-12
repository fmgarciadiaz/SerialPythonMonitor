import unittest,tempfile,subprocess
from pathlib import Path
EXP=Path(__file__).resolve().parent

def extract(path,name):
 s=path.read_text();start=s.index('static void '+name+'(');begin=s.index('{',start);end=begin+1;depth=1
 while depth:
  if s[end]=='{':depth+=1
  elif s[end]=='}':depth-=1
  end+=1
 return s[start:end]
class FrameTests(unittest.TestCase):
 def test_optimized_padding_produces_identical_wire_frames(self):
  old=extract(EXP/'baseline_sketch/sketch.ino','build_samples').replace('build_samples(','build_old(',1)
  new=extract(EXP/'fast8_sketch/sketch.ino','build_samples').replace('build_samples(','build_new(',1)
  header=EXP/'arduino/v16/oscilloscope/sketch/benchmark_protocol.h'
  source=f'''#include "{header}"\n#include <algorithm>\n#include <cstring>\nusing namespace scope_bench;using std::max;
constexpr unsigned DMA_NODE_PAIRS=2048;
struct Pair{{uint16_t ch1,ch2;}};using ChannelPair=Pair;
namespace acquisition {{struct Node{{uint32_t index,timestamp;Pair samples[2048];}};
uint32_t period=3,bits=14,epoch=2,dropped_nodes=0,fatal_errors=0;int full_slots=2,empty_slots=1;}}
uint32_t k_sem_count_get(const int*p){{return *p;}}
struct TransferMetrics {{uint32_t nodes,node_last,node_max,node_sum,frames,prep_sum,setup_sum,wait_sum,check_sum,queued_max,idle_frames;}};
static TransferMetrics transfer_metrics{{}};
{old}
{new}
int main(){{acquisition::Node node{{123,0xffffffe0U,{{}}}};
for(unsigned i=0;i<2048;++i)node.samples[i]={{uint16_t(i*7%16384),uint16_t(i*11%16384)}};
for(unsigned period:{{3,4,8,32}}){{
 for(unsigned count:{{0,1,14,113,226}}){{
  for(unsigned offset:{{0,113,2034}}){{
 if(offset+count>2048)continue;acquisition::period=period;
 uint8_t a[992],b[992];memset(a,0x55,992);memset(b,0xaa,992);
 transfer_metrics={{}};build_old(a,count?&node:nullptr,offset,count);
 transfer_metrics={{}};build_new(b,count?&node:nullptr,offset,count);
 data_frame(a,45,44,0,0,0,992,0,99,100);data_frame(b,45,44,0,0,0,992,0,99,100);
 put16(a+6,3);put16(b+6,3);seal(a);seal(b);if(memcmp(a,b,992))return 1;
  }}
 }}
}}
return 0;}}'''
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'frames.cpp';src.write_text(source);exe=src.with_suffix('')
   result=subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   subprocess.run([str(exe)],check=True,capture_output=True)
