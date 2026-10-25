"""CRC differential checks against zlib, including every tail and alignment."""
import ctypes,json,subprocess,tempfile,time,unittest,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
WRAPPER='''
#define main verifier_main
#include "base_verifier.c"
#undef main
uint32_t calculate(const uint8_t *p,size_t n){return crc32(p,n);}
void initialize(void){init_crc();}
uint32_t timed(unsigned count){uint8_t p[988];uint32_t c=0;memset(p,0x5a,sizeof p);
 for(unsigned i=0;i<count;++i){put32(p+8,i);c^=crc32(p,sizeof p);}return c;}
'''
def build(folder,recipe):
    src=folder/(recipe+'.c');src.write_text(WRAPPER);lib=folder/(recipe+'.so')
    subprocess.run(['cc','-O2','-std=c11','-shared','-fPIC','-I',str(HERE/recipe/'relay'),str(src),'-lm','-o',str(lib)],check=True)
    dll=ctypes.CDLL(str(lib));dll.initialize()
    dll.calculate.argtypes=[ctypes.c_void_p,ctypes.c_size_t];dll.calculate.restype=ctypes.c_uint32
    dll.timed.argtypes=[ctypes.c_uint];dll.timed.restype=ctypes.c_uint32
    return dll
class CrcTests(unittest.TestCase):
 def test_all_lengths_alignments_and_corruption(self):
    with tempfile.TemporaryDirectory() as name:
      lib=build(Path(name),'crc8')
      data=bytes((i*73+(i>>3)*19)&255 for i in range(4104));buf=ctypes.create_string_buffer(data)
      for offset in range(8):
       for length in range(4097):
        self.assertEqual(lib.calculate(ctypes.addressof(buf)+offset,length),zlib.crc32(data[offset:offset+length]),(offset,length))
      # Every bit of a full 988-byte frame must still affect the CRC.
      original=data[:988];expected=zlib.crc32(original)
      for bit in range(988*8):
       changed=bytearray(original);changed[bit//8]^=1<<(bit%8)
       self.assertNotEqual(lib.calculate(ctypes.create_string_buffer(bytes(changed)),988),expected)

def benchmark():
 with tempfile.TemporaryDirectory() as name:
    libs={r:build(Path(name),r) for r in ('full8','crc8')};result={}
    for recipe,lib in libs.items():
     runs=[]
     for _ in range(5):
      start=time.perf_counter();checksum=lib.timed(200000);runs.append(time.perf_counter()-start)
     result[recipe]=dict(seconds=runs,checksum=checksum,us_per_frame=min(runs)*1e6/200000)
    assert result['full8']['checksum']==result['crc8']['checksum']
    result['speedup']=result['full8']['us_per_frame']/result['crc8']['us_per_frame']
    return result
if __name__=='__main__':
 import sys
 if '--benchmark' in sys.argv:print(json.dumps(benchmark(),indent=2))
 else:unittest.main()
