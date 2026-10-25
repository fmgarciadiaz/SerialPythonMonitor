"""Bounded failure trace must preserve the newest metadata in physical order."""
import subprocess,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
class TraceTests(unittest.TestCase):
 def test_wrap_preserves_only_last_64_frames(self):
  self.check_recipe('trace8')
 def test_timing_variant_preserves_order_and_time_components(self):
  self.check_recipe('trace8time')
 def check_recipe(self,recipe):
  source=(HERE/recipe/'relay/unoq_config_stream.c').read_text()
  code=source[source.index('struct ScopeTrace {'):source.index('static volatile sig_atomic_t')]
  harness=r'''
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
static uint32_t get32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static unsigned get16(const uint8_t*p){return p[0]|(unsigned)p[1]<<8;}
static double now(void){static double t=100;return t+=.0002;}
static void put32(uint8_t*p,uint32_t v){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(v>>(8*i));}
'''+code+r'''
int main(void){uint8_t tx[992]={0},rx[992]={0};
 for(unsigned i=0;i<70;++i){tx[6]=i%3?2:13;rx[6]=20;put32(rx+8,i);put32(rx+52,i*872);put32(rx+88,i%8);trace8_record(tx,rx);}
 trace8_dump();return 0;}
'''
  if recipe=='trace8time':
   harness=harness.replace('trace8_record(tx,rx);','double t=now();trace8_record(tx,rx,t-.0001,t-.00008,t-.00007,t);')
   harness=harness.replace('trace8_dump();return','trace8_summary();trace8_dump();return')
  with tempfile.TemporaryDirectory() as name:
   p=Path(name);(p/'trace.c').write_text(harness)
   subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(p/'trace.c'),'-o',str(p/'trace')],check=True)
   output=subprocess.run([str(p/'trace')],capture_output=True,text=True,check=True).stderr.splitlines()
  if recipe=='trace8time':
   summary=output.pop(0)
   self.assertIn('data=64 audio=0 chunks=22',summary)
   self.assertIn('mean_gap_us=200.000 max_gap_us=200.000 mean_wait_us=20.000 mean_io_us=70.000',summary)
  self.assertEqual(len(output),65)
  self.assertIn('seq=6 tx=13 rx=20',output[1]);self.assertIn('seq=69 tx=13 rx=20',output[-1])
  if recipe=='trace8time':
   self.assertIn('wait_us=20.000 io_us=70.000',output[-1])
  self.assertIn('gap_us=200.000',output[-1]);self.assertIn('index=60168',output[-1])
if __name__=='__main__':unittest.main()
