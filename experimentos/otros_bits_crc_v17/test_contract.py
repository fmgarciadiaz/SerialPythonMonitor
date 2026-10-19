"""Real C packers -> strict C relay and Python decoder for candidate formats."""
import json,struct,subprocess,tempfile,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from monitor.v17.receiver import unoq_native
from monitor.v17.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v17.receiver.unoq_usb import ProtocolError
HERE=Path(__file__).resolve().parent
PACK=r'''
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cassert>
#include "sample_packing.h"
struct Sample {uint16_t ch1;};
int main(int argc,char**argv){assert(argc==3);unsigned bits=std::atoi(argv[1]),n=std::atoi(argv[2]);
 Sample values[8192];const uint32_t mask=(1U<<bits)-1;
 for(unsigned i=0;i<n;++i)values[i].ch1=i<4?(i==0?0:i==1?mask:i==2?1:mask/2):((i*12345U+7)&mask);
 const unsigned capacity=(872U*8U/bits)&~3U;
 for(unsigned offset=0;offset<n;offset+=capacity){const unsigned count=n-offset<capacity?n-offset:capacity;
 uint8_t out[872];std::memset(out,0xcc,sizeof out);const unsigned used=maxfreq_packing::pack(out,values+offset,count,bits);
 assert(used==count*bits/8);for(unsigned i=used;i<sizeof out;++i)assert(out[i]==0xcc);
 assert(std::fwrite(out,1,used,stdout)==used);}}
'''
CHECK=r'''
#define main base_main
#include "base_verifier.c"
#undef main
#include "config_relay_protocol.h"
int main(int argc,char**argv){if(argc!=4)return 2;init_crc();DualChecker d={0};d.bits=atoi(argv[1]);d.period=strtoul(argv[2],0,10);d.epoch=0;
 uint8_t frame[992];while(fread(frame,1,992,stdin)==992)if(!dual_feed(&d,frame))return 3;
 return d.adc.sample_pairs==strtoull(argv[3],0,10)?0:4;}
'''
class CandidateFormatTests(unittest.TestCase):
 def test_exact_values_timestamp_wrap_and_padding_all_resolutions(self):
  profiles=json.loads((HERE/'candidate_profiles.json').read_text())
  with tempfile.TemporaryDirectory() as name:
   folder=Path(name);src=folder/'pack.cpp';src.write_text(PACK);pack=folder/'pack'
   subprocess.run(['c++','-O2','-std=c++17','-fsanitize=address,undefined','-I',str(HERE/'oscilloscope/sketch'),str(src),'-o',str(pack)],check=True)
   src=folder/'checker.c';src.write_text(CHECK);checker=folder/'checker'
   subprocess.run(['cc','-O2','-std=c11','-I',str(HERE/'relay'),str(src),'-lm','-o',str(checker)],check=True)
   for profile in profiles:
    bits,n,ticks=profile['bits'],profile['node_pairs'],profile['ticks'];mask=(1<<bits)-1
    raw=subprocess.check_output([str(pack),str(bits),str(n)]);expected=[0,mask,1,mask//2]+[(i*12345+7)&mask for i in range(4,n)]
    capacity=(872*8//bits)&~3;frames=[]
    for seq,offset in enumerate(range(0,n,capacity)):
     count=min(capacity,n-offset);frame=bytearray(992)
     struct.pack_into('<4sHHII',frame,0,b'SCP1',4,20,seq,972);struct.pack_into('<i',frame,32,992)
     struct.pack_into('<IIIIHBBIII',frame,48,160000000//ticks,offset,0,0,count,bits,1,ticks,0,0)
     struct.pack_into('<I',frame,80,(0xffffff00+offset*ticks)&0xffffffff)
     struct.pack_into('<8I',frame,84,n,1,2,100,100,100,100,1)
     used=count*bits//8;start=offset*bits//8;frame[116:116+used]=raw[start:start+used]
     struct.pack_into('<I',frame,988,zlib.crc32(frame[:988]));frames.append(bytes(frame))
    wire=b''.join(frames);encoded=(n<<16)|ticks
    subprocess.run([str(checker),str(bits),str(encoded),str(n)],input=wire,check=True)
    with patch.object(unoq_native,'PROFILES',tuple(profiles)):
     for numeric in (False,True):
      decoder=ConfigurationDecoder();decoder.numeric=numeric;records=decoder.feed(wire)
      self.assertEqual([r[1] for r in records],expected)
      self.assertEqual(records[-1][0],(0xffffff00+(n-1)*ticks)&0xffffffff)
     damaged=bytearray(frames[-1])
     if bits==16:struct.pack_into('<H',damaged,64,capacity+4)
     else:damaged[987]=1
     # Reject oversized full 16-bit frames and corrupted padding in others.

     struct.pack_into('<I',damaged,988,zlib.crc32(damaged[:988]))
     with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(bytes(damaged))
     self.assertNotEqual(subprocess.run([str(checker),str(bits),str(encoded),str(n)],input=wire[:-992]+damaged).returncode,0)
if __name__=='__main__':unittest.main()
