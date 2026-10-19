import subprocess,tempfile,unittest
from pathlib import Path
class ADC1600StorageTests(unittest.TestCase):
    def test_repartition_preserves_samples_dma_and_legacy_layout(self):
        root=Path(__file__).resolve().parents[2]/'arduino/v17/oscilloscope/sketch'
        code='constexpr unsigned SERIAL_BLOCK_PAIRS=512;\n#include "'+str(root/'acquisition_storage.h')+'"\n'+r'''
#include <cassert>
#include <cstring>
int main(){
 scope_storage::Storage s;
 s.bind(true,8,3456);
 memset(s.adc,0x55,sizeof(scope_storage::SingleMemory::adc));
 memset(s.timestamps,0x77,sizeof(scope_storage::SingleMemory::timestamps));
 for(unsigned i=0;i<8;++i){
  assert(s.at(i,8).single_samples==s.memory.single.fast.samples[i]);
  for(unsigned j=0;j<3456;++j)s.at(i,8).single_samples[j].ch1=i*100+j;
 }
 for(unsigned i=0;i<8;++i)for(unsigned j=0;j<3456;++j)
  assert(s.at(i,8).single_samples[j].ch1==i*100+j);
 for(unsigned i=0;i<sizeof(scope_storage::SingleMemory::adc)/2;++i)assert(s.adc[i]==0x5555);
 for(unsigned i=0;i<sizeof(scope_storage::SingleMemory::timestamps)/4;++i)assert(s.timestamps[i]==0x77777777);
 s.bind(false);
 for(unsigned i=0;i<4;++i)assert(s.queue[i].samples==s.memory.dual.samples[i]);
 s.bind(true);
 for(unsigned i=0;i<4;++i)assert(s.queue[i].single_samples==s.memory.single.samples+i*SCOPE_NATIVE_MAX_SINGLE);
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.cpp';p.write_text(code);exe=Path(d)/'test'
            subprocess.run(['c++','-std=c++17','-fsanitize=address,undefined',str(p),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([str(exe)],check=True,capture_output=True)
if __name__=='__main__':unittest.main()
