"""Isolated ADC16 CH1 C pack -> production strict decoder, no Q access."""
import struct,subprocess,tempfile,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from monitor.v17.receiver import unoq_native
from monitor.v17.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v17.receiver.unoq_usb import ProtocolError
HERE=Path(__file__).resolve().parent
class FormatTests(unittest.TestCase):
 def test_c_pack_full_node_tail_wrap_and_corruption(self):
  code='''#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cassert>
#include "sample_packing.h"
struct Sample {uint16_t ch1;};
int main(){
 Sample samples[3456];
 for(unsigned i=0;i<3456;++i)samples[i].ch1=i<4?(i==0?0:i==1?65535:i==2?1:32768):uint16_t(i*12345U);
 for(unsigned offset=0;offset<3456;offset+=436){
  unsigned count=3456-offset;if(count>436)count=436;
  uint8_t out[872];memset(out,0xcc,sizeof out);
  unsigned used=maxfreq_packing::pack(out,samples+offset,count,16);
  assert(used==count*2);
  for(unsigned i=used;i<sizeof out;++i)assert(out[i]==0xcc);
  assert(fwrite(out,1,used,stdout)==used);
 }
}
'''
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'pack.cpp';src.write_text(code);exe=Path(d)/'pack'
   subprocess.run(['c++','-std=c++17','-fsanitize=address,undefined','-I',str(HERE),str(src),'-o',str(exe)],check=True)
   raw=subprocess.check_output([str(exe)])
  expected=[0,65535,1,32768]+[(i*12345)&65535 for i in range(4,3456)]
  self.assertEqual(list(struct.unpack('<3456H',raw)),expected)
  profile={'bits':16,'channels':1,'ticks':1050,'node_pairs':3456}
  for numeric in (False,True):
   decoder=ConfigurationDecoder();decoder.numeric=numeric;rows=[]
   with patch.object(unoq_native,'PROFILES',(profile,)):
    for seq,offset in enumerate(range(0,3456,436)):
     count=min(436,3456-offset);p=bytearray(992)
     struct.pack_into('<4sHHII',p,0,b'SCP1',4,20,seq,972);struct.pack_into('<i',p,32,992)
     struct.pack_into('<IIIIHBBIII',p,48,160000000//1050,offset,0,0,count,16,1,1050,0,0)
     struct.pack_into('<I',p,80,(0xffffff00+offset*1050)&0xffffffff)
     struct.pack_into('<8I',p,84,3456,1,2,100,100,100,100,1)
     p[116:116+count*2]=raw[offset*2:(offset+count)*2]
     struct.pack_into('<I',p,988,zlib.crc32(p[:988]));rows.extend(decoder.feed(bytes(p)))
    self.assertEqual([r[1] for r in rows],expected)
    self.assertEqual(rows[-1][0],(0xffffff00+3455*1050)&0xffffffff)
    self.assertTrue(all(r[2]==0 for r in rows))
    self.assertEqual(len(ConfigurationDecoder().feed(bytes(p))),count)
    p[987]=1;struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
    with self.assertRaisesRegex(ProtocolError,'Padding ADC'):ConfigurationDecoder().feed(bytes(p))
if __name__=='__main__':unittest.main()
