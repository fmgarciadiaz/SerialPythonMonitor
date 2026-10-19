"""Independent normal-polynomial peripheral model vs zlib and software CRC."""
import random,subprocess,tempfile,zlib,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CODE=r'''
#include <cstdint>
#include <cstdio>
#include <vector>
#include "crc32_fast.h"
uint32_t reverse(uint32_t n){uint32_t r=0;for(unsigned i=0;i<32;++i){r=(r<<1)|(n&1);n>>=1;}return r;}
struct Model {
 uint32_t crc;
 void begin(){crc=0xffffffffU;}
 void feed(uint32_t word){word=reverse(word);for(unsigned i=0;i<32;++i){const bool top=(crc>>31)^(word>>31);crc<<=1;if(top)crc^=0x04c11db7U;word<<=1;}}
 uint32_t read()const{return reverse(crc);}
};
int main(){unsigned n,offset;while(std::scanf("%u %u",&n,&offset)==2){
 std::vector<uint8_t> bytes(n+offset);for(unsigned i=0;i<n;++i){unsigned v;if(std::scanf("%u",&v)!=1)return 2;bytes[offset+i]=uint8_t(v);}
 Model model;const auto *p=bytes.data()+offset;
 const auto crc=scope_crc_fast::words(model,p,n);
 if(crc!=scope_crc_fast::software(p,n)||crc!=scope_crc_fast::compute(p,n))return 3;
 std::printf("%u\n",crc);
}}
'''
class CrcWordsTests(unittest.TestCase):
 def test_every_word_length_and_unaligned_memory_matches_zlib(self):
  rng=random.Random(417);cases=[]
  for n in range(0,1000,4):
   data=bytes(rng.randrange(256) for _ in range(n));cases.append((n,n%7,data))
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'crc.cpp';exe=Path(folder)/'crc';src.write_text(CODE)
   subprocess.run(['c++','-O2','-fsanitize=address,undefined','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'experimentos/radio_dac_headroom_v17/oscilloscope/sketch'),str(src),'-o',str(exe)],check=True)
   text=''.join(f'{n} {offset} '+' '.join(map(str,data))+'\n' for n,offset,data in cases)
   result=subprocess.run([str(exe)],input=text,text=True,capture_output=True,check=True)
  self.assertEqual([int(x) for x in result.stdout.split()],[zlib.crc32(data) for _,_,data in cases])
if __name__=='__main__':unittest.main()
