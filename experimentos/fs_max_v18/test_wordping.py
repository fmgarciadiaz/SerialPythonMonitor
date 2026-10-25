"""Validate optimized PING against original wire format and all payload bits."""
import ctypes,json,struct,subprocess,tempfile,time,unittest,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE='''
#include "benchmark_protocol.h"
extern "C" int validate(const uint8_t *p){return scope_bench::valid_ping(p);}
extern "C" unsigned timed(unsigned count){alignas(32) uint8_t p[992];unsigned result=0;
 scope_bench::frame(p,scope_bench::PING,1234567);scope_bench::seal(p);
 for(unsigned i=0;i<count;++i){asm volatile("" : : "r"(p) : "memory");result+=scope_bench::valid_ping(p);}return result;}
'''
def build(folder,recipe):
 p=folder/(recipe+'.cpp');p.write_text(SOURCE);out=folder/(recipe+'.so')
 subprocess.run(['c++','-O2','-std=c++17','-shared','-fPIC','-I',str(HERE/recipe/'oscilloscope/sketch'),str(p),'-o',str(out)],check=True)
 lib=ctypes.CDLL(str(out));lib.validate.argtypes=[ctypes.c_void_p];lib.validate.restype=ctypes.c_int
 lib.timed.argtypes=[ctypes.c_uint];lib.timed.restype=ctypes.c_uint
 return lib

def ping(seq):
 seed=(seq*0x9e3779b1)&0xffffffff
 p=bytearray(struct.pack('<4sHHII',b'SCP1',4,2,seq,972))
 p.extend(((seed>>(8*(i&3)))^(i*17+0x5a))&255 for i in range(972))
 p.extend(struct.pack('<I',zlib.crc32(p)));return p
class WordPingTests(unittest.TestCase):
 def test_reference_format_alignment_and_all_payload_bits(self):
  with tempfile.TemporaryDirectory() as name:
   libs=[build(Path(name),r) for r in ('full8','wordping','alignedping')]
   def check(p,expected):
    for offset in range(4):
     buf=ctypes.create_string_buffer(b'X'*offset+bytes(p))
     for lib in libs:self.assertEqual(lib.validate(ctypes.addressof(buf)+offset),expected)
   for seq in (0,1,127,255,256,65535,0x7fffffff,0x80000000,0xffffffff):check(ping(seq),1)
   for bit in range(972*8):
    p=ping(0x12345678);p[16+bit//8]^=1<<(bit%8)
    # Reseal so rejection proves the pattern check, rather than CRC alone.
    struct.pack_into('<I',p,988,zlib.crc32(p[:988]));check(p,0)
   p=ping(123);p[988]^=1;check(p,0)

def benchmark():
 with tempfile.TemporaryDirectory() as name:
  result={}
  for r in ('full8','wordping','alignedping'):
   lib=build(Path(name),r);runs=[]
   for _ in range(3):
    start=time.perf_counter();assert lib.timed(100000)==100000;runs.append(time.perf_counter()-start)
   result[r]=dict(seconds=runs,us_per_frame=min(runs)*10)
  return result
if __name__=='__main__':
 import sys
 if '--benchmark' in sys.argv:print(json.dumps(benchmark(),indent=2))
 else:unittest.main()
