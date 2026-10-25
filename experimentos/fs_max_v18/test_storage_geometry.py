"""Exercise real storage binding and all eight node boundaries under sanitizers."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROGRAM=r'''
#include <cstdint>
#include <cstdio>
#include <cassert>
constexpr unsigned SERIAL_BLOCK_PAIRS=512;
#include "acquisition_storage.h"
int main(){
 scope_storage::Storage storage;storage.bind(true,8,PAIRS);
 for(unsigned i=0;i<8;++i){
  auto *samples=storage.at(i,8).single_samples;
  for(unsigned j=0;j<PAIRS;++j)samples[j].ch1=uint16_t(i*1000+j);
 }
 for(unsigned i=0;i<8;++i)for(unsigned j=0;j<PAIRS;++j)
  assert(storage.at(i,8).single_samples[j].ch1==uint16_t(i*1000+j));
 static_assert(PAIRS*2U*sizeof(uint32_t)+1984U<=sizeof(scope_storage::SingleMemory::timestamps));
 std::printf("%zu\n",sizeof(storage));
}
'''
class StorageGeometryTests(unittest.TestCase):
 def test_full_payload_preserves_storage_size_and_node_ownership(self):
  with tempfile.TemporaryDirectory() as name:
   folder=Path(name);source=folder/'storage.cpp';source.write_text(PROGRAM);sizes=[]
   for variant,pairs in (('',3456),('full8',3488)):
    include=ROOT/variant/'oscilloscope/sketch';binary=folder/f'storage{pairs}'
    subprocess.run(['c++','-std=c++17','-fsanitize=address,undefined',f'-DPAIRS={pairs}',
                    '-I',str(include),str(source),'-o',str(binary)],check=True)
    sizes.append(int(subprocess.check_output([str(binary)])))
   self.assertEqual(sizes[0],sizes[1])
if __name__=='__main__':unittest.main()
