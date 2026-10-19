import subprocess
import tempfile
import unittest
from pathlib import Path

class OwnershipTests(unittest.TestCase):
    def test_node_reuse_preserves_pending_frames_and_physical_send_timing(self):
        folder=Path(__file__).parent/'arduino/v16/oscilloscope/sketch'
        source=(folder/'acquisition.h').read_text()
        functions=source[source.index('static void release_copied()'):source.index('static bool start()')]
        code='''#include <stdint.h>
#include <assert.h>
#include <string.h>
struct Sample {uint16_t ch1;};
unsigned consumer_slot=3;constexpr unsigned QUEUE_SLOTS=4;
unsigned empty_slots=0;uint32_t send_previous=17,consumer_started=100,cycle=200;
static void k_sem_give(unsigned*p){++*p;}
static uint32_t k_cycle_get_32(){return cycle;}
'''+ '#include "'+str((folder/'sample_packing.h').resolve())+'"\n'+functions+'''
int main(){
 Sample node[3456];uint8_t frames[4][864];
 for(unsigned i=0;i<3456;++i)node[i].ch1=i%256;
 for(unsigned i=0;i<4;++i)maxfreq_packing::pack(frames[i],node+i*864,864,8);
 release_copied();assert(empty_slots==1 && consumer_slot==0);
 assert(send_previous==17); // Memory release must not shorten physical timing.
 memset(node,0xff,sizeof node); // Producer overwrites a newly available slot.
 for(unsigned i=0;i<3456;++i)assert(frames[i/864][i%864]==i%256);
 cycle=900;finish_send();assert(send_previous==800);
 assert(empty_slots==1 && consumer_slot==0); // No double release at send completion.
 consumer_started=1000;cycle=1500;release();
 assert(empty_slots==2 && consumer_slot==1 && send_previous==500);
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.cpp';p.write_text(code);binary=Path(d)/'test'
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True,capture_output=True)

if __name__=='__main__':unittest.main()
