"""Real typed decoders retain every check and prevalidate both command halves."""
import subprocess,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=r'''
#include <cstring>
#include <cassert>
#include "benchmark_protocol.h"
#include "acquisition_protocol.h"
#include "generator_protocol.h"
#include "wav_protocol.h"
#include "batch_command.h"
using namespace scope_batch_command;
void make(uint8_t*p,unsigned kind){memset(p,0,992);memcpy(p,"SCP1",4);p[4]=4;p[6]=kind;
 scope_bench::put32(p+8,0x80001234);scope_bench::put32(p+12,972);
 if(kind==6){p[16]=8;scope_bench::put32(p+20,(3488U<<16)|88);}
 if(kind==13){p[24]=1;p[28]=0x34;p[29]=0x02;}
 scope_bench::seal(p);}
int main(){uint8_t batch[1984];Command decoded[2];
 for(unsigned kind: {2U,4U,6U,8U,10U,11U,13U}) {
  make(batch,kind);
  if(kind==2){scope_bench::frame(batch,2,0x80001234);scope_bench::seal(batch);}
  assert(decode(batch,decoded[0]));
  if(kind==10)assert(decoded[0].generator.query);
  if(kind==13){assert(decoded[0].wav.samples==batch+28);assert(decoded[0].wav.count==1);}
  memcpy(batch+992,batch,992);assert(decode_pair(batch,decoded));
  // Corrupt each half independently: caller applies nothing unless pair is valid.
  for(unsigned half=0;half<2;++half){batch[half*992+988]^=1;assert(!decode_pair(batch,decoded));batch[half*992+988]^=1;}
  // Reserved bytes with a valid CRC still fail unchanged field validation.
  batch[987]=1;scope_bench::seal(batch);assert(!decode(batch,decoded[0]));
 }
 make(batch,99);assert(!decode(batch,decoded[0]));return 0;}
'''
class BatchFastTests(unittest.TestCase):
 def test_typed_decoders_all_kinds_and_both_corruptions(self):
  with tempfile.TemporaryDirectory() as name:
   p=Path(name);(p/'test.cpp').write_text('#include <initializer_list>\n'+SOURCE)
   subprocess.run(['c++','-std=c++17','-O2','-fsanitize=address,undefined','-I',str(HERE/'batchfast/oscilloscope/sketch'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
